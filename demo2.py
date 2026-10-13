from conf_base import ConfigMeta, Section, crypto


# 5.不同的配置类存储到不同的配置文件
class TestConfig2(metaclass=ConfigMeta):
    _crypto = crypto.PlainCrypto('settings_2.json')  # 不同的类配置项使用不同的名称，防止文件名称重叠造成数据覆盖
    _auto_reload = True # 每次从最新文件读取

    setting = Section('Setting')
    bgm_volume = setting.add(option='bgm_volume', default=1.0)
    play_selection_card = setting.add(
        option='play_selection_card',
        default=['Peashooter', 'SunFlower']
    )

# import time
# while True:
#     print(TestConfig2.bgm_volume.value)
#     time.sleep(0.5)