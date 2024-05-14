# Copyright 2024 Samsung Electronics Co., Ltd.
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

from .list import ConfigList
from ..namespace import namespace, staticproperty
from ..builder import Builder
from ..eval_context import EvalContext

import collections.abc as cabc


class RecurseNode(ConfigList):
    ''' Implements ``!rec`` tag.

        The recurse node can be used to include content of another
        config file in any part of the currently parsed file, similar
        to the ``!include`` node but evaluated lazily (e.g., parses 
        the content of a file recursively during evaluation phase).

        The content of the node (string) will be treated as a filename
        of the file which will be included in the place of the node.
        This filename can either be absolute or relative.
        In the later case, a specific file will be looked up in directories
        defined by a builder object which was used to build the config - please
        see :py:meth:`awesomeyaml.Builder.get_lookup_dirs`.
        The standard implementation looks up files with respect to the source file
        of the include node (preferred) or the current working directory.

        Include nodes can also be constructed with a sequence of names.
        In that case, the files are read and merged together in order to
        form the final config object which will be used to replace the include
        node. See examples below.

        Supported syntax::

            !rec [files]    # long form
            !rec file       # short form, eq. to: !rec [file]

        Merge behaviour:

            Equivalent to ``ListNode``.
    '''
    def __init__(self, filenames, *args, **kwargs):
        if not isinstance(filenames, cabc.Sequence) or isinstance(filenames, str):
            filenames = [filenames]
        super().__init__(filenames, *args, **kwargs)

    @namespace('ayns')
    def on_evaluate_impl(self, path, ctx):
        safe_flags = [child.ayns.safe for child in self.ayns.children()]
        value = super().ayns.on_evaluate_impl(path, ctx)
        if not all(isinstance(v, str) for v in value):
            raise ValueError('Not all values evaluate to strings!')

        missing = []
        builder = Builder()
        for safe, filename in zip(safe_flags, value):
            found = False
            for lookup_dir in builder.get_lookup_dirs(self._source_file):
                file = os.path.normpath(os.path.join(lookup_dir, filename))
                try:
                    builder.add_source(file, raw_yaml=False, safe=safe)
                    found = True
                except FileNotFoundError:
                    continue

                if found:
                    break

            if not found:
                missing.append(filename)

        if missing:
            raise FileNotFoundError({ 'missing': missing, 'lookup_dirs': list(builder.get_lookup_dirs(self._source_file)), 'source': self._source_file })

        cfgobj = builder.build()

        enode = ctx._ecfg
        for p in path:
            enode = getattr(enode, p)

        assert isinstance(enode, EvalContext.PartialChild)
        enode.clear()
        enode._cfgobj = cfgobj
        return ctx.evaluate_node(cfgobj, path)

    @namespace('ayns')
    @staticproperty
    @staticmethod
    def tag():
        return '!rec'

    def __eq__(self, other):
        if isinstance(other, RecurseNode):
            return self._source_file == other._source_file and list.__eq__(self, other)
        return False
