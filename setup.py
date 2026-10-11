import setuptools  # 导入setuptools打包工具

with open(r"F:\README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="configbase",  # 用自己的名替换其中的YOUR_USERNAME_
    version="0.0.1",  # 包版本号，便于维护版本
    author="加点盐",  # 作者，可以写自己的姓名
    author_email="1431705288@qq.com",  # 作者联系方式，可写自己的邮箱地址
    description="一个简洁的 Python 配置管理框架，支持加密存储、属性描述符、嵌套配置段等功能。",  # 包的简述
    long_description=long_description,  # 包的详细介绍，一般在README.md文件内
    long_description_content_type="text/markdown",
    url="https://gitee.com/kuangjianke/configbase",  # 自己项目地址，比如github的项目地址
    packages=setuptools.find_packages(),
    install_requires=[], # 依赖模块
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.5',  # 对python的最低版本要求
)

# 用setup.py打包项目
# python F:\please_package\setup.py sdist bdist_wheel
# 上传项目
# python -m twine upload dist/* -u 1431705288qq.com -p a13641481495
# 输入账号密码完成上传
# 1431705288qq.com
# a13641481495
# https://upload.pypi.org/legacy/
