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
import token
import pickle
import tokenize
import contextlib
import collections.abc as cabc

from .nodes.node import ConfigNode
from .nodes.composed import ComposedNode
from .utils import pad_with_none
from . import errors


_fstr_regex = re.compile(r"^\s*f(['\"]).*\1\s*$")

_global_ctx = None


def rethrow_as_parsing_error_impl(func):
    def impl(*args, **kwargs):
        node = (args[2] if isinstance(args[1], str) else args[1])
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if errors.rethrow:
                if errors.include_original_exception:
                    raise errors.ParsingError(str(e), node) from e
                else:
                    raise errors.ParsingError(str(e), node) from None
            else:
                raise

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
        return None
    return pickle.loads(bytes.fromhex(encoded))


def _maybe_parse_scalar(loader, node, reparse=True):
    ret = loader.construct_scalar(node)
    if reparse and isinstance(ret, str) and not ret.strip().startswith('!'):
        ret = yaml.safe_load(ret)

    return ret


def _make_obj(loader, node, objtype, reparse_scalars=False):
    args = []
    kwargs = {}
    if isinstance(node, yaml.MappingNode):
        kwargs = loader.construct_mapping(node, deep=True)
    elif isinstance(node, yaml.SequenceNode):
        args = loader.construct_sequence(node, deep=True)
    elif isinstance(node, yaml.ScalarNode):
        val = _maybe_parse_scalar(loader, node, reparse=reparse_scalars)
        if val:
            args = [val]

    if '*' in kwargs:
        args.extend(kwargs['*'])
        del kwargs['*']

    return objtype(*args, **kwargs)


def _make_node(loader, node, node_type=ConfigNode, kwargs=None, data_arg_name=None, dict_is_data=True):
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
        data = _maybe_parse_scalar(loader, node, reparse=node_type is ConfigNode)

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


@rethrow_as_parsing_error_impl
def _del_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'delete': True })


@rethrow_as_parsing_error_impl
def _weak_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'merge_mode': ConfigNode.WEAK })


@rethrow_as_parsing_error_impl
def _force_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'merge_mode': ConfigNode.FORCE })


@rethrow_as_parsing_error_impl
def _merge_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'delete': False })


@rethrow_as_parsing_error_impl
def _append_constructor(loader, node):
    from .nodes.append import AppendNode
    return _make_node(loader, node, node_type=AppendNode)


@rethrow_as_parsing_error_impl
def _metadata_constructor(loader, tag_suffix, node):
    metadata = _decode_metadata(tag_suffix)
    kwargs = {}
    for special in ConfigNode.special_metadata_names:
        if special in metadata:
            kwargs[special] = metadata.pop(special)

    kwargs['metadata'] = metadata
    return _make_node(loader, node, kwargs=kwargs)


@rethrow_as_parsing_error_impl
def _include_constructor(loader, node):
    from .nodes.include import IncludeNode
    return _make_node(loader, node, node_type=IncludeNode, dict_is_data=False)


@rethrow_as_parsing_error_impl
def _prev_constructor(loader, node):
    from .nodes.prev import PrevNode
    return _make_node(loader, node, node_type=PrevNode)


@rethrow_as_parsing_error_impl
def _xref_constructor(loader, node):
    from .nodes.xref import XRefNode
    return _make_node(loader, node, node_type=XRefNode)

@rethrow_as_parsing_error_impl
def _xref_constructor_md(loader, tag_suffix, node):
    metadata = _decode_metadata(tag_suffix)
    kwargs = {}
    for special in ConfigNode.special_metadata_names:
        if special in metadata:
            kwargs[special] = metadata.pop(special)

    kwargs['metadata'] = metadata

    from .nodes.xref import XRefNode
    return _make_node(loader, node, kwargs=kwargs, node_type=XRefNode)


@rethrow_as_parsing_error_impl
def _simple_bind_constructor(loader, node):
    from .nodes.bind import BindNode
    return _make_node(loader, node, node_type=BindNode, data_arg_name='func')


@rethrow_as_parsing_error_impl
def _bind_constructor(loader, tag_suffix, node):
    from .nodes.bind import BindNode
    if tag_suffix.count(':') > 1:
        raise ValueError(f'Invalid bind tag: !bind:{tag_suffix}')

    target_f_name, metadata = pad_with_none(*tag_suffix.split(':', maxsplit=1), minlen=2)
    metadata = _decode_metadata(metadata)
    return _make_node(loader, node, node_type=BindNode, kwargs={ 'func': target_f_name, 'metadata': metadata }, data_arg_name='args')


@rethrow_as_parsing_error_impl
def _simple_call_constructor(loader, node):
    from .nodes.call import CallNode
    return _make_node(loader, node, node_type=CallNode, data_arg_name='func')


@rethrow_as_parsing_error_impl
def _call_constructor(loader, tag_suffix, node):
    from .nodes.call import CallNode
    if tag_suffix.count(':') > 1:
        raise ValueError(f'Invalid call tag: !call:{tag_suffix}')

    target_f_name, metadata = pad_with_none(*tag_suffix.split(':', maxsplit=1), minlen=2)
    metadata = _decode_metadata(metadata)
    return _make_node(loader, node, node_type=CallNode, kwargs={ 'func': target_f_name, 'metadata': metadata }, data_arg_name='args')


@rethrow_as_parsing_error_impl
def _eval_constructor(loader, tag_suffix, node):
    from .nodes.eval import EvalNode
    metadata = _decode_metadata(tag_suffix)
    kwargs = {}
    for special in ConfigNode.special_metadata_names:
        if special in metadata:
            kwargs[special] = metadata.pop(special)

    kwargs['metadata'] = metadata
    return _make_node(loader, node, node_type=EvalNode, kwargs=kwargs)


@rethrow_as_parsing_error_impl
def _simple_eval_constructor(loader, node):
    from .nodes.eval import EvalNode
    return _make_node(loader, node, node_type=EvalNode)


@rethrow_as_parsing_error_impl
def _fstr_constructor(loader, node):
    from .nodes.fstr import FStrNode

    def _maybe_fix_fstr(value, *args, **kwargs):
        try:
            return FStrNode(value, *args, **kwargs)
        except ValueError:
            return FStrNode("f'" + value.replace(r"'", r"\'") + "'", *args, **kwargs)

    return _make_node(loader, node, node_type=_maybe_fix_fstr)


@rethrow_as_parsing_error_impl
def _import_constructor(loader, node):
    import importlib
    module = importlib.import_module('.nodes.import', package='awesomeyaml') # dirty hack because "import" is a keyword
    ImportNode = module.ImportNode
    return _make_node(loader, node, node_type=ImportNode)


@rethrow_as_parsing_error_impl
def _required_constructor(loader, node):
    from .nodes.required import RequiredNode
    def _check_empty_str(arg, **kwargs):
        if arg != '':
            raise ValueError(f'!required node does not expect any arguments - got: {arg}')
        return RequiredNode(**kwargs)
    return _make_node(loader, node, node_type=_check_empty_str)


@rethrow_as_parsing_error_impl
def _required_constructor_md(loader, tag_suffix, node):
    metadata = _decode_metadata(tag_suffix)
    kwargs = {}
    for special in ConfigNode.special_metadata_names:
        if special in metadata:
            kwargs[special] = metadata.pop(special)

    kwargs['metadata'] = metadata

    from .nodes.required import RequiredNode
    def _check_empty_str(arg, **kwargs):
        if arg != '':
            raise ValueError(f'!required node does not expect any arguments - got: {arg}')
        return RequiredNode(**kwargs)
    return _make_node(loader, node, kwargs=kwargs, node_type=_check_empty_str)


@rethrow_as_parsing_error_impl
def _none_constructor(loader, node):
    def _check_empty_str(arg, *args, **kwargs):
        if arg != '' or args:
            raise ValueError(f'!null does not expect any arguments - got: {[arg]+list(args)}')
        return None
    return _make_node(loader, node, node_type=_check_empty_str)


@rethrow_as_parsing_error_impl
def _none_constructor_md(loader, tag_suffix, node):
    metadata = _decode_metadata(tag_suffix)
    kwargs = {}
    for special in ConfigNode.special_metadata_names:
        if special in metadata:
            kwargs[special] = metadata.pop(special)

    kwargs['metadata'] = metadata

    def _check_empty_str(arg, *args, **kwargs):
        if arg != '' or args:
            raise ValueError(f'!null does not expect any arguments - got: {[arg]+list(args)}')
        return None
    return _make_node(loader, node, kwargs=kwargs, node_type=_check_empty_str)


@rethrow_as_parsing_error_impl
def _simple_path_constructor(loader, node):
    from .nodes.path import PathNode
    return _make_node(loader, node, node_type=PathNode, kwargs={ 'ref_point': None, 'src_filename': loader.context.get_current_file() })


@rethrow_as_parsing_error_impl
def _path_constructor(loader, tag_suffix, node):
    from .nodes.path import PathNode
    if tag_suffix.count(':') > 1:
        raise ValueError(f'Invalid path tag: !path:{tag_suffix}')

    ref_point, metadata = pad_with_none(*tag_suffix.rsplit(':', maxsplit=1), minlen=2)
    metadata = _decode_metadata(metadata)
    return _make_node(loader, node, node_type=PathNode, kwargs={ 'ref_point': ref_point, 'src_filename': loader.context.get_current_file(), 'metadata': metadata }, dict_is_data=False)


@rethrow_as_parsing_error_impl
def make_call_node_with_fixed_func(loader, node, func):
    from .nodes.call import CallNode
    return _make_node(loader, node, node_type=CallNode, kwargs={ 'func': func }, data_arg_name='args')


yaml.add_constructor('!del', _del_constructor)
yaml.add_constructor('!weak', _weak_constructor)
yaml.add_constructor('!force', _force_constructor)
yaml.add_constructor('!merge', _merge_constructor)
yaml.add_constructor('!append', _append_constructor)
yaml.add_multi_constructor('!metadata:', _metadata_constructor)
yaml.add_constructor('!include', _include_constructor)
yaml.add_constructor('!prev', _prev_constructor)
yaml.add_constructor('!xref', _xref_constructor)
yaml.add_multi_constructor('!xref:', _xref_constructor_md)
yaml.add_constructor('!ref', _xref_constructor)
yaml.add_multi_constructor('!ref:', _xref_constructor_md)
yaml.add_multi_constructor('!bind:', _bind_constructor) # full bind form: !bind:func_name[:metadata] args_dict
yaml.add_constructor('!bind', _simple_bind_constructor) # simple argumentless bind from string: !bind func_name
yaml.add_multi_constructor('!call:', _call_constructor) # full call form: !call:func_name[:metadata] args_dict
yaml.add_constructor('!call', _simple_call_constructor) # simple argumentless call from string: !call func_name
yaml.add_multi_constructor('!eval:', _eval_constructor)
yaml.add_constructor('!eval', _simple_eval_constructor)
yaml.add_constructor('!fstr', _fstr_constructor)
yaml.add_implicit_resolver('!fstr', _fstr_regex)
yaml.add_constructor('!import', _import_constructor)
yaml.add_constructor('!required', _required_constructor)
yaml.add_multi_constructor('!required:', _required_constructor_md)
yaml.add_constructor('!null', _none_constructor)
yaml.add_multi_constructor('!null:', _none_constructor_md)
yaml.add_multi_constructor('!path:', _path_constructor)
yaml.add_constructor('!path', _simple_path_constructor)


def _node_representer(dumper, node):
    from .nodes.bind import BindNode
    tag, metadata, data = node.ayns.represent()
    if data is None:
        assert not tag
        tag = '!null'

    parent_metadata = dumper.metadata[-1] if dumper.metadata else {}
    type_defaults = node.ayns.get_default_mode()

    tags_to_infer = {
        'merge_mode': {
            ConfigNode.STANDARD: '',
            ConfigNode.WEAK: '!weak',
            ConfigNode.FORCE: '!force'
        },
        'delete': {
            True: '!del',
            False: '!merge'
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
            if tag:
                if data is None:
                    assert tag.startswith('!null')
                    return dumper.represent_scalar(tag, str(''))
                return dumper.represent_scalar(tag, str(data))
            else:
                from .nodes.scalar import ConfigScalar
                if isinstance(data, ConfigScalar):
                    return dumper.represent_data(data._dyn_base(data))
                else:
                    # fallback to str
                    return dumper.represent_scalar('tag:yaml.org,2002:str', str(data))
    finally:
        if pop:
            dumper.metadata.pop()


def _none_representer(dumper, none):
    return dumper.dump_scalar('!null', str(''))


yaml.add_multi_representer(ConfigNode, _node_representer)
yaml.add_representer(type(None), _none_representer)

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
            loader = yaml.Loader(*args, **kwargs)
            loader.context = context
            loader.name = context.get_current_file()
            return loader

        try:
            for raw in yaml.load_all(data, Loader=get_loader):
                if config_nodes:
                    yield ConfigNode(raw)
                else:
                    yield ConfigNode(raw).ayns.native_value
        except errors.ParsingError as pe:
            if errors.shorten_traceback:
                if errors.include_original_exception:
                    orig_exp = pe.__context__
                    if orig_exp is not None:
                        orig_exp.__traceback__ = orig_exp.__traceback__.tb_next # skip "rethrow_as_parsing_error_impl"
                    raise errors.ParsingError(pe.error_msg, pe.node) from orig_exp
                else:
                    raise errors.ParsingError(pe.error_msg, pe.node) from None
            else:
                raise
        except Exception as e:
            if errors.rethrow:
                if errors.include_original_exception:
                    raise errors.ParsingError(str(e), None) from e
                else:
                    raise errors.ParsingError(str(e), node=None) from None
            else:
                raise


def dump(nodes, output=None, open_mode='w', exclude_metadata=None, sort_keys=False, **kwargs):
    close = False
    if isinstance(output, str):
        output = open(output, open_mode)
        close = True

    def get_dumper(*args, **kwargs):
        dumper = yaml.Dumper(*args, **kwargs)
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
