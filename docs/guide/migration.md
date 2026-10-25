# Schema 迁移

配置结构会随版本演进：字段改名、类型调整、拆分子 section。conf_base 用「版本号 + 迁移函数链」描述这件事，老配置文件在加载时自动升级。

## 一段最小迁移

假设 1.0 版本的字段叫 `Server.threads`，2.0 改名为 `Server.workers`：

```python
from conf_base import ConfigBase, Section


def migrate_v1_to_v2(config):
    """把 v1 的 Server.threads 改名为 v2 的 Server.workers。"""
    data = dict(config)
    server = dict(data.get('Server', {}))
    server['workers'] = server.pop('threads', 4)
    data['Server'] = server
    return data


class AppConfig(ConfigBase):
    _path = 'config/app.json'
    _schema_version = 2
    _migrate = {1: migrate_v1_to_v2}

    server = Section('Server')
    host = server.field(default='127.0.0.1')
    port = server.field(default=8080)
    workers = server.field(default=4)
```

打开一份旧文件：

```json
{"_schema_version": 1, "Server": {"host": "10.0.0.5", "port": 9000, "threads": 8}}
```

类创建完成后：

- 内存里的配置已经变成 v2（`threads: 8` → `workers: 8`）
- 磁盘文件被回写为 `_schema_version: 2`
- 新增的 `host`/`port` 缺失项按默认值补齐

## 迁移函数的契约

```python
def migrate(config: dict) -> dict: ...
```

| 要求 | 说明 |
|---|---|
| 输入 | 当前版本的完整配置字典，**包含 `_schema_version`**，可原样带往下一级 |
| 输出 | 迁移后的完整字典；框架随后会用自己的版本号覆盖 `_schema_version` |
| 副作用 | 不要读写磁盘，也不要改全局状态——迁移应是纯变换 |
| 异常 | 原样抛给调用方（**不会**包装成 `SchemaError`）；文件不会落盘 |

一条链上多个版本按顺序执行：

```python
_migrate = {1: migrate_v1_to_v2, 2: migrate_v2_to_v3}
```

文件是 v1、代码是 v3 时，依次跑 `1→2`、`2→3`。

## 版本号规则

- `_schema_version` 必须是非负整数，`True`/`False` 也会被拒绝（bool 不算 int）
- 省略时默认是 `1`
- 文件版本 **低于** 代码版本：跑迁移链，成功后回写
- 文件版本 **高于** 代码版本：抛 `SchemaError`，不会强行降级——降级意味着丢字段，必须由人决定
- 文件版本等于代码版本：不动

## 迁移失败怎么办

迁移函数抛出的异常会**原样冒泡**（不会被包装成 `SchemaError`），加载中断；此时还没有写盘，原文件保持 v1 不变，修好迁移函数重新加载即可。

```python
try:
    from myapp.config import AppConfig
except RuntimeError as exc:      # 迁移函数自己抛出的异常类型
    print('配置升级失败：', exc)
```

只有「文件版本高于代码版本」这一种情况抛 `SchemaError`：

```
SchemaError: 配置文件 'app.json' 的版本 v5 高于代码声明的 _schema_version=v2，
             请升级代码或修正文件版本。
```

!!! warning "迁移链是单向的"
    写坏的迁移函数在被修正前，每次加载都会重新跑一遍并失败。线上环境建议先在副本上验证迁移结果，再放开。

## 什么时候需要迁移

| 场景 | 是否需要迁移 |
|---|---|
| 新增字段（有默认值） | 不需要，缺失项自动补齐 |
| 删除字段 | 不需要，`_prune_unknown` 会清掉旧键 |
| 字段改名 | 需要 |
| 类型变更（如 `port` 从 str 改 int） | 需要 |
| 结构重组（拆/并 section） | 需要 |
| 默认值变化 | 不需要 |

只有当**旧文件里的数据无法直接映射到新 schema** 时才写迁移函数。
