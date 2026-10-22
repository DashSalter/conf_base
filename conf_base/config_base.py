from typing import Any, Dict, List, Optional, Tuple

from .cipher import BaseCipher, NoCipher
from .config_file import ConfigFile
from .descriptor import ConfigProperty
from .format import BaseFormat, JsonFormat, format_from_path
from .section import Section

"""
读取配置类的数据和配置项
初始化和维护配置数据
"""


def _resolve_target(cls: Any, attrs: Dict[str, Any]) -> Tuple[str, BaseFormat, BaseCipher]:
    """解析配置文件路径、格式与加密器。

    - 显式 ``_path``：原样使用；未指定 ``_format`` 时按后缀推断，后缀冲突则报错
    - 未指定路径：按类名生成 ``{类名小写}{格式后缀}{加密后缀}``
    """
    path: Optional[str] = attrs.get('_path')
    fmt: Optional[BaseFormat] = attrs.get('_format')
    cipher: Optional[BaseCipher] = attrs.get('_cipher')

    if fmt is not None and not isinstance(fmt, BaseFormat):
        raise TypeError(
            f"{cls.__name__}._format 必须是 BaseFormat 实例，实际为 {type(fmt).__name__}"
        )
    if cipher is not None and not isinstance(cipher, BaseCipher):
        raise TypeError(
            f"{cls.__name__}._cipher 必须是 BaseCipher 实例，实际为 {type(cipher).__name__}"
        )
    resolved_cipher = NoCipher() if cipher is None else cipher

    if path is not None:
        if fmt is None:
            fmt = format_from_path(path) or JsonFormat()
        else:
            inferred = format_from_path(path)
            if inferred is not None and inferred.extension != fmt.extension:
                raise ValueError(
                    f"{cls.__name__}: 路径 '{path}' 的后缀与 _format="
                    f"{type(fmt).__name__} 不匹配，请统一格式或去掉路径后缀"
                )
        return path, fmt, resolved_cipher

    resolved_fmt = JsonFormat() if fmt is None else fmt
    generated = f'{cls.__name__.lower()}{resolved_fmt.extension}{resolved_cipher.extension}'
    return generated, resolved_fmt, resolved_cipher


def _bootstrap(target: Any, attrs: Dict[str, Any]) -> None:
    """加载配置、注册配置项并初始化默认值，把 config_node / to_dict 绑定到 target。"""
    if getattr(target, '_config_bootstrapped', False):
        return

    path, fmt, cipher = _resolve_target(target, attrs)
    config_file = ConfigFile(
        path=path,
        format=fmt,
        cipher=cipher,
        auto_reload=attrs.get('_auto_reload', False),
        target_version=attrs.get('_schema_version', 1),
        migrations=attrs.get('_migrate', {}),
        # 多进程文件锁（需要 pip install filelock）
        use_file_lock=attrs.get('_use_file_lock', True),
        lock_timeout=attrs.get('_lock_timeout', 10.0),
    )

    # ----- 注册配置节点 -----
    config_node: Dict[str, List[str]] = {}
    config_properties: List[ConfigProperty[Any]] = []
    for attr_value in attrs.values():
        if isinstance(attr_value, Section):
            config_node[attr_value.section] = attr_value.get_options()
        elif isinstance(attr_value, ConfigProperty):
            config_properties.append(attr_value)

    with config_file.batch():
        # ----- 批量初始化默认值 -----
        for prop in config_properties:
            prop._config_file = config_file  # 注入本配置类的 ConfigFile 实例
            if prop.option not in config_file.config.get(prop.section, {}):
                config_file.set_option(prop.section, prop.option, prop.default)

        # ----- 可选：清理代码中已不存在的 section/option -----
        # 默认保留未知项，避免手工添加的配置在启动时被静默删除
        if attrs.get('_prune_unknown', False):
            for key, value in list(config_file.config.items()):
                # 跳过框架内部字段（如 _schema_version）
                if key.startswith('_'):
                    continue
                if key not in config_node:
                    config_file.del_section(key)
                    continue
                options = config_node[key]
                for option in list(value.keys()):
                    if option not in options:
                        config_file.del_option(key, option)

    # ----- 注入配置节点与全量导出 -----
    target.config_node = config_node
    target.to_dict = config_file.to_dict
    target._config_bootstrapped = True


class ConfigBase:
    """配置类基类：继承本类即可声明配置。

    存储由两个正交参数控制：
    - ``_path``: 文件路径，省略时按类名生成
    - ``_format``: JsonFormat / YamlFormat / TomlFormat，省略时按路径后缀推断，默认 JSON
    - ``_cipher``: NoCipher / AesCipher / AesGcmCipher / ChaCha20Poly1305Cipher / SignedCipher

    配置类不支持继承复用配置项，请为每个配置文件定义独立的配置类。
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _bootstrap(cls, dict(cls.__dict__))
