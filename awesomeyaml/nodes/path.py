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

import os
import re
import pathlib

from .list import ConfigList
from .node import ConfigNode
from ..namespace import namespace, staticproperty

from collections.abc import Sequence

_parent_regexp = re.compile(r'parent(\(([0-9]+)\))?')
_abs_regexp = re.compile(r'abs\(([a-zA-Z0-9_/\ -.]+)\)')


class PathNode(ConfigList):
    ''' Implements ``!path`` tag.

        Path nodes can be used as a convenient way of defining
        paths in the underlaying file system.
        Internally, they are treated as list whose elements are
        names of components in the file system. A simple way of
        thinking about a path node is to interpret it as a list
        of arguments to ``os.path.join``.

        > Path nodes evaluate to ``pathlib.Path``.
        > Path nodes do not expand user home directory (i.e., ``~``)
        > Path nodes automatically normalize paths with ``os.path.normpath``

        In addition to holding a list of components, the path node object
        is extended with a single string specifying a *reference point*.
        This reference point defines the initial folder from which
        traversing the of file system begins.
        The end-to-end behaviour of a path node when evaluating can be
        summarized as::

            return pathlib.Path(self.get_reference_point()).joinpath(*self.components)

        Supported syntax::

            !path [names]       # long form, implicit ref. point (see below)
            !path:* [names]     # long form, explicit ref. point (see below for avail. values for *)

            !path name          # short form, eq. to: !path [name]
            !path:* name        # short form, eq. to: !path:* [name],

        Currently the following reference point specifiers are supported :

            ==============  ========================================================================
            Specifier       Value
            ==============  ========================================================================
            *(implicit)*    ``"."`` (default)
            cwd             ``os.getcwd()``
            file            name of the yaml file containing the path node
            parent          parent of the yaml file containing the path node (i.e., its folder)
            parent(n)       the n-th parent of the yaml file (0-based)
            abs(path)       user-defined ``path``
            ==============  ========================================================================


        Merge behaviour:

            The same as for list nodes.

    '''
    def __init__(self, values, ref_point, **kwargs):
        if not isinstance(values, Sequence) or isinstance(values, str) or isinstance(values, bytes):
            if not values:
                values = []
            else:
                values = [values]

        super().__init__(values, **kwargs)

        self.ref_point = ref_point or ''

        self._ref_point_parsed = None
        if self.ref_point not in ['', 'cwd', 'file']:
            parent_match = _parent_regexp.match(self.ref_point)
            abs_match = _abs_regexp.match(self.ref_point)
            assert not parent_match or not abs_match
            if parent_match:
                idx = 0
                if parent_match.group(2):
                    idx = int(parent_match.group(2))
                self._ref_point_parsed = 'parent', idx
            elif abs_match:
                self._ref_point_parsed = 'abs', str(abs_match.group(1))
        else:
            self._ref_point_parsed = self.ref_point, None

        if not self._ref_point_parsed:
            raise ValueError(f'Unknown reference point provided for a PathNode: {ref_point!r}.')

    @namespace('ayns')
    def on_evaluate_impl(self, path, ctx):
        args = super().ayns.on_evaluate_impl(path, ctx)
        ref_point, ref_point_args = self._ref_point_parsed
        if ref_point == '':
            ret = pathlib.Path('.').joinpath(*args)
        elif ref_point == 'cwd':
            ret = pathlib.Path(os.getcwd()).joinpath(*args)
        elif ref_point == 'file':
            if self.ayns.source_file is None:
                raise ValueError('!path node with :file reference requires to know source file of the node, but the node is missing this information')
            ret = pathlib.Path(self.ayns.source_file).joinpath(*args)
        elif ref_point == 'parent':
            if self.ayns.source_file is None:
                raise ValueError('!path node with :parent reference requires to know source file of the node, but the node is missing this information')
            src = pathlib.Path(self.ayns.source_file)
            if ref_point_args >= len(src.parents):
                diff = ref_point_args - len(src.parents) + 1
                ref_point_args = len(src.parents) - 1
                args = ['..'] * diff + args

            ret = src.parents[ref_point_args].joinpath(*args)
        elif ref_point == 'abs':
            ret = pathlib.Path(ref_point_args).joinpath(*args)
        else:
            raise ValueError(f'Unknown reference point: {ref_point!r}')

        ret = pathlib.Path(os.path.normpath(ret))
        return ret


    @namespace('ayns')
    @property
    def tag(self):
        if not self.ref_point:
            return '!path'
        return '!path:' + self.ref_point

    @namespace('ayns')
    @property
    def value(self):
        base = {
            'values': list(super()._get_value()),
            'ref_point': self.ref_point
        }
        if self.ayns.source_file is not None:
            base['source_file'] = self.ayns.source_file
        return base
