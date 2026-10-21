# ConfBase

[![Python](https://img.shields.io/badge/python-%3E%3D3.8-blue)](https://www.python.org/)
[![CI](https://github.com/DashSalter/conf_base/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/DashSalter/conf_base/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-65%20passed-brightgreen)](test/)
[![Coverage](https://img.shields.io/badge/coverage-82%25-brightgreen)](test/)

一个通过**类和属性**构建的 Python 配置管理框架，更加便捷与安全地操作与存储配置数据。

---

## 📦 安装

```bash
pip install conf_base
```
---
## 🚀 快速开始

写一个配置类，继承 `metaclass=ConfigMeta`，用 `Section` 和 `add()` 声明配置项：

```python
from conf_base import ConfigMeta, Section, crypto

class TestConfig(metaclass=ConfigMeta):
    # 全局设置
    setting = Section('Setting')
    screen_size = setting.add(
        option='screen_size', # 在配置文件的键名，可以是中文或者其他名称
        default=3,
        validator=lambda x: x > 0       # 设置修改校验，值必须大于 0
    )
    full_screen = setting.add(option='full_screen', default=False)
    bgm_volume  = setting.add(option='bgm_volume',  default=1.0)
    api_key     = setting.add(option='api_key',     default='', read_only=True)

    # 可切换关卡数据（Level / Level2 独立存储）
    level = Section('Level', 'Level2')
    complete_levels = level.add(option='done', default=[1, 2, 3])
```

然后就能像用普通属性一样操作了：

```python
# 读取
print(TestConfig.screen_size.value)       # 3
print(TestConfig.setting.current_options) # {'screen_size': 3, 'full_screen': False, ...}

# 修改（自动类型校验 + 落盘）
TestConfig.screen_size.value = 5          # ✅ 合法
TestConfig.screen_size.value = 0          # ❌ ValueError（validator）
TestConfig.screen_size.value = 'big'      # ❌ TypeError（类型不匹配）

# 快捷操作
TestConfig.screen_size.increment()        # +1 → 6
TestConfig.full_screen.toggle()           # → True
TestConfig.complete_levels.append(4)      # list 代理自动落盘

# 只读保护
TestConfig.api_key.value = 'xxx'          # ❌ WriteError
```

---

## 📖 功能详解

### 1. 读取配置

配置项有多种读取方式，结果完全一致：

```python
# 方式一：通过描述符（推荐，最通用）
TestConfig.screen_size.value

# 方式二：通过 Section 索引
TestConfig.setting['screen_size']
TestConfig.setting.screen_size

# 批量读取
TestConfig.setting.current_options   # 当前值 {'screen_size': 5, 'full_screen': True, ...}
TestConfig.setting.default_options   # 默认值 {'screen_size': 3, ...}
TestConfig.to_dict()                 # 全量导出 {'Setting': {...}, 'Level': {...}}
```

### 2. 修改配置

```python
# 单项修改
TestConfig.screen_size.value = 5
TestConfig.screen_size.set_value(5)    # 等价

# 批量修改（一次性落盘）
TestConfig.setting.update(
    screen_size=7,
    full_screen=True,
    bgm_volume=0.5
)

# 上下文批量（任意操作混合，退出时统一落盘）
with TestConfig.setting.batch():
    TestConfig.screen_size.increment(2)
    TestConfig.full_screen.toggle()
    TestConfig.complete_levels.append(99)
```

### 3. 快捷操作（类型代理）

配置项按默认值类型自动路由到对应代理类：

| 代理类 | 默认值类型 | 专属方法 |
|---|---|---|
| `PropertyProxy` | str / tuple / 其他 | `reset()` `value` `default` `is_default` `on_change()` |
| `NumberProxy` | int / float | 继承以上 + `increment(n=1)` |
| `ListProxy` | list | 继承以上 + `append/extend/insert/remove/pop/clear/sort/reverse` `__getitem__/__setitem__/__delitem__/__len__/__iter__/__contains__` |
| `DictProxy` | dict | 继承以上 + `__setitem__/__delitem__/pop/update/setdefault/clear/keys/values/items` |

**示例：**

```python
# list 操作
TestConfig.complete_levels.append(4)    # 自动浅拷贝 → 修改 → set_value → 落盘
TestConfig.complete_levels[1] = 99      # 同道理
TestConfig.complete_levels.remove(2)

# dict 操作
TestConfig.user_info['name'] = 'Alice'
TestConfig.user_info.pop('age')

# 数字快捷
TestConfig.score.increment()            # +1
TestConfig.score.increment(-5)          # -5
TestConfig.score.value += 10            # 普通赋值也可以

# bool 快捷
TestConfig.full_screen.toggle()         # False → True
```

### 4. 多 Section 切换

一组配置项可以定义在多个 section 下独立存取，用 `set_use_section` 切换：

```python
class TestConfig(metaclass=ConfigMeta):
    level = Section('Level', 'Level2')
    complete_levels = level.add(option='done', default=[1, 2, 3])

# Level 和 Level2 各自独立存储
TestConfig.level.set_use_section('Level')
TestConfig.complete_levels.value = [7, 8, 9]      # 写入 Level.done

TestConfig.level.set_use_section('Level2')
print(TestConfig.complete_levels.value)           # [1, 2, 3]（Level2 的默认值）
TestConfig.complete_levels.value = [4, 5, 6]      # 写入 Level2.done

print(TestConfig.level)
# <Section: Level={done=[7, 8, 9]}, Level2={done=[4, 5, 6]}>

# 两个 section 的数据都在
TestConfig.level.reset()          # 同时重置 Level 和 Level2 为默认值
```

### 5. 变更回调

配置值被修改时自动触发回调，支持按 section 过滤：

```python
# 方式一：普通绑定
TestConfig.complete_levels.on_change(func)

# 方式二：装饰器
@TestConfig.complete_levels.on_change
def func(section, option, value):
    print(f'{section}.{option} = {value}')

# 方式三：装饰器 + 指定 section（只监听 Level2）
@TestConfig.complete_levels.on_change(section='Level2')
def on_level2(section, option, value):
    print(f'Level2 变更了: {value}')

# 方式四：普通 + section
TestConfig.complete_levels.on_change(func2, section='Level')
```

**回调签名：** `callback(section, option, value)`

| 参数 | 类型 | 说明 |
|---|---|---|
| `section` | str | 实际发生变更的 section（多 section 配置块时自动区分） |
| `option` | str | 配置项名称 |
| `value` | Any | 修改后的新值 |

**触发时机：** `value=` / `set_value()` / `update()` / 所有代理写操作 / `toggle()` / `increment()` / `reset()`

### 6. 重置

```python
# 单项重置
TestConfig.screen_size.reset()

# Section 级重置（批量，N 个配置项 1 次落盘）
TestConfig.setting.reset()

# 多 section 配置块重置（同时重置所有分支）
TestConfig.level.reset()   # Level → 默认, Level2 → 默认
```

### 7. 校验机制

配置项写入时依次经过三层校验：

```
类型匹配 → validator → read_only
```

```python
# 类型锁定（内置，无法关闭）
TestConfig.screen_size.value = 'abc'    # ❌ ConfigTypeError

# 自定义 validator
TestConfig.port = setting.add('port', default=3306, validator=lambda x: 1 <= x <= 65535)
TestConfig.port.value = 999999          # ❌ ConfigValueError

# 只读保护
TestConfig.api_key = setting.add('api_key', default='secret', read_only=True)
TestConfig.api_key.value = 'xxx'        # ❌ WriteError
```

### 8. 多配置类独立文件

每个配置类独立拥有 `JsonConfig` 实例和配置文件，数据完全隔离：

```python
class GameConfig(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson('game_settings.json')
    ...

class ServerConfig(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson('server_settings.json')
    ...
```

### 9. 外部修改自动重载

默认情况下，配置数据只在类定义时从文件加载一次，之后所有读写都走内存，性能最优。

如果你的场景需要**外部进程修改配置文件后程序自动生效**（如服务器运维时手动改配置不需要重启），开启 `_auto_reload`：

```python
class ServerConfig(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson('server.json')
    _auto_reload = True   # 每次读取都从文件重新加载

    port = Section('Net')
    listen_port = port.add('listen_port', default=8080)
```

开启后**每次 `.value` 读取**都会重新解析文件，有轻微性能开销。适合：
- 运维手动改配置文件让程序生效
- 多进程共享配置文件

不适合：
- 高频读取的游戏客户端场景（默认关闭）

---

## 🌱 环境变量覆盖

生产部署时常用**环境变量 > 配置文件 > 默认值**的优先级链，方便 Docker/K8s 等容器化场景注入敏感配置（数据库密码、API Key 等），无需手动改配置文件。

### 启用方式

在 `add()` 里指定 `env_key` 参数：

```python
class AppConfig(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson('app.json')

    server = Section('Server')
    host = server.add('host', default='0.0.0.0', env_key='MYAPP_HOST')
    port = server.add('port', default=8080, env_key='MYAPP_PORT')
    debug = server.add('debug', default=False, env_key='MYAPP_DEBUG')
    db_pass = server.add('db_pass', default='', env_key='MYAPP_DB_PASS', read_only=True)

    cache = Section('Cache')
    hosts = cache.add('hosts', default=['127.0.0.1:6379'], env_key='MYAPP_REDIS_HOSTS')
```

### 优先级

```
环境变量 MYAPP_PORT=9090    →  优先，内存中生效
         ↓ 未设置
配置文件 app.json → port=8080  →  其次
         ↓ 不存在
代码 default=3306              →  兜底
```

### 类型转换

环境变量永远是字符串，框架会按 `default` 的类型自动解析：

| default 类型 | 环境变量示例 | 解析结果 |
|---|---|---|
| `int` | `"8080"` | `8080` |
| `float` | `"0.5"` | `0.5` |
| `bool` | `"true"` / `"1"` / `"yes"` | `True` |
| `bool` | `"false"` / `"0"` / `"no"` | `False` |
| `list` | `'["10.0.0.1", "10.0.0.2"]'` | `["10.0.0.1", "10.0.0.2"]`（JSON 解析） |
| `dict` | `'{"host": "db.local"}'` | `{"host": "db.local"}`（JSON 解析） |
| `str` | `"hello"` | `"hello"` |

解析失败（如 `"not_a_number"` 解析 int）会立即抛出明确的 `ConfigValueError`。

### 写入保护

环境变量覆盖的值**禁止回写配置文件**——避免污染文件：

```python
os.environ['MYAPP_PORT'] = '9090'

AppConfig.port.value = 8080
# ❌ WriteError: Setting.port 由环境变量 MYAPP_PORT 覆盖，禁止回写配置文件。
#    请移除环境变量后再修改。
```

要修改该值，先 `unset MYAPP_PORT` 或 `del os.environ['MYAPP_PORT']`。

### 检测环境变量覆盖

```python
AppConfig.port.has_env_override   # True
AppConfig.port.env_key            # 'MYAPP_PORT'
```

### 常见使用场景

```bash
# Docker 启动注入
docker run -e MYAPP_PORT=9090 -e MYAPP_DEBUG=true myapp

# K8s ConfigMap / Secret
env:
  - name: MYAPP_PORT
    valueFrom:
      secretKeyRef:
        name: app-secret
        key: port

# Shell 临时设置（开发调试）
export MYAPP_DEBUG=true
python main.py
```

---

## 🔐 加密存储

通过 `_crypto` 指定加密器，内置七种：

| 加密器 | 级别 | 依赖 | 适用场景 |
|---|---|---|---|
| `PlainJson` | 明文 JSON | 零依赖 | 开发调试、配置无敏感数据 |
| `PlainYaml` | 明文 YAML | `pip install conf_base[yaml]` | 需要注释、可读性更高的配置 |
| `PlainToml` | 明文 TOML | `pip install conf_base[toml]` | 手工编辑、强类型表格配置 |
| `SignedCrypto` | 明文 + HMAC-SHA256 签名 | 零依赖 | 内容可读但禁止篡改 |
| `AesCrypto` | AES-128-CBC + HMAC（Fernet） | `pip install conf_base[aes]` | 兼容既有数据、常规加密 |
| `AesGcmCrypto` | **AES-256-GCM（AEAD）** | `pip install conf_base[aes]` | 企业级首选，机密性 + 完整性 |
| `ChaCha20Poly1305Crypto` | ChaCha20-Poly1305（AEAD） | `pip install conf_base[aes]` | 无 AES 硬件加速的设备 |

### PlainJson（默认，明文 JSON）

```python
_crypto = crypto.PlainJson('settings.json')
```

### PlainYaml（明文 YAML）

```bash
pip install conf_base[yaml]
```

```python
_crypto = crypto.PlainYaml('settings.yaml')
```

### PlainToml（明文 TOML）

```bash
pip install conf_base[toml]
```

```python
_crypto = crypto.PlainToml('settings.toml')
```

### 数据格式限制

YAML / TOML 的表达能力与 JSON 不同，写入前会统一校验，避免序列化器抛出难以理解的底层异常：

| 数据情况 | 行为 |
|---|---|
| `tuple` 值 | 自动转为 `list`（与 JSON 一致），读取回来是 `list` |
| 字典的非字符串键（如元组键） | 抛出 `ConfigValueError`，错误信息指出具体位置 |
| `set` / `bytes` / 自定义对象 | 抛出 `ConfigValueError` |
| `None` | YAML 支持；**TOML 不支持 null**，抛出 `ConfigValueError` |
| `datetime` / `date` / `time` | YAML、TOML 原生支持 |

> TOML 没有 null 类型，且所有键必须是字符串。配置项默认值可能为 `None` 时，请改用 YAML 或 JSON。

### SignedCrypto（明文 + HMAC-SHA256 签名，零依赖）

适合“配置需要人能读懂，但不允许被改动”的场景（如只读下发配置）：

```python
_crypto = crypto.SignedCrypto(
    crypto.PlainYaml('settings.yaml'),
    key='signing-key',          # 也可省略，从 CONF_BASE_SIGN_KEY 环境变量读取
)
# 写入时同时生成 settings.yaml 与 settings.yaml.sig
# 加载时先校验签名：文件被手工改动、签名缺失、密钥不符都会抛 DecryptError
```

> 签名只保证完整性，不隐藏内容。签名密钥泄露后可以重新签名，因此密钥仍需通过环境变量或 KMS 注入。

### AesGcmCrypto（AES-256-GCM，AEAD，企业级首选）

```bash
pip install conf_base[aes]
```

```python
_crypto = crypto.AesGcmCrypto(
    key='my-app-master-key',    # 可省略，从 CONF_BASE_KEY 环境变量读取
    file_path='settings.enc',
    key_id='v1',                # 密钥版本标识，写入密文信封，便于轮换与审计
)
```

- 256 位密钥 + GCM 认证加密，同时保证**机密性**与**完整性**；密钥错误、密文被篡改、`key_id` 不匹配都会抛 `DecryptError`
- 每次写入使用随机 12 字节 nonce，相同明文也会产生不同密文
- 密文信封为 JSON：`{"v":1, "alg":"AES-256-GCM", "kid":"v1", "nonce":"...", "data":"..."}`
- 密钥长度需 >= 16 字节，框架用 SHA-256 派生为固定 32 字节

### ChaCha20Poly1305Crypto（ChaCha20-Poly1305，AEAD）

```python
_crypto = crypto.ChaCha20Poly1305Crypto(key='my-app-master-key', file_path='settings.enc')
```

与 AES-GCM 同级别的认证加密，在**没有 AES 硬件加速**的设备（部分 ARM/MIPS、老旧 x86）上性能更好。用法与密文信封格式和 `AesGcmCrypto` 完全一致，但两者不能混读（信封中的 `alg` 字段会校验）。

### AesCrypto（AES-128-CBC + HMAC-SHA256，生产级）

需要依赖：

```bash
pip install conf_base[aes]
# 或
pip install cryptography
```

用法——密钥支持**任意字符串**（自动 SHA256 派生）或 Fernet 原生密钥：

```python
# 方式 1：任意字符串密钥（推荐，方便记忆）
_crypto = crypto.AesCrypto(
    key='my-app-master-key',
    file_path='settings.enc'
)

# 方式 2：Fernet 原生密钥（推荐存环境变量）
from cryptography.fernet import Fernet
key = os.environ['APP_SECRET_KEY']   # 从环境变量读取
_crypto = crypto.AesCrypto(key=key, file_path='settings.enc')

# 方式 3：带有效期（密文超过 ttl_seconds 自动拒绝解密）
_crypto = crypto.AesCrypto(key='xxx', file_path='settings.enc', ttl_seconds=3600 * 24)
```

**密钥长度**：任意输入（str/bytes）都会被 SHA256 哈希为 32 字节密钥，用户不需要手动算。

**密文保护**：自动附加 HMAC-SHA256 签名，密文被篡改会立即解密失败（抛出 `ValueError`）。

### 密钥安全建议

| 方式 | 写法 | 说明 |
|---|---|---|
| ✅ 环境变量（内置支持） | `AesGcmCrypto(file_path='settings.enc')`，配合 `CONF_BASE_KEY` | 密钥不落源码，容器/K8s 友好 |
| ✅ 密钥管理服务 | `key=vault.get('app/secret')` | 生产推荐，支持轮换、审计、最小权限 |
| ⚠️ 硬编码 | `key='hardcoded_key_in_source'` | 仅限本地调试 |
| ❌ 提交到 git | 任何形式的明文密钥 | 会随仓库历史永久泄露 |

```python
# AEAD 加密器：key 为空时读取 key_env 指定的环境变量（默认 CONF_BASE_KEY）
_crypto = crypto.AesGcmCrypto(file_path='settings.enc', key_env='MYAPP_CONF_KEY')

# 签名包装器：默认读取 CONF_BASE_SIGN_KEY
_crypto = crypto.SignedCrypto(crypto.PlainJson('settings.json'), key_env='MYAPP_SIGN_KEY')

# 密钥来自 KMS / Vault
_crypto = crypto.AesGcmCrypto(key=vault.get('app/secret'), file_path='settings.enc')
```

### 未安装 cryptography 的提示

```python
_crypto = crypto.AesCrypto(key='xxx', file_path='settings.enc')
# ImportError: AesCrypto 需要 cryptography 库，请先安装:
#   pip install conf_base[aes]
#   或: pip install cryptography
```

### 自定义加密器

继承 `Crypto` 抽象基类，实现 `encrypt` 和 `decrypt`：

```python
class MyCrypto(crypto.Crypto):
    def encrypt(self, data: dict) -> str:
        # 把 dict 转成密文字符串
        ...
    def decrypt(self, content: str) -> dict:
        # 把密文字符串还原成 dict
        ...
```

---

## 🔄 Schema 版本迁移

长期维护项目时，配置文件的字段名、section 结构会随代码迭代而变化。`conf_base` 提供 schema 迁移机制：配置文件自动带版本号，启动时按链顺序调用迁移函数，把旧版本数据平滑升级到新版本。

### 核心概念

配置文件根 level 会存 `_schema_version` 字段：

```json
{
    "_schema_version": 2,
    "Setting": {
        "bgm": 0.5,
        "screen_size": 7
    }
}
```

配置类声明目标版本号和迁移函数字典：

```python
class TestConfig(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson('settings.json')
    _schema_version = 2          # 目标版本
    _migrate = {1: migrate_v1_to_v2}   # 迁移函数链

    setting = Section('Setting')
    bgm = setting.add('bgm', default=1.0)
    ...
```

### 迁移函数的签名

```python
def migrate_v1_to_v2(data: dict) -> dict:
    """
    接收旧版本的完整配置 dict，返回迁移后的 dict。
    - data 包含所有 section 和 option
    - 框架会自动处理 _schema_version 的版本号更新
    - 不需要迁移的 section/option 保持原样即可
    """
    if 'Setting' in data:
        s = data['Setting']
        # 字段重命名
        if 'bgm_volume' in s:
            s['bgm'] = s.pop('bgm_volume')
    return data
```

### 多版本链式迁移

迁移函数字典按版本号排序依次调用，支持跨多个版本：

```python
def migrate_v1_to_v2(data):
    # v1→v2：字段重命名
    if 'Setting' in data and 'bgm_volume' in data['Setting']:
        data['Setting']['bgm'] = data['Setting'].pop('bgm_volume')
    return data

def migrate_v2_to_v3(data):
    # v2→v3：Setting 拆成 Audio + Display
    if 'Setting' in data:
        s = data.pop('Setting')
        data['Audio'] = {'bgm': s.pop('bgm', 1.0)}
        data['Display'] = {'screen_size': s.pop('screen_size', 3)}
    return data

class ConfigV3(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson('settings.json')
    _schema_version = 3
    _migrate = {
        1: migrate_v1_to_v2,   # 先跑 v1→v2
        2: migrate_v2_to_v3,   # 再跑 v2→v3
    }
    ...
```

### 迁移规则

| 场景 | 行为 |
|---|---|
| 新文件首次启动 | 直接用目标版本号创建，不触发迁移 |
| 文件版本 < 目标版本 | 按 `_migrate` 顺序逐个调用，迁移后自动落盘 |
| 文件版本 = 目标版本 | 不迁移 |
| 文件版本 > 目标版本 | 不迁移（用户可能手动改过），只同步版本号 |
| 缺少某步迁移函数 | 启动即抛出 `ValueError`，明确提示缺哪一步 |

### 迁移后新增字段怎么办

迁移函数只负责"搬运旧数据"。新配置类里声明但迁移后仍不存在的 option，**ConfigMeta 会用 `default` 自动补齐**——你不需要在迁移函数里手动填默认值。

### `to_dict()` 过滤内部字段

`_schema_version` 是框架内部字段，`to_dict()` 导出时会自动过滤掉所有 `_` 开头的 key：

```python
TestConfig.to_dict()
# {'Setting': {'bgm': 0.5, 'screen_size': 7}}  ← _schema_version 不出现
```

---

## 📋 完整 API 参考

### Section

| 方法/属性 | 说明 |
|---|---|
| `Section(section, *sections)` | 创建配置块，支持多 section 名 |
| `.add(option, default, validator, read_only, env_key)` | 添加配置项，返回 `ConfigProperty` |
| `.set_use_section(name)` | 切换当前生效的 section（多 section 时） |
| `.reset()` | 批量重置所有配置项为默认值 |
| `.update(**kwargs)` | 批量写入配置项 |
| `.batch()` | 上下文管理器，退出时一次性落盘 |
| `.current_options` | 当前值字典（多 section 时嵌套返回） |
| `.default_options` | 默认值字典 |
| `.section_tuple` | 所有 section 名称元组 |
| `str(section)` | 格式化展示所有 section 当前值 |
| `'key' in section` | 判断 option 是否存在 |
| `section['key']` / `section.key` | 读取当前值 |

### ConfigProperty（配置项描述符）

| 方法/属性 | 说明 |
|---|---|
| `.value` | 当前值（读写） |
| `.default` | 默认值（只读） |
| `.section` | 当前 section 名 |
| `.option` | 配置项名 |
| `.section_tuple` | 所属 section 的所有名称 |
| `.set_value(value)` | 写入值（显式调用） |
| `.reset()` | 重置为默认值 |
| `.is_default` | 当前值是否等于默认值 |
| `.on_change(callback, section=None)` | 注册变更回调，返回 callback 支持装饰器写法 |
| `.validator` | 校验函数（只读） |
| `.read_only` | 是否只读（只读） |

### 配置类（类级）

| 方法/属性 | 说明 |
|---|---|
| `TestConfig.to_dict()` | 全量导出所有配置的深拷贝 |
| `TestConfig.xxx` | 访问配置项描述符（最常用） |

---

## ⚠️ 异常体系

所有 `conf_base` 异常都继承自 `ConfBaseError`，可统一捕获：

```python
import conf_base.Error as E

try:
    TestConfig.port.value = 999999
except E.ConfBaseError as e:
    print(f'配置错误: {e}')
```

| 异常 | 继承自 | 触发场景 |
|---|---|---|
| `ConfBaseError` | `Exception` | 所有框架异常的基类 |
| `WriteError` | `ConfBaseError` | 写入只读配置项 |
| `ParseError` | `ConfBaseError, ValueError` | 配置文件内容损坏，无法解析 |
| `ConfigTypeError` | `ConfBaseError, TypeError` | 写入值的类型与默认值不一致 |
| `ConfigValueError` | `ConfBaseError, ValueError` | 写入值未通过 validator 校验 |

---

## ⚡ 性能基准

基于 Windows 本地 SSD、Python 3.x、JSON 文件（~300 字节）的实测数据，可参考量级估算自己的场景：

| 操作 | 单次耗时 | 说明 |
|---|---|---|
| 单值读取 | **0.3 µs** | 纯内存字典访问，零 IO |
| 三项连续读 | **1.0 µs** | 三个配置项连续取值 |
| 单次落盘（1 项） | **2.2 ms** | 序列化 + 临时文件 + `os.replace` |
| 批量落盘（3 项/批） | **2.3 ms** | 3 项合并为 1 次文件 IO |
| update 批量写（3 项） | **2.2 ms** | 同上 |

### 关键结论

- **读永远是零成本**：所有读取都是内存字典 O(1) 查找，不碰文件
- **写瓶颈在磁盘**：2ms/次（含原子写入开销），批量落盘几乎不增加耗时
- **高频写场景用 `batch()`**：100 次修改如果各写各的 = 200ms；包在 `batch()` 里 ≈ 2ms
- **测试脚本**：`python test/test_perf.py` 自己跑一遍

### 不同规模文件对落盘的影响

| 文件大小 | 落盘耗时 |
|---|---|
| < 1 KB（常见配置） | ~2 ms |
| ~10 KB | ~5 ms |
| ~100 KB | ~30 ms |

> 如果配置文件会超过 100 KB，建议拆分或用 Redis。

---

## ✅ 测试覆盖

**65 个用例全部通过，总覆盖率 82%**（pytest + pytest-cov）

| 模块 | 覆盖率 | 覆盖重点 |
|---|:---:|---|
| `Error.py` | **100%** | 全部异常类 |
| `__init__.py` | **100%** | 导出符号 |
| `metaclass.py` | **92%** | 元类、默认值初始化、schema 迁移 |
| `crypto.py` | **87%** | PlainJson、YAML、TOML、AesCrypto、AES-GCM、ChaCha20-Poly1305、HMAC 签名 |
| `descriptor.py` | **84%** | 描述符、类型代理、回调 |
| `section.py` | **76%** | Section、update/reset、字典访问 |
| `json_config.py` | **75%** | 读写、批量、filelock |
| `test_typing.py` | — | `mypy --strict` 类型检查 |

运行方式：

```bash
pip install pytest pytest-cov
python -m pytest test/ -v --cov=conf_base --cov-report=term-missing
```

未覆盖代码主要是：错误分支的防御性代码、不同平台的 filelock 路径、部分 `__str__`/`__repr__`。

---

## 🔄 持续集成（CI）

仓库已配置 GitHub Actions 流水线，配置文件见 [ci.yml](https://github.com/DashSalter/conf_base/blob/master/.github/workflows/ci.yml)，每次 push 到 `main` / `master`（含 `v*` tag）或提交 PR 都会自动触发。

| 作业 | 内容 | 运行环境 |
|---|---|---|
| `test` | `pytest test/ -v` | Ubuntu 22.04 × Python 3.8 / 3.9 / 3.10 / 3.11 / 3.12 |
| `typecheck` | `mypy conf_base`（strict 模式） | Python 3.12 |
| `build` | `python -m build`，安装 wheel 后验证可导入 | Python 3.12 |
| `publish` | 对比 `setup.py` 版本与 PyPI 最新版本，仅当本地版本更大时发布 | Trusted Publishing（OIDC，无需 token） |

查看运行状态与历史记录：

- 流水线页面：https://github.com/DashSalter/conf_base/actions/workflows/ci.yml
- 状态徽章：`https://github.com/DashSalter/conf_base/actions/workflows/ci.yml/badge.svg?branch=master`

本地复现 CI 的全部检查：

```bash
pip install -e .[dev]
python -m pytest test/ -v --cov=conf_base
python -m mypy conf_base
python -m build
```

> Gitee 仓库（https://gitee.com/kuangjianke/conf_base）为镜像，CI 结论以 GitHub Actions 为准。

---

## 💡 最佳实践

**1. 让配置类在 `main()` 入口处被 import**

配置文件会在类定义时自动创建和初始化。如果配置类定义在子模块里，确保入口模块会 import 它，否则文件不会生成。

**2. 用 `batch()` 合并高频写入**

```python
# 循环里频繁修改 → 用 batch 包起来减少 IO
with TestConfig.setting.batch():
    for item in items:
        TestConfig.complete_levels.append(item)
```

**3. validator 保持简单、纯函数**

```python
# ✅ 好：纯校验
validator=lambda x: x >= 0

# ❌ 不好：里面有副作用或 IO
validator=lambda x: validate_remote(x)
```

**4. read_only 只防运行时误改，不防文件级篡改**

`read_only` 在 API 层拦截 `value=` / `set_value()` 写入。若配置文件本身可能被外部进程或人工修改，需要叠加密码学完整性保护：

```python
# 方案 A：明文 + 签名（人能读，改了就报错）
_crypto = crypto.SignedCrypto(crypto.PlainJson('settings.json'), key='sign-key')

# 方案 B：AEAD 加密（内容也不可见，且自带完整性校验）
_crypto = crypto.AesGcmCrypto(file_path='settings.enc')
```

> 加载时与默认值对比**无法解决**该问题：合法修改与恶意篡改在值层面无法区分（攻击者可以把 `api_key` 改成任意合法字符串）。只有 HMAC 签名或 AEAD 加密能真正检测篡改。

如果需要热更新密钥，把它移出 `read_only`，配合 `on_change` 回调通知应用重载。

**5. 配置文件损坏时用默认值重建**

`ParseError` 捕获后可以备份损坏文件再重建：

```python
import conf_base.Error as E
try:
    ... # 启动配置类
except E.ParseError:
    print('配置文件损坏，已用默认值重建')
    # 让 ConfigMeta 自动用默认值重建文件
```

---

## � 并发安全

框架内置**双重锁保护**，覆盖线程和进程两种并发场景：

| 层级 | 机制 | 防护对象 | 状态      |
|---|---|---|---------|
| 线程间 | `threading.RLock`（内置） | 同进程多线程读写冲突 | ✅ 始终生效  |
| 进程间 | `filelock`（可选依赖） | 多进程/多容器共享同一配置文件 | ⚙️ 依赖安装 |

### 安装 filelock

```bash
pip install conf_base[filelock]
# 或者
pip install filelock
```

未安装时进程间保护自动跳过，单进程/多进程不共享文件的场景无需关心。

### 默认开启，可关闭

```python
# 关闭进程间锁（单进程或多进程各用各的文件时）
class AppConfig(metaclass=ConfigMeta):
    _use_file_lock = False
    ...

# 自定义锁超时（默认 10 秒）
class AppConfig2(metaclass=ConfigMeta):
    _lock_timeout = 30.0  # 等待锁 30 秒
    ...
```

### 锁的作用范围

| 操作 | 线程锁 | 文件锁 |
|---|---|---|
| `load_config`（启动加载） | ✅ | ✅ |
| `write_config`（落盘） | ✅ | ✅ |
| `set_option` / `get_option` 等内存操作 | ✅ | — （不需要） |
| `batch()` 批量落盘 | ✅ | ✅ |

### 进程间竞争场景

```
进程 A: 写 tmp → os.replace(tmp, settings.json)
进程 B: 写 tmp → os.replace(tmp, settings.json)   ← 可能覆盖 A！
```

文件锁让 B 等 A 写完再读最新内容再写，不会丢失。

### 锁超时处理

等待锁超时会抛 `TimeoutError`：

```python
try:
    class AppConfig(metaclass=ConfigMeta):
        _lock_timeout = 5.0  # 5 秒
        ...
except TimeoutError as e:
    print(f'配置文件被占用: {e}')
```

### 锁文件说明

启用 filelock 后，配置文件旁会出现 `settings.json.lock` 文件，这是正常的锁标记。进程退出时自动清理，不要手动删除（否则锁会失效）。

---

## �📁 项目结构

```
conf_base/
├── __init__.py       # 对外导出
├── descriptor.py     # ConfigProperty + 类型代理
├── section.py        # Section 配置块
├── metaclass.py      # ConfigMeta 元类
├── json_config.py    # 文件读写 + 批量落盘
├── crypto.py         # 加解密器（PlainJson / PlainYaml / PlainToml / SignedCrypto / AesCrypto / AesGcmCrypto / ChaCha20Poly1305Crypto）
└── Error.py          # 统一异常体系
```

---

## 📜 License

MIT License
