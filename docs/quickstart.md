# 快速开始

十分钟走完 conf_base 的主要能力：声明、读取、修改、校验、加密、环境变量、迁移。

## 1. 声明

```python
from conf_base import ConfigBase, Section

class AppConfig(ConfigBase):
    _path = 'config/app.yaml'          # 相对路径基于进程当前目录

    server = Section('Server')
    host = server.field(default='127.0.0.1')
    port = server.field(default=8080, validator=lambda v: 1 <= v <= 65535)
    debug = server.field(default=False)

    db = Section('Database')
    dsn = db.field(default='sqlite:///app.db')
```

`import` 这个模块的瞬间，`config/app.yaml` 就被创建了（目录不存在会一并创建），内容是最新 schema 的默认值：

```yaml
Server:
  host: 127.0.0.1
  port: 8080
  debug: false
Database:
  dsn: sqlite:///app.db
_schema_version: 1
```

要点：

- **属性名 = 配置项名**，`Section('Server')` 决定它落在哪个顶层键下
- **`default` 的类型 = 配置项类型**，之后写 `'8080'` 会抛 `ConfigTypeError`
- **缺失项自动补齐**，新增字段后老配置文件也能直接用
- **不认识的键会被清掉**（`_prune_unknown`），删除前发 `UserWarning`，所以不会误删用户数据而不吭声

## 2. 读取

```python
AppConfig.server.port       # 当前值（str/int/bool/list/dict，不是代理）
AppConfig.port.value        # 通过代理读，和上面等价
AppConfig.to_dict()         # 整个配置的字典副本
```

`AppConfig.server.port` 拿到的是**值**，不是可继续链式访问的代理；写的时候用 `AppConfig.port.value = ...`。

## 3. 修改

```python
AppConfig.port.value = 9090      # 校验 → 落盘，一步完成
AppConfig.port.increment(10)     # 语义化方法，数字代理才有
AppConfig.debug.toggle()         # 布尔代理
```

不需要手动 `save()`。想合并多次写入只落一次盘：

```python
with AppConfig.server.batch():
    AppConfig.host.value = '0.0.0.0'
    AppConfig.port.value = 8000
    AppConfig.debug.value = True
# 退出 with 时一次性写入
```

块内抛异常会整体回滚，已经写进内存的值也不会落盘。

## 4. 校验

```python
AppConfig.port.value = 70000     # ConfigValueError: Server.port 配置项校验失败，值 70000 未通过 validator 校验
AppConfig.port.value = 'big'     # ConfigTypeError: Server.port 配置项期望类型 int 实际为 str
```

常见校验不必自己写 lambda：

```python
from conf_base.validators import in_range, is_url, one_of

port = server.field(default=8080, validator=in_range(1, 65535))
hook = server.field(default='https://example.com', validator=is_url())
level = server.field(default='info', validator=one_of('debug', 'info', 'warning', 'error'))
```

详见 [校验与只读](guide/validation.md)。

## 5. 加密

```python
from conf_base import AesGcmCipher

class AppConfig(ConfigBase):
    _path = 'config/app.yaml.enc'
    _cipher = AesGcmCipher(key='0123456789abcdef0123456789abcdef')

    server = Section('Server')
    secret = server.field(default='', env_key='APP_SECRET')
```

落盘后文件长这样——**配置值不可见**，只剩信封头：

```json
{"v": 1, "alg": "AES-256-GCM", "kid": "v1", "nonce": "...", "data": "..."}
```

密钥也是密文的一部分：没有 `key`，`data` 解不开；密文被改一个字节，解密直接抛 `DecryptError`。

更推荐把密钥放环境变量而不是源码里：

```python
_cipher = AesGcmCipher(key_env='APP_CONFIG_KEY')
```

详见 [存储格式与加密](guide/storage.md)。

## 6. 环境变量覆盖

```python
port = server.field(default=8080, env_key='APP_PORT')
```

```bash
APP_PORT=9000 python app.py
```

被环境变量覆盖的配置项**禁止回写**——`AppConfig.port.value = 8000` 会抛 `WriteError`，避免代码里的默认值悄悄盖掉运维设置。

详见 [环境变量覆盖](guide/environment.md)。

## 7. Schema 迁移

字段改名、类型变更时，用版本号 + 迁移函数描述演进：

```python
class AppConfig(ConfigBase):
    _path = 'config/app.yaml'
    _schema_version = 2
    _migrate = {1: migrate_v1_to_v2}


def migrate_v1_to_v2(config):
    config['Server']['workers'] = config['Server'].pop('threads', 4)
    return config
```

打开旧文件（`_schema_version: 1`）时自动升级到 2 并回写；文件版本高于代码版本则抛 `SchemaError`，不会强行降级。

详见 [Schema 迁移](guide/migration.md)。

## 已完成

继续看：

- [Section 与配置项](guide/sections.md)：多组同构数据、动态 section
- [并发与性能](guide/concurrency.md)：`transaction()`、文件锁、热重载
- [API 参考](api/config-base.md)：完整签名
