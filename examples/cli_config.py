"""示例 1：CLI 工具的偏好设置。

演示三件事：

- 声明式配置：``Section`` + ``field()``，值类型由 default 推断
- 环境变量覆盖：环境变量 > 配置文件 > 默认值，且被覆盖的项禁止回写
- ``batch()``：把多次修改合并成一次落盘

运行：

    python examples/cli_config.py
"""

import os

from conf_base import ConfigBase, Section
from conf_base.error import ConfigValueError, WriteError


class CliConfig(ConfigBase):
    """一个假想命令行工具的本地偏好。"""

    _path = 'demo_cli.json'

    general = Section('General')
    theme = general.field(default='dark', env_key='DEMO_CLI_THEME')
    verbose = general.field(default=False, env_key='DEMO_CLI_VERBOSE')
    workers = general.field(default=4, validator=lambda v: v >= 1)

    paths = Section('Paths')
    cache_dir = paths.field(default='cache')


def main() -> None:
    print('1) 类创建时自动建文件并补齐默认值')
    print(f'   theme={CliConfig.theme.value!r}  workers={CliConfig.workers.value}')
    print(f'   文件：{CliConfig.config_path}')

    print('\n2) batch() 把两次修改合并成一次落盘')
    with CliConfig.general.batch():
        CliConfig.theme.value = 'light'
        CliConfig.workers.value = 8
    print(f'   theme={CliConfig.theme.value!r}  workers={CliConfig.workers.value}')

    print('\n3) 环境变量优先级最高，且被覆盖项禁止回写')
    os.environ['DEMO_CLI_THEME'] = 'solarized'
    print(f'   theme={CliConfig.theme.value!r}（来自 DEMO_CLI_THEME）')
    try:
        CliConfig.theme.value = 'monokai'
    except WriteError as exc:
        print(f'   回写被拒绝：{exc}')
    del os.environ['DEMO_CLI_THEME']
    print(f'   取消环境变量后 theme={CliConfig.theme.value!r}（文件里的 light）')

    print('\n4) validator 在赋值时生效')
    try:
        CliConfig.workers.value = 0
    except ConfigValueError as exc:
        print(f'   workers=0 被拒绝：{exc}')

    print('\n5) 导出整份配置（内部字段 _schema_version 不导出）')
    print(f'   {CliConfig.to_dict()}')

if __name__ == '__main__':
    main()
