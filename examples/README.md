# 示例

三个可以直接运行的最小示例，覆盖最常见的三种用法。每个文件都能单独执行，不需要改代码。

| 文件 | 场景 | 演示的能力 |
|---|---|---|
| [`cli_config.py`](cli_config.py) | 命令行工具的本地偏好 | `Section` + `field()` 声明、环境变量覆盖、`batch()` 合并落盘、validator |
| [`game_config.py`](game_config.py) | 游戏客户端配置 | YAML 落盘、自定义校验、类型代理（`toggle()` / `append()`） |
| [`secure_server_config.py`](secure_server_config.py) | 服务端配置 | AES-256-GCM 加密落盘、Schema 版本迁移链 |

## 运行

```bash
# 在仓库根目录执行，让 Python 能找到 conf_base
pip install -e ".[dev]"

python examples/cli_config.py
python examples/game_config.py
python examples/secure_server_config.py
```

`game_config.py` 需要 `PyYAML`，`secure_server_config.py` 需要 `cryptography`；
上面的 `.[dev]` 已经把两者装好，只想按需安装时可改用
`pip install conf_base[yaml,aes]`。

## 关于产物文件

示例会把配置文件写在**当前工作目录**下（`demo_cli.json`、`demo_game.yaml`、
`demo_server.json.enc`、`demo_migrated.json`），方便你直接打开看内容。
这些文件名已在 `.gitignore` 里，不会误提交；不需要时直接删掉即可。

## 关于文件锁

示例未关闭多进程文件锁（`_use_file_lock` 默认 `True`）。如果你的环境禁止创建
`.lock` 文件（某些容器、只读挂载或企业安全策略），在类里加一行：

```python
class CliConfig(ConfigBase):
    _use_file_lock = False
    ...
```

生产环境不建议关闭：它保护的是同一份配置文件被多个进程同时写入的场景。
