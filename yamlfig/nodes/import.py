from .scalar import ConfigScalar
from ..namespace import namespace, staticproperty
from ..utils import import_name


class ImportNode(ConfigScalar(str)):
    ''' Implements ``!import`` tag.

        The import node can be used to embed any python entity within the config.
        Internally, it is treated as a standard string node with the only exception
        being its evaluation which is implemented by the means of :py:func:`yamlfig.utils.import_name`.
        Specifically, the evaluated value is defined as::

            return import_name(str(self))

        Please see :py:func:`import_name` function for more details about how name
        lookup is performed.

        Supported syntax::

            !import name

        Merge behaviour:

            The same as standard string node.
    '''
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        return import_name(str(self))

    @namespace('yamlfigns')
    @staticproperty
    @staticmethod
    def tag():
        return '!import'
