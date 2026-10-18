from collections.abc import Callable
from typing import Dict, Any

from .descriptor import ConfigProperty
from .json_config import JsonConfig
from .section import Section

"""
读取配置类的数据和配置项
初始化和维护配置数据
"""


class ConfigMeta(type):

    def __new__(cls, name, bases, attrs):
        _new_class = super().__new__(cls, name, bases, attrs)
        _instance = _new_class()

        # 从类属性读取配置
        init_kwargs = {
            key: value
            for key, value in (
                # 进行配置文件的加密
                ('crypto', attrs.get('_crypto', None)),
                # 每次读取配置数据都重新从文件读取最新数据，适用于服务器数据修改不重启，开启会消耗些许性能
                ('auto_reload', attrs.get('_auto_reload', False)),

            )
        }
        _json_config = JsonConfig(**init_kwargs)

        # ----- 注册配置节点 -----
        _config_node: Dict[str, list] = {}
        _config_properties = []
        for attr_name, attr_value in attrs.items():
            if isinstance(attr_value, Section):
                for section_name in attr_value.section_tuple:
                    _config_node[section_name] = attr_value.get_options()
                attr_value._section_name = attr_name  # 注入配置块属性名
            elif isinstance(attr_value, ConfigProperty):
                _config_properties.append((attr_name, attr_value))

        with _json_config.batch():
            # ----- 批量初始化默认值 -----
            for _, prop in _config_properties:
                prop._config_file = _json_config  # 注入本配置类的 JsonConfig 实例
                for section_name in prop.section_tuple:
                    _section = _json_config.config.setdefault(section_name, {})
                    if prop.option not in _section:
                        _section[prop.option] = prop.default
                        _json_config._dirty = True

            # ----- 整理配置文件：删除代码中已不存在的 section/option -----
            for key, value in list(_json_config.config.items()):
                if key not in _config_node:
                    _json_config.del_section(key)
                    continue
                options = _config_node[key]
                for option in list(value.keys()):
                    if option not in options:
                        _json_config.del_option(key, option)

        # ----- 注入配置节点与全量导出 -----
        _instance.config_node = _config_node
        _instance.to_dict = _json_config.to_dict
        return _instance

    def to_dict(cls) -> Dict[str, Any]:
        """导出全部数据"""
        return cls._instance.to_dict()
