import threading

"""单例元类"""


class SingletonMeta(type):
    _singleton_lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        instance = getattr(cls, '_instance', None)
        if instance is not None:
            return instance
        with cls._singleton_lock:
            instance = getattr(cls, '_instance', None)
            if instance is None:
                instance = super().__call__(*args, **kwargs)
                cls._instance = instance
            return instance
