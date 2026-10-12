from functools import partial
from typing import Any, Callable, Dict, Optional, Tuple

from .descriptor import ConfigProperty

"""
定义配置块，可以在其中添加配置项
"""


class Section:

    def __init__(self, *section: str):
        self.section_tuple: Tuple[str, ...] = section
        self.section = section[0]
        self._section_name: str = ''
        self._property_factory = partial(ConfigProperty, section_tuple=self.section_tuple)
        self._options: Dict[str, Any] = {}
        self._child_nodes: list = []

    def set_use_section(self, section) -> None:
        """
        切换 section。

        :param section: 字符串或元组。若为元组则取第一个元素。
        """
        if isinstance(section, (tuple, list)):
            self.section = section[0]
        else:
            self.section = section
        self._property_factory = partial(ConfigProperty, section_tuple=self.section_tuple)

        # 递归更新所有子节点的 section
        for child_node in self._child_nodes:
            child_node.set_section(self.section)

    def add(self, option: str,
            default: Any = '',
            validator: Optional[Callable[[Any], bool]] = None
            ) -> ConfigProperty:
        """
        添加一个配置项。

        :param option: 配置项名称,在配置文件中显示
        :param default: 默认值，配置值的类型始终与默认值类型一致
        :param validator: 校验函数，接收待写入的值，返回 True 表示合法。
                          不为 None 时必须是可调用对象，否则抛出 TypeError。
        :return: ConfigProperty 描述器，可直接赋值给类属性
        """
        if validator is not None and not callable(validator):
            raise TypeError('validator 必须是可调用对象,函数或lambda')

        self._options[option] = default
        child_node = self._property_factory(
            option=option,
            default=default,
            validator=validator
        )
        self._child_nodes.append(child_node)
        return child_node

    def __str__(self) -> str:
        parts = [f"{k}={v}" for k, v in self._options.items()]
        return f"<{self.__class__.__name__}:{self.section} [{', '.join(parts)}]>"

    def get_options(self) -> list:
        """返回该 section 下所有 option 名称列表。"""
        return list(self._options.keys())

    def reset(self) -> None:
        """重置该 section 下所有配置项为默认值"""
        for child in self._child_nodes:
            child._config_file.set_option(self.section, child.option, child.default)

    def update(self, **kwargs) -> None:
        """批量写入配置项，kwargs 的 key 为 option 名，value 为待写入的值"""
        valid_options = set(self._options.keys())
        for option, value in kwargs.items():
            if option not in valid_options:
                raise KeyError(f"配置项 '{option}' 不存在于 section '{self.section}' 中")
        for option, value in kwargs.items():
            for child in self._child_nodes:
                if child.option == option:
                    child.set_value(value)
                    break

    def __getattr__(self, item: str):
        # 仅当正常属性查找失败时才调用，把 option 名当作属性访问
        return self.__getitem__(item)

    def __getitem__(self, item: str) -> Any:
        return self._options.get(item)

    def __len__(self) -> int:
        return len(self._options)
