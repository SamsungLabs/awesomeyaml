from .eval import EvalNode


class FStrNode(EvalNode):
    ''' Implements ``!fstr`` tag.

        The f-string node can be used to construct dynamic strings
        in an convenient way - exactly the same as in standard Python.
        This behaviour is achieved by reducing the f-string node
        to a special case of an eval node.
        More specifically, the string associated with the f-string node
        is is transformed to form a valid Python f-string which is later
        evaluated with ``eval`` by the means of the :py:class:`EvalNode` class.
        This can be summarised as::

            def FStrNode(fmt):
                return EvalNode("f'{}'".format(escape(fmt)))

        where ``fmt`` should be the content of an f-string, without extra quotes
        and the leading ``f``. 

        Supported syntax::

            !fstr fmt       # explicit form
            f'fmt'          # implicit form, eq. to: !fstr fmt
            f"fmt"          # implicit form, eq. to: !fstr fmt

        Merge behaviour:

            The same as standard string node.
    '''
    def __init__(self, fstr, **kwargs):
        if len(fstr) < 3 or fstr[0] != 'f' or fstr[1] not in ['"', "'"] or fstr[1] != fstr[-1]:
            raise ValueError(f'Invalid f-string: {fstr!r}')
        super().__init__(fstr, **kwargs)
