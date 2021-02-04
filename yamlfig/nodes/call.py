from .dict import ConfigDict
from .function import FunctionNode
from ..namespace import namespace, staticproperty
from ..utils import import_name


class CallNode(FunctionNode):
    ''' A class implementing ``!call`` node.

        The bahaviour of this class is analogical to :py:class:`BindNode`
        but instead of evaluating to a ``functools.partial`` it calls the
        target function with provided arguments and returns its result::

            f = import_name(call_node.yamlfigns.func)
            return f(**call_node)

        Please see the BindNode's documentation for more details.

        Supported syntax::

            !call:name { args }
            !call:name [args]    # eq. to: !call:name { enumerate(args) }
            !call name           # eq. to: !call:name {}


        Merge behaviour:

            ==================  ================================================================================================================================
            Case                Behaviour
            ==================  ================================================================================================================================
            ``dict <- Call``    behaves as ``dict <- !del dict``, unless delete is explicitly set to False
            ``None <- Call``    ``Call``
            ``Call1 <- Call2``  ``Call2`` if target entity changes, otherwise ``dict1 <- dict2``
            ``Call <- dict``    Update ``Call``'s arguments without changing target function
            ``Call <- list``    Update ``Call``'s arguments (analogical to ``dict <- list``) without changing target function
            ``Call <- str``     if ``str`` is different than the current target function's name, update the name and remove all children, otherwise no effect
            ==================  ================================================================================================================================

    '''
    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        _func = self._func
        if isinstance(_func, str):
            _func = import_name(_func)
        args = ConfigDict.yamlfigns.on_evaluate(self, path, ctx)
        p, kw_p, kw = FunctionNode._resolve_args(_func, args)
        return _func(*p, **kw_p, **kw)

    @namespace('yamlfigns')
    @property
    def tag(self):
        _func = self._func
        if not isinstance(_func, str):
            _func = self._func.__module__ + '.' + self._func.__name__
        return '!call:' + _func
