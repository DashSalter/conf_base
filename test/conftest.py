"""全局 fixtures：临时目录、环境变量清理等。"""

import os
import sys
import pytest

# 让测试能 import conf_base
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def tmp_dir(tmp_path):
    """提供一个临时目录，测试结束自动清理。"""
    return str(tmp_path)


@pytest.fixture
def clean_env():
    """保存并恢复环境变量，确保测试间互不干扰。"""
    saved = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved)
