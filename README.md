# ConfigBase

一个通过**类和属性**构建的 Python 配置管理框架，更加便捷与安全地操作与存储配置数据。

---

## ✨ 特性亮点

- **声明式定义**：写一个类就是一份配置，像定义类属性一样定义配置项
- **自动落盘**：修改即写文件，原子写入（临时文件 + `os.replace`）防损坏
- **类型锁定**：值类型必须与默认值一致，杜绝 `screen_size='3'` 这类隐患
- **值校验**：`validator` 自定义校验函数，值域约束一行搞定
- **只读保护**：敏感配置项标记 `read_only=True`，防止运行时被改
- **多配置块切换**：同一组配置项在多个 section 间快速切换存取
- **容器类型代理**：`append` / `__setitem__` / `toggle` / `increment` 等快捷操作，自动落盘
- **批量修改**：`update()` 和 `batch()` 上下文，N 次修改 1 次落盘
- **变更回调**：`on_change` 注册回调，支持按 section 过滤
- **损坏兜底**：配置文件格式损坏时抛出明确 `ParseError`，而非原始 JSON 异常
- **加密存储**：内置明文 JSON 和 XOR+Base64 两种加密器，支持自定义继承
- **多配置类独立文件**：每个配置类独立 `JsonConfig` 实例和配置文件
- **零依赖**：除 Python 标准库外无任何第三方依赖

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

## 🔐 加密存储

通过 `_crypto` 指定加密器，内置两种：

### PlainJson（默认，明文 JSON）

```python
_crypto = crypto.PlainJson('settings.json')
```

### XorCrypto（XOR + Base64）

```python
_crypto = crypto.XorCrypto('settings_encrypted.json')
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
| `.add(option, default, validator, read_only)` | 添加配置项，返回 `ConfigProperty` |
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

**4. read_only 用于密钥、数据库密码等敏感配置**

防止运行时误改。如果需要热更新密钥，把它移出 `read_only`，配合 `on_change` 回调通知应用重载。

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

## 📁 项目结构

```
conf_base/
├── __init__.py       # 对外导出
├── descriptor.py     # ConfigProperty + 类型代理
├── section.py        # Section 配置块
├── metaclass.py      # ConfigMeta 元类
├── json_config.py    # 文件读写 + 批量落盘
├── crypto.py         # 加解密器（PlainJson / XorCrypto）
└── Error.py          # 统一异常体系
```

---

## 📜 License

MIT License
