import conf_base.Error
from conf_base import ConfigMeta, Section, crypto

"""
测试配置项的设置 校验 切换功能 类型校验
"""


class TestConfig(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson('settings_test.json')

    setting = Section('Setting')
    screen_size = setting.add(
        option='screen_size',
        default=3,
        validator=lambda x: x > 0  # 数据修改校验函数
    )
    full_screen = setting.add(option='full_screen', default=False)
    bgm_volume = setting.add(option='bgm_volume', default=1.0, read_only=True)

    # 关卡设置
    level = Section('Level', 'Level2')
    complete_levels = level.add(
        option='中文',  # 配置项名称,在配置文件中显示
        default=[1, 2, 3],
    )


try:
    TestConfig.screen_size.value = -1
except ValueError as e:
    print('数据校验函数 验证通过')
# ValueError: Setting.screen_size 配置项校验失败，值 -1 未通过 validator 校验

try:
    TestConfig.screen_size.value = 'a'
except TypeError as e:
    print('配置项期望类型 验证通过')
# TypeError: Setting.screen_size 配置项期望类型 int 实际为 str

try:
    TestConfig.bgm_volume.value = 2
except conf_base.Error.WriteError as e:
    print('只读功能 验证通过')

# 2.使用不同的配置项和数据修改
TestConfig.level.set_use_section('Level2')
TestConfig.complete_levels.value = [4, 5, 6]
assert TestConfig.complete_levels.value == [4, 5, 6]

TestConfig.level.set_use_section('Level')
TestConfig.complete_levels.value = [7, 8, 9]
assert TestConfig.complete_levels.value == [7, 8, 9]

TestConfig.level.set_use_section('Level2')
TestConfig.complete_levels[1] = 3
assert TestConfig.complete_levels.value == [4, 3, 6]
print('配置项使用 正常')

# 重置数据
TestConfig.setting.reset()

# 关卡数据重置
print(TestConfig.setting)
print(TestConfig.level)
TestConfig.level.reset()
print(TestConfig.level)
# <Section:Level [中文=[1, 2, 3]], Level2 [中文=[1, 2, 3]]>
print(TestConfig.level.current_options)

print('\n全部数据输出')
print(TestConfig.to_dict())

print('\n修改调用')


def func1(section, option, value):
    # 当数据修改时，自动调用该函数
    print(f'func1调用 section:{section}, option:{option}, value:{value}')


TestConfig.level.set_use_section('Level2')
# 普通写法,通过on_change方法进行绑定函数  section='Level2' 可选只监听的配置块，数据修改时调用func1
TestConfig.complete_levels.on_change(func1, section='Level2')
TestConfig.complete_levels.value = [1]


@TestConfig.complete_levels.on_change(section='Level')  # 装饰器写法,section='Level' 可选只监听的配置块
def func2(section, option, value):
    # 当数据修改时，自动调用该函数
    print(f'func2调用 section:{section}, option:{option}, value:{value}')


# 切换 Level 然后修改，调用func2函数
TestConfig.level.set_use_section('Level')
TestConfig.complete_levels.value = [1]
