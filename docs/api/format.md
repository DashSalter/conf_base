# 格式

格式只负责「字典 ↔ 文本」，不关心加密——加密在它之后发生。两者正交，可以自由组合。

## 内置格式

| 类 | `_format` 传入 | 识别后缀 | 依赖 |
|---|---|---|---|
| `JsonFormat` | `JsonFormat()` | `.json`、无后缀 | 标准库 |
| `YamlFormat` | `YamlFormat()` | `.yaml`、`.yml` | `pyyaml`（`pip install "conf-base[yaml]"`） |
| `TomlFormat` | `TomlFormat()` | `.toml` | 读：3.11+ 用 `tomllib`，3.8–3.10 需 `tomli`；写：需 `tomli-w`。装 `pip install "conf-base[toml]"` |

省略 `_format` 时按 `_path` 后缀推断；没有后缀则用 JSON。

`_format` 只接受 `BaseFormat` **实例**，传字符串会抛 `TypeError`；显式给了实例却与路径后缀冲突时抛 `ValueError`——不会静默选一个。

```python
class AppConfig(ConfigBase):
    _path = 'config/app.yaml'
    _format = JsonFormat()
    # ValueError: 路径 'config/app.yaml' 的后缀与 _format=JsonFormat 不匹配，
    #             请统一格式或去掉路径后缀
```

## 协议

自定义格式只需实现两个方法：

```python
from conf_base import BaseFormat

class CsvFormat(BaseFormat):
    def serialize(self, data: dict) -> str:
        ...

    def deserialize(self, text: str) -> dict:
        ...
```

| 方法 | 输入 | 输出 | 失败时 |
|---|---|---|---|
| `serialize(data)` | `Dict[str, Any]` | `str` | 抛异常 |
| `deserialize(text)` | `str` | `Dict[str, Any]` | 抛 `ParseError` |

`deserialize` 返回的不是 `dict` 时框架抛 `ParseError`。

```python
class AppConfig(ConfigBase):
    _path = 'config/app.csv'
    _format = CsvFormat()
```

## 解析错误

文件内容不合法时抛 `ParseError`，原始异常挂在 `__cause__` 上：

```python
try:
    from myapp.config import AppConfig
except ParseError as exc:
    print('配置文件格式错误：', exc.__cause__)
```

## API

::: conf_base.format
