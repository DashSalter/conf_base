# 环境变量覆盖

## 声明覆盖关系

在 `field()` 上给一个 `env_key`，这一项就有了「环境变量 > 配置文件 > 默认值」的优先级：

```python
class AppConfig(ConfigBase):
    _path = 'app.json'

    server = Section('Server')
    port = server.field(default=8080, env_key='APP_PORT')
    debug = server.field(default=False, env_key='APP_DEBUG')
    plugins = server.field(default=['core'], env_key='APP_PLUGINS')
```

```bash
APP_PORT=9000 APP_DEBUG=true APP_PLUGINS='["core","extra"]' python app.py
```

```python
AppConfig.port.value        # 9000，来自环境变量
AppConfig.debug.value       # True
AppConfig.plugins.value     # ['core', 'extra']
```

**环境变量不会写回配置文件**：被覆盖的项在磁盘上仍是原值，只是读取时被环境变量短路。

## 值的类型解析

环境变量本质是字符串，框架按 `default` 的类型解析：

| 类型 | 解析规则 | 例子 |
|---|---|---|
| `bool` | `true` / `1` / `yes` / `on` → `True`；`false` / `0` / `no` / `off` → `False`（不区分大小写） | `APP_DEBUG=yes` |
| `int` | `int()` 转换 | `APP_PORT=9000` |
| `float` | `float()` 转换 | `APP_RATIO=0.75` |
| `list` | JSON 数组 | `APP_PLUGINS='["a","b"]'` |
| `dict` | JSON 对象 | `APP_LIMITS='{"cpu":2}'` |
| `str` | 原样 | `APP_NAME=myapp` |

解析失败（比如 `APP_PORT=abc`）抛 `ConfigValueError`，不会静默退回默认值——环境变量写错时应当立即暴露。

## 被覆盖项禁止回写

```python
AppConfig.port.value = 8000
# WriteError: Server.port 由环境变量 APP_PORT 覆盖，禁止回写配置文件。
#             请移除环境变量后再修改。
```

这是刻意设计：如果运行时代码能覆盖运维通过环境变量设的值，部署配置就失去了确定性。想改就改环境变量，或者先 `unset`。

`reset()` 同样受限——被覆盖的项无法通过重置「绕回」默认值。

## 判断是否被覆盖

```python
AppConfig.port.has_env_override      # True / False
```

适合在启动日志里说明「这个值来自环境变量而不是文件」：

```python
if AppConfig.port.has_env_override:
    logger.info('port 由环境变量覆盖：%s', AppConfig.port.value)
```

## 和加密密钥的环境变量不是一回事

`env_key` 用于**覆盖某个配置项的值**。加密器的 `key_env` 用于**提供密钥**，两者互不影响：

```python
_cipher = AesGcmCipher(key_env='APP_CONFIG_KEY')      # 密钥来自这里
secret = server.field(default='', env_key='APP_SECRET')  # 值来自这里
```

内置的密钥环境变量约定是：

| 加密器 | 默认密钥变量 |
|---|---|
| `AesGcmCipher` / `ChaCha20Poly1305Cipher` | `CONF_BASE_KEY` |
| `SignedCipher` | `CONF_BASE_SIGN_KEY` |
| `AesCipher` | 无默认变量，必须显式传 `key` |

详见 [存储格式与加密](storage.md)。
