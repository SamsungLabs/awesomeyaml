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
        super().__init__(fstr, persistent_namespace=False, **kwargs)
