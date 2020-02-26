from .dict import ConfigDict
from ..namespace import namespace
from ..utils import import_name


class BindNode(ConfigDict):
    def __init__(self, func, args, **kwargs):
        self._func = func
        kwargs.setdefault('delete', True)
        super().__init__(args, **kwargs)

    def __call__(self, *args, **kwargs):
        kwargs = { **self, **kwargs }
        return self._func(*args, **kwargs)

    def __bool__(self):
        return bool(self._func)

    @namespace('yamlfigns')
    def merge(self, other):
        if isinstance(other, str):
            self._func = other
            self.clear()
            return self

        try:
            self._func = other._func
        except AttributeError:
            pass

        return super().yamlfigns.merge(other)

    @namespace('yamlfigns')
    def on_evaluate(self, path, root):
        self._func = import_name(self._func)
        return self

    @namespace('yamlfigns')
    @property
    def func(self):
        return self._func
