# Section 与配置项

## Section 是什么

`Section('Name')` 声明一个分组，对应配置文件里的一个顶层键。`field()` 挂在 section 上，决定配置项落在哪个键下：

```python
class AppConfig(ConfigBase):
    _path = 'app.json'

    server = Section('Server')
    host = server.field(default='127.0.0.1')
    port = server.field(default=8080)

    ui = Section('UI')
    theme = ui.field(default='dark')
```

落盘结果：

```json
{
  "Server": {"host": "127.0.0.1", "port": 8080},
  "UI": {"theme": "dark"},
  "_schema_version": 1
}
```

`_schema_version` 是框架内部字段，`to_dict()` 不会导出它。

## 三种访问方式

```python
AppConfig.server.host            # 当前值（str）
AppConfig.host.value             # 通过代理读，等价
AppConfig.server['host']         # 同 section.__getitem__
```

!!! warning "`AppConfig.server.host` 是值，不是代理"
    `AppConfig.server.host` 返回 `'127.0.0.1'` 这样的**值**，后面不能再接 `.value`：

    ```python
    AppConfig.server.host.value     # AttributeError: 'str' object has no attribute 'value'
    AppConfig.host.value            # ✅ 走代理
    ```

    想链式调用就用「类.配置项」而不是「类.section.配置项」。

## 修改与批量修改

```python
AppConfig.host.value = '0.0.0.0'      # 立即落盘
AppConfig.server.update(host='0.0.0.0', port=9000)   # 一次写多个，同样立即落盘
AppConfig.server.reset()              # 整个 section 恢复默认值，一次落盘
AppConfig.host.reset()                # 单项恢复默认值
```

想在若干次修改之间只写一次磁盘：

```python
with AppConfig.server.batch():
    AppConfig.host.value = '0.0.0.0'
    AppConfig.port.value = 9000
    AppConfig.theme.value = 'light'
```

`batch()` 是 section 级方法（`AppConfig.server.batch()`），块内任何一次写入失败，整块回滚且不落盘。详见 [并发与性能](concurrency.md)。

## 值类型由 default 决定

```python
port = server.field(default=8080)        # int，写 '8080' 抛 ConfigTypeError
ratio = server.field(default=0.5)        # float，写 1 也抛 ConfigTypeError
```

不会自动转换：`int` 不是 `float` 的实例，`ratio` 写 `1` 会报「期望类型 float 实际为 int」。想要「整数也能写」的数值项，把 `default` 设成整数即可。

`bool` 同样是独立类型，框架还会拦「int 冒充 bool」：

```python
flag = server.field(default=False)
AppConfig.flag.value = 1        # ConfigTypeError：期望类型 bool 实际为 int
```

反向也一样：`default=8080` 的项写 `True` 会被拒绝，消息里直接提示「int 子类请先转换为 int」，避免 `True`/`1` 在配置文件里悄悄混用。

## 多组同构数据

同一套结构要存多份（多个存档、多个数据源）时，声明多个独立 Section，不要试图继承配置类：

```python
class GameConfig(ConfigBase):
    _path = 'game.yaml'

    save1 = Section('Save1')
    name1 = save1.field(default='存档一')
    level1 = save1.field(default=1)

    save2 = Section('Save2')
    name2 = save2.field(default='存档二')
    level2 = save2.field(default=1)
```

配置类之间**禁止相互继承**（`__init_subclass__` 会抛 `TypeError`），因为描述符与文件句柄是类级绑定的，继承会让两个类共用同一份状态。

需要「动态数量的分组」时，把 `Dict[str, Any]` 当成一个配置项，由业务代码自己管理内部结构——框架只负责整体落盘。

## 类型代理

`field()` 的返回值是带类型的代理，能用语义化方法代替手写算术：

| 代理 | 额外方法 |
|---|---|
| `BoolProxy` | `toggle()` |
| `NumberProxy` | `increment(n=1)`（要减就传负数，没有 `decrement`） |
| `ListProxy` | `append` / `extend` / `insert` / `remove` / `pop` / `clear` / `sort` / `reverse` |
| `DictProxy` | `update` / `setdefault` / `pop` / `clear` / `get` / `keys` / `values` / `items` |
| `PropertyProxy` | 仅 `value` 读写 |

```python
AppConfig.debug.toggle()             # bool
AppConfig.port.increment(10)         # int / float
AppConfig.plugins.append('extra')    # list
AppConfig.limits.update(cpu=2)       # dict
```

代理的每个写方法都走完整校验链（类型 → validator）并落盘，和在代理上直接赋 `.value` 等价。

## IDE 里的类型

`field()` 有 6 个重载，静态检查器据 `default` 推断代理类型：

```python
width = screen.field(default=1280)
width.increment()        # IDE 知道这是 NumberProxy
```
