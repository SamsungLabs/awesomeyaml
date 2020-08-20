import os
import re
import pathlib

from .list import ConfigList
from .node import ConfigNode
from ..namespace import namespace, staticproperty

from collections import Sequence

_parent_regexp = re.compile(r'parent(\(([0-9]+)\))?')
_abs_regexp = re.compile(r'abs\(([a-zA-Z0-9_/\ -.]+)\)')


class PathNode(ConfigList):
    def __init__(self, values, ref_point, src_filename, **kwargs):
        if not isinstance(values, Sequence) or isinstance(values, str) or isinstance(values, bytes):
            if not values:
                values = []
            else:
                values = [values]

        super().__init__(values, **kwargs)

        self.ref_point = ref_point or ''
        self.src_filename = src_filename

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

    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        args = ConfigList.yamlfigns.on_evaluate(self, path, ctx)
        ref_point, ref_point_args = self._ref_point_parsed
        if ref_point == '':
            ret = pathlib.Path('.').joinpath(*args)
        elif ref_point == 'cwd':
            ret = pathlib.Path(os.getcwd()).joinpath(*args)
        elif ref_point == 'file':
            ret = pathlib.Path(self.src_filename).joinpath(*args)
        elif ref_point == 'parent':
            ret = pathlib.Path(self.src_filename).parents[ref_point_args].joinpath(*args)
        elif ref_point == 'abs':
            ret = pathlib.Path(ref_point_args).joinpath(*args)
        else:
            raise ValueError(f'Unknown reference point: {ref_point!r}')

        return pathlib.Path(os.path.normpath(ret))


    @namespace('yamlfigns')
    @property
    def tag(self):
        if not self.ref_point:
            return '!path'
        return '!path:' + self.ref_point

    @namespace('yamlfigns')
    @property
    def value(self):
        return {
            'values': super()._get_value(),
            'ref_point': self.ref_point,
            'src_filename': self.src_filename
        }
