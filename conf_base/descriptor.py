from typing import Any, Optional, Tuple

from .json_config import JsonConfig

"""
将代码的操作映射为文件的操作
为配置文件中的 section/option 设置更多的方法属性。
"""


class ConfigProperty:

    def __init__(self, section_tuple: Tuple[str, ...], option: str, default: Any, fix_type: bool):

        self._config_file: Optional[JsonConfig] = None
        self.section_tuple = section_tuple
        self.section = section_tuple[0]
        self.option = option
        self.default = default
        self.fix_type = fix_type
        self._proxy: Optional['PropertyProxy'] = None  # 缓存代理对象

    @property
    def config_file(self) -> JsonConfig:
        """延迟返回全局唯一的 JsonConfig 单例（首次属性访问时才创建）。"""
        if self._config_file is None:
            self._config_file = JsonConfig()
        return self._config_file

    def set_section(self, section: str) -> None:
        """切换到另一个 section（用于多 section 共享同一组 option）。"""
        self.section = section
        self._proxy = None  # section 变化后使缓存失效

    def set_value(self, value: Any) -> None:
        """写入配置值。fix_type=True 时校验类型必须与默认值一致。"""
        if self.fix_type and type(value) is not type(self.default):
            raise TypeError(
                f"{self.section}.{self.option} 配置项期望类型 "
                f"{type(self.default).__name__} 实际为 {type(value).__name__}， "
                f"否则请修改配置项 fix_type=False"
            )
        self.config_file.set_option(self.section, self.option, value)

    def __str__(self) -> str:
        return f"<{self.section} {self.option}:{self.default} [{self.section_tuple}]>"

    def __get__(self, obj, obj_type=None) -> 'PropertyProxy':
        if self._proxy is None:
            self._proxy = PropertyProxy(self)
        return self._proxy

    def __set__(self, obj, value) -> None:
        if isinstance(value, PropertyProxy):
            # 初始化时传入的是 PropertyProxy，取其实际值
            value = value.value
        self.set_value(value)


class PropertyProxy:
    """配置属性的代理对象，提供对配置项的扩展操作"""

    def __init__(self, parent: ConfigProperty):
        self._parent: ConfigProperty = parent
        self._get = parent.config_file.get_option
        self._set = parent.config_file.set_option

        self.section = self._parent.section
        self.option = self._parent.option

    def __eq__(self, other) -> bool:
        if not isinstance(other, PropertyProxy):
            return NotImplemented
        return (self._parent.section == other._parent.section
                and self._parent.option == other._parent.option)

    def __str__(self) -> str:
        return f"<class '{self._parent.section}:{self._parent.option}'>"

    def reset(self) -> Any:
        """重置属性值为默认值，并返回默认值。"""
        self._set(self._parent.section, self._parent.option, self._parent.default)
        return self._parent.default

    @property
    def default(self) -> Any:
        return self._parent.default

    @default.setter
    def default(self, value: Any) -> None:
        raise ValueError("default is readonly")

    @property
    def value(self) -> Any:
        return self._get(self._parent.section, self._parent.option, self._parent.default)

    @value.setter
    def value(self, value: Any) -> None:
        self._parent.set_value(value)
