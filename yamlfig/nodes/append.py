from .list import ConfigList
from ..namespace import namespace, staticproperty

from collections import Sequence


class AppendNode(ConfigList):
    ''' A class implementing ``!append`` node.

        The append tag creates a list node which appends its
        content to another list on merge, instead of overwriting it.

        Supported syntax::

            !append [list]

        Merge behaviour:

            ==================  =================================
            Case                Behaviour
            ==================  =================================
            ``A <- Append``     ``return A.extend(Append)``
            ``None <- Append``  ``raise KeyError``
            otherwise           behaves as :py:class:`ConfigList`
            ==================  =================================

    '''
    def __init__(self, value, **kwargs):
        if not isinstance(value, Sequence) or isinstance(value, str) or isinstance(value, bytes):
            value = [value]
        super().__init__(value, **kwargs)

    @namespace('yamlfigns')
    def on_premerge(self, path, into):
        node = into.yamlfigns.remove_node(path)
        if node is None:
            raise KeyError(f'Node {str(self)!r} does not exist in the previous context (possibly deleted?) - while processing a {type(self).__name__!r} node at {path!r}')
        node.extend(self)
        return node

    @namespace('yamlfigns')
    @staticproperty
    @staticmethod
    def tag():
        return '!append'
