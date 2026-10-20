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
            validator: Optional[Callable[[Any], bool]] = None,
            read_only: bool = False,
            env_key: Optional[str] = None,
            ) -> ConfigProperty:
        """
        添加一个配置项。

        :param read_only: 数据只读（运行时禁止写入）
        :param option: 配置项名称,在配置文件中显示
        :param default: 默认值，配置值的类型始终与默认值类型一致
        :param validator: 校验函数，接收待写入的值，返回 True 表示合法。
                          不为 None 时必须是可调用对象，否则抛出 TypeError。
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
        child_node = self._property_factory(
            option=option,
            default=default,
            validator=validator,
            read_only=read_only,
            env_key=env_key,
        )
        self._child_nodes.append(child_node)
        return child_node

    def _read_section(self, section: str) -> Dict[str, Any]:
        """读取指定 section 下所有配置项的当前值（环境变量 > 配置文件 > 默认值）。"""
        data = {}
        for child in self._child_nodes:
            # 环境变量优先
            config_file = getattr(child, '_config_file')
            env_val = child.get_from_env() if config_file is not None else None
            if env_val is not None:
                data[child.option] = env_val
            elif config_file is not None:
                data[child.option] = config_file.get_option(section, child.option, child.default)
            else:
                data[child.option] = child.default
        return data

    def __str__(self) -> str:
        # 显示所有 section 的当前值
        groups = []
        for section in self.section_tuple:
            parts = [f"{k}={v}" for k, v in self._read_section(section).items()]
            groups.append(f"{section}={{{', '.join(parts)}}}")
        return f"<{self.__class__.__name__}: {', '.join(groups)}>"

    def get_options(self) -> list:
        """返回该 section 下所有 option 名称列表。"""
        return list(self._options.keys())

    @property
    def default_options(self) -> Dict[str, Any]:
        """返回该 section 下所有配置项的 {option: 默认值} 字典。"""
        return dict(self._options)

    @property
    def current_options(self) -> Dict[str, Any]:
        """
        返回当前最新值的字典。
        单 section: {option: 当前值}
        可切换 section: {section名: {option: 当前值}}
        """
        if len(self.section_tuple) == 1:
            return self._read_section(self.section)
        return {section: self._read_section(section) for section in self.section_tuple}

    def _get_config_file(self):
        """获取所属配置类的 JsonConfig 实例（取第一个子节点注入的实例）。"""
        if not self._child_nodes:
            raise RuntimeError(f"Section '{self.section}' 下没有配置项")
        return getattr(self._child_nodes[0], '_config_file')

    def batch(self):
        """批量修改上下文：期间所有修改只写内存，退出时一次性落盘。"""
        return self._get_config_file().batch()

    def reset(self) -> None:
        """重置所有 section 下所有配置项为默认值，一次性落盘"""
        if not self._child_nodes:
            return
        config_file = self._get_config_file()
        with config_file.batch():
            for section in self.section_tuple:
                for child in self._child_nodes:
                    config_file.set_option(section, child.option, child.default)
                    child.notify_change(child.default, section=section)

    def update(self, **kwargs) -> None:
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

    def __getattr__(self, item: str):
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
                config_file = getattr(child, '_config_file')
                if config_file is not None:
                    return config_file.get_option(self.section, child.option, child.default)
                return child.default
        raise KeyError(f"配置项 '{item}' 不存在于 section '{self.section}' 中")

    def __contains__(self, item: str) -> bool:
        """判断 option 是否存在于该配置块：'item_name' in section"""
        return item in self._options

    def __len__(self) -> int:
        return len(self._options)
