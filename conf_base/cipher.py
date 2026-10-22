import base64
import hashlib
import hmac
import json
import os
import secrets
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from .error import DecryptError

"""
配置加密：只处理「文本 -> 文本」，与具体格式（JSON/YAML/TOML）正交。

明文：
- NoCipher: 不加密（默认）

加密（需要 pip install cryptography）：
- AesCipher: AES-128-CBC + HMAC-SHA256（Fernet），带完整性校验
- AesGcmCipher: AES-256-GCM（AEAD），企业级首选
- ChaCha20Poly1305Cipher: ChaCha20-Poly1305（AEAD），适合无 AES 硬件加速的设备

完整性签名：
- SignedCipher: HMAC-SHA256 签名，内容保持明文可读，签名附加在文件末尾
"""

if TYPE_CHECKING:
    from cryptography.fernet import Fernet as _FernetType

# cryptography 是可选依赖，未安装时延迟报错
try:
    from cryptography.fernet import Fernet as _Fernet  # noqa: F401

    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False


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


class BaseCipher(metaclass=ABCMeta):
    """加密接口：接收格式层产出的文本，返回可落盘的文本。"""

    #: 自动生成文件名时追加的后缀，不改变文件名的加密器返回 ''
    extension: str = ''

    @abstractmethod
    def encrypt(self, text: str) -> str:
        """加密（或签名）文本。"""
        ...

    @abstractmethod
    def decrypt(self, text: str) -> str:
        """解密（或校验签名）文本，失败时抛 DecryptError。"""
        ...


class NoCipher(BaseCipher):
    """不加密，原样读写。"""

    def encrypt(self, text: str) -> str:
        return text

    def decrypt(self, text: str) -> str:
        return text


class AesCipher(BaseCipher):
    """
    AES-128-CBC + HMAC-SHA256 加解密器（基于 cryptography.Fernet）。

    生产级加密，提供：
    - 对称加密，密钥自动从用户 key 派生（SHA256 → url-safe base64）
    - 完整性签名（HMAC-SHA256），防止密文被篡改
    - 可设置密文有效期（ttl_seconds），默认永不过期

    需要依赖：pip install cryptography

    :param key: 加密密钥，str 或 bytes，任意长度都会被 SHA256 哈希为 32 字节
    :param ttl_seconds: 密文有效秒数，默认 None（永不过期）。过期后解密抛异常。
    """

    extension = '.enc'

    def __init__(self, key: Union[str, bytes],
                 ttl_seconds: Optional[int] = None) -> None:
        if not _CRYPTO_AVAILABLE:
            raise ImportError(
                "AesCipher 需要 cryptography 库，请先安装:\n"
                "  pip install conf_base[aes]\n"
                "  或: pip install cryptography"
            )

        # 密钥处理：支持 Fernet 原始密钥（44 字节 base64）或任意字符串
        if isinstance(key, bytes) and len(key) == 44:
            try:
                base64.urlsafe_b64decode(key)
                self._fernet: '_FernetType' = _Fernet(key)
            except Exception:  # noqa
                self._fernet = _Fernet(self._derive_key(key))
        else:
            self._fernet = _Fernet(self._derive_key(key))

        self._ttl: Optional[int] = ttl_seconds

    @staticmethod
    def _derive_key(key: Union[str, bytes]) -> bytes:
        """从任意输入派生 Fernet 密钥：SHA256 → url-safe base64（32 字节 → 44 字符）。"""
        if isinstance(key, str):
            key = key.encode('utf-8')
        digest = hashlib.sha256(key).digest()
        return base64.urlsafe_b64encode(digest)

    def encrypt(self, text: str) -> str:
        encrypted: bytes = self._fernet.encrypt(text.encode('utf-8'))
        return encrypted.decode('ascii')

    def decrypt(self, text: str) -> str:
        try:
            if self._ttl is not None:
                plain: bytes = self._fernet.decrypt(text.encode('ascii'), ttl=self._ttl)
            else:
                plain = self._fernet.decrypt(text.encode('ascii'))
        except Exception as e:
            raise DecryptError(
                f"AES 解密失败（密钥错误 / 密文过期 / 被篡改）: {e}"
            ) from e
        return plain.decode('utf-8')


class _AeadCipher(BaseCipher):
    """AEAD 加密基类：AES-256-GCM / ChaCha20-Poly1305 共用信封格式。

    :param key: 密钥（str 或 bytes），为空时读取 key_env 环境变量
    :param key_env: 密钥环境变量名，默认 CONF_BASE_KEY
    :param key_id: 密钥版本标识，写入信封用于审计与轮换
    """

    extension = '.enc'
    _ALG_NAME: str = ''

    def __init__(self, key: Optional[Union[str, bytes]] = None,
                 key_env: str = 'CONF_BASE_KEY',
                 key_id: str = 'v1') -> None:
        self._key: bytes = _resolve_key(key, key_env)
        self._key_id: str = key_id

    def _cipher(self) -> Any:
        raise NotImplementedError

    def _aad(self) -> bytes:
        return f'{self._ALG_NAME}:{self._key_id}'.encode('utf-8')

    def encrypt(self, text: str) -> str:
        nonce = secrets.token_bytes(12)
        encrypted: bytes = self._cipher().encrypt(
            nonce,
            text.encode('utf-8'),
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

    def decrypt(self, text: str) -> str:
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
        return plaintext.decode('utf-8')


class AesGcmCipher(_AeadCipher):
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
                "AesGcmCipher 需要 cryptography 库，请先安装:\n"
                "  pip install conf_base[aes]\n"
                "  或: pip install cryptography"
            ) from exc
        return AESGCM(self._key)


class ChaCha20Poly1305Cipher(_AeadCipher):
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
                "ChaCha20Poly1305Cipher 需要 cryptography 库，请先安装:\n"
                "  pip install conf_base[aes]\n"
                "  或: pip install cryptography"
            ) from exc
        return ChaCha20Poly1305(self._key)


class SignedCipher(BaseCipher):
    """
    HMAC-SHA256 完整性签名（不加密内容）。

    内容保持明文可读，签名以注释行形式附加在文件末尾：

        <原始文本>
        # conf_base-signature: v1:<hex>

    加载时先校验签名再交给格式层解析。任何手工修改都会导致校验失败。

    :param key: 签名密钥，为空时读取 key_env 环境变量
    :param key_env: 签名密钥环境变量名，默认 CONF_BASE_SIGN_KEY
    :param key_id: 密钥版本标识，写入签名行
    """

    extension = ''
    _MARKER = '\n# conf_base-signature: '

    def __init__(self, key: Optional[Union[str, bytes]] = None,
                 key_env: str = 'CONF_BASE_SIGN_KEY',
                 key_id: str = 'v1') -> None:
        self._key: bytes = _resolve_key(key, key_env)
        self._key_id: str = key_id

    def _sign(self, body: str) -> str:
        return hmac.new(self._key, body.encode('utf-8'), hashlib.sha256).hexdigest()

    def encrypt(self, text: str) -> str:
        return f'{text}{self._MARKER}{self._key_id}:{self._sign(text)}\n'

    def decrypt(self, text: str) -> str:
        index = text.rfind(self._MARKER)
        if index == -1:
            raise DecryptError('配置文件中缺少签名信息，无法校验完整性')
        body = text[:index]
        stored = text[index + len(self._MARKER):].strip()
        expected = f'{self._key_id}:{self._sign(body)}'
        if not hmac.compare_digest(stored, expected):
            raise DecryptError('配置文件签名校验失败，内容可能已被篡改')
        return body
