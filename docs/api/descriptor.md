# 描述符与代理

`AppConfig.port` 拿到的不是数字，而是一个**代理对象**。这样做是为了在不牺牲 `AppConfig.port.value` 写法可读性的前提下，提供 `increment()`、`toggle()` 这类语义化方法。

## 结构

```
AppConfig.port          → ConfigProperty.__get__() → NumberProxy 实例
NumberProxy.value       → ConfigProperty.get_value()  （env > 文件 > 默认值）
NumberProxy.value = 9000→ ConfigProperty.set_value()  （env 检查 → read_only → 类型 → validator → 落盘）
```

`ConfigProperty` 是描述符本身（类属性），代理是它按 `default` 的类型缓存的单例。

## 代理类型分派

| `default` 类型 | 代理类 | 额外方法 |
|---|---|---|
| `bool` | `BoolProxy` | `toggle()` |
| `int` / `float` | `NumberProxy` | `increment(n=1)` |
| `list` | `ListProxy` | `append/extend/insert/remove/pop/clear/sort/reverse` |
| `dict` | `DictProxy` | `update/setdefault/pop/clear/get/keys/values/items` |
| 其他（`str` 等） | `PropertyProxy` | 无，只有 `value` |

!!! note "bool 在 int 之前判断"
    `bool` 是 `int` 的子类，分派顺序上必须优先，否则 `toggle()` 会被吞成 `increment()`。

## 共有成员

| 成员 | 说明 |
|---|---|
| `value` | 读 / 写当前值（写入走完整校验链） |
| `default` | 默认值，**只读**，赋值抛 `ValueError: default is readonly` |
| `env_key` | 环境变量名（可能为 `None`） |
| `has_env_override` | 当前是否被环境变量覆盖 |
| `is_default` | 当前值是否等于默认值 |
| `option` / `section` | 所属键名与 section 名 |
| `set_value(v)` | 同 `value = v` |
| `reset()` | 恢复默认值并落盘，返回默认值副本 |
| `on_change(cb)` | 注册变更回调 |

## 变更回调

回调签名固定为 `callback(section, option, value)`，即 `Callback = Callable[[str, str, Any], None]`。支持装饰器与普通调用两种写法：

```python
@AppConfig.port.on_change
def on_port_change(section, option, value):
    print(f'{section}.{option} -> {value!r}')


def audit(section, option, value):
    ...

AppConfig.port.on_change(audit)
```

无论用哪种写法，回调都在**落盘之后**触发；`reset()` 与 `batch()` 内的修改同样会触发。回调抛出的异常不会被吞掉，会从赋值语句冒泡。

!!! warning "batch() 内每次赋值都会触发回调"
    回调是按「值变更」触发的，不是按「落盘」触发的。`batch()` 里改 50 个值，就触发 50 次回调。

## 比较语义

代理重写了 `__eq__`，与非代理对象比较时比较的是**当前值**：

```python
AppConfig.port == 8080        # True，比较的是值
AppConfig.port == AppConfig.other_port   # 比较的是「是不是同一个配置项」
```

## 直接给类属性赋值

描述符实现了 `__set__`，所以下面三行等价：

```python
AppConfig.port.value = 9000
AppConfig.port = 9000
AppConfig.server['port'] = 9000
```

## API

::: conf_base.ConfigProperty

::: conf_base.PropertyProxy

::: conf_base.BoolProxy

::: conf_base.NumberProxy

::: conf_base.ListProxy

::: conf_base.DictProxy
