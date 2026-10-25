# 校验器

`conf_base.validators` 提供一组开箱即用的校验器工厂。每个工厂返回 `Callable[[Any], bool]`，直接传给 `field(validator=...)`。

```python
from conf_base import ConfigBase, Section, validators


class AppConfig(ConfigBase):
    server = Section('Server')
    port = server.field(default=8080, validator=validators.in_range(1, 65535))
    host = server.field(default='127.0.0.1', validator=validators.is_url(schemes=('http',)))
    level = server.field(default='info', validator=validators.one_of('debug', 'info', 'warn', 'error'))
```

## 工厂一览

| 工厂 | 校验内容 |
|---|---|
| `in_range(minimum=None, maximum=None, *, inclusive=True)` | 数值落在区间内 |
| `one_of(*choices, ignore_case=False)` | 值属于候选集合 |
| `matches(pattern, flags=0)` | 整串匹配正则（`fullmatch`） |
| `is_url(*, schemes=('http', 'https'), require_host=True)` | 结构像 URL |
| `is_path(*, must_exist=False, kind=None)` | 结构像路径，可选检查存在性 |
| `length(minimum=None, maximum=None)` | `len()` 落在区间内 |

## 行为约定

这些校验器**只回答「合法吗」，不做任何类型转换**。类型始终由 `default` 的类型决定，写错类型在 validator 之前就被 `ConfigTypeError` 拦下了。

```python
port = server.field(default=8080, validator=validators.in_range(1, 65535))
AppConfig.port.value = '8080'
# ConfigTypeError: Server.port 配置项期望类型 int 实际为 str
```

返回 `False` 时抛 `ConfigValueError`：

```
ConfigValueError: Server.port 配置项校验失败，值 70000 未通过 validator 校验
```

validator 自己抛异常时，异常被包装成 `ConfigValueError`，原始异常挂在 `__cause__` 上：

```python
def boom(value):
    raise RuntimeError('内部错误')

port = server.field(default=8080, validator=boom)
# ConfigValueError: Server.port validator 执行异常: RuntimeError: 内部错误
```

!!! warning "bool 不算数字"
    `in_range(0, 10)(True)` 返回 `False`。`bool` 是 `int` 的子类，但把它当数字参与范围判断几乎总是 bug，所以显式排除。

## 组合

校验器是普通可调用对象，可以直接组合：

```python
def port_validator(value):
    return validators.in_range(1, 65535)(value) and value not in (22, 23)


port = server.field(default=8080, validator=port_validator)
```

## 自己写

一个校验器就是一个函数：接收值，返回 `bool`。

```python
def is_even(value):
    return isinstance(value, int) and value % 2 == 0


workers = server.field(default=4, validator=is_even)
```

## API

::: conf_base.validators
