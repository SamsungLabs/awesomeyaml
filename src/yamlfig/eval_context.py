from .nodes.node import ConfigNode
from .nodes.composed import ComposedNode
from .namespace import Namespace, NamespaceableMeta


class EvalContext(metaclass=NamespaceableMeta):
    def __init__(self, config_dict):
        self.cfg = config_dict
        self._removed_nodes = {}
        self._eval_cache = {}
        self._done = False

    class yamlfigns(Namespace):
        def get_node(self, *path, **kwargs):
            def access_fn(node, component):
                return node[component]
            def query_fn(node, component):
                try:
                    _ = node[component]
                    return True
                except:
                    return False

            return ComposedNode.yamlfigns._get_node(self.ecfg, access_fn, query_fn, *path, **kwargs)

        def remove_node(self, *path):
            def remove_fn(node, component):
                del node[component]
            
            return ComposedNode.yamlfigns._remove_node(self, remove_fn, *path)

        def named_children(self, allow_duplicates=True):
            memo = set()
            for name, child in self.ecfg.items():
                if not allow_duplicates:
                    if id(child) in memo:
                        continue
                    memo.add(id(child))
                yield name, child

    def evaluate_node(self, cfgobj, prefix=None):
        if not isinstance(cfgobj, ConfigNode):
            return cfgobj

        prefix = ComposedNode.get_list_path(prefix, check_types=False) or []
        def maybe_evaluate(node, name):
            if id(node) in self._eval_cache:
                return self._eval_cache[id(node)]
            path = list(prefix)
            if name:
                path.append(name)
            e = node.yamlfigns.evaluate_node(path, self)
            self._eval_cache[id(node)] = e
            return e

        evaluated_cfgobj = maybe_evaluate(cfgobj, '')
        if not cfgobj.yamlfigns.is_leaf:
            for name, child in cfgobj.yamlfigns.named_children():
                child_path = prefix + [name]
                evaluated_child = self.evaluate_node(child, prefix=child_path)
                evaluated_cfgobj[name] = evaluated_child

        return evaluated_cfgobj

    def evaluate(self):
        self._eval_cache.clear()
        self.ecfg = self.cfg.yamlfigns.evaluate_node([], self)
        self._eval_cache[id(self.cfg)] = self.ecfg
        return self.evaluate_node(self.cfg)
