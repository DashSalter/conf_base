# ConfigBase

配置类的基类。子类在类体中声明配置项；类创建时框架会自动完成「建文件 → 补齐默认值 → 加载 → 迁移」。

```python
from conf_base import ConfigBase, Section


class AppConfig(ConfigBase):
    _path = 'config/app.json'

    server = Section('Server')
    host = server.field(default='127.0.0.1')
    port = server.field(default=8080)
```

## 类级配置

这些属性写在子类里，框架在类创建时读取一次。

| 属性 | 默认值 | 说明 |
|---|---|---|
| `_path` | `<类名小写>.json` | 配置文件路径，相对路径按当前工作目录解析；父目录不存在会自动创建 |
| `_format` | `None`（按后缀推断） | `BaseFormat` 实例（如 `JsonFormat()`）；省略时看 `_path` 的后缀，无后缀用 JSON。**不接受字符串** |
| `_cipher` | `None` | 加密器实例，如 `AesGcmCipher()`；加密器自带的后缀（如 `.enc`）会先从 `_path` 上剥离再推断格式 |
| `_schema_version` | `1` | 代码侧的 schema 版本，必须是 `>= 0` 的 `int`（`bool` 也会被拒绝） |
| `_migrate` | `{}` | `{旧版本号: 迁移函数}`，见 [Schema 迁移](../guide/migration.md) |
| `_auto_reload` | `False` | 读取时按 `(mtime_ns, size)` 指纹检测外部修改 |
| `_use_file_lock` | `True`（装了 `filelock` 时） | 多进程写锁 |
| `_lock_timeout` | `10.0` | 等锁超时秒数 |

!!! warning "配置类不能相互继承"
    `__init_subclass__` 直接检查基类列表，出现 `class Sub(MyConfig)` 会抛 `TypeError`。描述符与 `ConfigFile` 是类级绑定，继承会让两套 schema 抢同一个文件。

    ```python
    class Base(ConfigBase): ...
    class Sub(Base): ...        # TypeError
    ```

    需要复用字段时，把公共部分抽成 mixin 函数或模块级常量，不要继承配置类。

## 运行时属性

| 属性 / 方法 | 类型 | 说明 |
|---|---|---|
| `config_path` | `str` | 实际使用的配置路径（`_path` 的解析结果，原样保留相对路径） |
| `config_node` | `Dict[str, List[str]]` | `{section: [option, ...]}`，运行时 schema 快照 |
| `to_dict()` | `Dict[str, Any]` | 导出当前全部配置值，不含 `_schema_version` |

这三个成员由框架在类创建时绑定到类上，因此类型声明写在 `ConfigBase` 类体里，IDE 与 mypy 都能识别。

```python
AppConfig.config_path     # 'config/app.json'
AppConfig.config_node     # {'Server': ['host', 'port']}
AppConfig.to_dict()       # {'Server': {'host': '127.0.0.1', 'port': 8080}}
```

## API

::: conf_base.config_base.ConfigBase
