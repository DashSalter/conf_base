import warnings
from typing import Any, Callable, Dict, List, Optional, Tuple

from .cipher import BaseCipher, NoCipher
from .config_file import ConfigFile
from .descriptor import ConfigProperty
from .error import ParseError
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
        # 推断格式前先剥离加密后缀，否则 'server.yaml.enc' 会因结尾不是
        # '.yaml' 而静默退回默认的 JSON
        probe_path = path
        if resolved_cipher.extension and probe_path.endswith(resolved_cipher.extension):
            probe_path = probe_path[:-len(resolved_cipher.extension)]
        if fmt is None:
            fmt = format_from_path(probe_path) or JsonFormat()
        else:
            inferred = format_from_path(probe_path)
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
    # 只检查类自身，不读继承值：配置类禁止继承，这里仅防御重复引导
    if attrs.get('_config_bootstrapped', False):
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

    # 配置文件中的 section 必须是字典；手写成标量时给出明确错误，
    # 而不是在后续 `option not in value` 处抛出难以理解的 TypeError
    for section in config_node:
        existing = config_file.config.get(section)
        if existing is not None and not isinstance(existing, dict):
            raise ParseError(
                f"配置文件 '{config_file.file_path}' 的 section '{section}' "
                f"必须是字典，实际为 {type(existing).__name__}，请修正文件内容。"
            )

    with config_file.batch():
        # ----- 批量初始化默认值 -----
        for prop in config_properties:
            prop._config_file = config_file  # 注入本配置类的 ConfigFile 实例
            if prop.option not in config_file.config.get(prop.section, {}):
                config_file.set_option(prop.section, prop.option, prop.default)

        # ----- 可选：清理代码中已不存在的 section/option -----
        # 默认保留未知项，避免手工添加的配置在启动时被静默删除
        if attrs.get('_prune_unknown', False):
            removed: List[str] = []
            for key, value in list(config_file.config.items()):
                # 跳过框架内部字段（如 _schema_version）
                if key.startswith('_'):
                    continue
                if key not in config_node:
                    removed.append(key)
                    config_file.del_section(key)
                    continue
                options = config_node[key]
                for option in list(value.keys()):
                    if option not in options:
                        removed.append(f'{key}.{option}')
                        config_file.del_option(key, option)
            if removed:
                # 删除不可逆：把被删的键显式暴露出来，避免用户误开开关后静默丢数据
                warnings.warn(
                    f'\n{target.__name__} 按 _prune_unknown=True 删除了配置文件中'
                    f'代码未声明的项: {", ".join(removed)}。'
                    f'如需保留，请关闭 _prune_unknown 并手动清理。',
                    UserWarning,
                    stacklevel=2,
                )

    # ----- 注入配置节点与全量导出 -----
    target.config_node = config_node
    target.to_dict = config_file.to_dict
    target._config_bootstrapped = True


class ConfigBase:
    """配置类基类：继承本类即可声明配置。
    配置类不支持继承复用配置项，请为每个配置文件定义独立的配置类。
    """

    # 下列类属性由子类按需覆盖，显式声明后 IDE 才能补全与做类型检查
    _path: Optional[str] = None  # 配置文件路径；省略时按类名生成
    _format: Optional[BaseFormat] = None  # 存储格式；省略时按路径后缀推断，默认 JSON
    _cipher: Optional[BaseCipher] = None  # 加密器；省略时不加密
    _auto_reload: bool = False  # 读取时检查文件指纹并自动重载外部修改
    _schema_version: int = 1  # schema 目标版本号，配合 _migrate 使用
    _migrate: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}  # 迁移函数：{旧版本号: 函数}
    _use_file_lock: bool = True  # 是否启用多进程文件锁，需安装 filelock
    _lock_timeout: float = 10.0  # 等待文件锁的超时时间（秒）
    _prune_unknown: bool = False  # 启动时是否删除代码中已不存在的 section / option

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # 配置项描述符与 ConfigFile 绑定在类级别，继承会让父子类共享同一份
        # 配置数据（或让子类停留在半初始化状态），因此直接拒绝继承。
        if ConfigBase not in cls.__bases__:
            base_name = cls.__bases__[0].__name__ if cls.__bases__ else '?'
            raise TypeError(
                f"{cls.__name__} 不能继承配置类 {base_name}："
                f"配置类不支持继承复用配置项。请直接继承 ConfigBase，"
                f"为每个配置文件定义独立的配置类。"
            )
        _bootstrap(cls, dict(cls.__dict__))
