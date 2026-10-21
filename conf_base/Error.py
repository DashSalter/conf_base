"""
conf_base 统一异常体系
所有框架异常都继承 ConfBaseError，可用 except ConfBaseError 统一捕获。
同时多重继承内建异常，保持与既有 except TypeError / ValueError 代码兼容。
"""


class ConfBaseError(Exception):
    """conf_base 框架所有异常的基类"""


class WriteError(ConfBaseError):
    """只读配置项被写入"""


class ParseError(ConfBaseError, ValueError):
    """配置文件内容损坏，无法解析"""


class ConfigTypeError(ConfBaseError, TypeError):
    """配置项类型与默认值类型不一致"""


class ConfigValueError(ConfBaseError, ValueError):
    """配置项未通过 validator 校验"""


class DecryptError(ConfBaseError, ValueError):
    """密文解密失败、签名校验失败或配置文件被篡改"""
