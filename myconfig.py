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
