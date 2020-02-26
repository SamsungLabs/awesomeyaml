from .eval import EvalNode


class FStrNode(EvalNode):
    def __init__(self, fstr, **kwargs):
        if len(fstr) < 3 or fstr[0] != 'f' or fstr[1] not in ['"', "'"] or fstr[1] != fstr[-1]:
            raise ValueError(f'Invalid f-string: {fstr!r}')
        super().__init__(fstr, **kwargs)
