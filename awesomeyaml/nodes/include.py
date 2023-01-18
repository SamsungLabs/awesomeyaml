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

from .node import ConfigNode
from ..namespace import namespace, staticproperty

import os
import collections.abc as cabc


class IncludeNode(ConfigNode):
    ''' Implements ``!include`` tag.

        The include node can be used to include content of another
        config file in any part of the currently parsed file.

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

            !include [files]    # long form
            !include file       # short form, eq. to: !include [file]

        Merge behaviour:

            Include nodes are somewhat special because their lifespan is very short.
            In fact, the standard behaviour is to process them even before merging
            is performed (since they define content which will be merged) during a stage
            called "preprocessing".
            Preprocessing is very similar to evaluating in a sense that it also allows
            a node to change itself. The main difference is the fact that during preprocessing
            a node is not given access to other nodes and therefore should be self-contained.
            Because of this short lifespan, include nodes don't have explicitly defined
            merging behaviour. However, should one try to merge a config tree with unprocessed
            include node, it would behave following the most common merging behaviour.

        Examples:
            The following snippets are equivalent.
            Python only::

                cfg = awesomeyaml.Config.build('file1', 'file2', 'file3')

            Aggregated in a single file::

                # in yaml (content of master_file)
                ---
                !include file1
                ---
                !include file2
                ---
                !include file3

                # in Python
                cfg = awesomeyaml.Config.build('master_file')

            The same using long form:

                # in yaml (content of master_file)
                ---
                !include [file1, file2, file3]

                # in Python
                cfg = awesomeyaml.Config.build('master_file')

    '''
    def __init__(self, filenames, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not isinstance(filenames, cabc.Sequence) or isinstance(filenames, str):
            filenames = [filenames]

        for filename in filenames:
            if not isinstance(filename, str):
                raise ValueError(f'Include node expects a string parameter with a filename to read, but got: {type(filename)}')

        self.filenames = [os.path.expanduser(f) for f in filenames]

    @namespace('ayns')
    def on_preprocess_impl(self, path, builder):
        subbuilder = builder.get_subbuilder(path)
        missing = []
        for filename in self.filenames:
            found = False
            for lookup_dir in subbuilder.get_lookup_dirs(self._source_file):
                file = os.path.normpath(os.path.join(lookup_dir, filename))
                try:
                    subbuilder.add_source(file, raw_yaml=False, safe=self.ayns.safe)
                    found = True
                except FileNotFoundError:
                    continue

                if found:
                    break

            if not found:
                missing.append(filename)

        if missing:
            raise FileNotFoundError({ 'missing': missing, 'lookup_dirs': list(subbuilder.get_lookup_dirs(self._source_file)), 'source': self._source_file })

        return subbuilder.build().ayns.on_preprocess(path, builder)


    @namespace('ayns')
    @staticproperty
    @staticmethod
    def tag():
        return '!include'

    @namespace('ayns')
    @property
    def value(self):
        return self.filenames

    def __eq__(self, other):
        if isinstance(other, IncludeNode):
            return self._source_file == other._source_file and self.filenames == other.filenames
        return False
