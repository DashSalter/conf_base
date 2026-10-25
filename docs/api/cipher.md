# 加密器

加密器只负责「文本 ↔ 文本」，位于格式序列化之后。所以密文文件里是「加密后的 JSON 文本」，解密后交给格式解析。

## 内置加密器

| 类 | 算法 | 扩展后缀 | 依赖 |
|---|---|---|---|
| `NoCipher` | 不加密（默认） | 无 | 标准库 |
| `AesGcmCipher` | AES-256-GCM（AEAD） | `.enc` | `cryptography` |
| `ChaCha20Poly1305Cipher` | ChaCha20-Poly1305（AEAD） | `.enc` | `cryptography` |
| `AesCipher` | Fernet（AES-128-CBC + HMAC） | `.enc` | `cryptography` |
| `SignedCipher` | HMAC-SHA256 签名，**不加密** | 无 | 标准库 |

装依赖：

```bash
pip install "conf-base[aes]"
```

## 密钥

两条路：直接传 `key`，或指定读哪个环境变量。

```python
from conf_base import AesGcmCipher

class AppConfig(ConfigBase):
    _path = 'config/app.json'
    _cipher = AesGcmCipher(key_env='CONF_BASE_KEY', key_id='v1')
```

| 加密器 | 默认 `key_env` | 说明 |
|---|---|---|
| `AesGcmCipher` | `CONF_BASE_KEY` | 推荐 |
| `ChaCha20Poly1305Cipher` | `CONF_BASE_KEY` | 与上面共用同一个变量 |
| `SignedCipher` | `CONF_BASE_SIGN_KEY` | 签名用，不与加密共用 |
| `AesCipher` | 无 | **只接受 `key` 参数**，不支持 `key_env`，保留给早期代码 |

密钥规则（`_resolve_key`）：

- 接受 `str` 或 `bytes`，长度必须 **>= 16 字节**，否则抛 `ValueError`
- 统一 SHA-256 派生成 32 字节，所以任意长度的口令都能用，但不要用弱口令
- 环境变量未设置时抛 `ValueError`，不会退化成不加密

!!! danger "密钥不是配置的一部分"
    密钥只从参数或环境变量读，**永远不会写进配置文件**。这是设计上的硬约束：配置文件可以进 git、可以被备份，密钥不行。

## 信封格式

AEAD 加密器的磁盘文件是**明文 JSON 信封**：

```json
{
  "v": 1,
  "alg": "AES-256-GCM",
  "kid": "v1",
  "nonce": "9f3c1b7e...",
  "data": "4B2E9A7C5D1F..."
}
```

| 字段 | 含义 |
|---|---|
| `v` | 信封版本，固定 `1` |
| `alg` | 算法名，解密时必须与加密器一致 |
| `kid` | 密钥标识，解密时必须与 `key_id` 一致 |
| `nonce` | 每次加密随机生成 |
| `data` | 密文（base64） |

信封头是明文，**配置值不可见**。要替换密钥轮换时，`kid` 让你能认出旧文件是用哪把钥匙加密的。

## 后缀剥离

加密器的 `extension` 会先从 `_path` 上剥离，再推断格式：

```python
class AppConfig(ConfigBase):
    _path = 'config/app.yaml.enc'    # 剥离 .enc → 按 .yaml 推断出 YAML
    _cipher = AesGcmCipher()
```

`SignedCipher.extension` 是空串，所以 `app.yaml` 这种文件名不需要改名，签名以注释行的形式追加在文件末尾。

## 解密失败

密钥不对、文件被改动、`alg`/`kid` 不匹配，都会抛 `DecryptError`：

```python
try:
    from myapp.config import AppConfig
except DecryptError as exc:
    print('解密失败，检查 CONF_BASE_KEY 是否与写入时一致')
```

## 签名而不加密

`SignedCipher` 适合「内容可以公开但要能发现篡改」的场景，比如随仓库分发的默认配置：

```python
class AppConfig(ConfigBase):
    _path = 'config/app.yaml'
    _cipher = SignedCipher(key_env='CONF_BASE_SIGN_KEY')
```

签名行追加在文件末尾：

```
# conf_base-signature: v1:<hex>
```

## 协议

```python
from conf_base import BaseCipher

class MyCipher(BaseCipher):
    extension = '.myc'

    def encrypt(self, text: str) -> str: ...
    def decrypt(self, text: str) -> str: ...
```

## API

::: conf_base.cipher
