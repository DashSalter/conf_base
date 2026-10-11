# ConfigBase

一个简洁强大的 Python 配置管理框架，支持加密存储、属性描述符、嵌套配置段等功能。

## 特性

- **单例模式**：全局唯一的配置实例
- **加密支持**：支持明文和 XOR 加密配置内容
- **描述符管理**：通过 Python 描述符优雅访问配置
- **嵌套配置**：支持多层嵌套的配置段
- **类型自动转换**：自动处理配置值的类型
- **脏标记机制**：自动检测配置变更，批量写入

## 架构

```
configbase/
├── crypto.py        # 加密模块（PlainCrypto、XorCrypto）
├── descriptor.py    # 配置属性描述符
├── json_config.py   # 核心配置管理（单例）
├── metaclass.py     # 配置元类
├── section.py       # 配置段管理
└── singleton.py     # 单例元类
```

## 安装

```bash
pip install configbase
```

## 快速开始

### 1. 定义配置类

```python
from configbase import Section, ConfigMeta
from configbase import crypto

class TestConfig(metaclass=ConfigMeta):
    # 可选：设置加密方式
    # _crypto = crypto.PlainCrypto()  # 默认
    # _crypto = crypto.XorCrypto(key=b"YourSecretKey")
    
    # 定义配置段
    database = Section("database")
    database.add("host", "localhost")
    database.add("port", 3306)
    database.add("username", "root")
    database.add("password", "")
    
    # 嵌套配置段
    cache = Section("cache", "redis")
    cache.add("host", "localhost")
    cache.add("port", 6379)
```

### 2. 使用配置

```python
# 访问配置
host = TestConfig.database.host        # "localhost"
port = TestConfig.database.port        # 3306

# 修改配置
TestConfig.database.host = "127.0.0.1"

# 获取默认值
timeout = TestConfig.database.timeout  # 使用 add 时的默认值

# 删除配置
del TestConfig.database.username
```

## 配置加密

### XOR 加密

```python
from configbase import crypto

class TestConfig(metaclass=ConfigMeta):
    _crypto = crypto.XorCrypto(key=b"YourSecretKey12345")
    
    database = Section("database")
    database.add("password", "secret")
```

## API 参考

### Section 类

```python
Section(*section_name)
```

创建配置段，支持多层嵌套。

**方法：**

- `add(option, default='', fix_type=True)` - 添加配置项
- `get_options()` - 获取所有配置项

### 配置属性

通过描述符访问配置值，支持：

- 属性方式：`Config.section.option`
- 字典方式：`Config.section['option']`
- 默认值：访问未设置的选项返回默认值

### JsonConfig 核心方法

- `load_config()` - 加载配置文件
- `write_config()` - 写入配置文件
- `set_option(section, option, value)` - 设置配置
- `get_option(section, option, default)` - 获取配置
- `del_option(section, option)` - 删除配置
- `dirty` - 检查配置是否已修改

## 配置文件

默认配置文件为 `settings.json`，内容示例：

```json
{
    "database": {
        "host": "localhost",
        "port": 3306
    }
}
```

## 许可证

MIT License