# 存储格式与加密

配置从内存到磁盘要经过两段独立的变换：

```
写入：dict --序列化--> text --加密--> file
读取：file --解密--> text --反序列化--> dict
```

序列化由 `BaseFormat` 负责，加密由 `BaseCipher` 负责，两者正交——可以「YAML + AES-GCM」，也可以「JSON + 不加密」。

## 格式

三种内置格式，通常不需要显式声明，**路径后缀决定格式**：

| 后缀 | 格式 | 需要额外依赖 |
|---|---|---|
| `.json` | `JsonFormat`（默认） | 无 |
| `.yaml` / `.yml` | `YamlFormat` | `pip install "conf-base[yaml]"` |
| `.toml` | `TomlFormat` | `pip install "conf-base[toml]"` |
| 无后缀 | 按 `_format`，缺省 JSON | 无 |

```python
class AppConfig(ConfigBase):
    _path = 'config/app.yaml'        # 后缀推断为 YAML
```

后缀与 `_format` 冲突时抛 `ValueError`，避免「文件叫 .yaml 实际存 JSON」的混乱。无后缀又想用 YAML：

```python
class AppConfig(ConfigBase):
    _path = 'config/app'
    _format = YamlFormat()
```

## 加密器

| 加密器 | 保护什么 | 算法 | 依赖 |
|---|---|---|---|
| `NoCipher` | 不加密（默认） | — | 无 |
| `SignedCipher` | 防篡改，内容仍可读 | HMAC-SHA256 签名 | 无 |
| `AesCipher` | 内容不可见 + 完整性 | Fernet（AES-128-CBC + HMAC） | `cryptography` |
| `AesGcmCipher` | 内容不可见 + 完整性 | AES-256-GCM（AEAD） | `cryptography` |
| `ChaCha20Poly1305Cipher` | 内容不可见 + 完整性 | ChaCha20-Poly1305 | `cryptography` |

**推荐 `AesGcmCipher`**：AEAD 算法，一次运算同时完成加密与认证，没有「先解密再校验」的时间窗口。

`AesCipher`（Fernet）只接受 `key` 参数，不支持 `key_env`，保留给早期代码；新项目直接用 `AesGcmCipher`。

### 加密落盘长什么样

```python
from conf_base import AesGcmCipher

class AppConfig(ConfigBase):
    _path = 'config/app.json.enc'
    _cipher = AesGcmCipher(key='0123456789abcdef0123456789abcdef')

    server = Section('Server')
    secret = server.field(default='change-me')
```

```python
AppConfig.secret.value = 'sk-live-8f2a91c3'
```

磁盘内容是**明文信封**，只有配置值被加密：

```json
{"v": 1, "alg": "AES-256-GCM", "kid": "v1", "nonce": "...", "data": "..."}
```

- `v` / `alg` / `kid`：信封协议版本、算法名、密钥编号
- `nonce`：每次写入随机生成
- `data`：密文

所以「文件被拷走」不等于「密钥泄漏」——但没有密钥确实解不开，改动 `data` 任意一个字节都会抛 `DecryptError`。

### 密钥从哪来

三种来源，优先级从高到低：

```python
# 1. 直接给字面量（仅适合本地玩具项目）
_cipher = AesGcmCipher(key='0123456789abcdef0123456789abcdef')

# 2. 从指定环境变量读（推荐）
_cipher = AesGcmCipher(key_env='APP_CONFIG_KEY')

# 3. 用内置默认变量名 CONF_BASE_KEY
_cipher = AesGcmCipher()
```

密钥要求**至少 16 字节**，内部统一用 SHA-256 派生成 32 字节再交给 AES，所以任意长度 ≥16 的字符串都能用，不需要自己补齐。

`key_id='v1'` 会写进信封的 `kid` 字段，轮换密钥时可以用它区分新旧密文。

### 签名（内容可读，禁止篡改）

不想藏内容、只想防手改时用 `SignedCipher`：

```python
from conf_base import SignedCipher

_cipher = SignedCipher()            # 读环境变量 CONF_BASE_SIGN_KEY
_cipher = SignedCipher(key='...')   # 或直接给密钥
```

签名以一行注释附在文件末尾：

```
# conf_base-signature: v1:<hex>
```

读取时先剥离该行再解析原文；签名不匹配抛 `DecryptError`。注意它**不隐藏内容**，配置值仍然是明文。

### 路径后缀与加密

`_path` 带 `.enc` 时，框架会先剥离这个后缀再推断格式：

| `_path` | 推断格式 |
|---|---|
| `config/app.json` | JSON |
| `config/app.json.enc` | JSON（AES 加密） |
| `config/app.enc` | 按 `_format`，缺省 JSON |

## 自定义格式 / 加密

两个抽象都很小，继承后直接传给 `_format` / `_cipher`：

```python
from conf_base import BaseFormat

class IniFormat(BaseFormat):
    def serialize(self, data):
        ...

    def deserialize(self, text):
        ...
```

```python
class AppConfig(ConfigBase):
    _path = 'config/app.ini'
    _format = IniFormat()
```

完整签名见 [格式 API](../api/format.md) 与 [加密器 API](../api/cipher.md)。
