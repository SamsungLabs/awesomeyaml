import collections

from ..namespace import NamespaceableMeta, Namespace, staticproperty


class ConfigNodeMeta(NamespaceableMeta):
    def __call__(cls, *args,_force_type=False, _nodes_cache=None, _cache_nodes=True, _force_new=False, _deep_new=False, _copy_guard=False, **kwargs):
        value = None
        has_value = False
        if args:
            value = args[0]
            args = args[1:]
            has_value = True

        if has_value and _cache_nodes and _nodes_cache is not None and id(value) in _nodes_cache:
            return _nodes_cache[id(value)]
        
        t = cls
        if isinstance(value, ConfigNode) and not _copy_guard:
            assert has_value
            if not _force_new:
                return value
            t = type(value)
            value = value.yamlfigns.value
            return t(value, *args, _force_type=True, _nodes_cache=_nodes_cache, _cache_nodes=True, _force_new=_deep_new, _deep_new=_deep_new, _copy_guard=True, **kwargs)

        if cls is ConfigNode and not _force_type:
            # deduce type and call it recursively (this time enforcing it)
            if not has_value:
                raise ValueError('Cannot deduce target type without a positional argument - deduction is always done w.r.t. the first argument')
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
                t = ConfigScalar

            return t(value, *args, _force_type=True, _nodes_cache=_nodes_cache, _cache_nodes=True, _force_new=_force_new, _deep_new=_deep_new, **kwargs)
        
        from .composed import ComposedNode
        if issubclass(cls, ComposedNode):
            kwargs['_nodes_cache'] = _nodes_cache
            kwargs['_cache_nodes'] = _cache_nodes
            kwargs['_force_new'] = _force_new
            kwargs['_deep_new'] = _deep_new

        if has_value:
            ret = super().__call__(value, *args, **kwargs)
        else:
            ret = super().__call__(*args, **kwargs)

        if has_value and _cache_nodes and _nodes_cache is not None:
            _nodes_cache[id(value)] = ret
 
        return ret


class ConfigNode(metaclass=ConfigNodeMeta):
    WEAK = -1
    FORCE = 1

    special_metadata_names = [
        'idx',
        'merge_mode',
        'delete',
        'dependencies',
        'users'
    ]

    def __init__(self, idx=None, merge_mode=0, delete=False, metadata=None):
        if merge_mode not in [0, ConfigNode.WEAK, ConfigNode.FORCE]:
            raise ValueError(f'Unknown merge mode value: {merge_mode}')
        self._idx = idx
        self._merge_mode = merge_mode
        self._delete = delete
        self._metadata = metadata or {}

    def __repr__(self, simple=False):
        return f'<Object {type(self).__name__!r} at 0x{id(self):02x}>'

    class yamlfigns(Namespace):
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

        def has_priority_over(self, other, if_equal=False):
            if self._merge_mode == other._merge_mode:
                return if_equal
            return self._merge_mode > other._merge_mode

        def preprocess(self, builder):
            return self.yamlfigns.on_preprocess([], builder)

        def on_preprocess(self, path, builder):
            return self

        def premerge(self, into=None):
            return self.yamlfigns.on_premerge([], into)

        def on_premerge(self, path, into):
            return self

        def evaluate(self):
            return self.yamlfigns.evaluate_node([], self)
            
        def evaluate_node(self, path, root):
            evaluated = self.yamlfigns.on_evaluate(path, root)
            assert evaluated is not self
            assert not isinstance(evaluated, ConfigNode)
            return evaluated

        def on_evaluate(self, path, root):
            return self.yamlfigns.value

        def copy(self):
            return ConfigNode(self, _force_new=True, _deep_new=False)

        def deepcopy(self):
            return ConfigNode(self, _force_new=True, _deep_new=True)
