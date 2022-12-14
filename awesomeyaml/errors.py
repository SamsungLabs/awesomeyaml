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


import yaml.error


rethrow = True
include_original_exception = True
shorten_traceback = True


class ParsingError(yaml.error.MarkedYAMLError):
    def __init__(self, error_msg, node): # node is pyyaml's node
        self.error_msg = error_msg
        self.node = node
        super().__init__(problem=error_msg, problem_mark=(node.start_mark if node else None))


class EvalError(RuntimeError):
    pass


def _get_mark_or_fallback_str(aynode):
    if aynode._pyyaml_node is not None:
        return aynode._pyyaml_node.start_mark
    return f'<A node from file: {aynode._source_file!r}>'


class MergeError(yaml.error.MarkedYAMLError):
    def __init__(self, error_msg, node1, node2, path): # node is awesomeyaml's node
        self.error_msg = error_msg
        self.node1 = node1
        self.node2 = node2
        self.path = path 
        super().__init__(context=f'An error occurred while merging nodes under path: {path!r}: {error_msg!r}.', context_mark=_get_mark_or_fallback_str(self.node1), problem_mark=_get_mark_or_fallback_str(self.node2))
