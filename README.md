# ConfigBase

一个简洁的 Python 配置管理框架，支持加密存储、属性描述符、嵌套配置段等功能。


## 安装

```bash
pip install conf_base
```

## 快速开始

### 1. 定义配置类

```python
from conf_base import ConfigMeta, Section, crypto

"""
测试使用示例
"""


class TestConfig(metaclass=ConfigMeta):
    # _crypto = crypto.PlainCrypto() # 默认使用
    # _crypto = crypto.XorCrypto()

    # 全局设置
    setting = Section('Setting')
    screen_size = setting.add(
        option='screen_size',
        default=3,
        validator=lambda x: x > 0 # 数据修改校验函数
    )
    full_screen = setting.add(option='full_screen', default=False)
    bgm_volume = setting.add(option='bgm_volume', default=1.0)
    sound_volume = setting.add(option='sound_volume', default=1.0)

    # 关卡设置
    level = Section('Level', 'Level2')

    complete_levels = level.add(
        option='中文',  # 配置项名称,在配置文件中显示
        default=[1, 2, 3],
        fix_type=False # fix_type 默认为True 数据修改类型必须保持一致
    )

    play_selection_card = level.add(
        option='play_selection_card',
        default=['Peashooter', 'SunFlower']
    )


# 基础信息
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

# 数据校验函数
# TestConfig.screen_size.value = -1
# ValueError: Setting.screen_size 配置项校验失败，值 -1 未通过 validator 校验
# TestConfig.screen_size.value = 'a'
# TypeError: Setting.screen_size 配置项期望类型 int 实际为 str， 否则请修改配置项 fix_type=False

```
