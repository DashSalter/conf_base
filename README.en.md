# ConfigBase

A concise and powerful Python configuration management framework, supporting encrypted storage, attribute descriptors, nested configuration sections, and more.

## Features

- **Singleton Pattern**: Globally unique configuration instance
- **Encryption Support**: Supports plaintext and XOR encrypted configuration content
- **Descriptor Management**: Elegant access to configuration via Python descriptors
- **Nested Configuration**: Supports multi-layer nested configuration sections
- **Automatic Type Conversion**: Automatically handles the type of configuration values
- **Dirty Flag Mechanism**: Automatically detects configuration changes for batch writing

## Architecture

```
configbase/
├── crypto.py        # Encryption module (PlainCrypto, XorCrypto)
├── descriptor.py    # Configuration attribute descriptor
├── json_config.py   # Core configuration management (Singleton)
├── metaclass.py     # Configuration metaclass
├── section.py       # Configuration section management
└── singleton.py     # Singleton metaclass
```

## Installation

```bash
pip install configbase
```

## Quick Start

### 1. Define Config Class

```python
from configbase import Section, ConfigMeta
from configbase import crypto

class TestConfig(metaclass=ConfigMeta):
    # Optional: Set encryption method
    # _crypto = crypto.PlainCrypto()  # Default
    # _crypto = crypto.XorCrypto(key=b"YourSecretKey")
    
    # Define configuration sections
    database = Section("database")
    database.add("host", "localhost")
    database.add("port", 3306)
    database.add("username", "root")
    database.add("password", "")
    
    # Nested configuration sections
    cache = Section("cache", "redis")
    cache.add("host", "localhost")
    cache.add("port", 6379)
```

### 2. Use Config

```python
# Access config
host = TestConfig.database.host        # "localhost"
port = TestConfig.database.port        # 3306

# Modify config
TestConfig.database.host = "127.0.0.1"

# Get default value
timeout = TestConfig.database.timeout  # Use default value when adding

# Delete config
del TestConfig.database.username
```

## Configuration Encryption

### XOR Encryption

```python
from configbase import crypto

class TestConfig(metaclass=ConfigMeta):
    _crypto = crypto.XorCrypto(key=b"YourSecretKey12345")
    
    database = Section("database")
    database.add("password", "secret")
```

## API Reference

### Section Class

```python
Section(*section_name)
```

Create a configuration section, supporting multi-layer nesting.

**Methods:**

- `add(option, default='', fix_type=True)` - Add configuration item
- `get_options()` - Get all configuration items

### Configuration Properties

Access configuration values via descriptors, supports:

- Attribute style: `Config.section.option`
- Dictionary style: `Config.section['option']`
- Default value: Returns default value for accessing unset options

### JsonConfig Core Methods

- `load_config()` - Load configuration file
- `write_config()` - Write configuration file
- `set_option(section, option, value)` - Set configuration
- `get_option(section, option, default)` - Get configuration
- `del_option(section, option)` - Delete configuration
- `dirty` - Check if configuration has been modified

## Configuration File

Default configuration file is `settings.json`, content example:

```json
{
    "database": {
        "host": "localhost",
        "port": 3306
    }
}
```

## License

MIT License