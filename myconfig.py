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
        validator=lambda x: x > 0  # 数据修改校验函数
    )
    full_screen = setting.add(option='full_screen', default=False)
    bgm_volume = setting.add(option='bgm_volume', default=1.0)

    # 关卡设置
    level = Section('Level', 'Level2')

    complete_levels = level.add(
        option='中文',  # 配置项名称,在配置文件中显示
        default=[1, 2, 3],
    )

    play_selection_card = level.add(
        option='play_selection_card',
        default=['Peashooter', 'SunFlower']
    )


# 1.基础信息使用
print('section: ', TestConfig.screen_size.section)  # 所属配置块名称
print('option: ', TestConfig.screen_size.option)  # 当前配置项名称
print('value: ', TestConfig.screen_size.value)  # 配置项当前使用1的值
print('default: ', TestConfig.screen_size.default)  # 默认值
print('-' * 20)

# 2.使用不同的配置项和数据修改
TestConfig.level.set_use_section('Level2')
TestConfig.complete_levels.value = [4, 5, 6]
print(TestConfig.complete_levels.value)

TestConfig.level.set_use_section('Level')
TestConfig.complete_levels.value = [7, 8, 9]
print(TestConfig.complete_levels.value)

TestConfig.level.set_use_section('Level2')
print(TestConfig.complete_levels.value)
TestConfig.complete_levels[1] = 3
print(TestConfig.complete_levels.value)

# 3.重置数据
TestConfig.complete_levels.reset()
print(TestConfig.complete_levels.value)


# 4.数据校验函数
# TestConfig.screen_size.value = -1
# ValueError: Setting.screen_size 配置项校验失败，值 -1 未通过 validator 校验
# TestConfig.screen_size.value = 'a'
# TypeError: Setting.screen_size 配置项期望类型 int 实际为 str



