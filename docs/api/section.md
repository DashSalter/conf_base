# Section 与 field()

## Section

`Section` 把配置项分到配置文件的不同顶层对象。每个 section 名就是一个顶层 JSON/YAML/TOML 键。

```python
class AppConfig(ConfigBase):
    server = Section('Server')
    host = server.field(default='127.0.0.1')
    port = server.field(default=8080)
```

`field()` 返回的描述器赋给类属性；`option` 参数决定写入文件时的键名，省略时用左边的类属性名：

```python
host = server.field(default='127.0.0.1', option='bind_host')
# 配置文件里是 {"Server": {"bind_host": "127.0.0.1"}}
```

## 读取

两种写法都返回**当前值**，不是代理对象：

```python
AppConfig.server.host        # '127.0.0.1'
AppConfig.server['host']     # '127.0.0.1'
```

!!! warning "别在 section 访问后继续点 .value"
    `AppConfig.server.host` 已经是 `str`，再写 `.value` 会抛 `AttributeError: 'str' object has no attribute 'value'`。

    需要代理对象（用 `increment()`、`toggle()` 等语义方法）时，用**顶层属性**：

    ```python
    AppConfig.host.value                  # '127.0.0.1'
    AppConfig.port.increment(1)           # 需要 NumberProxy
    ```

## 写入

| 写法 | 说明 |
|---|---|
| `AppConfig.host.value = v` | 最常用，走校验后落盘 |
| `AppConfig.server['host'] = v` | 与上一行等价（0.5.0 起支持） |
| `AppConfig.server.update(host=v, port=9000)` | 一次写多个，内部自动 `batch()`，全成功才落盘 |
| `AppConfig.server.reset()` | 把该 section 所有项恢复默认值 |
| `with AppConfig.server.batch():` | 期间只写内存，退出时落盘一次 |

!!! warning "不能直接赋值给 Section 属性"
    ```python
    AppConfig.server.host = '0.0.0.0'
    # WriteError: 不能直接给 Section 属性 'host' 赋值（这样不会写入配置文件）。
    #             请改用 section['host'] = value 或 section.host.value = value
    ```

    直接赋值只会产生一个实例属性，既不校验也不落盘，所以框架直接拒绝。

## 批量操作

```python
with AppConfig.server.batch():
    AppConfig.host.value = '0.0.0.0'
    AppConfig.port.value = 8000
# 退出时一次性落盘；块内抛异常则整块回滚
```

```python
AppConfig.server.update(host='0.0.0.0', port=8000)   # 等价，且省掉 with
```

`update()` 传入不存在的键会抛 `ConfigKeyError`，一个都不写。

## 其他方法

| 成员 | 说明 |
|---|---|
| `AppConfig.server.current_options` | `{option: 当前值}` |
| `AppConfig.server.default_options` | `{option: 默认值}`（深拷贝） |
| `AppConfig.server.get_options()` | `[option, ...]` |
| `len(section)` | 配置项个数 |
| `'host' in section` | 判断 option 是否存在 |
| `str(section)` | `<Section: Server={host=127.0.0.1, port=8080}>` |

## field() 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `default` | `''` | 默认值；**配置值的类型始终与默认值类型一致** |
| `option` | 类属性名 | 写入文件的键名 |
| `validator` | `None` | `Callable[[Any], bool]`，返回 `False` 触发 `ConfigValueError` |
| `read_only` | `False` | 运行时可读不可写 |
| `env_key` | `None` | 环境变量名，设置后被覆盖且禁止回写文件 |

同一 section 内 option 重名会抛 `ValueError`；`option` 不是 `str`、`validator` 不可调用、`read_only` 不是 `bool`、`env_key` 不是 `str` 都会抛 `TypeError`。

## API

::: conf_base.Section
