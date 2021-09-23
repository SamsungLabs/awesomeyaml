from .node import ConfigNode
from ..namespace import namespace, staticproperty

import os
import collections


class IncludeNode(ConfigNode):
    ''' Implements ``!include`` tag.

        The include node can be used to include content of another
        config file in any part of the currently parsed file.

        The content of the node (string) will be treated as a filename
        of the file which will be included in the place of the node.
        This filename can either be absolute or relative.
        In the later case, a specific file will be looked up in directories
        defined by a builder object which was used to build the config - please
        see :py:meth:`yamlfig.Builder.get_lookup_dirs`.
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

                cfg = yamlfig.Config.build('file1', 'file2', 'file3')

            Aggregated in a single file::

                # in yaml (content of master_file)
                ---
                !include file1
                ---
                !include file2
                ---
                !include file3

                # in Python
                cfg = yamlfig.Config.build('master_file')

            The same using long form:

                # in yaml (content of master_file)
                ---
                !include [file1, file2, file3]

                # in Python
                cfg = yamlfig.Config.build('master_file')

    '''
    def __init__(self, filenames, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not isinstance(filenames, collections.Sequence) or isinstance(filenames, str):
            filenames = [filenames]

        for filename in filenames:
            if not isinstance(filename, str):
                raise ValueError(f'Include node expects a string parameter with a filename to read, but got: {type(filename)}')

        self.filenames = [os.path.expanduser(f) for f in filenames]

    @namespace('yamlfigns')
    def on_preprocess(self, path, builder):
        subbuilder = builder.get_subbuilder(path)
        missing = []
        for filename in self.filenames:
            found = False
            for lookup_dir in subbuilder.get_lookup_dirs(self._source_file):
                file = os.path.normpath(os.path.join(lookup_dir, filename))
                try:
                    subbuilder.add_source(file, raw_yaml=False)
                    found = True
                except FileNotFoundError:
                    continue

                if found:
                    break

            if not found:
                missing.append(filename)

        if missing:
            raise FileNotFoundError({ 'missing': missing, 'lookup_dirs': list(subbuilder.get_lookup_dirs(self._source_file)) })

        return subbuilder.build().yamlfigns.on_preprocess(path, builder)


    @namespace('yamlfigns')
    @staticproperty
    @staticmethod
    def tag():
        return '!include'

    @namespace('yamlfigns')
    @property
    def value(self):
        return {
            'filenames': self.filenames,
            'ref_file': self.ref_file
        }
