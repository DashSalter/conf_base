# ConfigBase

一个简洁的 Python 配置管理框架，支持加密存储、属性描述符、嵌套配置段等功能。

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
from configbase import ConfigMeta, Section, crypto


class TestConfig(metaclass=ConfigMeta):
    # _crypto = crypto.PlainCrypto() # 默认使用
    # _crypto = crypto.XorCrypto()

    # 全局设置
    setting = Section('Setting')
    screen_size = setting.add(option='screen_size', default=3)
    full_screen = setting.add(option='full_screen', default=False)
    bgm_volume = setting.add(option='bgm_volume', default=1.0)
    sound_volume = setting.add(option='sound_volume', default=1.0)

    # 关卡设置
    level = Section('Level', 'Level2')
    # fix_type 默认为True 数据修改类型必须保持一致
    complete_levels = level.add(option='中文', default=[1, 2, 3], fix_type=False)
    play_selection_card = level.add(
        option='play_selection_card',
        default=['Peashooter', 'SunFlower']
    )


print('section: ', TestConfig.screen_size.section)
print('option: ', TestConfig.screen_size.option)
print('value: ', TestConfig.screen_size.value)
print('default: ', TestConfig.screen_size.default)
print('-' * 20)

# 使用不同的配置项和数据修改
TestConfig.level.set_use_section('Level2')
TestConfig.complete_levels.value = {1: 1}
print(TestConfig.complete_levels.value)

TestConfig.level.set_use_section('Level')
TestConfig.complete_levels.value = {2: 2}
print(TestConfig.complete_levels.value)

TestConfig.level.set_use_section('Level2')
TestConfig.complete_levels.value = {3: 3}
print(TestConfig.complete_levels.value)

# 重置数据
TestConfig.complete_levels.reset()
print(TestConfig.complete_levels.value)

# 如何快速进行读写操作
```
