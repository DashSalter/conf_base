# 校验与只读

## 写入时的检查顺序

任何一次写入（`.value =`、`update()`、`reset()`、代理的语义化方法）都走同一条链：

1. **环境变量覆盖** —— 该项被 `env_key` 覆盖时，直接抛 `WriteError`
2. **`read_only`** —— 声明为只读时抛 `WriteError`
3. **类型** —— 与 `default` 类型不符时抛 `ConfigTypeError`
4. **validator** —— 返回 `False` 或抛异常时抛 `ConfigValueError`

顺序是固定的：类型不对就不会走到 validator，被环境变量覆盖的项也不会因为 validator 通过而写进去。

## validator 的两种失败方式

```python
port = server.field(default=8080, validator=lambda v: 1 <= v <= 65535)
```

- **返回 `False`/假值** → `ConfigValueError`，消息里带 `section.option`、实际值和失败原因
- **自己抛异常** → 同样包装成 `ConfigValueError`，原始异常挂在 `__cause__` 上

```python
try:
    AppConfig.port.value = 70000
except ConfigValueError as exc:
    print(exc)
    # Server.port 配置项校验失败，值 70000 未通过 validator 校验
```

validator 抛异常的场景：

```python
def guard(value):
    if value in BANNED:
        raise ValueError('这个端口被占用')
    return True

port = server.field(default=8080, validator=guard)
```

`ConfigValueError` 同时继承 `ValueError`，所以既有的 `except ValueError` 代码不用改。

## 内置校验器

`conf_base.validators` 提供了六个工厂，省去重复写 lambda：

```python
from conf_base.validators import in_range, is_path, is_url, length, matches, one_of

class AppConfig(ConfigBase):
    port = server.field(default=8080, validator=in_range(1, 65535))
    bind = server.field(default='127.0.0.1', validator=matches(r'\d{1,3}(\.\d{1,3}){3}'))
    hook = server.field(default='https://example.com/hook', validator=is_url())
    log_dir = server.field(default='logs', validator=is_path())
    level = server.field(default='info', validator=one_of('debug', 'info', 'warning', 'error'))
    tags = server.field(default=['a'], validator=length(1, 5))
```

| 工厂 | 作用 | 边界行为 |
|---|---|---|
| `in_range(minimum, maximum, inclusive=True)` | 数值范围 | 只接受 `int`/`float`；`True`/`False` 不算数字 |
| `one_of(*choices, ignore_case=False)` | 枚举 | `ignore_case` 只对 str 生效；`one_of(1,2)(True)` 为 `False` |
| `matches(pattern, flags=0)` | 正则 | 整体匹配（同 `re.fullmatch`），也接受已编译 pattern |
| `is_url(schemes=('http','https'))` | URL 结构 | 只做结构检查，不发请求 |
| `is_path(must_exist=False, kind=None)` | 路径 | `kind` 可为 `'file'`/`'dir'` |
| `length(minimum, maximum)` | 长度 | `str`/`list`/`dict`/`tuple` |

它们只判断合法性，**不做类型转换**，类型仍由 `default` 决定。参数非法时（如 `in_range()` 不给边界）在**声明阶段**就抛 `ValueError`，不会等到运行时才发现规则写错。

完整签名与示例见 [校验器 API](../api/validators.md)。

## 组合校验

内置工厂返回的是普通函数，可以组合：

```python
validator=lambda v: in_range(1, 65535)(v) and v % 2 == 1
```

或写一个返回函数的工厂：

```python
def multiple_of(step):
    return lambda v: isinstance(v, int) and v % step == 0

workers = server.field(default=4, validator=multiple_of(2))
```

## 只读配置项

```python
build_id = server.field(default='dev', read_only=True)

AppConfig.build_id.value = 'v2'   # WriteError: Server.build_id is read only.
```

!!! note "只读项的错误消息是英文"
    `read_only` 与「环境变量覆盖」两类 `WriteError` 消息来自不同分支，前者目前是英文
    （`Server.build_id is read only.`），后者是中文；按消息文本匹配时请留意。

常见用法是「首次写入后不再改」：把默认值留给代码，实际值作为产物写入文件。

`reset()` 也会被 `read_only` 拦住——只读项无法通过 `reset()` 绕过。

## 环境变量覆盖与校验的关系

被 `env_key` 覆盖的项，读取时走的是环境变量值，写入时一律 `WriteError`：

```python
port = server.field(default=8080, env_key='APP_PORT')
```

```bash
APP_PORT=9000 python app.py     # AppConfig.port.value == 9000
```

```python
AppConfig.port.value = 8000     # WriteError：Server.port 被环境变量覆盖
```

详见 [环境变量覆盖](environment.md)。
