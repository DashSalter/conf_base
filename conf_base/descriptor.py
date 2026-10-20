import json
import os
from typing import (
    Any, Callable, Dict, ItemsView, Iterator, KeysView, List, Optional,
    Tuple, Type, TypeVar, Union, ValuesView, cast, overload,
)

from .json_config import JsonConfig
from .Error import WriteError, ConfigTypeError, ConfigValueError

"""
将代码的操作映射为文件的操作
为配置文件中的 section/option 设置更多的方法属性。
"""

# 回调签名：callback(section, option, value)
Callback = Callable[[str, str, Any], None]
# 配置项默认值的类型（int 或 float）
Number = Union[int, float]


def _convert_env_value(raw: str, target_type: Type[Any]) -> Any:
    """
    把环境变量的字符串值解析为目标 Python 类型。
    - bool: 'true'/'1' → True, 'false'/'0' → False（大小写不敏感）
    - int/float: 直接转换
    - list/dict: JSON 解析（格式如 '[1,2,3]' 或 '{"a":1}'）
    - str: 原值返回
    """
    if target_type is bool:
        low = raw.strip().lower()
        if low in ('true', '1', 'yes', 'on'):
            return True
        if low in ('false', '0', 'no', 'off'):
            return False
        raise ValueError(f"环境变量值 '{raw}' 无法解析为 bool，合法值: true/false/1/0/yes/no")
    if target_type is int:
        return int(raw.strip())
    if target_type is float:
        return float(raw.strip())
    if target_type is list or target_type is dict:
        return json.loads(raw)
    if target_type is str:
        return raw
    if target_type is type(None):
        raise ValueError('默认值为 None，无法推断环境变量应解析为何种类型')
    # 其他类型尝试直接构造
    return target_type(raw)


class ConfigProperty:
    """配置项描述符。每个配置项对应一个 Section 下的一个 option。"""

    def __init__(self, section_tuple: Tuple[str, ...], option: str, default: Any,
                 validator: Optional[Callable[[Any], bool]] = None,
                 read_only: bool = False,
                 env_key: Optional[str] = None) -> None:
        self._config_file: Optional[JsonConfig] = None
        self.section_tuple: Tuple[str, ...] = section_tuple
        self.section: str = section_tuple[0]
        self.option: str = option
        self.default: Any = default
        self.validator: Optional[Callable[[Any], bool]] = validator
        self.read_only: bool = read_only
        self.env_key: Optional[str] = env_key
        self._proxy: Optional['PropertyProxy'] = None
        self._callbacks: List[Tuple[Callback, Optional[str]]] = []

    @property
    def config_file(self) -> JsonConfig:
        assert self._config_file is not None
        return self._config_file

    @property
    def has_env_override(self) -> bool:
        """当前值是否由环境变量覆盖（env_key 存在且 os.environ 中有值）。"""
        return self.env_key is not None and self.env_key in os.environ

    def get_from_env(self) -> Any:
        """从环境变量读取并解析值。未设置时返回 None；解析失败抛 ConfigValueError。

        注：这里无法用 ``Optional[Any]`` 表达“可能没有值”，因为 ``Optional[Any]``
        等价于 ``Any``，对类型检查器没有任何约束作用，故直接用 ``Any``。
        """
        if self.env_key is None or self.env_key not in os.environ:
            return None
        raw = os.environ[self.env_key]
        try:
            return _convert_env_value(raw, type(self.default))
        except (ValueError, json.JSONDecodeError) as e:
            raise ConfigValueError(
                f"环境变量 {self.env_key} 的值 '{raw}' "
                f"无法解析为 {type(self.default).__name__}: {e}"
            ) from e

    def set_section(self, section: str) -> None:
        """切换到另一个 section（用于多 section 共享同一组 option）。"""
        self.section = section
        self._proxy = None

    def set_value(self, value: Any) -> None:
        """写入配置值。环境变量覆盖时禁止回写；类型必须与默认值一致；validator 存在时校验值是否合法。"""
        if self.has_env_override:
            raise WriteError(
                f'{self.section}.{self.option} 由环境变量 {self.env_key} 覆盖，'
                f'禁止回写配置文件。请移除环境变量后再修改。'
            )
        if self.read_only:
            raise WriteError(f'{self.section}.{self.option} is read only.')
        if type(value) is not type(self.default):
            raise ConfigTypeError(
                f"{self.section}.{self.option} 配置项期望类型 "
                f"{type(self.default).__name__} 实际为 {type(value).__name__}"
            )
        if self.validator is not None and not self.validator(value):
            raise ConfigValueError(
                f"{self.section}.{self.option} 配置项校验失败，"
                f"值 {value!r} 未通过 validator 校验"
            )
        self.config_file.set_option(self.section, self.option, value)
        self.notify_change(value)

    def on_change(self, callback: Optional[Callback] = None,
                  section: Optional[str] = None) -> Any:
        """
        注册值变更回调，修改/重置时自动调用。
        回调签名: callback(section, option, value)
        支持装饰器和普通调用两种写法。
        """
        if section is not None and section not in self.section_tuple:
            raise ValueError(
                f"section '{section}' 不存在，可选值: {list(self.section_tuple)}"
            )

        def register(fn: Callback) -> Callback:
            if not callable(fn):
                raise TypeError('on_change 回调必须是可调用对象')
            self._callbacks.append((fn, section))
            return fn

        if callback is None:
            return register
        return register(callback)

    def notify_change(self, value: Any, section: Optional[str] = None) -> None:
        """触发所有变更回调。section 为实际写入的 section 名。"""
        sec = section or self.section
        for callback, section_filter in self._callbacks:
            if section_filter is None or section_filter == sec:
                callback(sec, self.option, value)

    def __str__(self) -> str:
        env = f' env={self.env_key}' if self.env_key else ''
        return f"<{self.section} {self.option}:{self.default} [{self.section_tuple}]{env}>"

    def __get__(self, obj: Any, obj_type: Optional[Type[Any]] = None) -> 'PropertyProxy':
        if self._proxy is None:
            t = type(self.default)
            if t is bool:
                self._proxy = BoolProxy(self)
            elif t is int or t is float:
                self._proxy = NumberProxy(self)
            elif t is list:
                self._proxy = ListProxy(self)
            elif t is dict:
                self._proxy = DictProxy(self)
            else:
                self._proxy = PropertyProxy(self)
        return self._proxy

    def __set__(self, obj: Any, value: Any) -> None:
        if isinstance(value, PropertyProxy):
            value = value.value
        self.set_value(value)


class PropertyProxy:
    """配置属性的代理对象，提供对配置项的扩展操作"""

    def __init__(self, parent: ConfigProperty) -> None:
        self._parent: ConfigProperty = parent
        self._get_option = parent.config_file.get_option
        self._set_option = parent.config_file.set_option
        self.section: str = self._parent.section
        self.option: str = self._parent.option
        self._set_value = self._parent.set_value
        self._notify_change = self._parent.notify_change
        self._get_from_env = self._parent.get_from_env

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PropertyProxy):
            return NotImplemented
        return (self._parent.section == other._parent.section
                and self._parent.option == other._parent.option)

    def __str__(self) -> str:
        return f"<class '{self._parent.section}:{self._parent.option}'>"

    def reset(self) -> Any:
        """重置属性值为默认值，并返回默认值。"""
        self._set_option(self._parent.section, self._parent.option, self._parent.default)
        self._notify_change(self._parent.default)
        return self._parent.default

    def on_change(self, callback: Optional[Callback] = None,
                  section: Optional[str] = None) -> Any:
        """注册值变更回调：callback(section, option, value)，详见 ConfigProperty.on_change"""
        return self._parent.on_change(callback, section=section)

    @property
    def default(self) -> Any:
        return self._parent.default

    @default.setter
    def default(self, value: Any) -> None:
        raise ValueError("default is readonly")

    @property
    def value(self) -> Any:
        # 优先级：环境变量 > 配置文件 > 默认值
        env_val = self._get_from_env()
        if env_val is not None:
            return env_val
        return self._get_option(self._parent.section, self._parent.option, self._parent.default)

    @value.setter
    def value(self, value: Any) -> None:
        self.set_value(value=value)

    def set_value(self, value: Any) -> None:
        """设置数据"""
        self._set_value(value)

    @property
    def is_default(self) -> bool:
        """当前值是否等于默认值"""
        return bool(self.value == self._parent.default)

    @property
    def has_env_override(self) -> bool:
        """当前值是否由环境变量覆盖"""
        return self._parent.has_env_override

    @property
    def env_key(self) -> Optional[str]:
        """环境变量名（None 表示未配置）"""
        return self._parent.env_key


class BoolProxy(PropertyProxy):
    """bool 类型代理"""

    def toggle(self) -> bool:
        """切换 bool 值并返回新值"""
        new_val = not self.value
        self.set_value(new_val)
        return new_val


class NumberProxy(PropertyProxy):
    """int/float 类型代理"""

    def increment(self, n: Number = 1) -> Number:
        """增减 n，返回新值。写入时仍会执行类型校验，int 配置加浮点数会被拒绝。"""
        new_val = self.value + n
        self.set_value(new_val)
        return cast(Number, new_val)


_T = TypeVar('_T')


class ListProxy(PropertyProxy):
    """list 类型代理，所有写操作走 set_value 确保校验+落盘"""

    def _mutate(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """读-改-写回：浅拷贝当前值，执行修改，再走 set_value"""
        lst = list(self.value)
        fn(lst, *args, **kwargs)
        self.value = lst

    def append(self, item: Any) -> None:
        self._mutate(list.append, item)

    def extend(self, items: Any) -> None:
        self._mutate(list.extend, items)

    def insert(self, index: int, item: Any) -> None:
        self._mutate(list.insert, index, item)

    def remove(self, item: Any) -> None:
        self._mutate(list.remove, item)

    def pop(self, index: int = -1) -> Any:
        lst = list(self.value)
        item = lst.pop(index)
        self.value = lst
        return item

    def clear(self) -> None:
        self.value = []

    def sort(self, *, key: Optional[Callable[[Any], Any]] = None, reverse: bool = False) -> None:
        self._mutate(list.sort, key=key, reverse=reverse)

    def reverse(self) -> None:
        self._mutate(list.reverse)

    @overload
    def __getitem__(self, i: int) -> Any: ...

    @overload
    def __getitem__(self, i: slice) -> List[Any]: ...

    def __getitem__(self, i: Union[int, slice]) -> Any:
        return self.value[i]

    def __setitem__(self, i: Union[int, slice], v: Any) -> None:
        self._mutate(lambda lst, idx, val: lst.__setitem__(idx, val), i, v)

    def __delitem__(self, i: Union[int, slice]) -> None:
        self._mutate(lambda lst, idx: lst.__delitem__(idx), i)

    def __len__(self) -> int:
        return len(self.value)

    def __iter__(self) -> Iterator[Any]:
        return iter(self.value)

    def __contains__(self, item: Any) -> bool:
        return item in self.value


class DictProxy(PropertyProxy):
    """dict 类型代理，所有写操作走 set_value 确保校验+落盘"""

    def _mutate(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """读-改-写回：浅拷贝当前值，执行修改，再走 set_value"""
        d = dict(self.value)
        fn(d, *args, **kwargs)
        self.value = d

    def __getitem__(self, k: Any) -> Any:
        return self.value[k]

    def __setitem__(self, k: Any, v: Any) -> None:
        self._mutate(dict.__setitem__, k, v)

    def __delitem__(self, k: Any) -> None:
        self._mutate(dict.__delitem__, k)

    def get(self, k: Any, default: Any = None) -> Any:
        return self.value.get(k, default)

    def pop(self, k: Any, *args: Any) -> Any:
        d = dict(self.value)
        item = d.pop(k, *args)
        self.value = d
        return item

    def update(self, *args: Any, **kwargs: Any) -> None:
        self._mutate(dict.update, *args, **kwargs)

    def setdefault(self, k: Any, default: Any = None) -> Any:
        if k in self.value:
            return self.value[k]
        self.__setitem__(k, default)
        return default

    def clear(self) -> None:
        self.value = {}

    def __len__(self) -> int:
        return len(self.value)

    def __iter__(self) -> Iterator[Any]:
        return iter(self.value)

    def __contains__(self, k: Any) -> bool:
        return k in self.value

    def keys(self) -> KeysView[Any]:
        return cast(KeysView[Any], self.value.keys())

    def values(self) -> ValuesView[Any]:
        return cast(ValuesView[Any], self.value.values())

    def items(self) -> ItemsView[Any, Any]:
        return cast(ItemsView[Any, Any], self.value.items())
