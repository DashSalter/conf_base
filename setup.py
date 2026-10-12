import setuptools  # 导入setuptools打包工具

long_description = ''

with open(r"README.md", "r", encoding="utf-8") as fh:
    long_description += fh.read()

with open(r"myconfig.py", "r", encoding="utf-8") as fh:
    long_description += '```python\n'
    long_description += fh.read()
    long_description += '\n```'

setuptools.setup(
    name="conf_base",  # 用自己的名替换其中的YOUR_USERNAME_
    version="0.0.4",  # 包版本号，便于维护版本
    author="加点盐",  # 作者，可以写自己的姓名
    author_email="1431705288@qq.com",  # 作者联系方式，可写自己的邮箱地址
    description="一个简洁的 Python 配置管理框架，支持加密存储、属性描述符、嵌套配置段等功能。",  # 包的简述
    long_description=long_description,  # 包的详细介绍，一般在README.md文件内
    long_description_content_type="text/markdown",
    url="https://gitee.com/kuangjianke/conf_base",  # 自己项目地址，比如github的项目地址
    packages=setuptools.find_packages(),
    install_requires=[],  # 依赖模块
    include_package_data=True,
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',  # 对python的最低版本要求
)

# 打包
# pip install build twine
# python -m build
# twine upload dist/*
