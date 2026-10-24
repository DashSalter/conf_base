"""示例 2：游戏客户端配置（YAML 存储 + 自定义校验 + 类型代理）。

演示：

- ``YamlFormat``：按原生 YAML 落盘，便于人工查看与版本管理
- ``validator``：赋值即校验，非法值进不了内存，也写不进文件
- 类型代理：``toggle()`` / ``append()`` 这类语义化方法，读写原子完成

运行：

    pip install conf_base[yaml]
    python examples/game_config.py
"""

from conf_base import ConfigBase, Section, YamlFormat
from conf_base.error import ConfigValueError


class GameConfig(ConfigBase):
    """一个假想游戏客户端的配置。"""

    _path = 'demo_game.yaml'
    _format = YamlFormat()

    screen = Section('Screen')
    width = screen.field(default=1280, validator=lambda v: v >= 800)
    height = screen.field(default=720, validator=lambda v: v >= 600)
    fullscreen = screen.field(default=False)

    audio = Section('Audio')
    bgm_volume = audio.field(default=0.8, validator=lambda v: 0.0 <= v <= 1.0)
    mute = audio.field(default=False)

    save = Section('Save')
    unlocked_levels = save.field(default=[1])


def main() -> None:
    print(f'初始窗口：{GameConfig.width.value} x {GameConfig.height.value}')

    print('\n1) 类型代理带语义化方法，不需要手动读改写')
    GameConfig.fullscreen.toggle()
    GameConfig.bgm_volume.value = 0.6
    GameConfig.unlocked_levels.append(2)
    print(f'   全屏={GameConfig.fullscreen.value}  音量={GameConfig.bgm_volume.value}')
    print(f'   已解锁关卡={GameConfig.unlocked_levels.value}')

    print('\n2) validator 拒绝非法值')
    try:
        GameConfig.width.value = 640
    except ConfigValueError as exc:
        print(f'   width=640 被拒绝：{exc}')
    print(f'   width 仍是 {GameConfig.width.value}')

    print('\n3) 落盘就是可读的 YAML')
    with open(GameConfig._path, encoding='utf-8') as fh:
        print(''.join(f'   {line}' for line in fh.readlines()))


if __name__ == '__main__':
    main()
