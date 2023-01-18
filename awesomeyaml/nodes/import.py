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
from ..namespace import namespace, staticproperty
from ..utils import import_name


class ImportNode(ConfigScalar(str)):
    ''' Implements ``!import`` tag.

        The import node can be used to embed any python entity within the config.
        Internally, it is treated as a standard string node with the only exception
        being its evaluation which is implemented by the means of :py:func:`awesomeyaml.utils.import_name`.
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

    @namespace('ayns')
    def on_evaluate_impl(self, path, ctx):
        self.ayns._require_safe(path)
        return import_name(str(self))

    @namespace('ayns')
    @staticproperty
    @staticmethod
    def tag():
        return '!import'
