import base64
import datetime as _dt
import hashlib
import json
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Union, cast

from .Error import ConfigValueError

if TYPE_CHECKING:
    from cryptography.fernet import Fernet as _FernetType

"""
管理配置数据的输入输出
可以使用提供的加密类，或者继承Crypto来实现自己的加密配置文件

加密器/格式选择：
- PlainJson: 明文 JSON，默认，无依赖
- PlainYaml: 明文 YAML，需要 pip install PyYAML
- PlainToml: 明文 TOML，需要 pip install tomli-w（Python < 3.11 读取还需 tomli）
- XorCrypto: 轻量混淆，非生产加密
- AesCrypto: AES-128-CBC + HMAC 签名（Fernet），需要 pip install cryptography
"""

# cryptography 是可选依赖，未安装时延迟报错
try:
    from cryptography.fernet import Fernet as _Fernet  # noqa: F401

    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False


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


def _load_toml(text: str) -> Dict[str, Any]:
    """读取 TOML：Python >= 3.11 用标准库 tomllib，低版本用 tomli。"""  # noqa
    loader: Any
    try:
        import tomllib  # noqa

        loader = tomllib
    except ImportError:
        try:
            import tomli

            loader = tomli
        except ImportError as exc:
            raise ImportError(
                "PlainToml 需要 tomli 读取库（Python < 3.11），请先安装:\n"
                "  pip install conf_base[toml]\n"
                "  或: pip install tomli"
            ) from exc

    loaded: Dict[str, Any] = loader.loads(text)
    if not isinstance(loaded, dict):
        raise ConfigValueError(
            f"TOML 配置的根节点必须是字典，实际为 {type(loaded).__name__}"
        )
    return loaded


class Crypto(metaclass=ABCMeta):
    """加解密接口协议"""

    def __init__(self, file_path: str = 'settings.txt') -> None:
        self.file_path: str = file_path

    @abstractmethod
    def encrypt(self, data: Dict[str, Any]) -> str:
        """
        将字典加密为字符串。
        :param data: 待加密的字典数据
        :return: 加密后的字符串
        """
        ...

    @abstractmethod
    def decrypt(self, text: str) -> Dict[str, Any]:
        """
        将字符串解密回字典。
        :param text: 加密的字符串
        :return: 解密后的字典数据
        """
        ...


class PlainJson(Crypto):
    """明文Json格式"""

    def __init__(self, file_path: str = 'settings.json') -> None:
        super().__init__(file_path)

    def encrypt(self, data: Dict[str, Any]) -> str:
        return json.dumps(data, ensure_ascii=False, indent=4, sort_keys=False)

    def decrypt(self, text: str) -> Dict[str, Any]:
        return cast(Dict[str, Any], json.loads(text))


class PlainYaml(Crypto):
    """明文 YAML 格式。元组值自动转为 list，字典键必须是字符串。"""

    def __init__(self, file_path: str = 'settings.yaml') -> None:
        super().__init__(file_path)

    @staticmethod
    def _module() -> Any:
        """延迟导入 PyYAML，未安装时给出明确提示。"""
        try:
            import yaml
        except ImportError as exc:
            raise ImportError(
                "PlainYaml 需要 PyYAML，请先安装:\n"
                "  pip install conf_base[yaml]\n"
                "  或: pip install PyYAML"
            ) from exc
        return yaml

    def encrypt(self, data: Dict[str, Any]) -> str:
        yaml = self._module()
        normalized = cast(Dict[str, Any], _normalize_value(data, 'YAML', True, ''))
        content: str = yaml.safe_dump(
            normalized,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
        return content

    def decrypt(self, text: str) -> Dict[str, Any]:
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


class PlainToml(Crypto):
    """明文 TOML 格式。元组值自动转为 list，字典键必须是字符串，不支持 None。"""

    def __init__(self, file_path: str = 'settings.toml') -> None:
        super().__init__(file_path)

    @staticmethod
    def _dumps(data: Dict[str, Any]) -> str:
        """延迟导入 tomli-w，未安装时给出明确提示。"""
        try:
            import tomli_w
        except ImportError as exc:
            raise ImportError(
                "PlainToml 需要 tomli-w 写入库，请先安装:\n"
                "  pip install conf_base[toml]\n"
                "  或: pip install tomli-w"
            ) from exc
        content: str = tomli_w.dumps(data)
        return content

    def encrypt(self, data: Dict[str, Any]) -> str:
        normalized = cast(Dict[str, Any], _normalize_value(data, 'TOML', False, ''))
        return self._dumps(normalized)

    def decrypt(self, text: str) -> Dict[str, Any]:
        return _load_toml(text)


class XorCrypto(Crypto):
    """
    异或 + Base64 加解密器。
    对称加密，密钥需 >= 16 字节。生产环境建议使用更强的加密方式。
    轻量混淆，如果需要更高的加密等级，请继承Crypto类实现！！！
    :param key: 加密密钥，bytes 类型，长度需 >= 16
    """

    def __init__(self, key: bytes, file_path: str = 'settings_xor.enc') -> None:
        super().__init__(file_path)
        if len(key) < 16:
            raise ValueError(f"加密密钥长度需 >= 16 字节，当前 {len(key)} 字节")
        self._key: bytes = key

    @staticmethod
    def xor_encrypt(data: bytes, key: bytes) -> bytes:
        """异或加密/解密（对称，加密和解密是同一函数）。"""
        key_len = len(key)
        return bytes(data[i] ^ key[i % key_len] for i in range(len(data)))

    def encrypt(self, data: Dict[str, Any]) -> str:
        """将字典加密为 Base64 字符串。"""
        json_str = json.dumps(data, ensure_ascii=False)
        encrypted = self.xor_encrypt(json_str.encode('utf-8'), self._key)
        return base64.b64encode(encrypted).decode('ascii')

    def decrypt(self, text: str) -> Dict[str, Any]:
        """将 Base64 加密字符串解密回字典。"""
        decoded = base64.b64decode(text)
        decrypted = self.xor_encrypt(decoded, self._key).decode('utf-8')
        return cast(Dict[str, Any], json.loads(decrypted))


class AesCrypto(Crypto):
    """
    AES-128-CBC + HMAC-SHA256 加解密器（基于 cryptography.Fernet）。

    生产级加密，提供：
    - 对称加密，密钥自动从用户 key 派生（SHA256 → url-safe base64）
    - 完整性签名（HMAC-SHA256），防止密文被篡改
    - 内置时间戳，可设置密文有效期（ttl_seconds）

    需要依赖：pip install cryptography

    :param key: 加密密钥，str 或 bytes，任意长度都会被 SHA256 哈希为 32 字节
    :param file_path: 配置文件路径
    :param ttl_seconds: 密文有效秒数，默认 None（永不过期）。过期后解密抛异常。

    密钥生成：
        from cryptography.fernet import Fernet
        Fernet.generate_key()  # 生成 44 字符 base64 密钥
    """

    def __init__(self, key: Union[str, bytes],
                 file_path: str = 'settings_aes.enc',
                 ttl_seconds: Optional[int] = None) -> None:
        super().__init__(file_path)

        # 延迟导入检查
        if not _CRYPTO_AVAILABLE:
            raise ImportError(
                "AesCrypto 需要 cryptography 库，请先安装:\n"
                "  pip install conf_base[aes]\n"
                "  或: pip install cryptography"
            )

        # 密钥处理：支持 Fernet 原始密钥（44 字节 base64）或任意字符串
        if isinstance(key, bytes) and len(key) == 44:
            # 可能是 Fernet 原生密钥，尝试直接解码
            try:
                base64.urlsafe_b64decode(key)
                self._fernet: '_FernetType' = _Fernet(key)
            except Exception:  # noqa
                # 不是合法的 Fernet 密钥，走哈希派生
                self._fernet = _Fernet(self._derive_key(key))
        else:
            self._fernet = _Fernet(self._derive_key(key))

        self._ttl: Optional[int] = ttl_seconds

    @staticmethod
    def _derive_key(key: Union[str, bytes]) -> bytes:
        """从任意输入派生 Fernet 密钥：SHA256 → url-safe base64（32 字节 → 44 字符）。"""
        if isinstance(key, str):
            key = key.encode('utf-8')
        digest = hashlib.sha256(key).digest()  # 32 字节
        return base64.urlsafe_b64encode(digest)  # 44 字符

    def encrypt(self, data: Dict[str, Any]) -> str:
        """加密字典为字符串（JSON → UTF-8 → Fernet → str）。"""
        json_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        # 显式注解收窄：未安装 cryptography 时 _fernet 为 Any
        encrypted: bytes = self._fernet.encrypt(json_bytes)
        return encrypted.decode('ascii')

    def decrypt(self, text: str) -> Dict[str, Any]:
        """解密字符串回字典。密文过期或被篡改时抛 ValueError。"""
        try:
            if self._ttl is not None:
                json_bytes = self._fernet.decrypt(text.encode('ascii'), ttl=self._ttl)
            else:
                json_bytes = self._fernet.decrypt(text.encode('ascii'))
        except Exception as e:
            raise ValueError(f"AES 解密失败（密钥错误 / 密文过期 / 被篡改）: {e}") from e
        return cast(Dict[str, Any], json.loads(json_bytes.decode('utf-8')))
