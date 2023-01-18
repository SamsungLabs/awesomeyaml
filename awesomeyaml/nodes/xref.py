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

from .scalar import ConfigScalar
from .node_path import NodePath
from ..namespace import namespace, staticproperty


class XRefNode(ConfigScalar(str)):
    def __init__(self, value, **kwargs):
        super().__init__(value, **kwargs)

    @namespace('ayns')
    def on_evaluate_impl(self, path, ctx):
        chain = [NodePath.get_str_path(path)]
        curr = self
        while isinstance(curr, XRefNode):
            try:
                ref = ctx.get_node(curr)
            except KeyError:
                msg = f'Referenced node {str(curr)!r} is missing, while following a chain of references: {chain}'
                raise ValueError(msg) from None

            chain.append(str(curr))
            curr = ref
        assert curr is not self
        return ctx.evaluate_node(curr, prefix=chain[-1])

    @namespace('ayns')
    @staticproperty
    @staticmethod
    def tag():
        return '!xref'
