import collections

from ..namespace import NamespaceableMeta, Namespace, staticproperty


class ConfigNodeMeta(NamespaceableMeta):
    def __call__(cls, value=None, _force=False, **kwargs):
        t = cls
        if isinstance(value, ConfigNode):
            t = type(value)
            value = value.node_info.value
        elif cls is ConfigNode and not _force:
            from .dict import ConfigDict
            from .list import ConfigList
            from .tuple import ConfigTuple
            from .scalar import ConfigScalar

            if isinstance(value, collections.Sequence) and not isinstance(value, str) and not isinstance(value, bytes):
                if isinstance(value, collections.MutableSequence):
                    t = ConfigList
                else:
                    t = ConfigTuple
            elif isinstance(value, collections.MutableMapping):
                t = ConfigDict
            else:
                return ConfigScalar(value, **kwargs)

        obj = t.__new__(t, value)
        if obj is not None:
            if t is ConfigNode:
                obj.__init__(**kwargs)
            else:
                obj.__init__(value, **kwargs)

        return obj


class ConfigNode(metaclass=ConfigNodeMeta):
    WEAK = 1
    FORCE = 2

    def __init__(self, idx=None, merge_mode=0, delete=True, metadata=None):
        if merge_mode not in [0, ConfigNode.WEAK, ConfigNode.FORCE]:
            raise ValueError(f'Unknown merge mode value: {merge_mode}')
        self._idx = idx
        self._merge_mode = merge_mode
        self._delete = delete
        self._metadata = metadata

    def __repr__(self):
        return f'<Object {type(self).__name__!r} at 0x{id(self):02x}>'

    class node_info(Namespace):
        @property
        def idx(self):
            return self._idx

        @property
        def weak(self):
            return self._merge_mode == ConfigNode.WEAK

        @property
        def force(self):
            return self._merge_mode == ConfigNode.FORCE

        @property
        def delete(self):
            return self._delete

        @property
        def metadata(self):
            return self._metadata

        @staticproperty
        @staticmethod
        def is_leaf():
            return True

        @staticproperty
        @staticmethod
        def is_root():
            return False

        @property
        def value(self):
            return self._get_value()

        @value.setter
        def value(self, value):
            return self._set_value(value)
