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

from .list import ConfigList
from ..namespace import namespace


class StreamNode(ConfigList):
    _default_delete = False

    def __init__(self, builder, **kwargs):
        kwargs.setdefault('delete', False)
        super().__init__(builder.stages, **kwargs)
        self.builder = builder

    @property
    def stages(self):
        return self.builder.stages

    @namespace('ayns')
    def on_premerge_impl(self, path, into):
        self.clear()
        self.builder.flatten()
        self.append(self.builder.stages[0])
        return self.builder.stages[0].ayns.on_premerge(path, into)
