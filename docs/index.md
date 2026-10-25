# conf_base

用类和属性声明 Python 配置：**JSON / YAML / TOML 落盘、AES-GCM 加密、环境变量覆盖、Schema 迁移**，零必需依赖。

```python
from conf_base import ConfigBase, Section

class AppConfig(ConfigBase):
    _path = 'config/app.yaml'            # 后缀决定格式，无需额外配置

    server = Section('Server')
    port = server.field(default=8080)
    secret = server.field(default='', env_key='APP_SECRET')

AppConfig.port.value = 9090              # 类型与 validator 校验通过后自动落盘
print(AppConfig.port.value)              # 9090
```

配置类本身就是 schema：属性名即配置项名，`default` 的类型即配置项类型，文件在类定义时自动创建、缺失项自动补齐。

## 它解决什么问题

`configparser` / `json.load` 这一类做法把配置当普通字典，类型、默认值、校验、加密、版本迁移全靠调用方自觉。conf_base 把这些收进声明层：

| 你原来要手写的 | conf_base 里 |
|---|---|
| 读文件、判断格式、缺键补默认值 | 类定义时自动完成 |
| `int(cfg['port'])` 之类的手工转换 | 类型由 `default` 固定，写错类型直接 `ConfigTypeError` |
| `if not 1 <= port <= 65535: raise` | `validator=` 参数，失败抛 `ConfigValueError` |
| 自己找地方存密钥、自己加密 | `_cipher = AesGcmCipher(...)`，落盘即密文 |
| 手工迁移旧字段 | `_schema_version` + `_migrate` 迁移链 |
| 每次改字段都要 `save()` | 赋值即落盘，或用 `batch()` 合并写入 |

## 适用与不适用

**适合**：桌面工具、CLI、单机服务、需要把配置连同密钥一起放到用户机器上、配置结构会随版本演进的项目。

**不适合**：远程/分布式配置中心（用 Nacos、Apollo、Consul）、高频写入（用数据库）、多用户并发编辑同一文件、复杂嵌套模型（用 pydantic）。

完整的边界说明见 [边界与取舍](boundaries.md)。

## 下一步

- [安装](installation.md)：三种安装方式与可选依赖
- [快速开始](quickstart.md)：十分钟走完声明、读取、修改、校验、加密
- [API 参考](api/config-base.md)：每个类和函数的签名与语义
- [变更记录](changelog.md)：从 0.0.1 到现在的全部版本
