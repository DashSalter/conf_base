# 安装

## 从 PyPI 安装

```bash
pip install conf-base
```

包名是 `conf-base`（PyPI 上的连字符写法），导入时是 `conf_base`。

只装核心包时**没有任何运行时依赖**——JSON 格式、声明式配置、`batch()`、`on_change`、Schema 迁移全部可用。

## 按需安装可选能力

| 触发场景 | 安装命令 | 引入的依赖 |
|---|---|---|
| 用 YAML 格式 | `pip install "conf-base[yaml]"` | PyYAML |
| 用 TOML 格式 | `pip install "conf-base[toml]"` | tomli-w（Python < 3.11 另加 tomli） |
| 用 AES / ChaCha20 加密 | `pip install "conf-base[aes]"` | cryptography |
| 需要多进程文件锁 | `pip install "conf-base[filelock]"` | filelock |
| 跑测试 | `pip install "conf-base[test]"` | pytest、pytest-cov |
| 运行 mypy 类型检查 | `pip install "conf-base[type]"` | mypy |

一次装齐开发环境：

```bash
pip install "conf-base[dev]"
```

## 支持的 Python 版本

Python 3.8 – 3.14，CI 在 GitHub Actions 上逐版本测试（见 [`.github/workflows/ci.yml`](https://github.com/DashSalter/conf_base/blob/master/.github/workflows/ci.yml)）。

代码本身只用了标准库；`tomllib` 在 3.11+ 直接用，更低版本回退到 `tomli`。

## 从源码安装

```bash
git clone https://github.com/DashSalter/conf_base.git
cd conf_base
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## 验证安装

```python
import conf_base

print(conf_base.__all__[:3])   # ['Section', 'ConfigBase', 'ConfigFile']
```

能用加密器：

```python
from conf_base import AesGcmCipher

AesGcmCipher(key='0123456789abcdef0123456789abcdef')
```

如果这一步报 `ImportError: cryptography is required`，说明装的是核心包，补一个 `pip install "conf-base[aes]"` 即可。
