from typing import Any, Dict, List, Tuple, Type

from .descriptor import ConfigProperty
from .json_config import JsonConfig
from .section import Section

"""
读取配置类的数据和配置项
初始化和维护配置数据
"""


class ConfigMeta(type):
    """配置元类。定义配置类时自动完成：配置文件加载、默认值初始化、schema 迁移、废弃项清理。"""

    def __new__(mcls: Type['ConfigMeta'], name: str, bases: Tuple[type, ...],
                attrs: Dict[str, Any]) -> Any:
        new_class = super().__new__(mcls, name, bases, attrs)
        instance = new_class()

        # 读取配置类的框架级配置
        json_config = JsonConfig(
            crypto=attrs.get('_crypto'),
            auto_reload=attrs.get('_auto_reload', False),
            target_version=attrs.get('_schema_version', 1),
            migrations=attrs.get('_migrate', {}),
            # 多进程文件锁（需要 pip install filelock）
            use_file_lock=attrs.get('_use_file_lock', True),
            lock_timeout=attrs.get('_lock_timeout', 10.0),
        )

        # ----- 注册配置节点 -----
        config_node: Dict[str, List[str]] = {}
        config_properties: List[ConfigProperty] = []
        for attr_value in attrs.values():
            if isinstance(attr_value, Section):
                config_node[attr_value.section] = attr_value.get_options()
            elif isinstance(attr_value, ConfigProperty):
                config_properties.append(attr_value)

        with json_config.batch():
            # ----- 批量初始化默认值 -----
            for prop in config_properties:
                prop._config_file = json_config  # 注入本配置类的 JsonConfig 实例
                section = json_config.config.setdefault(prop.section, {})
                if prop.option not in section:
                    section[prop.option] = prop.default
                    json_config._dirty = True

            # ----- 整理配置文件：删除代码中已不存在的 section/option -----
            for key, value in list(json_config.config.items()):
                # 跳过框架内部字段
                if key == '_schema_version':
                    continue
                if key not in config_node:
                    json_config.del_section(key)
                    continue
                options = config_node[key]
                for option in list(value.keys()):
                    if option not in options:
                        json_config.del_option(key, option)

        # ----- 注入配置节点与全量导出 -----
        instance.config_node = config_node
        instance.to_dict = json_config.to_dict
        return instance
