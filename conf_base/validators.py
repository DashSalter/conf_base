"""常用 ``validator`` 工厂函数。

每个工厂都返回 ``Callable[[Any], bool]``，可直接传给
``field(validator=...)``：

    >>> from conf_base import ConfigBase, Section
    >>> from conf_base.validators import in_range, is_url
    >>> class C(ConfigBase):
    ...     s = Section('S')
    ...     port = s.field(default=8080, validator=in_range(1, 65535))
    ...     home = s.field(default='https://example.com', validator=is_url())

校验函数只负责判断「值是否合法」，不做类型转换；类型仍由 ``default``
决定。返回 ``False`` 时框架抛出 :class:`~conf_base.error.ConfigValueError`，
消息里带 ``section.option`` 与实际值；若校验函数自身抛异常，异常会被包装成
``ConfigValueError`` 并保留原始异常链。
"""
import os
import re
from typing import Any, Callable, Iterable, Optional, Pattern, Tuple, Union
from urllib.parse import urlsplit

__all__ = [
    'in_range',
    'one_of',
    'matches',
    'is_url',
    'is_path',
    'length',
]

_Number = Union[int, float]


def _is_number(value: Any) -> bool:
    """bool 是 int 的子类，但配置里的 True/False 不应被当成数字。"""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def in_range(minimum: Optional[_Number] = None,
             maximum: Optional[_Number] = None,
             *,
             inclusive: bool = True) -> Callable[[Any], bool]:
    """数值范围校验：``minimum <= value <= maximum``。

    :param minimum: 下界；省略表示不限制
    :param maximum: 上界；省略表示不限制
    :param inclusive: 是否包含端点，``False`` 时改为开区间
    :raises ValueError: 上下界都省略
    :raises TypeError: 边界不是数字

    >>> in_range(1, 10)(10)
    True
    >>> in_range(1, 10, inclusive=False)(10)
    False
    """
    if minimum is None and maximum is None:
        raise ValueError('in_range 至少需要 minimum 或 maximum 之一')
    for name, bound in (('minimum', minimum), ('maximum', maximum)):
        if bound is not None and not _is_number(bound):
            raise TypeError(f'in_range 的 {name} 必须是数字')

    def check(value: Any) -> bool:
        if not _is_number(value):
            return False
        assert minimum is not None or maximum is not None
        if minimum is not None:
            if value < minimum or (not inclusive and value == minimum):
                return False
        if maximum is not None:
            if value > maximum or (not inclusive and value == maximum):
                return False
        return True

    return check


def one_of(*choices: Any, ignore_case: bool = False) -> Callable[[Any], bool]:
    """枚举校验：值必须等于给定的候选之一。

    :param choices: 允许的取值，至少一个
    :param ignore_case: 为 ``True`` 时字符串按大小写不敏感比较
    :raises ValueError: 没有传入候选值

    >>> one_of('debug', 'info')('info')
    True
    >>> one_of('debug', 'info')('INFO')
    False
    >>> one_of('debug', 'info', ignore_case=True)('INFO')
    True
    """
    if not choices:
        raise ValueError('one_of 至少需要一个候选值')
    if not ignore_case:
        allowed = tuple(choices)
        has_bool = any(isinstance(choice, bool) for choice in choices)

        def check_exact(value: Any) -> bool:
            # True == 1，避免布尔值被当成数字命中
            if isinstance(value, bool) and not has_bool:
                return False
            return value in allowed

        return check_exact

    lowered = {str(choice).lower() for choice in choices}

    def check_ignore_case(value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return value.lower() in lowered

    return check_ignore_case


def matches(pattern: Union[str, Pattern[str]], flags: int = 0) -> Callable[[Any], bool]:
    """正则校验：整个字符串必须匹配 ``pattern``（等价于 ``re.fullmatch``）。

    想只要求「包含」时，把 pattern 写成 ``r'.*关键字.*'``。

    :param pattern: 正则字符串或已编译的 pattern 对象
    :param flags: 传给 :func:`re.compile` 的标志，仅当 pattern 是字符串时生效
    :raises TypeError: pattern 既不是字符串也没有 ``fullmatch`` 方法

    >>> matches(r'\\d{3}-\\d{4}')('555-1234')
    True
    >>> matches(r'\\d{3}-\\d{4}')('tel:555-1234')
    False
    """
    if isinstance(pattern, str):
        compiled: Pattern[str] = re.compile(pattern, flags)
    elif hasattr(pattern, 'fullmatch'):
        compiled = pattern
    else:
        raise TypeError('matches 需要字符串正则或已编译的 pattern 对象')

    def check(value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return compiled.fullmatch(value) is not None

    return check


def is_url(*, schemes: Iterable[str] = ('http', 'https'),
           require_host: bool = True) -> Callable[[Any], bool]:
    """URL 校验：协议在 ``schemes`` 内，且主机部分非空。

    只做结构检查，不发起网络请求，也不校验域名是否真实存在。

    :param schemes: 允许的协议名（不区分大小写）
    :param require_host: 是否要求主机部分非空（``http:///path`` 视为非法）

    >>> is_url()('https://example.com/x?y=1')
    True
    >>> is_url()('example.com')
    False
    >>> is_url(schemes=('ftp',))('ftp://example.com')
    True
    """
    allowed: Tuple[str, ...] = tuple(str(s).lower() for s in schemes)
    if not allowed:
        raise ValueError('is_url 至少需要一个协议名')

    def check(value: Any) -> bool:
        if not isinstance(value, str) or not value:
            return False
        try:
            parts = urlsplit(value)
        except ValueError:
            return False
        if parts.scheme.lower() not in allowed:
            return False
        if require_host and not parts.netloc:
            return False
        return True

    return check


def is_path(*, must_exist: bool = False,
            kind: Optional[str] = None) -> Callable[[Any], bool]:
    """路径校验：非空字符串，可选要求文件已存在、以及是文件还是目录。

    :param must_exist: 为 ``True`` 时要求路径在磁盘上存在
    :param kind: ``'file'`` / ``'dir'`` / ``None``，用于进一步限制类型
    :raises ValueError: kind 不是 ``'file'`` / ``'dir'`` / ``None``

    >>> is_path()('C:/data/app.json')
    True
    >>> is_path()('')
    False
    """
    if kind not in (None, 'file', 'dir'):
        raise ValueError("is_path 的 kind 只能是 None、'file' 或 'dir'")

    def check(value: Any) -> bool:
        if not isinstance(value, str) or not value:
            return False
        if must_exist and not os.path.exists(value):
            return False
        if kind == 'file' and not os.path.isfile(value):
            return False
        if kind == 'dir' and not os.path.isdir(value):
            return False
        return True

    return check


def length(minimum: Optional[int] = None,
           maximum: Optional[int] = None) -> Callable[[Any], bool]:
    """长度校验：``str`` / ``list`` / ``dict`` / ``tuple`` 的元素个数在范围内。

    :param minimum: 最小长度；省略表示不限制
    :param maximum: 最大长度；省略表示不限制
    :raises ValueError: 上下界都省略，或边界为负数

    >>> length(1, 3)('abc')
    True
    >>> length(1, 3)('abcd')
    False
    >>> length(2)([1, 2, 3])
    True
    """
    if minimum is None and maximum is None:
        raise ValueError('length 至少需要 minimum 或 maximum 之一')
    for name, bound in (('minimum', minimum), ('maximum', maximum)):
        if bound is not None and (not isinstance(bound, int) or bound < 0):
            raise ValueError(f'length 的 {name} 必须是非负整数')
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError('length 的 minimum 不能大于 maximum')

    def check(value: Any) -> bool:
        try:
            size = len(value)
        except TypeError:
            return False
        if minimum is not None and size < minimum:
            return False
        if maximum is not None and size > maximum:
            return False
        return True

    return check
