from typing import Any, Callable, ContextManager, Dict, List, Optional

from .descriptor import ConfigProperty
from .json_config import JsonConfig

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
        self._options: Dict[str, Any] = {}
        self._child_nodes: List[ConfigProperty] = []

    def add(self, option: str,
            default: Any = '',
            validator: Optional[Callable[[Any], bool]] = None,
            read_only: bool = False,
            env_key: Optional[str] = None,
            ) -> ConfigProperty:
        """
        添加一个配置项。

        :param option: 配置项名称,在配置文件中显示
        :param default: 默认值，配置值的类型始终与默认值类型一致
        :param validator: 校验函数，接收待写入的值，返回 True 表示合法。
                          不为 None 时必须是可调用对象，否则抛出 TypeError。
        :param read_only: 数据只读（运行时禁止写入）
        :param env_key: 环境变量名，设置后该配置项支持被环境变量覆盖（优先级：env > 文件 > 默认值）
        :return: ConfigProperty 描述器，可直接赋值给类属性
        """
        if validator is not None and not callable(validator):
            raise TypeError('validator 必须是可调用对象,函数或lambda')
        if not isinstance(read_only, bool):
            raise TypeError('read_only is not bool.')
        if env_key is not None and not isinstance(env_key, str):
            raise TypeError('env_key 必须是字符串')

        self._options[option] = default
        child_node = ConfigProperty(
            section=self.section,
            option=option,
            default=default,
            validator=validator,
            read_only=read_only,
            env_key=env_key,
        )
        self._child_nodes.append(child_node)
        return child_node

    def _read_options(self) -> Dict[str, Any]:
        """读取该 section 下所有配置项的当前值（环境变量 > 配置文件 > 默认值）。"""
        return {child.option: child.get_value() for child in self._child_nodes}

    def __str__(self) -> str:
        parts = [f"{k}={v}" for k, v in self._read_options().items()]
        return f"<{self.__class__.__name__}: {self.section}={{{', '.join(parts)}}}>"

    def get_options(self) -> List[str]:
        """返回该 section 下所有 option 名称列表。"""
        return list(self._options.keys())

    @property
    def default_options(self) -> Dict[str, Any]:
        """返回该 section 下所有配置项的 {option: 默认值} 字典。"""
        return dict(self._options)

    @property
    def current_options(self) -> Dict[str, Any]:
        """返回该 section 下所有配置项的 {option: 当前值} 字典。"""
        return self._read_options()

    def _get_config_file(self) -> JsonConfig:
        """获取所属配置类的 JsonConfig 实例（取第一个子节点注入的实例）。"""
        if not self._child_nodes:
            raise RuntimeError(f"Section '{self.section}' 下没有配置项")
        config_file = self._child_nodes[0]._config_file # noqa
        if config_file is None:
            raise RuntimeError(f"Section '{self.section}' 未绑定配置文件")
        return config_file

    def batch(self) -> ContextManager[JsonConfig]:
        """批量修改上下文：期间所有修改只写内存，退出时一次性落盘。"""
        return self._get_config_file().batch()

    def reset(self) -> None:
        """重置该 section 下所有配置项为默认值，一次性落盘"""
        if not self._child_nodes:
            return
        config_file = self._get_config_file()
        with config_file.batch():
            for child in self._child_nodes:
                config_file.set_option(self.section, child.option, child.default)
                child.notify_change(child.default)

    def update(self, **kwargs: Any) -> None:
        """批量写入配置项，kwargs 的 key 为 option 名，value 为待写入的值，一次性落盘"""
        valid_options = set(self._options.keys())
        for option in kwargs:
            if option not in valid_options:
                raise KeyError(f"配置项 '{option}' 不存在于 section '{self.section}' 中")
        if not kwargs or not self._child_nodes:
            return
        with self._get_config_file().batch():
            for option, value in kwargs.items():
                for child in self._child_nodes:
                    if child.option == option:
                        child.set_value(value)
                        break

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
        for child in self._child_nodes:
            if child.option == item:
                return child.get_value()
        raise KeyError(f"配置项 '{item}' 不存在于 section '{self.section}' 中")

    def __contains__(self, item: object) -> bool:
        """判断 option 是否存在于该配置块：'item_name' in section"""
        return item in self._options

    def __len__(self) -> int:
        return len(self._options)
