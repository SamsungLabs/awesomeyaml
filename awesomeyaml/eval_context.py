# Copyright 2022 Samsung Electronics Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .nodes.node import ConfigNode
from .nodes.composed import ComposedNode, NodePath
from .namespace import Namespace, NamespaceableMeta
from .utils import Bunch

import copy


class EvalContext(metaclass=NamespaceableMeta):
    ''' A class used to provide evaluation context for a top-level `awesomeyaml.nodes.ConfigDict`.
        After the top level node is put within a context, it can be evaluated to create `awesomeyaml.utils.Bunch`
        which will hold the evaluation result - evaluated nodes are no longer `awesomeyaml` nodes and can represent anything.
        The primary use-case for this class and the resulting `Bunch` object is to construct a `awesomeyaml.Config` object
        which basically combines the returned `Bunch` object with the original `ConfigDict`.
    '''

    class PartialChild(Bunch):
        def __init__(self, path, eval_ctx):
            self._path = path
            self._eval_ctx = eval_ctx
            super().__init__({})

        def __getitem__(self, key):
            if key not in self:
                return self._eval_ctx.cfg.ayns.get_node(self._path + [key])

            return super().__getitem__(key)

        def __getattr__(self, name):
            #if name not in self:
            #    raise AttributeError(f'Object {type(self).__name__!r} does not have attribute {name!r}')
            return self[name]

        def __setattr__(self, name, value):
            if name.startswith('_'):
                return super().__setattr__(name, value)

            if name in self.__dict__:
                raise ValueError('Name conflict!')

            self[name] = value

        def __delattr__(self, name):
            try:
                super().__delattr__(name)
            except AttributeError:
                del self[name]

    _default_eval_symbols = {}

    def __init__(self, config_dict, eval_symbols=None):
        ''' Arguments:
                config_dict : a `awesomeyaml.nodes.ConfigDict` object to be evaluated,
                    to construct a single `ConfigDict` from multiple sources
                    `awesomeyaml.builder.Builder` can be used.
                eval_symbols : a dict containing symbols which can be used when evaluating
                    ``config_dict``. The values from this argument will be used to update
                    the defaults from :py:meth:`get_default_eval_symbols`.
        '''
        self.cfg = config_dict
        self._removed_nodes = {}
        self._eval_cache = {}
        self._eval_paths = set()
        self._done = False
        self._eval_symbols = copy.copy(EvalContext._default_eval_symbols)
        if eval_symbols:
            self._eval_symbols.update(eval_symbols)

    class ayns(Namespace):
        def get_node(self, *path, **kwargs):
            def access_fn(node, component):
                return node[component]
            def query_fn(node, component):
                try:
                    _ = node[component]
                    return True
                except:
                    return False

            incomplete = kwargs.get('incomplete', False)
            kwargs['incomplete'] = False
            try:
                return ComposedNode.ayns._get_node(self.ecfg, access_fn, query_fn, *path, **kwargs)
            except KeyError:
                kwargs['incomplete'] = incomplete
                return self.cfg.ayns.get_node(*path, **kwargs)

        def remove_node(self, *path):
            def remove_fn(node, component):
                if isinstance(node, ComposedNode):
                    return node.ayns.remove_child(component)
                else:
                    node = node[component]
                    del node[component]
                    return node

            return ComposedNode.ayns._remove_node(self, remove_fn, *path)

        def named_children(self, allow_duplicates=True):
            memo = set()
            for name, child in self.ecfg.items():
                if not allow_duplicates:
                    if id(child) in memo:
                        continue
                    memo.add(id(child))
                yield name, child
            for name, child in self.cfg.ayns.named_children():
                if name not in self.ecfg:
                    yield name, child

    def get_evaluated_node(self, nodepath):
        nodepath = ComposedNode.get_list_path(nodepath, check_types=False) or NodePath()
        node = self.ayns.get_node(nodepath)
        if str(nodepath) in self._eval_paths:
            return node

        return self.evaluate_node(node, prefix=nodepath)

    def evaluate_node(self, cfgobj, prefix=None):
        if not isinstance(cfgobj, ConfigNode):
            return cfgobj

        prefix = ComposedNode.get_list_path(prefix, check_types=False) or NodePath()
        if str(prefix) in self._eval_paths:
            assert id(cfgobj) in self._eval_cache
            return self._eval_cache[id(cfgobj)]

        def maybe_evaluate(node):
            if id(node) in self._eval_cache:
                return self._eval_cache[id(node)]
            e = node.ayns.evaluate_node(prefix, self)
            self._eval_cache[id(node)] = e
            return e

        evaluated_parent = None
        if prefix:
            evaluated_parent = self.ayns.get_node(prefix[:-1])
            if isinstance(evaluated_parent, ConfigNode):
                evaluated_parent = self.evaluate_node(evaluated_parent, prefix=prefix[:-1])

            evaluated_parent[prefix[-1]] = EvalContext.PartialChild(prefix, self)

        evaluated_cfgobj = maybe_evaluate(cfgobj)
        if evaluated_parent is not None:
            evaluated_parent[prefix[-1]] = evaluated_cfgobj

        self._eval_paths.add(str(prefix))
        return evaluated_cfgobj

    def evaluate(self):
        ''' Returns:
                `awesomeyaml.utils.Bunch` representing evaluated config node.
        '''
        self._eval_cache.clear()
        self._eval_paths.clear()
        self.ecfg = {}
        return self.evaluate_node(self.cfg)

    @staticmethod
    def set_default_eval_symbols(symbols):
        ''' Sets the default symbols available to use when evaluating nodes.

            The symbols provided can be used by certain node types on evaluation.
            The defaults can be updated with values passed to the :py:meth:`__init__`
            method.

            Arguments:
                symbols : a lookup table (dict) of available symbols - for exampe, can be provided by
                    calling ``globals()`` in a module whose content one wishes to be available
                    during evaluation.

            Raises:
                TypeError: if ``symbols`` is not a dict.
        '''
        if not isinstance(symbols, dict):
            raise TypeError('dict expected')
        EvalContext._default_eval_symbols = symbols

    @staticmethod
    def get_default_eval_symbols():
        ''' Returns a dict with the default symbols available to use when evaluating nodes.

            The symbols provided can be used by certain node types on evaluation.
            The defaults can be updated with values passed to the :py:meth:`__init__`
            method.

            Returns:
                dict: symbols available by default
        '''
        return EvalContext._default_eval_symbols

    def get_eval_symbols(self):
        ''' Returns a dict with symbols available when evaluating nodes within this :py:class:`EvalContext`.

            Some node types might use this to evaluate their values.

            The returned value considers both the default symbols (see :py:meth:`set_default_eval_symbols`) and
            non-default ones passed to :py:meth:`__init__`.

            Returns:
                dict: symbols available in this evaluation context
        '''
        return self._eval_symbols
