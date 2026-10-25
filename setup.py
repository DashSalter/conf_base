import os
import setuptools  # 导入setuptools打包工具

HERE = os.path.dirname(os.path.abspath(__file__))

long_description = ''

with open(os.path.join(HERE, "README.md"), "r", encoding="utf-8") as fh:
    long_description += fh.read()

setuptools.setup(
    name="conf_base",  # 用自己的名替换其中的YOUR_USERNAME_
    version="0.5.0",  # 包版本号，便于维护版本
    author="加点盐",  # 作者，可以写自己的姓名
    author_email="1431705288@qq.com",  # 作者联系方式，可写自己的邮箱地址
    description="Declarative config for Python: JSON/YAML/TOML files, AES-GCM encryption, env override, schema migration. 用类和属性声明配置，零必需依赖。",  # 包的简述
    long_description=long_description,  # 包的详细介绍，一般在README.md文件内
    long_description_content_type="text/markdown",
    url="https://github.com/DashSalter/conf_base",  # 主仓库（PyPI 页面的主页链接）
    keywords="config configuration settings yaml toml json encryption aes-gcm fernet chacha20 declarative dotenv environment-variables schema-migration python",
    project_urls={
        "Homepage": "https://github.com/DashSalter/conf_base",
        "Source (Gitee)": "https://gitee.com/kuangjianke/conf_base",
        "Documentation": "https://gitee.com/kuangjianke/conf_base#readme",
        "Changelog": "https://github.com/DashSalter/conf_base/blob/master/CHANGELOG.md",
        "Issue Tracker": "https://github.com/DashSalter/conf_base/issues",
    },
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
        'docs': ['mkdocs-material>=9.5', 'mkdocstrings[python]>=0.26'],
        'dev': ['filelock', 'cryptography', 'PyYAML', 'tomli-w', 'pytest', 'pytest-cov', 'mypy', 'build', 'twine'],
    },
    include_package_data=True,
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Typing :: Typed",
    ],
    python_requires='>=3.8',  # 对python的最低版本要求
)
