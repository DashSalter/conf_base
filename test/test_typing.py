"""类型注解质量检查：conf_base 必须在 mypy --strict 下零错误。"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_py_typed_marker_exists():
    """发布包必须携带 py.typed，下游类型检查器才会读取内联注解。"""
    assert (ROOT / 'conf_base' / 'py.typed').is_file()


def test_mypy_strict_passes():
    """类型注解必须真实可校验，而不是写了但禁用了检查。"""
    pytest.importorskip('mypy')
    result = subprocess.run(
        [sys.executable, '-m', 'mypy', 'conf_base', '--no-incremental'],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f'mypy 发现类型错误:\n{result.stdout}{result.stderr}'
