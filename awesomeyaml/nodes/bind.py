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

from .dict import ConfigDict
from .function import FunctionNode
from ..namespace import namespace, staticproperty
from ..utils import import_name

from functools import partial


class BindNode(FunctionNode):
    ''' A class implementing ``!bind`` node.

        The bind tag creates a dict node extended with a string.
        The children of the bind node are interpreted as arguments
        to a callable entity identified by the string.

        In most cases, the bind node can be treated like a normal
        dict in which case the string part is "hidden" as it's not
        exposed through a standard dict API.
        However, due to the children nodes being connected to a particular
        value of the string, the merging behaviour of the bind node is
        slightly different. Specifically, if the entity's name changes
        due to merging, bind node discards any existing children.
        Please see the table below for details.

        The children can be identified by either string or int keys.
        In the first case, their values should match names of the function's
        arguments (analogical to standard keyword arguments). In the second
        case, the integers can be used to specify positions of arguments -
        they do not need to be continues as long as overall a valid
        bind (and consecutive call) is formed. If both a positional
        and keyword arguments match the same argument in the function's
        signature, an error is raised.

        When evaluated, the bind node returns a ``functools.partial``
        obtained by binding the arguments kept in its children to the
        entity identified by its string part (following semantics expplained
        briefly above). Specifically, the behaviour could be summarized as::

            f = import_name(bind_node.ayns.func)
            return functools.partial(f, **bind_node)

        Supported syntax::

            !bind:name { args }
            !bind:name [args]    # eq. to: !bind:name { enumerate(args) }
            !bind name           # eq. to: !bind:name {}


        Merge behaviour:

            ==================  ================================================================================================================================
            Case                Behaviour
            ==================  ================================================================================================================================
            ``dict <- Bind``    behaves as ``dict <- !del dict``, unless delete is explicitly set to False
            ``None <- Bind``    ``Bind``
            ``Bind1 <- Bind2``  Update ``Bind1``'s target function with that of ``Bind2``, then update the arguments following the path for ``dict <- Bind``
            ``Bind <- dict``    Update ``Bind``'s arguments without changing target function
            ``Bind <- list``    Update ``Bind``'s arguments (analogical to ``dict <- list``) without changing target function
            ``Bind <- str``     if ``str`` is different than the current target function's name, update the name and remove all children, otherwise no effect
            ==================  ================================================================================================================================

    '''

    @namespace('ayns')
    def on_evaluate_impl(self, path, ctx):
        self.ayns._require_safe(path)
        _func = self._func
        if isinstance(_func, str):
            _func = import_name(_func)
        with ctx.require_all_safe(self, path):
            args = ConfigDict.ayns.on_evaluate_impl(self, path, ctx)
        p, kw_p, kw = FunctionNode._resolve_args(_func, args)
        return partial(_func, *p, **kw_p, **kw)

    @namespace('ayns')
    @property
    def tag(self):
        _func = self._func
        if not isinstance(_func, str):
            _func = self._func.__module__ + '.' + self._func.__name__
        return '!bind:' + _func
