import os
import threading
from typing import Any, Dict
from .crypto import Crypto, PlainCrypto

"""
配置文件管理器，管理配置数据的读写操作。
每个配置类拥有独立的 JsonConfig 实例，互不干扰。
"""


class JsonConfig:

    def __init__(self, crypto=None, auto_reload=False):
        self._lock = threading.RLock()
        self._dirty = False  # 脏标记：内存已修改但未写入文件
        self.config: Dict[str, Any] = {}

        # 每次请求都重新从文件读取最新数据（外部可能修改文件）
        if not isinstance(auto_reload, bool):
            raise TypeError('auto_reload is not bool')
        self.auto_reload = auto_reload

        # 选择加解密器：None 表示不加密，使用明文 PlainCrypto
        if crypto is not None and not isinstance(crypto, Crypto):
            raise TypeError(f"类型 {type(crypto).__name__} 未实现 Crypto 协议")
        self.crypto = PlainCrypto() if crypto is None else crypto

        # 文件路径与加载
        self.file_path = self.crypto.file_path
        self.encoding = 'utf-8'
        self.load_config()

    def _mark_dirty(self) -> None:
        """标记内存数据已修改并立即落盘。"""
        self._dirty = True
        self.write_config()

    def load_config(self) -> None:
        """从文件加载配置到内存。"""
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                content = f.read()
        except FileNotFoundError:
            self.config = {}
            self.write_config()  # 文件不存在则创建
            return

        self.config = self.crypto.decrypt(content)
        self._dirty = False

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

    @property
    def dirty(self):
        return self._dirty
