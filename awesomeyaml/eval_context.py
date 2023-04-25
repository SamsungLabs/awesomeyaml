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
from .nodes.node_path import NodePath
from .namespace import NamespaceableMeta
from .utils import Bunch
from . import errors
from . import utils

import copy
import contextlib


class EvalContext(metaclass=NamespaceableMeta):
    ''' A class used to provide evaluation context for a top-level `awesomeyaml.nodes.ConfigDict`.
        After the top level node is put within a context, it can be evaluated to create `awesomeyaml.utils.Bunch`
        which will hold the evaluation result - evaluated nodes are no longer `awesomeyaml` nodes and can represent anything.
        The primary use-case for this class and the resulting `Bunch` object is to construct a `awesomeyaml.Config` object
        which basically combines the returned `Bunch` object with the original `ConfigDict`.
    '''

    class PartialChild(Bunch):
        def __init__(self, path, eval_ctx, cfgobj):
            self._path = path
            self._eval_ctx = eval_ctx
            self._cfgobj = cfgobj
            super().__init__({})

        def __getitem__(self, key):
            if key not in self:
                node = self._cfgobj[key]
                return self._eval_ctx.evaluate_node(node, self._path + [key])

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

        def get_or_set(self, key):
            return self.setdefault(key, EvalContext.PartialChild(self._path + [key], self._eval_ctx, self._cfgobj[key]))

    _default_eval_symbols = {}

    def __init__(self, eval_symbols=None):
        ''' Arguments:
                eval_symbols : a dict containing symbols which can be used when evaluating
                    ``config_dict``. The values from this argument will be used to update
                    the defaults from :py:meth:`get_default_eval_symbols`.
        '''
        self._cfg = None
        self._ecfg = None
        self._removed_nodes = {}
        self._eval_cache = {}
        self._eval_cache_id = {}
        self._eval_symbols = copy.copy(EvalContext._default_eval_symbols)
        if eval_symbols:
            self._eval_symbols.update(eval_symbols)

        self._require_all_safe = False
        self._eval_stack = []

        self.user_data = None

    @property
    def cfg(self):
        if self._cfg is None:
            raise ValueError('Missing _cfg attribute - method called outside the call to .evaluate(config_dict)?')

        return self._cfg

    @property
    def ecfg(self):
        if self._ecfg is None:
            raise ValueError('Missing _ecfg attribute - method called outside the call to .evaluate(config_dict)?')

        return self._ecfg

    @contextlib.contextmanager
    def require_all_safe(self, node, path):
        old, self._require_all_safe = self._require_all_safe, True
        sp = len(self._eval_stack)-1
        try:
            yield
        except errors.UnsafeError as e:
            raise errors.EvalError(f'The node requires all dependencies to be safe but the above error was raised indicating at least one !unsafe node was attempted to be executed while following the chain of dependencies: {self._eval_stack[sp:]}', node, path) from e
        finally:
            self._require_all_safe = old

    def get_node(self, *path, **kwargs):
        path = NodePath.get_list_path(*path)
        if str(path) in self._eval_cache:
            return self._eval_cache[str(path)]
        return self.cfg.ayns.get_node(path, **kwargs)

    def get_evaluated_node(self, nodepath):
        nodepath = NodePath.get_list_path(nodepath, check_types=False) or NodePath()
        node = self.ayns.get_node(nodepath)
        if str(nodepath) in self._eval_cache:
            return node

        return self.evaluate_node(node, prefix=nodepath)

    @errors.api_entry
    def evaluate_node(self, cfgobj, prefix=None):
        if not isinstance(cfgobj, ConfigNode):
            return cfgobj

        self._eval_stack.append(prefix)
        prefix = NodePath.get_list_path(prefix, check_types=False) or NodePath()

        if self._require_all_safe:
            if not cfgobj.ayns.safe:
                raise errors.UnsafeError(f'Note: the current context requires all evaluated nodes to be safe - see chained exceptions for more information', cfgobj, str(prefix))

        if id(cfgobj) in self._eval_cache_id:
            return self._eval_cache_id[id(cfgobj)]

        evaluated_parent = None
        if prefix:
            enode = self.ecfg
            for p in prefix[:-1]:
                assert isinstance(enode, EvalContext.PartialChild)
                enode = enode.get_or_set(p)

            evaluated_parent = enode

        evaluated_cfgobj = cfgobj.ayns.on_evaluate(prefix, self)
        if evaluated_parent is not None:
            evaluated_parent[prefix[-1]] = evaluated_cfgobj

        self._eval_cache[str(prefix)] = evaluated_cfgobj
        self._eval_cache_id[utils.persistent_id(cfgobj)] = evaluated_cfgobj
        self._eval_stack.pop()
        return evaluated_cfgobj

    @errors.api_entry
    def evaluate(self, config_dict):
        ''' Arguments:
                config_dict : a `awesomeyaml.nodes.ConfigDict` object to be evaluated,
                            to construct a single `ConfigDict` from multiple sources
                            `awesomeyaml.builder.Builder` can be used.
            Returns:
                `awesomeyaml.utils.Bunch` representing evaluated config node.
        '''
        self._cfg = config_dict
        self._ecfg = EvalContext.PartialChild(NodePath(), self, self._cfg)
        self._eval_cache.clear()
        self._eval_cache_id.clear()
        self.user_data = Bunch()

        try:
            ret = self.evaluate_node(self.cfg)
        finally:
            self._eval_cache.clear()
            self._eval_cache_id.clear()
            self._cfg = None
            self._ecfg = None

        return ret

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
