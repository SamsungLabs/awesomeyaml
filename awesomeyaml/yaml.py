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

import yaml
import re
import copy
import token
import pickle
import tokenize
import functools
import contextlib
import collections.abc as cabc

from .nodes.node import ConfigNode
from .nodes.composed import ComposedNode
from .utils import pad_with_none
from . import errors


_fstr_regex = re.compile(r"^\s*f(['\"]).*\1\s*$")

_global_ctx = None


class UnquotedNode(yaml.ScalarNode):
    pass


class AwesomeyamlLoader(yaml.Loader):
    def _convert(self, value, node):
        if value is None and node.value == '':
            return value
        ret = ConfigNode(value, pyyaml_node=node)
        if ret._idx is None:
            ret._idx = self.context.get_next_stage_idx()
        if ret._source_file is None:
            ret._source_file = self.context.get_current_file()
        return ret

    @staticmethod
    def _make_generator(value, update_fn):
        yield
        update_fn(value)

    def construct_object(self, node, deep=False, convert=True):
        value = super().construct_object(node, deep=deep)
        if not convert:
            return value

        aynode = self._convert(value, node)

        if not deep and value is not aynode:
            if isinstance(node, yaml.SequenceNode):
                self.state_generators.append(self._make_generator(value, aynode.extend))
            elif isinstance(node, yaml.MappingNode):
                self.state_generators.append(self._make_generator(value, aynode.update))

        return aynode


class AwesomeyamlDumper(yaml.Dumper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._unquoted = False

    @contextlib.contextmanager
    def force_unquoted(self, value=True):
        old, self._unquoted = self._unquoted, value
        try:
            yield
        finally:
            self._unquoted = old

    def represent_scalar(self, tag, value, style=None):
        ret = super().represent_scalar(tag, value, style)
        if self._unquoted:
            ret.__class__ = UnquotedNode
        return ret

    def serialize_node(self, node, parent, index):
        old = None
        if isinstance(node, UnquotedNode):
            old, self._unquoted = self._unquoted, True

        try:
            ret = super().serialize_node(node, parent, index)
        finally:
            if old is not None:
                self._unquoted = old

        return ret

    def emit(self, event):
        event._unquoted = self._unquoted
        return super().emit(event)

    def choose_scalar_style(self):
        if self.event._unquoted:
            return ''

        return super().choose_scalar_style()

    def write_plain(self, text, *args, **kwargs):
        super().write_plain(text, *args, **kwargs)
        if self.event._unquoted and not text:
            self.stream.write(' ')


def add_constructor(tag, constructor):
    yaml.add_constructor(tag, constructor, Loader=AwesomeyamlLoader)


def add_multi_constructor(tag, constructor):
    yaml.add_multi_constructor(tag, constructor, Loader=AwesomeyamlLoader)


def add_implicit_resolver(tag, regex):
    yaml.add_implicit_resolver(tag, regex, Loader=AwesomeyamlLoader, Dumper=AwesomeyamlDumper)


def add_representer(data_type, representer):
    yaml.add_representer(data_type, representer, Dumper=AwesomeyamlDumper)


def add_multi_representer(data_type, representer):
    yaml.add_multi_representer(data_type, representer, Dumper=AwesomeyamlDumper)


def rethrow_as_parsing_error(func):
    @functools.wraps(func)
    def impl(*args, **kwargs):
        node = args[2] if len(args) > 2 else args[1]
        with errors.rethrow(errors.ParsingError, node, None, None):
            return func(*args, **kwargs)

    return impl


@contextlib.contextmanager
def global_ctx(filename):
    global _global_ctx
    if _global_ctx is None:
        import awesomeyaml.builder as b
        _global_ctx = b.Builder()

    _global_ctx._current_file = filename
    with ConfigNode.default_filename(filename):
        yield _global_ctx
    _global_ctx._current_file = None


def _encode_metadata(metadata):
    return pickle.dumps(metadata).hex()


def _decode_metadata(encoded):
    if not encoded:
        return {}
    metadata = pickle.loads(bytes.fromhex(encoded))
    kwargs = {}
    for special in ConfigNode.special_metadata_names:
        if special in metadata:
            kwargs[special] = metadata.pop(special)

    kwargs['metadata'] = metadata
    return kwargs


def parse_scalar(loader, node):
    plain = (node.style is None)
    implicit = (True, False) if plain else (False, True)
    notag = copy.deepcopy(node)
    notag.tag = loader.resolve(yaml.ScalarNode, notag.value, implicit)
    ret = loader.construct_object(notag, deep=True, convert=False)
    if ret is None and node.value != '':
        # we differentiate between explicit and implicit None
        # for explicit None, return ConfigNode(None) so that "value is None"
        # evaluates to False, this is needed by e.g., FunctionNode to detect lack of
        # arguments (implicit None) and a single None argument (explicit None)
        return ConfigNode(None)
    return ret


def _make_node(loader, node, node_type=ConfigNode, kwargs=None, data_arg_name=None, dict_is_data=True, parse_scalars=True):
    ''' A generic function to create new config nodes.

        Arguments:
            loader : a yaml.Loader
            node : a yaml node to parse, which will be used to create a config node
            node_type : a callable which will be called to create a config node - the following arguments control
                what are the arguments to the callable
            kwargs : a fixed directory of extra keyword arguments which will be passed to ``node_type``
            data_arg_name : if parsed node data should be passed as a keyword argument, the name of the
                argument should be specified by this argument, if it is ``None``, parsed node data
                will be passed as the first (positional) argument::

                    data = parse(node)
                    if data_arg_name:
                        kwargs[data_arg_name] = data
                        return node_type(**kwargs)
                    else:
                        return node_type(data, **kwargs)

            dict_is_data : if ``True`` and the parsed node data is mapping, the data will be used as
                a single ``"data"`` argument (see ``data_arg_name``), otherwise if ``False`` and the parsed
                node data is mapping, the dict will be treated as ``**kwargs`` for ``node_type``::

                    data = parse(node)
                    if isinstance(data, dict) and not dict_is_data:
                        kwargs.update(data)
                        return node_type(**kwargs)
                    else:
                        return node_type(data, **kwargs)

    '''
    kwargs = kwargs or {}
    data = None
    is_dict = False

    if isinstance(node, yaml.MappingNode):
        data = loader.construct_mapping(node, deep=True)
        is_dict = True
    elif isinstance(node, yaml.SequenceNode):
        data = loader.construct_sequence(node, deep=True)
    elif isinstance(node, yaml.ScalarNode):
        if not parse_scalars:
            data = loader.construct_scalar(node)
        else:
            data = parse_scalar(loader, node)

    kwargs.setdefault('source_file', loader.context.get_current_file())

    if is_dict and not dict_is_data:
        kwargs.update(data)
        return node_type(**kwargs)

    if data_arg_name is None:
        return node_type(data, idx=loader.context.get_next_stage_idx(), **kwargs)
    else:
        assert data_arg_name not in kwargs
        kwargs[data_arg_name] = data
        return node_type(idx=loader.context.get_next_stage_idx(), **kwargs)


make_node = rethrow_as_parsing_error(_make_node)


@rethrow_as_parsing_error
def _del_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'delete': True })


@rethrow_as_parsing_error
def _weak_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'priority': ConfigNode.WEAK })


@rethrow_as_parsing_error
def _force_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'priority': ConfigNode.FORCE })


@rethrow_as_parsing_error
def _merge_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'delete': False })


@rethrow_as_parsing_error
def _append_constructor(loader, node):
    from .nodes.append import AppendNode
    return _make_node(loader, node, node_type=AppendNode)


@rethrow_as_parsing_error
def _metadata_constructor(loader, tag_suffix, node):
    kwargs = _decode_metadata(tag_suffix)
    return _make_node(loader, node, kwargs=kwargs)


@rethrow_as_parsing_error
def _include_constructor(loader, node):
    from .nodes.include import IncludeNode
    return _make_node(loader, node, node_type=IncludeNode, dict_is_data=False, parse_scalars=False)


@rethrow_as_parsing_error
def _prev_constructor(loader, node):
    from .nodes.prev import PrevNode
    return _make_node(loader, node, node_type=PrevNode, parse_scalars=False)


@rethrow_as_parsing_error
def _xref_constructor(loader, node):
    from .nodes.xref import XRefNode
    return _make_node(loader, node, node_type=XRefNode, parse_scalars=False)

@rethrow_as_parsing_error
def _xref_constructor_md(loader, tag_suffix, node):
    from .nodes.xref import XRefNode
    kwargs = _decode_metadata(tag_suffix)
    return _make_node(loader, node, kwargs=kwargs, node_type=XRefNode, parse_scalars=False)


@rethrow_as_parsing_error
def _simple_bind_constructor(loader, node):
    from .nodes.bind import BindNode
    return _make_node(loader, node, node_type=BindNode, data_arg_name='func')


@rethrow_as_parsing_error
def _bind_constructor(loader, tag_suffix, node):
    from .nodes.bind import BindNode
    if tag_suffix.count(':') > 1:
        raise ValueError(f'Invalid bind tag: !bind:{tag_suffix}')

    target_f_name, metadata = pad_with_none(*tag_suffix.split(':', maxsplit=1), minlen=2)
    kwargs = _decode_metadata(metadata)
    return _make_node(loader, node, node_type=BindNode, kwargs={ 'func': target_f_name, **kwargs }, data_arg_name='args')


@rethrow_as_parsing_error
def _simple_call_constructor(loader, node):
    from .nodes.call import CallNode
    return _make_node(loader, node, node_type=CallNode, data_arg_name='func')


@rethrow_as_parsing_error
def _call_constructor(loader, tag_suffix, node):
    from .nodes.call import CallNode
    if tag_suffix.count(':') > 1:
        raise ValueError(f'Invalid call tag: !call:{tag_suffix}')

    target_f_name, metadata = pad_with_none(*tag_suffix.split(':', maxsplit=1), minlen=2)
    kwargs = _decode_metadata(metadata)
    return _make_node(loader, node, node_type=CallNode, kwargs={ 'func': target_f_name, **kwargs }, data_arg_name='args')


@rethrow_as_parsing_error
def _eval_constructor(loader, tag_suffix, node):
    from .nodes.eval import EvalNode
    kwargs = _decode_metadata(tag_suffix)
    return _make_node(loader, node, node_type=EvalNode, kwargs=kwargs, parse_scalars=False)


@rethrow_as_parsing_error
def _simple_eval_constructor(loader, node):
    from .nodes.eval import EvalNode
    return _make_node(loader, node, node_type=EvalNode, parse_scalars=False)


@rethrow_as_parsing_error
def _fstr_constructor(loader, node):
    from .nodes.fstr import FStrNode

    def _maybe_fix_fstr(value, *args, **kwargs):
        try:
            return FStrNode(value, *args, **kwargs)
        except ValueError:
            return FStrNode("f'" + value.replace(r"'", r"\'") + "'", *args, **kwargs)

    return _make_node(loader, node, node_type=_maybe_fix_fstr, parse_scalars=False)


@rethrow_as_parsing_error
def _import_constructor(loader, node):
    import importlib
    module = importlib.import_module('.nodes.import', package='awesomeyaml') # dirty hack because "import" is a keyword
    ImportNode = module.ImportNode
    return _make_node(loader, node, node_type=ImportNode, parse_scalars=False)


@rethrow_as_parsing_error
def _required_constructor(loader, node):
    from .nodes.required import RequiredNode
    return _make_node(loader, node, node_type=RequiredNode)


@rethrow_as_parsing_error
def _required_constructor_md(loader, tag_suffix, node):
    from .nodes.required import RequiredNode
    kwargs = _decode_metadata(tag_suffix)
    return _make_node(loader, node, kwargs=kwargs, node_type=RequiredNode)


@rethrow_as_parsing_error
def _none_constructor(loader, node):
    from .nodes.scalar import ConfigScalar
    return _make_node(loader, node, node_type=ConfigScalar(type(None)))


@rethrow_as_parsing_error
def _none_constructor_md(loader, tag_suffix, node):
    from .nodes.scalar import ConfigScalar
    kwargs = _decode_metadata(tag_suffix)
    return _make_node(loader, node, kwargs=kwargs, node_type=ConfigScalar(type(None)))


@rethrow_as_parsing_error
def _simple_path_constructor(loader, node):
    from .nodes.path import PathNode
    return _make_node(loader, node, node_type=PathNode, kwargs={ 'ref_point': None })


@rethrow_as_parsing_error
def _path_constructor(loader, tag_suffix, node):
    from .nodes.path import PathNode
    if tag_suffix.count(':') > 1:
        raise ValueError(f'Invalid path tag: !path:{tag_suffix}')

    ref_point, metadata = pad_with_none(*tag_suffix.rsplit(':', maxsplit=1), minlen=2)
    kwargs = _decode_metadata(metadata)
    return _make_node(loader, node, node_type=PathNode, kwargs={ 'ref_point': ref_point, **kwargs }, dict_is_data=False)


@rethrow_as_parsing_error
def _new_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'allow_new': True })


@rethrow_as_parsing_error
def _notnew_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'allow_new': False })


@rethrow_as_parsing_error
def _unsafe_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'safe': False })


@rethrow_as_parsing_error
def make_call_node_with_fixed_func(loader, node, func):
    from .nodes.call import CallNode
    return _make_node(loader, node, node_type=CallNode, kwargs={ 'func': func }, data_arg_name='args')


@rethrow_as_parsing_error
def _clear_constructor(loader, node):
    from .nodes.clear import ClearNode
    return _make_node(loader, node, node_type=ClearNode)


@rethrow_as_parsing_error
def _clear_constructor_md(loader, tag_suffix, node):
    from .nodes.clear import ClearNode
    kwargs = _decode_metadata(tag_suffix)
    return _make_node(loader, node, kwargs=kwargs, node_type=ClearNode)


add_constructor('!del', _del_constructor)
add_constructor('!weak', _weak_constructor)
add_constructor('!force', _force_constructor)
add_constructor('!merge', _merge_constructor)
add_constructor('!append', _append_constructor)
add_multi_constructor('!metadata:', _metadata_constructor)
add_constructor('!include', _include_constructor)
add_constructor('!prev', _prev_constructor)
add_constructor('!xref', _xref_constructor)
add_multi_constructor('!xref:', _xref_constructor_md)
add_constructor('!ref', _xref_constructor)
add_multi_constructor('!ref:', _xref_constructor_md)
add_multi_constructor('!bind:', _bind_constructor) # full bind form: !bind:func_name[:metadata] args_dict
add_constructor('!bind', _simple_bind_constructor) # simple argumentless bind from string: !bind func_name
add_multi_constructor('!call:', _call_constructor) # full call form: !call:func_name[:metadata] args_dict
add_constructor('!call', _simple_call_constructor) # simple argumentless call from string: !call func_name
add_multi_constructor('!eval:', _eval_constructor)
add_constructor('!eval', _simple_eval_constructor)
add_constructor('!fstr', _fstr_constructor)
add_implicit_resolver('!fstr', _fstr_regex)
add_constructor('!import', _import_constructor)
add_constructor('!required', _required_constructor)
add_multi_constructor('!required:', _required_constructor_md)
add_constructor('!null', _none_constructor)
add_multi_constructor('!null:', _none_constructor_md)
add_multi_constructor('!path:', _path_constructor)
add_constructor('!path', _simple_path_constructor)
add_constructor('!new', _new_constructor)
add_constructor('!notnew', _notnew_constructor)
add_constructor('!unsafe', _unsafe_constructor)
add_constructor('!clear', _clear_constructor)
add_multi_constructor('!clear:', _clear_constructor_md)


def _node_representer(dumper, node):
    from .nodes.bind import BindNode
    tag, metadata, data = node.ayns.represent()
    if data is None:
        assert not tag
        tag = '!null'

    parent_metadata = dumper.metadata[-1] if dumper.metadata else {}
    type_defaults = node.ayns.get_default_mode()

    tags_to_infer = {
        'priority': {
            ConfigNode.STANDARD: '',
            ConfigNode.WEAK: '!weak',
            ConfigNode.FORCE: '!force'
        },
        'delete': {
            True: '!del',
            False: '!merge'
        },
        'allow_new': {
            True: '!new',
            False: '!notnew'
        },
        'safe': {
            True: '!safe',
            False: '!unsafe'
        }
    }

    to_infer = list(tags_to_infer.keys())

    for f in to_infer:
        if f not in metadata:
            continue

        current = metadata[f]
        parent = parent_metadata.get(f, None) if parent_metadata else None
        default = type_defaults[f]
        if current is not None:
            if current == parent or current == default:
                del metadata[f]
        else:
            del metadata[f]

    metadata = { key: value for key, value in metadata.items() if key not in dumper.exclude_metadata }

    # try to use simple standard tag rather then encoded metadata
    # this is possible if we only have one special thing to handle
    # (e.g. delete is set to True)
    # if more then one things are changed for a particular node, we need
    # to se !metadata:hash anyway since it's impossible to have more
    # then two tags at the same time
    if not tag and len(metadata) == 1:
        # check if the only element in metadata is one of the standard
        # things which can be controller with simple tags (those listed
        # in "tags_to_infer")
        key = next(iter(metadata.keys()))
        maybe_tag = tags_to_infer.get(key)
        if maybe_tag:
            tag = maybe_tag[metadata[key]]
            del metadata[key]

    if metadata:
        if tag is None:
            tag = '!metadata'

        tag += ':' + _encode_metadata(metadata)

    pop = False
    if isinstance(node, ComposedNode):
        dumper.metadata.append({ **parent_metadata, **metadata })
        pop = True

    try:
        if not tag and not isinstance(data, ConfigNode):
            return dumper.represent_data(data)

        if isinstance(data, cabc.Mapping):
            if tag:
                return dumper.represent_mapping(tag, data)
            else:
                data = dict(data)
                return dumper.represent_data(data)

        elif isinstance(data, cabc.Sequence) and not isinstance(data, str) and not isinstance(data, bytes):
            if tag:
                return dumper.represent_sequence(tag, data)
            else:
                if isinstance(data, cabc.MutableSequence):
                    data = list(data)
                else:
                    data = tuple(data)
                return dumper.represent_data(data)
        else:
            from .nodes.scalar import ConfigScalar
            if tag:
                if data is None:
                    assert tag.startswith('!null')
                    with dumper.force_unquoted():
                        return dumper.represent_scalar('!null', '', style='')
                with dumper.force_unquoted():
                    if isinstance(data, ConfigScalar):
                        return dumper.represent_scalar(tag, repr(data._dyn_base(data)))
                    return dumper.represent_scalar(tag, str(data))
            else:
                if isinstance(data, ConfigScalar):
                    return dumper.represent_data(data._dyn_base(data))
                else:
                    # fallback to str
                    return dumper.represent_scalar('tag:yaml.org,2002:str', str(data))
    finally:
        if pop:
            dumper.metadata.pop()


def _none_representer(dumper, none):
    with dumper.force_unquoted():
        return dumper.represent_scalar('!null', '', style='')


add_multi_representer(ConfigNode, _node_representer)
add_representer(type(None), _none_representer)


def _get_metadata_end(data, beg):
    _beg = beg+2
    def _readline():
        nonlocal _beg
        end = data.find('}}', _beg)
        if end == -1:
            end = len(data)
        else:
            end += 2

        ret = data[_beg:end]
        _beg = end
        return ret.encode('utf8')
         
    last_close = False
    end = None
    for tok in tokenize.tokenize(_readline):
        if tok.type == token.OP and tok.string == '}':
            if last_close:
                end = _beg
                break
            else:
                last_close = True
        else:
            last_close = False

    return end


def _get_metadata_content(data):
    _metadata_tag = re.compile(r'(![a-zA-Z0-9_:.]+){{')
    curr_match = _metadata_tag.search(data)
    while curr_match is not None:
        beg = curr_match.end(1)
        assert data[beg:beg+2] == '{{'
        end = _get_metadata_end(data, beg)
        if end is None:
            raise ValueError(f'Cannot find the end of a !metadata node which begins at: {curr_match.start()}')
        
        yield beg, end
        curr_match = _metadata_tag.search(data, end+1)


def _encode_all_metadata(data):
    ranges = list(_get_metadata_content(data))
    offset = 0
    for beg, end in ranges:
        beg += offset
        end += offset

        metadata = eval(data[beg+1:end-1])
        encoded = _encode_metadata(metadata)
        repl = ':' + encoded
        orig_len = end-beg
        repl_len = len(repl)
        data = data[:beg] + repl + data[end:]
        offset += repl_len - orig_len

    return data


@errors.api_entry
def parse(data, filename_or_builder=None, config_nodes=True):
    if not isinstance(data, str):
        data = data.read()

    @contextlib.contextmanager
    def _dummy(context):
        yield context

    try:
        filename_or_builder.get_current_stage_idx()
    except:
        # filename_or_builder doesn't seem to be a builder
        # use global context
        context_fn = global_ctx
    else:
        # filename_or_builder behaves like builder so let's use it
        # as it is
        context_fn = _dummy

    #print(data)
    with context_fn(filename_or_builder) as context:
        data = _encode_all_metadata(data)
        def get_loader(*args, **kwargs):
            loader = AwesomeyamlLoader(*args, **kwargs)
            loader.context = context
            loader.name = context.get_current_file()
            return loader

        try:
            for node in yaml.load_all(data, Loader=get_loader):
                if config_nodes:
                    yield node
                else:
                    yield node.ayns.native_value
        except errors.ParsingError:
            raise
        except Exception as e:
            if errors.rethrow:
                if errors.include_original_exception:
                    raise errors.ParsingError(str(e), node=None, path=None) from e
                else:
                    raise errors.ParsingError(str(e), node=None, path=None) from None
            else:
                raise


@errors.api_entry
def dump(nodes, output=None, open_mode='w', exclude_metadata=None, sort_keys=False, **kwargs):
    close = False
    if isinstance(output, str):
        output = open(output, open_mode)
        close = True

    def get_dumper(*args, **kwargs):
        dumper = AwesomeyamlDumper(*args, **kwargs)
        assert not hasattr(dumper, 'metadata')
        dumper.metadata = []
        dumper.exclude_metadata = exclude_metadata or set()
        return dumper

    try:
        ret = yaml.dump(ConfigNode(nodes), stream=output, Dumper=get_dumper, sort_keys=sort_keys, **kwargs)
    finally:
        if close:
            output.close()

    if output is None:
        return ret
    return None
