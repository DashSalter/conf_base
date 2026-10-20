import copy
import os
import threading
from contextlib import contextmanager
from typing import Any, Dict
from .crypto import Crypto, PlainJson
from .Error import ParseError

"""
配置文件管理器，管理配置数据的读写操作。
每个配置类拥有独立的 JsonConfig 实例，互不干扰。
"""


class JsonConfig:

    def __init__(self, crypto=None, auto_reload=False,
                 target_version: int = 1, migrations: Dict[int, Any] = None):
        self._lock = threading.RLock()
        self._dirty = False  # 脏标记：内存已修改但未写入文件
        self._batch_depth = 0  # 批量模式深度，>0 时修改只落内存，退出批量后一次性落盘
        self.config: Dict[str, Any] = {}

        # 每次请求都重新从文件读取最新数据（外部可能修改文件）
        if not isinstance(auto_reload, bool):
            raise TypeError('auto_reload is not bool')
        self.auto_reload = auto_reload

        # 选择加解密器：None 表示不加密，使用明文 PlainCrypto
        if crypto is not None and not isinstance(crypto, Crypto):
            raise TypeError(f"类型 {type(crypto).__name__} 未实现 Crypto 协议")
        self.crypto = PlainJson() if crypto is None else crypto

        # schema 迁移配置
        if not isinstance(target_version, int):
            raise TypeError('target_version 必须是 int 类型')
        if target_version < 1:
            raise ValueError('target_version 必须 >= 1')
        self._target_version = target_version
        self._migrations = migrations or {}

        # 文件路径与加载
        self.file_path = self.crypto.file_path
        self.encoding = 'utf-8'
        self.load_config()

    def _mark_dirty(self) -> None:
        """标记内存数据已修改；批量模式下延迟落盘，否则立即落盘。"""
        self._dirty = True
        if self._batch_depth == 0:
            self.write_config()

    @contextmanager
    def batch(self):
        """批量修改上下文：期间所有修改只写内存，退出时一次性落盘。"""
        with self._lock:
            self._batch_depth += 1
        try:
            yield self
        finally:
            with self._lock:
                self._batch_depth -= 1
                if self._batch_depth == 0 and self._dirty:
                    self.write_config()

    def save(self) -> None:
        """显式将未落盘的修改写入文件。"""
        with self._lock:
            if self._dirty:
                self.write_config()

    def load_config(self) -> None:
        """从文件加载配置到内存，自动执行 schema 迁移。"""
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                content = f.read()
        except FileNotFoundError:
            self.config = {'_schema_version': self._target_version}
            self.write_config()  # 文件不存在则创建
            return

        try:
            self.config = self.crypto.decrypt(content)
        except Exception as e:
            raise ParseError(
                f"配置文件 '{self.file_path}' 无法解析，请检查文件内容格式是否正确。"
                f"原始错误: {e}"
            ) from e

        # schema 版本迁移（迁移后 _dirty 会被设为 True，无需额外处理）
        self._run_migrations()

    def _run_migrations(self) -> None:
        """执行 schema 版本迁移链。"""
        current = self.config.get('_schema_version', 1)
        need_write_back = False

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
        """将内存配置写入文件"""
        with self._lock:
            if not isinstance(self.config, dict):
                raise ValueError(f"配置数据类型异常，期望 dict，实际 {type(self.config).__name__}")

            # 序列化失败则不碰文件
            content = self.crypto.encrypt(self.config)
            directory = os.path.dirname(self.file_path)
            if directory:
                os.makedirs(directory, exist_ok=True)

            # 写入零时缓存
            temp_file = self.file_path + '.tmp'
            try:
                with open(temp_file, 'w', encoding=self.encoding) as f:
                    f.write(content)
                os.replace(temp_file, self.file_path)
            except Exception:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                raise

            self._dirty = False

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
    def dirty(self):
        return self._dirty
