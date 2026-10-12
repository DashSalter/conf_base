from typing import Dict

from .descriptor import ConfigProperty
from .json_config import JsonConfig
from .section import Section

"""
读取配置类的数据和配置项
初始化和维护配置数据
"""

class ConfigMeta(type):

    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)
        instance = new_class()

        # 从类属性读取配置
        init_kwargs = {
            key: value
            for key, value in (
                ('crypto', attrs.get('_crypto')),  # 进行配置文件的加密
            )
        }
        json_config = JsonConfig(**init_kwargs)

        # ----- 注册配置节点 -----
        config_node: Dict[str, list] = {}
        config_properties = []
        for attr_name, attr_value in attrs.items():
            if isinstance(attr_value, Section):
                for section_name in attr_value.section_tuple:
                    config_node[section_name] = attr_value.get_options()
                attr_value._section_name = attr_name  # 注入配置块属性名
            elif isinstance(attr_value, ConfigProperty):
                config_properties.append((attr_name, attr_value))

        # ----- 批量初始化默认值 -----
        for _, prop in config_properties:
            prop._config_file = json_config  # 注入本配置类的 JsonConfig 实例
            for section_name in prop.section_tuple:
                section = json_config.config.setdefault(section_name, {})
                if prop.option not in section:
                    section[prop.option] = prop.default
                    json_config._dirty = True
        if json_config.dirty:
            json_config.write_config()

        # ----- 整理配置文件：删除代码中已不存在的 section/option -----
        for key, value in list(json_config.config.items()):
            if key not in config_node:
                json_config.del_section(key)
                continue
            options = config_node[key]
            for option in list(value.keys()):
                if option not in options:
                    json_config.del_option(key, option)

        # ----- 注入配置节点 -----
        instance.config_node = config_node
        return instance
