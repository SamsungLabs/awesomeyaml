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


import threading
import contextlib
import yaml.error


rethrow = True # whether errors happening inside awesomeyaml should be rethrown as higher-level errors (listed below)
include_original_exception = True # if exceptions are rethrown, whether to include the original exception as "__cause__" of the new exception
shorten_traceback = True # if exceptions are rethrown, whether to shorten their stack by removing some intermediate frames

_api_entered = threading.local()


def api_entry(fn):
    def impl(*args, **kwargs):
        if getattr(_api_entered, 'value', False) or not rethrow or not shorten_traceback:
            return fn(*args, **kwargs)

        _api_entered.value = True
        try:
            return fn(*args, **kwargs)
        except Error as e:
            if include_original_exception:
                orig_exp = e.__context__
                if orig_exp is not None:
                    orig_exp.__traceback__ = orig_exp.__traceback__.tb_next # skip "rethrow_as_XXX"
                reason = orig_exp
            else:
                reason = None

            raise type(e)(
                error_msg=e.error_msg,
                node=e.node,
                path=e.path,
                extra_node=e.extra_node,
                note=e.note
            ) from reason
        finally:
            _api_entered.value = False

    return impl


def _get_mark_or_fallback_str(aynode):
    if aynode is None:
        return None
    if aynode._pyyaml_node is not None:
        return aynode._pyyaml_node.start_mark
    return f'<A node from file: {aynode._source_file!r}>'


class Error(yaml.error.MarkedYAMLError):
    def __init__(self, error_msg, node, path=None, extra_node=None, note=None):
        self.error_msg = error_msg
        self.node = node
        self.path = path
        self.extra_node = extra_node

        msg = self.base_msg

        try:
            types = repr(type(self.node).__name__)
            if self.extra_node is not None:
                types += f' and {type(self.extra_node).__name__!r}'

            path_str = repr(path if path else '<top-level node>') + f' from file {self.node._source_file!r}'
            if self.extra_node is not None:
                path_str += f' and {self.extra_node._source_file!r}'

            msg = msg.format(types, path_str)
        except:
            pass

        if error_msg:
            if msg:
                msg += '\n'
            msg += error_msg

        if self.extra_node is None:
            if self.stage == 'parsing':
                if self.node is not None:
                    mark = self.node.start_mark
                else:
                    mark = None
            else:
                mark = _get_mark_or_fallback_str(self.node)

            super().__init__(
                problem=msg,
                problem_mark=mark,
                note=note
            )
        else:
            super().__init__(
                context=msg,
                context_mark=_get_mark_or_fallback_str(self.node),
                problem_mark=_get_mark_or_fallback_str(self.extra_node),
                note=note
            )


class ParsingError(Error):
    stage = 'parsing'
    base_msg = 'Parsing error occurred'


class PreprocessError(Error):
    stage = 'preprocess'
    base_msg = 'An error occurred while preprocessing a {} node under path: {}'

class PremergeError(Error):
    stage = 'premerge'
    base_msg = 'An error occurred while performing pre-merge actions for a {} node under path: {}'


class MergeError(Error):
    stage = 'merge'
    base_msg = 'An error occurred while merging {} nodes under path: {}'

class EvalError(Error):
    stage = 'eval'
    base_msg = 'An error occurred while evaluating a {} node under path: {}'


class UnsafeError(EvalError):
    base_msg = 'Avoiding execution of an !unsafe {} node under path: {}'


@contextlib.contextmanager
def rethrow(error_type, self, path, other):
    try:
        yield
    except error_type as e:
        if shorten_traceback:
            raise
        else:
            raise error_type(error_msg=None, node=self, path=path, extra_node=other) from e
    except Exception as e:
        if rethrow:
            reason = None
            if include_original_exception:
                reason = e

            raise error_type(error_msg=str(e), node=self, path=path, extra_node=other) from reason
        else:
            raise
