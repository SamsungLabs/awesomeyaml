from .node import ConfigNode
from ..namespace import namespace

import os
import collections


class IncludeNode(ConfigNode):
    def __init__(self, filenames, *args, ref_file=None, **kwargs):
        super().__init__(*args, **kwargs)

        if not isinstance(filenames, collections.Sequence) or isinstance(filenames, str):
            filenames = [filenames]

        for filename in filenames:
            if not isinstance(filename, str):
                raise ValueError(f'Include node expects a string parameter with a filename to read, but got: {type(filename)}')

        self.filenames = filenames
        self.ref_file = ref_file

    @namespace('yamlfigns')
    def on_preprocess(self, path, builder):
        subbuilder = builder.get_subbuilder(path)
        missing = []
        for filename in self.filenames:
            found = False
            for lookup_dir in subbuilder.get_lookup_dirs(self.ref_file):
                file = os.path.join(lookup_dir, filename)
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
            raise FileNotFoundError({ 'missing': missing, 'lookup_dirs': list(subbuilder.get_lookup_dirs(self.ref_file)) })

        return subbuilder.build().yamlfigns.on_preprocess(path, builder)
