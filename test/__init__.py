"""
# 本地
python -m pytest test/ -v
python -m pytest test/test_basic.py::TestBasicConfig::test_read_write -v

# 安装开发全套依赖
pip install conf_base[dev]
"""