from typing import (
    Any, Callable, ContextManager, Dict, List, Optional, overload,
)

from .config_file import ConfigFile
from .descriptor import (
    BoolProxy,
    ConfigProperty,
    DictProxy,
    ListProxy,
    NumberProxy,
    PropertyProxy,
)

"""
定义配置块，可以在其中添加配置项
"""


class Section:
    """配置块：一组配置项的命名空间，支持批量读写与分组操作。"""

    def __init__(self, section: str) -> None:
        if not isinstance(section, str):
            raise TypeError('section 必须是字符串')
        if not section:
            raise ValueError('section 不能为空字符串')
        self.section: str = section
        # option -> ConfigProperty，唯一数据源
        self._options: Dict[str, ConfigProperty[Any]] = {}

    # 按 default 的类型重载返回的代理类型，让 IDE 能提示 increment/toggle/append 等专属方法
    # bool 是 int 的子类，必须排在 int 之前；两者返回类型无关，需显式忽略重叠检查
    @overload
    def field(self, *, default: bool, option: Optional[str] = None,  # type: ignore[overload-overlap]
              validator: Optional[Callable[[Any], bool]] = None,
              read_only: bool = False,
              env_key: Optional[str] = None) -> ConfigProperty[BoolProxy]: ...

    @overload
    def field(self, *, default: int, option: Optional[str] = None,
              validator: Optional[Callable[[Any], bool]] = None,
              read_only: bool = False,
              env_key: Optional[str] = None) -> ConfigProperty[NumberProxy]: ...

    @overload
    def field(self, *, default: float, option: Optional[str] = None,
              validator: Optional[Callable[[Any], bool]] = None,
              read_only: bool = False,
              env_key: Optional[str] = None) -> ConfigProperty[NumberProxy]: ...

    @overload
    def field(self, *, default: List[Any], option: Optional[str] = None,
              validator: Optional[Callable[[Any], bool]] = None,
              read_only: bool = False,
              env_key: Optional[str] = None) -> ConfigProperty[ListProxy]: ...

    @overload
    def field(self, *, default: Dict[str, Any], option: Optional[str] = None,
              validator: Optional[Callable[[Any], bool]] = None,
              read_only: bool = False,
              env_key: Optional[str] = None) -> ConfigProperty[DictProxy]: ...

    @overload
    def field(self, *, default: Any = '', option: Optional[str] = None,
              validator: Optional[Callable[[Any], bool]] = None,
              read_only: bool = False,
              env_key: Optional[str] = None) -> ConfigProperty[PropertyProxy]: ...

    def field(self, *, default: Any = '', option: Optional[str] = None,
              validator: Optional[Callable[[Any], bool]] = None,
              read_only: bool = False,
              env_key: Optional[str] = None) -> ConfigProperty[Any]:
        """
        声明一个配置项，返回值赋值给类属性即可。

        >>> class C(ConfigBase):
        ...     s = Section('S')
        ...     port = s.field(default=8080, validator=lambda v: 1 <= v <= 65535)

        :param default: 默认值，配置值的类型始终与默认值类型一致
        :param option: 写入配置文件的键名；省略时使用左侧类属性名
        :param validator: 校验函数，接收待写入的值，返回 True 表示合法。
                          不为 None 时必须是可调用对象，否则抛出 TypeError。
        :param read_only: 数据只读（运行时禁止写入）
        :param env_key: 环境变量名，设置后该配置项支持被环境变量覆盖（优先级：env > 文件 > 默认值）
        :return: ConfigProperty 描述器，可直接赋值给类属性
        """
        if option is not None and not isinstance(option, str):
            raise TypeError('option 必须是字符串或 None')
        if validator is not None and not callable(validator):
            raise TypeError('validator 必须是可调用对象,函数或lambda')
        if not isinstance(read_only, bool):
            raise TypeError('read_only is not bool.')
        if env_key is not None and not isinstance(env_key, str):
            raise TypeError('env_key 必须是字符串')
        if option is not None and option in self._options:
            raise ValueError(
                f"配置项 '{option}' 在 section '{self.section}' 中已存在，"
                f"不能重复添加"
            )

        child_node: ConfigProperty[Any] = ConfigProperty(
            section=self.section,
            option=option,
            default=default,
            validator=validator,
            read_only=read_only,
            env_key=env_key,
        )
        child_node._section_obj = self
        if option is not None:
            self._register(child_node)
        return child_node

    def _register(self, prop: ConfigProperty[Any]) -> None:
        """把配置项登记到 Section；未命名配置项在 __set_name__ 时调用。"""
        option = prop.option
        if option in self._options:
            raise ValueError(
                f"配置项 '{option}' 在 section '{self.section}' 中已存在，"
                f"不能重复添加"
            )
        self._options[option] = prop

    def _read_options(self) -> Dict[str, Any]:
        """读取该 section 下所有配置项的当前值（环境变量 > 配置文件 > 默认值）。"""
        return {option: child.get_value() for option, child in self._options.items()}

    def __str__(self) -> str:
        parts = [f"{k}={v}" for k, v in self._read_options().items()]
        return f"<{self.__class__.__name__}: {self.section}={{{', '.join(parts)}}}>"

    def get_options(self) -> List[str]:
        """返回该 section 下所有 option 名称列表。"""
        return list(self._options)

    @property
    def default_options(self) -> Dict[str, Any]:
        """返回该 section 下所有配置项的 {option: 默认值} 字典。"""
        return {option: child.default for option, child in self._options.items()}

    @property
    def current_options(self) -> Dict[str, Any]:
        """返回该 section 下所有配置项的 {option: 当前值} 字典。"""
        return self._read_options()

    def _get_config_file(self) -> ConfigFile:
        """获取所属配置类的 ConfigFile 实例（取第一个配置项注入的实例）。"""
        if not self._options:
            raise RuntimeError(f"Section '{self.section}' 下没有配置项")
        config_file = next(iter(self._options.values()))._config_file # noqa
        if config_file is None:
            raise RuntimeError(f"Section '{self.section}' 未绑定配置文件")
        return config_file

    def batch(self) -> ContextManager[ConfigFile]:
        """批量修改上下文：期间所有修改只写内存，退出时一次性落盘。"""
        return self._get_config_file().batch()

    def reset(self) -> None:
        """重置该 section 下所有配置项为默认值，一次性落盘"""
        if not self._options:
            return
        with self._get_config_file().batch():
            for child in self._options.values():
                child.set_value(child.default)

    def update(self, **kwargs: Any) -> None:
        """批量写入配置项，kwargs 的 key 为 option 名，value 为待写入的值，一次性落盘"""
        for option in kwargs:
            if option not in self._options:
                raise KeyError(f"配置项 '{option}' 不存在于 section '{self.section}' 中")
        if not kwargs:
            return
        with self._get_config_file().batch():
            for option, value in kwargs.items():
                self._options[option].set_value(value)

    def __getattr__(self, item: str) -> Any:
        # 仅当正常属性查找失败时才调用，把 option 名当作属性访问当前值
        if item.startswith('_'):
            raise AttributeError(item)
        try:
            return self[item]
        except KeyError:
            raise AttributeError(f"配置项 '{item}' 不存在于 section '{self.section}' 中") from None

    def __getitem__(self, item: str) -> Any:
        """按 option 名读取当前值，不存在时抛出 KeyError"""
        try:
            return self._options[item].get_value()
        except KeyError:
            raise KeyError(f"配置项 '{item}' 不存在于 section '{self.section}' 中") from None

    def __contains__(self, item: object) -> bool:
        """判断 option 是否存在于该配置块：'item_name' in section"""
        return item in self._options

    def __len__(self) -> int:
        return len(self._options)
