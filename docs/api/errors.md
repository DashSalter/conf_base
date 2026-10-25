# 异常

所有框架异常都继承 `ConfBaseError`，可以一次性捕获；同时多重继承对应的内建异常，所以旧代码里的 `except ValueError` / `except KeyError` 仍然有效。

```python
from conf_base import ConfBaseError

try:
    ...
except ConfBaseError as exc:
    print('配置出问题了：', exc)
```

## 继承关系

| 异常 | 继承自 | 触发场景 |
|---|---|---|
| `ConfBaseError` | `Exception` | 所有框架异常的基类 |
| `WriteError` | `ConfBaseError` | 写只读项；给 `Section` 属性直接赋值；环境变量覆盖时回写 |
| `ParseError` | `ConfBaseError`, `ValueError` | 配置文件内容损坏，无法解析 |
| `ConfigTypeError` | `ConfBaseError`, `TypeError` | 写入的值类型与 `default` 类型不一致 |
| `ConfigValueError` | `ConfBaseError`, `ValueError` | 未通过 validator；或 validator 自身抛异常 |
| `DecryptError` | `ConfBaseError`, `ValueError` | 解密失败、签名不匹配、文件被篡改 |
| `SchemaError` | `ConfBaseError`, `ValueError` | 文件版本高于代码版本；迁移失败 |
| `ConfigKeyError` | `ConfBaseError`, `KeyError` | section 或 option 不存在 |
| `LockError` | `ConfBaseError`, `TimeoutError` | 等文件锁超时 |

## 常见消息

```
ConfigTypeError:  Server.port 配置项期望类型 int 实际为 str
ConfigTypeError:  S.port 配置项期望类型 int 实际为 bool，int 子类请先转换为 int
ConfigValueError: Server.port 配置项校验失败，值 70000 未通过 validator 校验
WriteError:       S.ro is read only.
WriteError:       Server.key 由环境变量 DEMO_KEY 覆盖，禁止回写配置文件。请移除环境变量后再修改。
WriteError:       不能直接给 Section 属性 'host' 赋值（这样不会写入配置文件）。
                  请改用 section['host'] = value 或 section.host.value = value
SchemaError:      配置文件 'm3.json' 的版本 v5 高于代码声明的 _schema_version=v2，
                  请升级代码或修正文件版本。
```

## 定位根因

包装型异常保留原始异常：

| 异常 | `__cause__` |
|---|---|
| `ParseError` | 解析器抛出的原始异常（如 `json.JSONDecodeError`） |
| `ConfigValueError`（validator 抛错） | validator 内部抛出的异常 |

迁移函数抛出的异常不做包装，直接冒泡——所以你 `except` 的类型就是迁移函数自己抛的那个。

## API

::: conf_base.error
