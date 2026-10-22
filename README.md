# ConfBase

[![Python](https://img.shields.io/badge/python-%3E%3D3.8-blue)](https://www.python.org/)
[![CI](https://github.com/DashSalter/conf_base/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/DashSalter/conf_base/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-70%20passed-brightgreen)](test/)
[![Coverage](https://img.shields.io/badge/coverage-83%25-brightgreen)](test/)

用**类属性和 Section** 声明配置。一个配置项就是一个类属性，读写时自动完成类型校验、校验函数检查和落盘，不用再手写读写文件的样板代码。

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
| Redis / MySQL 等远程存储 | 配置中心，或自行实现 `Crypto` 存储适配 |
| 每秒级高频写入 | 数据库、配置中心 |
| 超大配置或二进制数据 | 数据库、对象存储 |
| 复杂嵌套模型、字段级校验 | pydantic / pydantic-settings |
| 多用户并发编辑同一文件 | 数据库 + 乐观锁 |
| 运行时动态增删配置项 | 动态配置中心 |
| 配置类之间继承复用配置项 | 独立配置类 + 共享默认值常量 |
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
from conf_base import ConfigBase, Section, crypto


class GameConfig(ConfigBase):
    # 配置文件路径与格式由加密器决定
    _crypto = crypto.PlainJson('config/game.json')

    # 画面
    screen = Section('Screen')
    width = screen.add(default=1280, validator=lambda v: v >= 800)
    height = screen.add(default=720)
    fullscreen = screen.add(default=False)

    # 声音
    audio = Section('Audio')
    bgm_volume = audio.add(default=0.8, validator=lambda v: 0 <= v <= 1)
    mute = audio.add(default=False)

    # 存档
    save = Section('Save')
    unlocked_levels = save.add(default=[1])
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

## 核心用法

### 1. 声明配置项

`Section.add()` 的参数：

```python
port = server.add(
    default=8080,                          # 默认值，同时决定配置值的类型
    validator=lambda v: 1 <= v <= 65535,   # 可选，返回 False 时拒绝写入
    read_only=False,                       # 可选，True 时禁止运行时修改
    env_key='APP_PORT',                    # 可选，允许环境变量覆盖
)
# option 省略时，配置键名自动取变量名 'port'
# 需要与变量名不同时显式传入，例如 server.add('listen_port', default=8080)
```

配置值的类型始终锁定为 `default` 的类型，写入其他类型会抛 `ConfigTypeError`。

### 2. 读取

四种方式结果完全一致：

```python
GameConfig.width.value                  # 描述符方式
GameConfig.screen['width']              # Section 索引
GameConfig.screen.width                 # Section 属性
GameConfig.screen.current_options       # 整个 Section
```

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

> `add()` 的返回值带有泛型类型信息，IDE 会把 `GameConfig.width` 推断为 `NumberProxy`，可直接补全 `increment()`。

### 5. 校验与只读

写入时依次检查：类型 → validator → read_only。

```python
net = Section('Net')
port = net.add(default=8080, validator=lambda v: 1 <= v <= 65535)
token = net.add(default='', read_only=True)

port.value = 'big'      # ❌ ConfigTypeError：类型不匹配
port.value = 999999     # ❌ ConfigValueError：validator 不通过
token.value = 'new'     # ❌ WriteError：只读
```

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
    _crypto = crypto.PlainJson('config/game.json')

    level1 = Section('Level1')
    data1 = level1.add('data', default=dict(DEFAULT_LEVEL))

    level2 = Section('Level2')
    data2 = level2.add('data', default=dict(DEFAULT_LEVEL))


GameConfig.data1['score'] = 1200
GameConfig.data2['score'] = 800

GameConfig.level1.reset()       # 只重置 Level1，Level2 不受影响
```

`dict(DEFAULT_LEVEL)` 保证每组的默认值互不共享。

## 环境变量覆盖

部署时常用环境变量注入配置，优先级为：

```
环境变量  >  配置文件  >  默认值
```

```python
class ServerConfig(ConfigBase):
    _crypto = crypto.AesGcmCrypto(file_path='config/server.enc')

    net = Section('Net')
    host = net.add(default='0.0.0.0', env_key='APP_HOST')
    port = net.add(default=8080, env_key='APP_PORT')
    debug = net.add(default=False, env_key='APP_DEBUG')
    db_pass = net.add(default='', env_key='APP_DB_PASS', read_only=True)
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

解析失败会立即抛出 `ConfigValueError`。

被环境变量覆盖的配置项禁止回写文件，避免把部署注入的值写进配置：

```python
ServerConfig.port.value = 9090   # ❌ WriteError：由 APP_PORT 覆盖
ServerConfig.port.has_env_override   # True
```

## 存储格式与加密

通过 `_crypto` 指定格式或加密方式：

| 加密器 | 说明 | 依赖 |
|---|---|---|
| `PlainJson` | 明文 JSON，默认 | 无 |
| `PlainYaml` | 明文 YAML，可写注释 | `conf_base[yaml]` |
| `PlainToml` | 明文 TOML | `conf_base[toml]` |
| `SignedCrypto` | 明文 + HMAC-SHA256 签名，可读但不可改 | 无 |
| `AesCrypto` | AES-128-CBC + HMAC（Fernet） | `conf_base[aes]` |
| `AesGcmCrypto` | AES-256-GCM（AEAD），推荐 | `conf_base[aes]` |
| `ChaCha20Poly1305Crypto` | ChaCha20-Poly1305（AEAD） | `conf_base[aes]` |

### 明文格式

```python
_crypto = crypto.PlainJson('config/app.json')
_crypto = crypto.PlainYaml('config/app.yaml')
_crypto = crypto.PlainToml('config/app.toml')
```

YAML / TOML 写入前会统一校验数据，无法表达的类型会给出明确错误：

| 数据情况 | 行为 |
|---|---|
| `tuple` | 自动转为 `list` |
| 非字符串字典键 | `ConfigValueError`，并指出位置 |
| `set` / `bytes` / 自定义对象 | `ConfigValueError` |
| `None` | YAML 支持；TOML 不支持，抛 `ConfigValueError` |
| `datetime` / `date` / `time` | 原生支持 |

### 签名（内容可读，禁止篡改）

```python
_crypto = crypto.SignedCrypto(
    crypto.PlainYaml('config/app.yaml'),
    key='signing-key',      # 省略时读取 CONF_BASE_SIGN_KEY
)
```

写入时同时生成 `app.yaml` 与 `app.yaml.sig`。加载时先校验签名，文件被手工修改、签名缺失或密钥不符都会导致加载失败。

### 加密（内容不可见，自带完整性校验）

```python
# AES-256-GCM，密钥省略时读取 CONF_BASE_KEY
_crypto = crypto.AesGcmCrypto(file_path='config/app.enc', key_id='v1')

# 无 AES 硬件加速的设备
_crypto = crypto.ChaCha20Poly1305Crypto(file_path='config/app.enc')

# 兼容既有数据
_crypto = crypto.AesCrypto(key='my-app-key', file_path='config/app.enc')
```

AEAD 加密器每次写入使用随机 nonce，相同明文产生不同密文；密文信封中包含算法与 `key_id`，密钥错误、密文篡改、密钥版本不匹配都会解密失败。

密钥建议：

| 方式 | 写法 |
|---|---|
| 环境变量（推荐） | `AesGcmCrypto(file_path='app.enc')`，配合 `CONF_BASE_KEY` |
| 密钥管理服务 | `AesGcmCrypto(key=vault.get('app/secret'), file_path='app.enc')` |
| 硬编码 | 仅限本地调试，不要提交到仓库 |

### 自定义存储

继承 `Crypto` 并实现两个方法，即可接入任意存储后端：

```python
class MyCrypto(crypto.Crypto):
    def encrypt(self, data: dict) -> str:
        ...

    def decrypt(self, text: str) -> dict:
        ...


class AppConfig(ConfigBase):
    _crypto = MyCrypto('config/app.dat')
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
    _crypto = crypto.PlainJson('config/game.json')
    _schema_version = 2
    _migrate = {1: migrate_v1_to_v2}

    audio = Section('Audio')
    bgm = audio.add(default=1.0)
```

| 情况 | 行为 |
|---|---|
| 新文件首次启动 | 直接按目标版本创建 |
| 文件版本 < 目标版本 | 依次执行迁移函数，完成后写回版本号 |
| 文件版本 = 目标版本 | 不迁移 |
| 文件版本 > 目标版本 | 不迁移，仅同步数据 |
| 缺少某一步迁移函数 | 启动时抛出 `ValueError` |

迁移后新增的配置项不需要在迁移函数里填值，框架会用 `default` 自动补齐。代码中删除的 section / option 会在启动时自动从文件清理。

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
    _crypto = crypto.PlainJson('config/server.json')
    _auto_reload = True         # 每次读取都重新解析文件
```

参考量级（JSON 文件，约 300 字节）：

| 操作 | 耗时 |
|---|---|
| 单值读取 | ~0.3 µs（纯内存） |
| 单次落盘 | ~2 ms |
| `batch()` 合并 3 项写入 | ~2.3 ms |

读取几乎零成本，写入瓶颈在磁盘；高频修改优先用 `batch()`。

## 异常体系

所有异常继承 `ConfBaseError`，可统一捕获：

```python
import conf_base.Error as E

try:
    GameConfig.width.value = -1
except E.ConfBaseError as exc:
    print(f'配置错误: {exc}')
```

| 异常 | 触发场景 |
|---|---|
| `ConfBaseError` | 所有框架异常的基类 |
| `ConfigTypeError` | 写入类型与默认值不一致 |
| `ConfigValueError` | validator 校验失败、环境变量解析失败 |
| `WriteError` | 写入只读配置项，或写入被环境变量覆盖的配置项 |
| `ParseError` | 配置文件损坏，无法解析 |
| `DecryptError` | 解密失败、签名校验失败、文件被篡改 |

配置文件加载阶段的解密 / 签名错误会统一包装为 `ParseError`，原始异常保存在 `__cause__` 中。

## API 速查

### ConfigBase（配置类）

| 成员 | 说明 |
|---|---|
| `_crypto` | 存储格式或加密器 |
| `_auto_reload` | 每次读取重新加载文件，默认 `False` |
| `_use_file_lock` / `_lock_timeout` | 进程锁开关与超时，默认 `True` / `10.0` |
| `_schema_version` / `_migrate` | 目标版本号与迁移函数字典 |
| `to_dict()` | 导出全部配置的深拷贝 |
| `config_node` | 已注册的 section → option 列表 |

### Section

| 成员 | 说明 |
|---|---|
| `add(option=None, default='', validator=None, read_only=False, env_key=None)` | 添加配置项，`option` 省略时使用类属性名 |
| `update(**kwargs)` | 批量写入，一次落盘 |
| `batch()` | 上下文管理器，退出时统一落盘 |
| `reset()` | 重置本 Section 所有配置项 |
| `current_options` / `default_options` | 当前值 / 默认值字典 |
| `section['key']` / `section.key` | 读取单个配置项 |
| `'key' in section` | 判断配置项是否存在 |

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
├── descriptor.py     # ConfigProperty + 类型代理
├── section.py        # Section 配置块
├── json_config.py    # 文件读写 + 批量落盘
├── crypto.py         # 存储格式与加密器
└── Error.py          # 统一异常体系
```

## 测试与 CI

70 个用例，总覆盖率 83%。本地运行：

```bash
pip install -e .[dev]
python -m pytest test/ -v --cov=conf_base
python -m mypy conf_base
```

GitHub Actions 会在每次 push / PR 时执行 Python 3.8–3.12 的测试矩阵、`mypy` 严格检查与打包验证。

## License

MIT License
