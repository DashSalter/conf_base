import copy
import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, Optional, Tuple

from .cipher import BaseCipher, NoCipher
from .error import DecryptError, ParseError
from .format import BaseFormat, JsonFormat

"""
配置文件管理器：管理配置数据的读写操作。

每个配置类拥有独立的 ConfigFile 实例，互不干扰。存储由两个正交的部分组成：
- format: dict <-> 文本（JsonFormat / YamlFormat / TomlFormat）
- cipher: 文本 <-> 文本（NoCipher / AesGcmCipher / SignedCipher ...）

多线程防护：threading.RLock（内置，始终生效）
多进程防护：filelock（可选依赖，pip install filelock）
"""

# filelock 是可选依赖，没有就跳过文件锁保护
try:
    from filelock import FileLock, Timeout as FileLockTimeout  # noqa: F401

    _FILELOCK_AVAILABLE = True
except ImportError:
    _FILELOCK_AVAILABLE = False


class ConfigFile:
    """配置文件管理器：读写、批量落盘、schema 迁移、并发安全。"""

    def __init__(self, path: str,
                 format: Optional[BaseFormat] = None,
                 cipher: Optional[BaseCipher] = None,
                 auto_reload: bool = False,
                 target_version: int = 1,
                 migrations: Optional[Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]]] = None,
                 use_file_lock: bool = True,
                 lock_timeout: float = 10.0) -> None:
        self._lock = threading.RLock()
        self._dirty: bool = False
        self._batch_depth: int = 0
        self.config: Dict[str, Any] = {}

        if not isinstance(path, str) or not path:
            raise TypeError('path 必须是非空字符串')
        self.file_path: str = path
        self.encoding: str = 'utf-8'

        if format is not None and not isinstance(format, BaseFormat):
            raise TypeError(f"类型 {type(format).__name__} 未实现 BaseFormat 协议")
        self.format: BaseFormat = JsonFormat() if format is None else format

        if cipher is not None and not isinstance(cipher, BaseCipher):
            raise TypeError(f"类型 {type(cipher).__name__} 未实现 BaseCipher 协议")
        self.cipher: BaseCipher = NoCipher() if cipher is None else cipher

        if not isinstance(auto_reload, bool):
            raise TypeError('auto_reload is not bool')
        self.auto_reload: bool = auto_reload

        if not isinstance(target_version, int):
            raise TypeError('target_version 必须是 int 类型')
        if target_version < 1:
            raise ValueError('target_version 必须 >= 1')
        self._target_version: int = target_version
        self._migrations: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = migrations or {}

        # 文件锁（多进程防护）
        self._use_file_lock: bool = use_file_lock
        self._lock_timeout: float = lock_timeout
        self._file_lock: Optional['FileLock'] = None

        # 最近一次加载/写入时的文件指纹 (mtime_ns, size)，用于 auto_reload 跳过无变化的磁盘读取
        self._loaded_signature: Optional[Tuple[int, int]] = None
        self._file_lock_setup()
        self.load_config()

    def _file_lock_setup(self) -> None:
        """初始化文件锁。filelock 不可用时跳过，use_file_lock=False 也跳过。"""
        if not self._use_file_lock:
            return
        if not _FILELOCK_AVAILABLE:
            return  # 可选依赖未安装，静默跳过
        self._file_lock = FileLock(self.file_path + '.lock', timeout=self._lock_timeout)

    def _mark_dirty(self) -> None:
        """标记内存数据已修改；批量模式下延迟落盘，否则立即落盘。"""
        self._dirty = True
        if self._batch_depth == 0:
            self.write_config()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """独占锁上下文：把多次读改写合成一个原子操作（同线程可重入）。"""
        with self._lock:
            yield

    @contextmanager
    def batch(self) -> Iterator['ConfigFile']:
        """批量修改上下文：期间所有修改只写内存，退出时一次性落盘。

        具备事务语义：最外层进入时保存快照，块内抛异常时恢复内存数据，
        不会把半批修改落盘；嵌套 batch 由最外层统一提交或回滚。
        """
        snapshot: Optional[Dict[str, Any]] = None
        dirty_before: bool = False
        with self._lock:
            outermost = self._batch_depth == 0
            if outermost:
                snapshot = copy.deepcopy(self.config)
                dirty_before = self._dirty
            self._batch_depth += 1
        try:
            yield self
        except BaseException:
            with self._lock:
                self._batch_depth -= 1
                if outermost and snapshot is not None:
                    self.config = snapshot
                    self._dirty = dirty_before
            raise
        else:
            with self._lock:
                self._batch_depth -= 1
                if self._batch_depth == 0 and self._dirty:
                    self.write_config()

    def save(self) -> None:
        """显式将未落盘的修改写入文件。"""
        with self._lock:
            if self._dirty:
                self.write_config()

    @contextmanager
    def _acquire_file_lock(self) -> Iterator[None]:
        """获取文件锁上下文。filelock 不可用或关闭时退化为 no-op。"""
        if self._file_lock is not None:
            try:
                with self._file_lock:
                    yield
            except FileLockTimeout as e:
                raise TimeoutError(
                    f"等待配置文件锁超时（{self._lock_timeout}s）: {self.file_path}"
                ) from e
        else:
            yield

    def _stat_signature(self) -> Optional[Tuple[int, int]]:
        """返回文件指纹 (mtime_ns, size)；文件不存在时返回 None。"""
        try:
            st = os.stat(self.file_path)
        except FileNotFoundError:
            return None
        return (st.st_mtime_ns, st.st_size)

    def load_config(self) -> None:
        """从文件加载配置到内存，自动执行 schema 迁移。

        先用文件指纹 (mtime_ns, size) 判断是否需要真正读取：未变化时直接返回，
        避免 auto_reload 每次取值都付出文件锁与解析开销。
        """
        signature = self._stat_signature()
        if signature is not None and signature == self._loaded_signature:
            return
        with self._acquire_file_lock():
            # 加锁后复查，避免检查与加锁之间文件被其他进程替换
            signature = self._stat_signature()
            if signature is not None and signature == self._loaded_signature:
                return
            try:
                with open(self.file_path, 'r', encoding=self.encoding) as f:
                    content = f.read()
            except FileNotFoundError:
                self.config = {'_schema_version': self._target_version}
                self.write_config()
                return

            try:
                plain = self.cipher.decrypt(content)
            except DecryptError:
                raise
            except Exception as e:
                raise DecryptError(
                    f"配置文件 '{self.file_path}' 解密失败: {e}"
                ) from e

            try:
                data = self.format.deserialize(plain)
            except Exception as e:
                raise ParseError(
                    f"配置文件 '{self.file_path}' 无法解析，请检查文件内容格式是否正确。"
                    f"原始错误: {e}"
                ) from e
            if not isinstance(data, dict):
                raise ParseError(
                    f"配置文件 '{self.file_path}' 的根节点必须是字典，"
                    f"实际为 {type(data).__name__}"
                )
            self.config = data
            self._loaded_signature = signature

            self._run_migrations()

    def _run_migrations(self) -> None:
        """执行 schema 版本迁移链。"""
        current = self.config.get('_schema_version', 1)
        if isinstance(current, bool) or not isinstance(current, int):
            raise ParseError(
                f"配置文件 '{self.file_path}' 的 _schema_version 必须是整数，"
                f"实际为 {type(current).__name__}，请修正文件内容。"
            )
        need_write_back: bool = False

        # 版本号相同或文件版本更高，不需要迁移
        if current >= self._target_version:
            # 确保目标版本号写回（用户可能手动改过文件）
            if self.config.get('_schema_version') != self._target_version:
                self.config['_schema_version'] = self._target_version
                need_write_back = True
        else:
            v = current
            while v < self._target_version:
                if v not in self._migrations:
                    raise ValueError(
                        f"schema 迁移缺失: 从 v{v} → v{v + 1} 的迁移函数未找到 "
                        f"（目标版本 v{self._target_version}）"
                    )
                self.config = self._migrations[v](self.config)
                v += 1
            self.config['_schema_version'] = self._target_version
            need_write_back = True

        if need_write_back:
            self.write_config()

    def write_config(self) -> None:
        """将内存配置写入文件（线程锁 + 文件锁双重保护）"""
        with self._lock:  # 线程间互斥
            with self._acquire_file_lock():  # 进程间互斥
                if not isinstance(self.config, dict):
                    raise ValueError(f"配置数据类型异常，期望 dict，实际 {type(self.config).__name__}")

                content = self.cipher.encrypt(self.format.serialize(self.config))
                directory = os.path.dirname(self.file_path)
                if directory:
                    os.makedirs(directory, exist_ok=True)

                temp_file = self.file_path + '.tmp'
                try:
                    with open(temp_file, 'w', encoding=self.encoding) as f:
                        f.write(content)
                    self._replace_with_retry(temp_file, self.file_path)
                except Exception:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    raise

                self._loaded_signature = self._stat_signature()
                self._dirty = False

    @staticmethod
    def _replace_with_retry(src: str, dst: str, attempts: int = 5,
                            delay: float = 0.02) -> None:
        """Windows 上杀毒软件/索引服务可能短暂占用目标文件导致 os.replace 失败，做有限重试。"""
        for attempt in range(attempts):
            try:
                os.replace(src, dst)
                return
            except PermissionError:
                if attempt == attempts - 1:
                    raise
                time.sleep(delay)

    # ------------------------------------------------------------------ #
    #  配置项操作
    def set_option(self, section: str, option: str, value: Any) -> None:
        """设置配置项的值，value 始终生效。"""
        with self._lock:
            if section not in self.config:
                self.config[section] = {}
            self.config[section][option] = value
            self._mark_dirty()

    def get_option(self, section: str, option: str, default: Any) -> Any:
        """
        获取配置项的值。不存在时写入 default 并返回。

        :param section: 配置块名称
        :param option: 配置项名称
        :param default: 默认值
        :return: 配置项的值
        """
        with self._lock:
            if self.auto_reload:
                self.load_config()

            if section not in self.config:
                self.config[section] = {}
            if option not in self.config[section]:
                self.config[section][option] = default
                self._mark_dirty()
                return default
            return self.config[section][option]

    def del_option(self, section: str, option: str) -> None:
        """删除指定配置项。"""
        with self._lock:
            if section not in self.config:
                return
            if option in self.config[section]:
                del self.config[section][option]
                self._mark_dirty()

    def del_section(self, section: str) -> None:
        """删除整个配置块。"""
        with self._lock:
            if section in self.config:
                del self.config[section]
                self._mark_dirty()

    def reset_section(self, section: str) -> None:
        """将指定配置块重置为空字典。"""
        with self._lock:
            if section not in self.config:
                return
            self.config[section] = {}
            self._mark_dirty()

    def to_dict(self) -> Dict[str, Any]:
        """导出全部配置数据的深拷贝：{section: {option: value}}，修改返回值不影响内部数据。
        内部字段（如 _schema_version）不会被导出。"""
        with self._lock:
            if self.auto_reload:
                self.load_config()
            # 过滤掉框架内部字段
            return {k: copy.deepcopy(v)
                    for k, v in self.config.items()
                    if not k.startswith('_')}

    @property
    def dirty(self) -> bool:
        return self._dirty
