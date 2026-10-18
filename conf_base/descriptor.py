from typing import Any, Callable, Optional, Tuple

from .json_config import JsonConfig
from .Error import WriteError, ConfigTypeError, ConfigValueError

"""
将代码的操作映射为文件的操作
为配置文件中的 section/option 设置更多的方法属性。
"""


class ConfigProperty:

    def __init__(self, section_tuple: Tuple[str, ...], option: str, default: Any,
                 validator: Optional[Callable[[Any], bool]] = None, read_only=False):

        self._config_file: Optional[JsonConfig] = None
        self.section_tuple = section_tuple
        self.section = section_tuple[0]
        self.option = option
        self.default = default
        self.validator = validator
        self.read_only = read_only
        self._proxy: Optional['PropertyProxy'] = None  # 缓存代理对象
        self._callbacks: list = []  # 值变更回调列表

    @property
    def config_file(self) -> JsonConfig:
        """返回所属配置类对应的 JsonConfig 实例（由 ConfigMeta 注入）。"""
        return self._config_file

    def set_section(self, section: str) -> None:
        """切换到另一个 section（用于多 section 共享同一组 option）。"""
        self.section = section
        self._proxy = None  # section 变化后使缓存失效

    def set_value(self, value: Any) -> None:
        """写入配置值。类型必须与默认值一致；validator 存在时校验值是否合法。"""
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

    def on_change(self, callback: Optional[Callable] = None, section: Optional[str] = None) -> Callable:
        """
        注册值变更回调，修改/重置时自动调用，返回 callback 支持装饰器写法。
        回调签名: callback(section, option, value)
          section: 发生变更的 section
          option: 配置项名称
          value: 修改后的新值

        :param callback: 回调函数；不传时返回装饰器（用于 @on_change(section='X') 写法）
        :param section: 指定后仅当该 section 的数据变化时才触发，None 表示监听所有 section
        """
        if section is not None and section not in self.section_tuple:
            raise ValueError(
                f"section '{section}' 不存在，可选值: {list(self.section_tuple)}"
            )

        def register(fn: Callable) -> Callable:
            if not callable(fn):
                raise TypeError('on_change 回调必须是可调用对象')
            self._callbacks.append((fn, section))
            return fn

        if callback is None:
            return register  # 装饰器工厂：@on_change(section='Level2')
        return register(callback)

    def notify_change(self, value: Any, section: Optional[str] = None) -> None:
        """触发所有变更回调（按绑定的 section 过滤）"""
        section = section or self.section
        for callback, section_filter in self._callbacks:
            if section_filter is None or section_filter == section:
                callback(section, self.option, value)

    def __str__(self) -> str:
        return f"<{self.section} {self.option}:{self.default} [{self.section_tuple}]>"

    def __get__(self, obj, obj_type=None):
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

    def __set__(self, obj, value) -> None:
        if isinstance(value, PropertyProxy):
            # 初始化时传入的是 PropertyProxy，取其实际值
            value = value.value
        self.set_value(value)


class PropertyProxy:
    """配置属性的代理对象，提供对配置项的扩展操作"""

    def __init__(self, parent):
        self._parent: 'ConfigProperty' = parent

        self._get_option = parent.config_file.get_option
        self._set_option = parent.config_file.set_option

        self.section = self._parent.section
        self.option = self._parent.option
        self._set_value: Callable = self._parent.set_value
        self._notify_change = self._parent.notify_change

    def __eq__(self, other) -> bool:
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

    def on_change(self, callback: Optional[Callable] = None, section: Optional[str] = None) -> Callable:
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
        return self._get_option(self._parent.section, self._parent.option, self._parent.default)

    @value.setter
    def value(self, value: Any) -> None:
        self._set_value(value=value)

    def set_value(self, value: Any) -> None:
        self._set_value(value=value)

    @property
    def is_default(self) -> bool:
        """当前值是否等于默认值"""
        return self.value == self._parent.default


class BoolProxy(PropertyProxy):
    """bool 类型代理"""

    def toggle(self) -> bool:
        """切换 bool 值并返回新值"""
        new_val = not self.value
        self.set_value(new_val)
        return new_val


class NumberProxy(PropertyProxy):
    """int/float 类型代理"""

    def increment(self, n=1):
        """增减 n，返回新值"""
        new_val = self.value + n
        self.set_value(new_val)
        return new_val


class ListProxy(PropertyProxy):
    """list 类型代理，所有写操作走 set_value 确保校验+落盘"""

    def _mutate(self, fn, *args, **kwargs):
        """读-改-写回：浅拷贝当前值，执行修改，再走 set_value"""
        lst = list(self.value)
        fn(lst, *args, **kwargs)
        self.value = lst

    def append(self, item):
        self._mutate(list.append, item)

    def extend(self, items):
        self._mutate(list.extend, items)

    def insert(self, index, item):
        self._mutate(list.insert, index, item)

    def remove(self, item):
        self._mutate(list.remove, item)

    def pop(self, index=-1):
        lst = list(self.value)
        item = lst.pop(index)
        self.value = lst
        return item

    def clear(self):
        self.value = []

    def sort(self, *, key=None, reverse=False):
        self._mutate(list.sort, key=key, reverse=reverse)

    def reverse(self):
        self._mutate(list.reverse)

    def __getitem__(self, i):
        return self.value[i]

    def __setitem__(self, i, v):
        self._mutate(lambda lst, idx, val: lst.__setitem__(idx, val), i, v)

    def __delitem__(self, i):
        self._mutate(lambda lst, idx: lst.__delitem__(idx), i)

    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, item):
        return item in self.value


class DictProxy(PropertyProxy):
    """dict 类型代理，所有写操作走 set_value 确保校验+落盘"""

    def _mutate(self, fn, *args, **kwargs):
        """读-改-写回：浅拷贝当前值，执行修改，再走 set_value"""
        d = dict(self.value)
        fn(d, *args, **kwargs)
        self.value = d

    def __getitem__(self, k):
        return self.value[k]

    def __setitem__(self, k, v):
        self._mutate(dict.__setitem__, k, v)

    def __delitem__(self, k):
        self._mutate(dict.__delitem__, k)

    def get(self, k, default=None):
        return self.value.get(k, default)

    def pop(self, k, *args):
        d = dict(self.value)
        item = d.pop(k, *args)
        self.value = d
        return item

    def update(self, *args, **kwargs):
        self._mutate(dict.update, *args, **kwargs)

    def setdefault(self, k, default=None):
        if k in self.value:
            return self.value[k]
        self.__setitem__(k, default)
        return default

    def clear(self):
        self.value = {}

    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, k):
        return k in self.value

    def keys(self):
        return self.value.keys()

    def values(self):
        return self.value.values()

    def items(self):
        return self.value.items()
