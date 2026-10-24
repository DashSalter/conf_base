# ConfBase

[![Python](https://img.shields.io/badge/python-%3E%3D3.8-blue)](https://www.python.org/)
[![CI](https://github.com/DashSalter/conf_base/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/DashSalter/conf_base/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-112%20passed-brightgreen)](test/)
[![Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen)](test/)

conf_base 是一个基于 Section-Field 模型的 Python 配置管理库，支持多格式、加密、热更新与 Schema 迁移。

## 与其他方案怎么选

| 能力 | conf_base | python-dotenv | dynaconf | pydantic-settings | Hydra |
|---|---|---|---|---|---|
| 声明式 schema + 默认值 | ✅ | ❌ | ⚠️ | ✅ | ✅ |
| JSON / YAML / TOML | ✅ | ❌（仅 `.env`） | ✅ | ✅（需装格式插件） | ⚠️（以 YAML 为主） |
| 环境变量覆盖 | ✅ | ✅ | ✅ | ✅ | ⚠️（需自写 resolver） |
| 内置加密落盘 | ✅ AES-GCM / ChaCha20-Poly1305 | ❌ | ❌ | ❌ | ❌ |
| 防篡改签名 | ✅ HMAC-SHA256 | ❌ | ❌ | ❌ | ❌ |
| Schema 版本迁移 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 批量写入 / 变更回调 | ✅ | ❌ | ⚠️ | ❌ | ❌ |
| 运行时必需依赖 | 0 | 0 | 有 | pydantic v2 | omegaconf 等 |
| 上手成本 | 低 | 低 | 中 | 中 | 高 |

一句话选型：

- 只要读写 `.env` → `python-dotenv`
- 需要强类型校验、嵌套模型、序列化 → `pydantic-settings` / `pydantic`
- 需要多环境、多层合并、远程后端 → `dynaconf`
- 需要实验配置矩阵扫描、多组参数组合 → `Hydra`
- **本地单机配置文件 + 加密 / 签名 / 版本迁移 / 零依赖** → `conf_base`

> 表中 ✅/⚠️ 依据各项目官方文档整理（2026-10），以各自最新版为准；如有出入欢迎提 issue 纠正。

## 适用场景

**适合**

- 桌面应用 / 游戏客户端的本地配置
- CLI 工具、脚本的参数与偏好设置
- 单机服务或小型 Web 服务的配置文件
- 配置需要 JSON / YAML / TOML 多种格式
- 需要配置加密、防篡改签名、版本迁移
- 需要批量修改、变更回调、按分组重置

**不适合**

| 场景 | 更合适的选择 |
|---|---|
| 分布式配置中心、多节点实时同步 | Nacos / Apollo / Consul / etcd |
| Redis / MySQL 等远程存储 | 配置中心，或自行实现 `BaseFormat` / `BaseCipher` 适配 |
| 每秒级高频写入 | 数据库、配置中心 |
| 超大配置或二进制数据 | 数据库、对象存储 |
| 复杂嵌套模型、字段级校验 | pydantic / pydantic-settings |
| 多用户并发编辑同一文件 | 数据库 + 乐观锁 |
| 运行时动态增删配置项 | 动态配置中心 |
| 配置类之间继承复用配置项 | 直接继承 `ConfigBase`，重复声明配置项（配置类禁止相互继承） |
| 配置审计、权限、回滚 | 配置中心、密钥管理服务 |

> ConfBase 是「本地文件 + 声明式配置」的轻量工具，不是配置中心客户端，也不是 pydantic 的替代品。

## 安装

```bash
pip install conf_base
```

按需安装可选依赖：

| 功能 | 安装命令 |
|---|---|
| YAML 格式 | `pip install conf_base[yaml]` |
| TOML 格式 | `pip install conf_base[toml]` |
| 加密 / 签名 | `pip install conf_base[aes]` |
| 多进程文件锁 | `pip install conf_base[filelock]` |

## 快速开始

以游戏客户端配置为例：

```python
from conf_base import ConfigBase, Section


class GameConfig(ConfigBase):
    # 配置文件路径；格式按后缀推断（无后缀时默认 JSON）
    _path = 'config/game.json'

    # 画面
    screen = Section('Screen')
    width = screen.field(default=1280, validator=lambda v: v >= 800)
    height = screen.field(default=720)
    fullscreen = screen.field(default=False)

    # 声音
    audio = Section('Audio')
    bgm_volume = audio.field(default=0.8, validator=lambda v: 0 <= v <= 1)
    mute = audio.field(default=False)

    # 存档
    save = Section('Save')
    unlocked_levels = save.field(default=[1])
```

类定义时自动创建 `config/game.json`，并把缺失的默认值写入文件：

```json
{
    "_schema_version": 1,
    "Screen": {
        "width": 1280,
        "height": 720,
        "fullscreen": false
    },
    "Audio": {
        "bgm_volume": 0.8,
        "mute": false
    },
    "Save": {
        "unlocked_levels": [
            1
        ]
    }
}
```

结构一目了然：顶层是 Section 名，第二层是配置项名，值与代码中的 `default` 完全对应。`_schema_version` 是内部字段，用于配置版本迁移，`to_dict()` 不会导出它。

之后像操作普通属性一样读写：

```python
# 读取
GameConfig.width.value                      # 1280
GameConfig.screen.current_options           # {'width': 1280, 'height': 720, ...}

# 修改：自动校验类型与 validator，并落盘
GameConfig.width.value = 1920
GameConfig.bgm_volume.value = 0.5
GameConfig.bgm_volume.value = 1.5           # ❌ ConfigValueError（超出 0~1）

# 类型专属快捷操作
GameConfig.fullscreen.toggle()              # False -> True
GameConfig.width.increment(100)             # 1920 -> 2020
GameConfig.unlocked_levels.append(2)        # [1] -> [1, 2]

# 批量修改：所有配置项只落盘一次
GameConfig.audio.update(bgm_volume=0.6, mute=True)

# 全量导出
GameConfig.to_dict()
# {'Screen': {...}, 'Audio': {...}, 'Save': {...}}
```

三个可直接运行的完整示例（CLI 工具、游戏客户端、服务端加密 + 迁移）见 [`examples/`](examples/)，
每个文件都能单独执行：

```bash
python examples/cli_config.py
python examples/game_config.py
python examples/secure_server_config.py
```

## 核心用法

### 1. 声明配置项

`Section.field()` 的参数：

```python
port = server.field(
    default=8080,                          # 默认值，同时决定配置值的类型
    option='port',                         # 配置键名，省略时自动使用左侧变量名
    validator=lambda v: 1 <= v <= 65535,   # 可选，返回 False 时拒绝写入
    read_only=False,                       # 可选，True 时禁止运行时修改
    env_key='APP_PORT',                    # 可选，允许环境变量覆盖
)
# 本例 option 与变量名相同，也可省略；需要不同键名时改成 option='listen_port'
# IDE 能通过 __set_name__ 自动推导属性名，field() 返回类型感知的 Proxy 对象（BoolProxy/NumberProxy/ListProxy/DictProxy），提供了 toggle()、increment()、append() 等语义化操作
```

配置值的类型始终锁定为 `default` 的类型，写入其他类型会抛 `ConfigTypeError`。

### 2. 读取

四种方式结果完全一致：

```python
GameConfig.width.value                  # 描述符方式
GameConfig.screen['width']              # Section 索引
GameConfig.screen.width                 # Section 属性（只读语法）
GameConfig.screen.current_options       # 整个 Section
```

> `section.width` 只用于读取。写入必须用 `section['width'] = 1600` 或 `section.width.value = 1600`；
> `section.width = 1600` 会抛 `WriteError`，避免创建一个不落盘的实例属性把配置项遮住。

`default_options` / `current_options` / `to_dict()` 返回的都是副本，修改返回值不会影响内部数据。

批量导出：

```python
GameConfig.screen.default_options   # 默认值字典
GameConfig.to_dict()                # 全部配置的深拷贝
```

### 3. 修改

```python
# 单项
GameConfig.width.value = 1920
GameConfig.width.set_value(1920)        # 等价写法

# 同一 Section 批量写（一次落盘）
GameConfig.audio.update(bgm_volume=0.6, mute=True)

# 任意操作合并落盘
with GameConfig.audio.batch():
    GameConfig.bgm_volume.value = 0.4
    GameConfig.mute.toggle()
```

> 循环里连续修改几十次配置时，用 `batch()` 包起来可以把几十次磁盘写入合并为一次。

`batch()` 具备保存点语义：块内任一步抛异常时，该块内的修改整体回滚，不会把半批数据落盘；嵌套时每层各自是独立的保存点，内层异常只回滚内层修改，被内层吞掉的异常也不会影响外层已做的修改。同理，`append` / `update` / `toggle` / `increment` 这类读改写操作整体持有线程锁，并发调用不会丢失更新。

### 4. 类型代理

配置项根据默认值类型自动获得专属操作：

| 默认值类型 | 代理类 | 专属方法 |
|---|---|---|
| `bool` | `BoolProxy` | `toggle()` |
| `int` / `float` | `NumberProxy` | `increment(n=1)` |
| `list` | `ListProxy` | `append` `extend` `insert` `remove` `pop` `clear` `sort` `reverse`，以及索引读写 |
| `dict` | `DictProxy` | `pop` `update` `setdefault` `clear` `get` `keys` `values` `items`，以及键读写 |
| 其他 | `PropertyProxy` | `value` `default` `reset` `is_default` `on_change` |

所有代理都提供 `value`、`reset()`、`is_default`、`on_change()`，且写操作全部经过校验并落盘。

```python
GameConfig.unlocked_levels.append(2)
GameConfig.unlocked_levels.remove(1)
GameConfig.unlocked_levels[0] = 3
GameConfig.screen['width'] = 1600
```

> `field()` 的返回值带有泛型类型信息，IDE 会把 `GameConfig.width` 推断为 `NumberProxy`，可直接补全 `increment()`。

### 5. 校验与只读

写入时依次检查：环境变量覆盖 → read_only → 类型 → validator。

```python
net = Section('Net')
port = net.field(default=8080, validator=lambda v: 1 <= v <= 65535)
token = net.field(default='', read_only=True)

port.value = 'big'      # ❌ ConfigTypeError：类型不匹配
port.value = 999999     # ❌ ConfigValueError：validator 不通过
token.value = 'new'     # ❌ WriteError：只读
```

validator 返回 `False` 时抛出 `ConfigValueError`；validator 自身抛出异常时同样包装为 `ConfigValueError`，原始异常保存在 `__cause__`，不会裸抛到业务代码。

`reset()`（单项或整个 Section）与普通写入走同一套检查：被环境变量覆盖或标记为 `read_only` 的配置项会抛 `WriteError`，整个 Section 的重置随之回滚。

### 6. 变更回调

```python
@GameConfig.bgm_volume.on_change
def on_volume_change(section, option, value):
    print(f'{section}.{option} 变为 {value}')


# 普通调用也可以
GameConfig.width.on_change(lambda section, option, value: save_now())
```

回调签名为 `callback(section, option, value)`，在 `value=`、`set_value()`、`update()`、`reset()`、代理写操作后触发。

### 7. 重置

```python
GameConfig.width.reset()        # 单项恢复默认值
GameConfig.screen.reset()       # 整个 Section 批量恢复，一次落盘
```

## 多组同构数据

同一套数据格式需要多份实例时（例如多个存档、多套关卡数据），声明多个独立 Section：

```python
DEFAULT_LEVEL = {'score': 0, 'stars': 0, 'cleared': False}

class GameConfig(ConfigBase):
    _path = 'config/game.json'

    level1 = Section('Level1')
    data1 = level1.field(default=DEFAULT_LEVEL, option='data')

    level2 = Section('Level2')
    data2 = level2.field(default=DEFAULT_LEVEL, option='data')


GameConfig.data1['score'] = 1200
GameConfig.data2['score'] = 800

GameConfig.level1.reset()       # 只重置 Level1，Level2 不受影响
```

声明配置项时框架会深拷贝 `list` / `dict` 默认值，因此直接复用同一个常量即可，各组默认值互不共享，不需要手写 `dict(DEFAULT_LEVEL)`。

## 环境变量覆盖

部署时常用环境变量注入配置，优先级为：

```
环境变量  >  配置文件  >  默认值
```

```python
class ServerConfig(ConfigBase):
    _path = 'config/server.enc'
    _cipher = AesGcmCipher()          # 密钥省略时读取 CONF_BASE_KEY

    net = Section('Net')
    host = net.field(default='0.0.0.0', env_key='APP_HOST')
    port = net.field(default=8080, env_key='APP_PORT')
    debug = net.field(default=False, env_key='APP_DEBUG')
    db_pass = net.field(default='', env_key='APP_DB_PASS', read_only=True)
```

环境变量永远是字符串，框架按 `default` 的类型自动解析：

| 默认值类型 | 环境变量示例 | 解析结果 |
|---|---|---|
| `int` | `"8080"` | `8080` |
| `float` | `"0.5"` | `0.5` |
| `bool` | `"true"` / `"1"` / `"yes"` | `True` |
| `bool` | `"false"` / `"0"` / `"no"` | `False` |
| `list` | `'["10.0.0.1", "10.0.0.2"]'` | 列表（JSON 解析） |
| `dict` | `'{"host": "db.local"}'` | 字典（JSON 解析） |
| `str` | `"hello"` | `"hello"` |

解析失败会立即抛出 `ConfigValueError`。`list` / `dict` 必须使用 JSON 语法，例如 `APP_HOSTS='["10.0.0.1","10.0.0.2"]'`。

`default=None` 的配置项无法从 `default` 推断类型，因此不支持 `env_key`；一旦设置对应环境变量，读取时会抛出 `ConfigValueError`。

被环境变量覆盖的配置项禁止回写文件，避免把部署注入的值写进配置：

```python
ServerConfig.port.value = 9090   # ❌ WriteError：由 APP_PORT 覆盖
ServerConfig.port.has_env_override   # True
```

## 存储格式与加密

存储拆成两个正交的部分，分别用 `_format` 与 `_cipher` 配置：

```
写入：dict --format.serialize--> text --cipher.encrypt--> file
读取：file --cipher.decrypt--> text --format.deserialize--> dict
```

| 类 | 角色 | 说明 | 依赖 |
|---|---|---|---|
| `JsonFormat` | 格式 | 明文 JSON，默认 | 无 |
| `YamlFormat` | 格式 | 明文 YAML，按原生格式落盘 | `conf_base[yaml]` |
| `TomlFormat` | 格式 | 明文 TOML，按原生格式落盘 | `conf_base[toml]` |
| `NoCipher` | 加密 | 不加密，默认 | 无 |
| `SignedCipher` | 加密 | 明文 + HMAC-SHA256 签名，可读但不可改 | 无 |
| `AesCipher` | 加密 | AES-128-CBC + HMAC（Fernet） | `conf_base[aes]` |
| `AesGcmCipher` | 加密 | AES-256-GCM（AEAD），推荐 | `conf_base[aes]` |
| `ChaCha20Poly1305Cipher` | 加密 | ChaCha20-Poly1305（AEAD） | `conf_base[aes]` |

### 路径、格式与加密

```python
from conf_base import AesGcmCipher, ConfigBase, Section, YamlFormat


class AppConfig(ConfigBase):
    _path = 'config/app.yaml'      # 显式路径：原样使用，不做任何改写
    _format = YamlFormat()         # 可省略：按 _path 后缀推断
    _cipher = AesGcmCipher()       # 加密后写入同一路径

    s = Section('Server')
    port = s.field(default=8080)
```

- `_path` 原样使用；未指定时按类名生成 `{类名小写}{格式后缀}{加密后缀}`，如 `appconfig.json`、`appconfig.yaml.enc`
- `_format` 未指定时按后缀推断（`.json` / `.yaml` / `.yml` / `.toml`）；推断前会先剥离 `_cipher` 的加密后缀，因此 `app.yaml.enc` 仍按 YAML 处理；无法识别则用 `JsonFormat`
- 路径后缀与显式格式冲突时（如 `_path='app.yaml'` 配 `JsonFormat()`）立即抛 `ValueError`
- `_cipher` 未指定时为 `NoCipher`

| 配置 | 生成的文件名 |
|---|---|
| 全省略 | `appconfig.json` |
| `_format = YamlFormat()` | `appconfig.yaml` |
| `_format = YamlFormat()` + `_cipher = AesGcmCipher()` | `appconfig.yaml.enc` |
| `_path = 'app.conf'` | `app.conf`（后缀无法识别，按 JSON 处理） |

实际使用的路径（显式声明或按类名生成的那个）可以随时用 `config_path` 读出来，
不需要访问下划线开头的 `_path`：

```python
AppConfig.config_path        # 'config/app.yaml'
```

YAML / TOML / JSON 写入前会统一校验数据，无法表达的类型会给出明确错误：

| 数据情况 | 行为 |
|---|---|
| `tuple` | 自动转为 `list` |
| 非字符串字典键 | `ConfigValueError`，并指出位置（JSON 不会再静默转成字符串键） |
| `set` / `bytes` / 自定义对象 | `ConfigValueError` |
| `None` | JSON / YAML 支持；TOML 不支持，抛 `ConfigValueError` |
| `datetime` / `date` / `time` | YAML / TOML 原生支持；JSON 抛 `ConfigValueError` |

> 文件按所选格式写入，但每次保存都会从内存字典重新序列化，因此手工添加的注释与排版不会保留。

### 签名（内容可读，禁止篡改）

```python
_cipher = SignedCipher(key='signing-key')   # 省略 key 时读取 CONF_BASE_SIGN_KEY
```

签名以注释行附加在文件末尾（`# conf_base-signature: v1:<hex>`），不产生额外文件。加载时先校验签名再解析内容，文件被手工修改、签名缺失或密钥不符都会抛 `DecryptError`。

### 加密（内容不可见，自带完整性校验）

```python
# AES-256-GCM，密钥省略时读取 CONF_BASE_KEY
_cipher = AesGcmCipher(key_id='v1')

# 无 AES 硬件加速的设备
_cipher = ChaCha20Poly1305Cipher()

# 兼容既有数据
_cipher = AesCipher(key='my-app-key')
```

AEAD 加密器每次写入使用随机 nonce，相同明文产生不同密文；密文信封中包含算法与 `key_id`，密钥错误、密文篡改、密钥版本不匹配都会解密失败。

密钥建议：

| 方式 | 写法 |
|---|---|
| 环境变量（推荐） | `AesGcmCipher()`，配合 `CONF_BASE_KEY` |
| 密钥管理服务 | `AesGcmCipher(key=vault.get('app/secret'))` |
| 硬编码 | 仅限本地调试，不要提交到仓库 |

### 自定义格式 / 加密

格式与加密互不影响，按需继承其中一个即可接入任意存储方式：

```python
from typing import Any, Dict

from conf_base import BaseCipher, BaseFormat


class MyFormat(BaseFormat):
    extension = '.dat'

    def serialize(self, data: Dict[str, Any]) -> str:
        ...

    def deserialize(self, text: str) -> Dict[str, Any]:
        ...


class MyCipher(BaseCipher):
    extension = ''          # 自动生成文件名时追加的后缀，不改变文件名则为 ''

    def encrypt(self, text: str) -> str:
        ...

    def decrypt(self, text: str) -> str:
        ...


class AppConfig(ConfigBase):
    _format = MyFormat()
    _cipher = MyCipher()
```

## 配置版本迁移

配置文件会记录 `_schema_version`，启动时按 `_migrate` 中的函数链把旧数据升级到新结构：

```python
def migrate_v1_to_v2(data: dict) -> dict:
    """把 bgm_volume 重命名为 bgm"""
    setting = data.get('Setting', {})
    if 'bgm_volume' in setting:
        setting['bgm'] = setting.pop('bgm_volume')
    return data


class GameConfig(ConfigBase):
    _path = 'config/game.json'
    _schema_version = 2
    _migrate = {1: migrate_v1_to_v2}

    audio = Section('Audio')
    bgm = audio.field(default=1.0)
```

| 情况 | 行为 |
|---|---|
| 新文件首次启动 | 直接按目标版本创建 |
| 文件版本 < 目标版本 | 依次执行迁移函数，完成后写回版本号 |
| 文件版本 = 目标版本 | 不迁移 |
| 文件版本 > 目标版本 | 启动时抛出 `ValueError`，不会把版本号降级写回 |
| 缺少某一步迁移函数 | 启动时抛出 `ValueError` |
| 迁移函数返回非字典 | 启动时抛出 `ValueError` |

迁移后新增的配置项不需要在迁移函数里填值，框架会用 `default` 自动补齐。文件中的未知 section / option 默认原样保留，避免误删手工添加的内容；需要与代码严格同步时设置 `_prune_unknown = True`，启动时会删除代码中已不存在的项。

> `_prune_unknown` 的删除不可逆。框架在删除前会发出 `UserWarning`，列出所有被删的 `section.option`，请留意启动日志；手工添加的字段想保留时不要开启该开关，或先备份配置文件。

`_schema_version` 是内部字段，`to_dict()` 不会导出。

## 并发与性能

**线程安全**：内置 `threading.RLock`，始终生效。

**多进程**：安装 `filelock` 后自动启用文件锁，避免多个进程同时写同一文件时互相覆盖。

```python
class AppConfig(ConfigBase):
    _use_file_lock = False      # 关闭进程锁（各进程各用各的文件时）
    _lock_timeout = 30.0        # 等待锁的时间，默认 10 秒
```

**外部修改自动重载**：默认配置只在类定义时读取一次，之后全部走内存。需要运维改文件即时生效时开启：

```python
class ServerConfig(ConfigBase):
    _path = 'config/server.json'
    _auto_reload = True         # 读取时比对文件指纹，变化才重新解析
```

参考量级（JSON 文件，约 300 字节）：

| 操作 | 耗时 |
|---|---|
| 单值读取 | ~0.3 µs（纯内存） |
| `auto_reload` 单值读取 | ~5 µs（含文件指纹检查） |
| 单次落盘 | ~2 ms |
| `batch()` 合并 3 项写入 | ~2.3 ms |

读取几乎零成本，写入瓶颈在磁盘；高频修改优先用 `batch()`。

> 指纹由 `(mtime_ns, size)` 组成。部分文件系统（如 Windows NTFS）时间戳精度只有约 15ms，刚写完的文件可能得到相同的 mtime，因此文件修改后的 100ms 内会强制重读一次，之后恢复指纹缓存。

## Web 后端集成

配置类本身就是模块级单例：类定义时完成加载、迁移与默认值补齐，导入失败即启动失败，不需要额外的初始化钩子。

```python
# config.py
from conf_base import ConfigBase, Section


class AppConfig(ConfigBase):
    _path = 'config/app.json'
    _auto_reload = True                 # 运维改文件后，下次读取即生效

    server = Section('Server')
    host = server.field(default='0.0.0.0', env_key='APP_HOST')
    port = server.field(default=8000, env_key='APP_PORT')

    db = Section('DB')
    url = db.field(default='sqlite:///app.db', env_key='APP_DB_URL', read_only=True)
```

```python
# main.py
from typing import Dict

from fastapi import FastAPI

from config import AppConfig

app = FastAPI()


@app.get('/health')
def health() -> Dict[str, int]:
    return {'port': AppConfig.port.value}
```

需要注入以便测试替换时，加一个依赖函数即可：

```python
from typing import Type

from fastapi import Depends


def get_config() -> Type[AppConfig]:
    return AppConfig


@app.get('/health')
def health(config: Type[AppConfig] = Depends(get_config)) -> Dict[str, int]:
    return {'port': config.port.value}
```

Flask 用一次性快照最直接：

```python
from flask import Flask

from config import AppConfig

app = Flask(__name__)
app.config.update(AppConfig.to_dict())   # 只复制当前值，之后两边不再联动
```

注意事项：

- **请求内只取一次快照**。`_auto_reload` 在每次 `.value` 读取时都要做一次文件指纹检查（约 5 µs）。一个请求要读多个配置项时，先 `snapshot = AppConfig.to_dict()`，不要在循环里逐项读。
- **`.env` 由外部加载**。框架只读 `os.environ`，不解析 `.env` 文件。本地开发用 `python-dotenv` 的 `load_dotenv()`，部署用容器环境变量即可。环境变量是实时读取的，但已启动的进程不会感知注入后的变化。
- **多 worker 各持一份内存数据**（`uvicorn --workers`、gunicorn）。文件锁只保证文件不被写坏，**不保证跨进程合并写入**。Web 场景应保持配置「读多写少」，写入走单个进程或独立管理端点。
- **Flask 的 `app.config.update()` 是单向复制**，之后改 `AppConfig` 不会同步到 `app.config`，反之亦然。

## 与 pydantic / pydantic-settings 的关系

两者解决的是不同问题，不需要互相替代（更广的横向对比见上文「与其他方案怎么选」）：

| | conf_base | pydantic-settings |
|---|---|---|
| 建模方式 | `default` 推断类型 + 描述符 | 类型注解 + 校验器 |
| 数据来源 | 文件优先（env > 文件 > 默认值） | 环境变量优先，文件需自行接入 |
| 写回文件 | 支持（校验通过后立即落盘） | 不支持 |
| 加密 / 签名 / schema 迁移 | 内置 | 无 |

互操作就是两次显式转换：

```python
from pydantic import BaseModel


class ServerModel(BaseModel):
    host: str
    port: int


# conf_base -> pydantic：构造时按模型规则再校验一次
server = ServerModel(**AppConfig.server.current_options)

# pydantic -> conf_base：逐字段写入，仍走 conf_base 的类型与 validator 校验
AppConfig.server.update(**server.model_dump())
```

`Section.update()` 遇到模型中多出的字段会抛 `ConfigKeyError`，不会被静默忽略。

不建议做双向自动转换：pydantic-settings 以环境变量为第一优先级、支持任意嵌套建模；conf_base 以文件为持久化主体，并带加密与 schema 迁移。两者语义不对等，自动映射必然丢信息。已有 pydantic 体系时的推荐组合是：**pydantic 负责请求/响应与领域模型，conf_base 负责落盘配置**。

## 异常体系

运行期的配置错误都继承 `ConfBaseError`，可统一捕获：

```python
import conf_base.error as E

try:
    GameConfig.width.value = -1
except E.ConfBaseError as exc:
    print(f'配置错误: {exc}')
```

| 异常 | 触发场景 |
|---|---|
| `ConfBaseError` | 所有框架异常的基类 |
| `ConfigTypeError` | 写入类型与默认值不一致 |
| `ConfigValueError` | validator 校验失败、validator 自身抛异常、环境变量解析失败、格式无法表达的数据 |
| `WriteError` | 写入只读配置项、写入被环境变量覆盖的配置项、直接给 Section 属性赋值 |
| `ConfigKeyError` | 读写的 section / option 不存在（同时是 `KeyError`） |
| `ParseError` | 配置文件损坏，无法解析 |
| `DecryptError` | 解密失败、签名校验失败、文件被篡改 |
| `SchemaError` | `_schema_version` 高于代码目标版本、迁移函数缺失或返回非字典（同时是 `ValueError`） |
| `LockError` | 等待多进程文件锁超时（同时是 `TimeoutError`） |

配置文件加载阶段，解密 / 签名失败直接抛 `DecryptError`；`DecryptError` 之外的读取或解析问题统一包装为 `ParseError`。原始异常保存在 `__cause__` 中。

类声明阶段的参数错误（`_format` 不是 `BaseFormat`、路径后缀与格式冲突等）仍直接抛内建 `TypeError` / `ValueError`。

## API 速查

### ConfigBase（配置类）

> 配置类必须**直接继承 `ConfigBase`**。`class Child(SomeConfig)` 会在类创建时抛 `TypeError`：配置项描述符与 `ConfigFile` 都是类级绑定，继承会让父子类共享同一份配置数据。

| 成员 | 说明 |
|---|---|
| `_path` | 配置文件路径，省略时按类名生成 |
| `_format` | `JsonFormat` / `YamlFormat` / `TomlFormat`，省略时按路径后缀推断 |
| `_cipher` | 加密器，省略时为 `NoCipher` |
| `_auto_reload` | 读取时检查文件指纹，变化后重新加载，默认 `False` |
| `_prune_unknown` | 启动时删除代码中不存在的 section / option，默认 `False`（保留）；删除前发 `UserWarning` 列出被删的键 |
| `_use_file_lock` / `_lock_timeout` | 进程锁开关与超时，默认 `True` / `10.0` |
| `_schema_version` / `_migrate` | 目标版本号与迁移函数字典 |
| `to_dict()` | 导出全部配置的深拷贝 |
| `config_path` | 实际使用的配置文件路径（只读，由框架注入；与 `_path` 一致，省略 `_path` 时为按类名生成的路径） |
| `config_node` | 已注册的 section → option 列表 |

### Section

| 成员 | 说明 |
|---|---|
| `field(default='', option=None, validator=None, read_only=False, env_key=None)` | 声明配置项，`option` 省略时使用类属性名 |
| `update(**kwargs)` | 批量写入，一次落盘 |
| `batch()` | 上下文管理器，退出时统一落盘 |
| `reset()` | 重置本 Section 所有配置项 |
| `current_options` / `default_options` | 当前值 / 默认值字典 |
| `section['key']` / `section.key` | 读取单个配置项（返回**当前值**，不是代理） |
| `'key' in section` | 判断配置项是否存在 |

> 读写配置值请直接用 `Config.option`，例如 `CliConfig.theme.value = 'light'`。
> `CliConfig.general.theme` 拿到的是当前值（`str`），再写 `.value` 会报
> `AttributeError`；只有 `Config.theme` 才是带 `.value` / `.toggle()` 等方法的代理。

### 配置项代理

| 成员 | 说明 |
|---|---|
| `.value` | 当前值，可读写 |
| `.set_value(value)` | 写入值 |
| `.default` | 默认值（只读） |
| `.reset()` | 恢复默认值 |
| `.is_default` | 当前值是否等于默认值 |
| `.on_change(callback)` | 注册变更回调，支持装饰器 |
| `.section` / `.option` | 所属 Section 与配置项名 |
| `.has_env_override` / `.env_key` | 是否被环境变量覆盖 / 环境变量名 |

## 项目结构

```
conf_base/
├── __init__.py       # 对外导出
├── config_base.py    # ConfigBase 配置类引导
├── config_file.py    # 文件读写 + 批量落盘
├── format.py         # JsonFormat / YamlFormat / TomlFormat
├── cipher.py         # NoCipher / SignedCipher / AesCipher / AEAD
├── descriptor.py     # ConfigProperty + 类型代理
├── section.py        # Section 配置块
└── error.py          # 统一异常体系
```

## 测试与 CI

112 个用例，总覆盖率 87%。本地运行：

```bash
pip install -e .[dev]
python -m pytest test/ -v --cov=conf_base
python -m mypy conf_base
```

GitHub Actions 会在每次 push / PR 时执行 Python 3.8–3.12 的测试矩阵、`mypy` 严格检查与打包验证。

## 参与贡献

- 想提 bug 或需求：用 [issue 模板](.github/ISSUE_TEMPLATE)
- 想改代码：先读 [CONTRIBUTING.md](CONTRIBUTING.md)
- 不知道做什么：看 [ROADMAP.md](ROADMAP.md) 里标了 `good first issue` 的任务
- 主仓库在 GitHub（[DashSalter/conf_base](https://github.com/DashSalter/conf_base)），Gitee（[kuangjianke/conf_base](https://gitee.com/kuangjianke/conf_base)）为镜像

## License

MIT License
