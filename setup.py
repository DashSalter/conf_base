import os
import setuptools  # 导入setuptools打包工具

HERE = os.path.dirname(os.path.abspath(__file__))

long_description = ''

with open(os.path.join(HERE, "README.md"), "r", encoding="utf-8") as fh:
    long_description += fh.read()

setuptools.setup(
    name="conf_base",  # 用自己的名替换其中的YOUR_USERNAME_
    version="0.2.0",  # 包版本号，便于维护版本
    author="加点盐",  # 作者，可以写自己的姓名
    author_email="1431705288@qq.com",  # 作者联系方式，可写自己的邮箱地址
    description="一个通过类和属性构建的Python配置管理框架，更加便捷与安全的操作与存储配置数据。",  # 包的简述
    long_description=long_description,  # 包的详细介绍，一般在README.md文件内
    long_description_content_type="text/markdown",
    url="https://gitee.com/kuangjianke/conf_base",  # 自己项目地址，比如github的项目地址
    packages=setuptools.find_packages(),
    package_data={'conf_base': ['py.typed']},  # 让下游工具识别内联类型注解
    install_requires=[],  # 依赖模块
    extras_require={
        'filelock': ['filelock'],
        'aes': ['cryptography'],
        'yaml': ['PyYAML'],
        'toml': ['tomli-w', "tomli; python_version<'3.11'"],
        'test': ['pytest', 'pytest-cov'],
        'type': ['mypy'],
        'dev': ['filelock', 'cryptography', 'PyYAML', 'tomli-w', 'pytest', 'pytest-cov', 'mypy', 'build', 'twine'],
    },
    include_package_data=True,
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',  # 对python的最低版本要求
)
