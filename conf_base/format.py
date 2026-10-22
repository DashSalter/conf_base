import datetime as _dt
import json
from abc import ABCMeta, abstractmethod
from typing import Any, Dict, Optional, cast

from .error import ConfigValueError

"""
配置格式：负责 dict <-> 文本 的纯序列化，不涉及任何加密。

- JsonFormat: 明文 JSON，默认，无依赖
- YamlFormat: 明文 YAML，需要 pip install PyYAML
- TomlFormat: 明文 TOML，需要 pip install tomli-w（Python < 3.11 读取还需 tomli）
"""


def _normalize_value(value: Any, fmt: str, allow_none: bool, path: str) -> Any:
    """
    递归校验配置值，返回可安全序列化的副本。

    - 元组统一转为 list（与 JSON 行为一致）
    - 字典键必须是 str（元组键等无法跨格式表达，直接报错）
    - TOML 不支持 null，遇到 None 报错
    - 其他不可序列化类型（set/bytes/自定义对象）报错并指出具体位置
    """
    if isinstance(value, dict):
        result: Dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ConfigValueError(
                    f"{fmt} 配置的字典键必须是字符串，位置 '{path}' 发现 "
                    f"{type(key).__name__} 类型键 {key!r}。请改用字符串键。"
                )
            child_path = f"{path}.{key}" if path else key
            result[key] = _normalize_value(item, fmt, allow_none, child_path)
        return result

    if isinstance(value, (list, tuple)):
        return [
            _normalize_value(item, fmt, allow_none, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]

    if value is None:
        if allow_none:
            return None
        raise ConfigValueError(
            f"{fmt} 不支持 null，位置 '{path}' 的值为 None。"
            f"请提供非空默认值，或在写入前移除该值。"
        )

    if isinstance(value, (str, int, float, bool, _dt.datetime, _dt.date, _dt.time)):
        return value

    raise ConfigValueError(
        f"{fmt} 不支持 {type(value).__name__} 类型，位置 '{path}'。"
        f"可用的值类型：str / int / float / bool / list / tuple / dict。"
    )


class BaseFormat(metaclass=ABCMeta):
    """配置格式接口：把配置字典序列化为文本，以及反向解析。

    格式只关心数据长什么样，不关心文件路径与加密。篡改校验、加密等能力
    由 ``conf_base.cipher.BaseCipher`` 负责，两者通过文本衔接：

        写入：dict --serialize--> text --cipher.encrypt--> file
        读取：file --cipher.decrypt--> text --deserialize--> dict
    """

    #: 文件后缀，包含点号，例如 '.json'
    extension: str = ''

    @abstractmethod
    def serialize(self, data: Dict[str, Any]) -> str:
        """把配置字典序列化为文本。"""
        ...

    @abstractmethod
    def deserialize(self, text: str) -> Dict[str, Any]:
        """把文本解析为配置字典。根节点不是字典时抛 ConfigValueError。"""
        ...


class JsonFormat(BaseFormat):
    """明文 JSON 格式。"""

    extension = '.json'

    def serialize(self, data: Dict[str, Any]) -> str:
        return json.dumps(data, ensure_ascii=False, indent=4, sort_keys=False)

    def deserialize(self, text: str) -> Dict[str, Any]:
        loaded = json.loads(text)
        if not isinstance(loaded, dict):
            raise ConfigValueError(
                f"JSON 配置的根节点必须是字典，实际为 {type(loaded).__name__}"
            )
        return loaded


class YamlFormat(BaseFormat):
    """明文 YAML 格式。元组值自动转为 list，字典键必须是字符串。"""

    extension = '.yaml'

    @staticmethod
    def _module() -> Any:
        """延迟导入 PyYAML，未安装时给出明确提示。"""
        try:
            import yaml
        except ImportError as exc:
            raise ImportError(
                "YamlFormat 需要 PyYAML，请先安装:\n"
                "  pip install conf_base[yaml]\n"
                "  或: pip install PyYAML"
            ) from exc
        return yaml

    def serialize(self, data: Dict[str, Any]) -> str:
        yaml = self._module()
        normalized = _normalize_value(data, 'YAML', True, '')
        content: str = yaml.safe_dump(
            normalized,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
        return content

    def deserialize(self, text: str) -> Dict[str, Any]:
        yaml = self._module()
        loaded = yaml.safe_load(text)
        if loaded is None:
            return {}
        if not isinstance(loaded, dict):
            raise ConfigValueError(
                f"YAML 配置的根节点必须是字典，实际为 {type(loaded).__name__}"
            )
        for key in loaded:
            if not isinstance(key, str):
                raise ConfigValueError(
                    f"YAML 配置的根节点键必须是字符串，发现 {type(key).__name__} 类型键 {key!r}"
                )
        return cast(Dict[str, Any], loaded)


class TomlFormat(BaseFormat):
    """明文 TOML 格式。元组值自动转为 list，字典键必须是字符串，不支持 None。"""

    extension = '.toml'

    @staticmethod
    def _dumps(data: Dict[str, Any]) -> str:
        """延迟导入 tomli-w，未安装时给出明确提示。"""
        try:
            import tomli_w
        except ImportError as exc:
            raise ImportError(
                "TomlFormat 需要 tomli-w 写入库，请先安装:\n"
                "  pip install conf_base[toml]\n"
                "  或: pip install tomli-w"
            ) from exc
        content: str = tomli_w.dumps(data)
        return content

    def serialize(self, data: Dict[str, Any]) -> str:
        normalized = _normalize_value(data, 'TOML', False, '')
        return self._dumps(cast(Dict[str, Any], normalized))

    def deserialize(self, text: str) -> Dict[str, Any]:
        """读取 TOML：Python >= 3.11 用标准库 tomllib，低版本用 tomli。"""
        loader: Any
        try:
            import tomllib

            loader = tomllib
        except ImportError:
            try:
                import tomli

                loader = tomli
            except ImportError as exc:
                raise ImportError(
                    "TomlFormat 需要 tomli 读取库（Python < 3.11），请先安装:\n"
                    "  pip install conf_base[toml]\n"
                    "  或: pip install tomli"
                ) from exc

        loaded: Dict[str, Any] = loader.loads(text)
        if not isinstance(loaded, dict):
            raise ConfigValueError(
                f"TOML 配置的根节点必须是字典，实际为 {type(loaded).__name__}"
            )
        return loaded


def format_from_path(path: str) -> Optional[BaseFormat]:
    """根据文件后缀推断格式，无法识别时返回 None。"""
    lower = path.lower()
    for suffix, factory in (
        ('.json', JsonFormat),
        ('.yaml', YamlFormat),
        ('.yml', YamlFormat),
        ('.toml', TomlFormat),
    ):
        if lower.endswith(suffix):
            return factory()
    return None
