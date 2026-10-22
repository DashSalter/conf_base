import base64
import datetime as _dt
import hashlib
import hmac
import json
import os
import secrets
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Union, cast

from .Error import ConfigValueError, DecryptError

if TYPE_CHECKING:
    from cryptography.fernet import Fernet as _FernetType

"""
管理配置数据的输入输出
可以使用提供的加密类，或者继承Crypto来实现自己的加密配置文件

格式（明文）：
- PlainJson: 明文 JSON，默认，无依赖
- PlainYaml: 明文 YAML，需要 pip install PyYAML
- PlainToml: 明文 TOML，需要 pip install tomli-w（Python < 3.11 读取还需 tomli）

加密（需要 pip install cryptography）：
- AesCrypto: AES-128-CBC + HMAC-SHA256（Fernet），带完整性校验
- AesGcmCrypto: AES-256-GCM（AEAD），带完整性校验，企业级首选
- ChaCha20Poly1305Crypto: ChaCha20-Poly1305（AEAD），带完整性校验

完整性签名：
- SignedCrypto: HMAC-SHA256 包装器，为 PlainJson/Yaml/Toml 提供防篡改校验
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


def _resolve_key(key: Optional[Union[str, bytes]], key_env: str) -> bytes:
    """
    解析密钥：key 参数优先，其次读取环境变量；统一 SHA-256 派生为 32 字节。

    生产环境建议通过环境变量或密钥管理服务（Vault/KMS）注入高熵密钥，
    不要把密钥写死在源码里。
    """
    if key is None:
        key = os.environ.get(key_env)
    if key is None:
        raise ValueError(
            f"未提供加密密钥：请通过 key 参数传入，或设置环境变量 {key_env}"
        )
    material = key.encode('utf-8') if isinstance(key, str) else key
    if len(material) < 16:
        raise ValueError(f"加密密钥长度需 >= 16 字节，当前 {len(material)} 字节")
    return hashlib.sha256(material).digest()


class _AeadCrypto(Crypto):
    """AEAD 加密基类：AES-256-GCM / ChaCha20-Poly1305 共用信封格式。
    :param key: 密钥（str 或 bytes），为空时读取 key_env 环境变量
    :param key_env: 密钥环境变量名，默认 CONF_BASE_KEY
    :param key_id: 密钥版本标识，写入信封用于审计与轮换
    """

    _ALG_NAME: str = ''

    def __init__(self, key: Optional[Union[str, bytes]] = None,
                 file_path: str = 'settings.enc',
                 key_env: str = 'CONF_BASE_KEY',
                 key_id: str = 'v1') -> None:
        super().__init__(file_path)
        self._key: bytes = _resolve_key(key, key_env)
        self._key_id: str = key_id

    def _cipher(self) -> Any:
        raise NotImplementedError

    def _aad(self) -> bytes:
        return f'{self._ALG_NAME}:{self._key_id}'.encode('utf-8')

    def encrypt(self, data: Dict[str, Any]) -> str:
        normalized = cast(Dict[str, Any], _normalize_value(data, self._ALG_NAME, True, ''))
        nonce = secrets.token_bytes(12)
        encrypted: bytes = self._cipher().encrypt(
            nonce,
            json.dumps(normalized, ensure_ascii=False).encode('utf-8'),
            self._aad(),
        )
        envelope = {
            'v': 1,
            'alg': self._ALG_NAME,
            'kid': self._key_id,
            'nonce': base64.b64encode(nonce).decode('ascii'),
            'data': base64.b64encode(encrypted).decode('ascii'),
        }
        return json.dumps(envelope, ensure_ascii=False, indent=2)

    def decrypt(self, text: str) -> Dict[str, Any]:
        try:
            envelope: Any = json.loads(text)
            if not isinstance(envelope, dict) or envelope.get('v') != 1:
                raise ValueError('不支持的密文版本')
            if envelope.get('alg') != self._ALG_NAME:
                raise ValueError(f"算法不匹配：期望 {self._ALG_NAME}")
            if envelope.get('kid') != self._key_id:
                raise ValueError(f"密钥 ID 不匹配：期望 {self._key_id}")
            nonce = base64.b64decode(envelope['nonce'])
            payload = base64.b64decode(envelope['data'])
            plaintext: bytes = self._cipher().decrypt(nonce, payload, self._aad())
        except Exception as e:
            raise DecryptError(
                f"{self._ALG_NAME} 解密失败（密钥错误 / 密钥 ID 不匹配 / 密文被篡改）: {e}"
            ) from e
        return cast(Dict[str, Any], json.loads(plaintext.decode('utf-8')))


class AesGcmCrypto(_AeadCrypto):
    """
    AES-256-GCM 加解密器（AEAD，企业级首选）。

    - 256 位密钥，GCM 同时提供机密性与完整性校验
    - 每次加密使用随机 12 字节 nonce，相同明文产生不同密文
    - 密文信封包含 alg / kid / nonce，可识别密钥版本
    - 需要依赖：pip install cryptography
    """

    _ALG_NAME = 'AES-256-GCM'

    def _cipher(self) -> Any:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as exc:
            raise ImportError(
                "AesGcmCrypto 需要 cryptography 库，请先安装:\n"
                "  pip install conf_base[aes]\n"
                "  或: pip install cryptography"
            ) from exc
        return AESGCM(self._key)


class ChaCha20Poly1305Crypto(_AeadCrypto):
    """
    ChaCha20-Poly1305 加解密器（AEAD）。

    与 AES-GCM 同级别的认证加密，适合没有 AES 硬件加速的设备。
    需要依赖：pip install cryptography
    """

    _ALG_NAME = 'ChaCha20-POLY1305'

    def _cipher(self) -> Any:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        except ImportError as exc:
            raise ImportError(
                "ChaCha20Poly1305Crypto 需要 cryptography 库，请先安装:\n"
                "  pip install conf_base[aes]\n"
                "  或: pip install cryptography"
            ) from exc
        return ChaCha20Poly1305(self._key)


class SignedCrypto(Crypto):
    """
    HMAC-SHA256 完整性签名包装器（不加密内容）。

    与 PlainJson / PlainYaml / PlainToml 组合使用，用于检测配置文件被手工篡改。
    签名保存在同目录的 `<file_path>.sig`，加载时先校验签名再解析内容。

    :param inner: 被包装的格式加密器
    :param key: 签名密钥，为空时读取 key_env 环境变量
    :param key_env: 签名密钥环境变量名，默认 CONF_BASE_SIGN_KEY
    :param key_id: 密钥版本标识，写入签名文件
    """

    def __init__(self, inner: Crypto,
                 key: Optional[Union[str, bytes]] = None,
                 key_env: str = 'CONF_BASE_SIGN_KEY',
                 key_id: str = 'v1') -> None:
        super().__init__(inner.file_path)
        self._inner: Crypto = inner
        self._key: bytes = _resolve_key(key, key_env)
        self._key_id: str = key_id

    @property
    def signature_path(self) -> str:
        return self.file_path + '.sig'

    def _sign(self, body: str) -> str:
        return hmac.new(self._key, body.encode('utf-8'), hashlib.sha256).hexdigest()

    def encrypt(self, data: Dict[str, Any]) -> str:
        body = self._inner.encrypt(data)
        directory = os.path.dirname(self.signature_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.signature_path, 'w', encoding='utf-8') as fh:
            fh.write(f'{self._key_id}:{self._sign(body)}')
        return body

    def decrypt(self, text: str) -> Dict[str, Any]:
        if not os.path.exists(self.signature_path):
            raise DecryptError(
                f"缺少签名文件 '{self.signature_path}'，无法校验配置文件完整性"
            )
        with open(self.signature_path, 'r', encoding='utf-8') as fh:
            stored = fh.read().strip()
        expected = f'{self._key_id}:{self._sign(text)}'
        if not hmac.compare_digest(stored, expected):
            raise DecryptError(
                f"配置文件 '{self.file_path}' 签名校验失败，内容可能已被篡改"
            )
        return self._inner.decrypt(text)
