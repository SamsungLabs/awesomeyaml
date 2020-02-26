import yaml
import re
import tokenize

from .nodes.node import ConfigNode
from .utils import pad_with_none


_fstr_regex = re.compile(r"^\s*f(['\"]).*\1\s*$")


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

def _make_node(loader, node, node_type=ConfigNode, kwargs=None, data_arg_name=None):
    kwargs = kwargs or {}
    data = None
    if isinstance(node, yaml.MappingNode):
        data = loader.construct_mapping(node, deep=True)
    elif isinstance(node, yaml.SequenceNode):
        data = loader.construct_sequence(node, deep=True)
    elif isinstance(node, yaml.ScalarNode):
        data = _maybe_parse_scalar(loader, node, reparse=False)

    if data_arg_name is None:
        return node_type(data, idx=loader.context.get_next_stage_idx(), **kwargs)
    else:
        assert data_arg_name not in kwargs
        kwargs[data_arg_name] = data
        return node_type(idx=loader.context.get_next_stage_idx(), **kwargs)


def _del_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'delete': True })

def _weak_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'merge_mode': ConfigNode.WEAK })

def _force_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'merge_mode': ConfigNode.FORCE })

def _merge_constructor(loader, node):
    return _make_node(loader, node, kwargs={ 'delete': False })

def _append_constructor(loader, node):
    from .nodes.append import AppendNode
    return _make_node(loader, node, node_type=AppendNode)

def _metadata_constructor(loader, tag_suffix, node):
    import pickle
    metadata = pickle.loads(bytes.fromhex(tag_suffix))
    kwargs = {}
    for special in ConfigNode.special_metadata_names:
        if special in metadata:
            kwargs[special] = metadata.pop(special)

    kwargs['metadata'] = metadata
    return _make_node(loader, node, kwargs=kwargs)

def _include_constructor(loader, node):
    from .nodes.include import IncludeNode
    return _make_node(loader, node, node_type=IncludeNode, kwargs={ 'ref_file': loader.context.get_current_file() })


def _prev_node_constructor(loader, node):
    from .nodes.prev import PrevNode
    return _make_node(loader, node, node_type=PrevNode)


def _xref_node_constructor(loader, node):
    from .nodes.xref import XRefNode
    return _make_node(loader, node, node_type=XRefNode)


def _bind_node_constructor(loader, tag_suffix, node):
    from .nodes.bind import BindNode
    if tag_suffix.count(':') > 1:
        raise ValueError(f'Invalid bind tag: !bind:{tag_suffix}')

    target_f_name, metadata = pad_with_none(*tag_suffix.split(':', maxsplit=1), minlen=2)
    return _make_node(loader, node, node_type=BindNode, kwargs={ 'func': target_f_name, 'metadata': metadata }, data_arg_name='args')


def _eval_node_constructor(loader, node):
    from .nodes.eval import EvalNode
    return _make_node(loader, node, node_type=EvalNode)


def _fstr_node_constructor(loader, node):
    from .nodes.fstr import FStrNode

    def _maybe_fix_fstr(value, *args, **kwargs):
        try:
            return FStrNode(value, *args, **kwargs)
        except ValueError:
            return FStrNode("f'" + value + "'", *args, **kwargs)

    return _make_node(loader, node, node_type=_maybe_fix_fstr)

yaml.add_constructor('!del', _del_constructor)
yaml.add_constructor('!weak', _weak_constructor)
yaml.add_constructor('!force', _force_constructor)
yaml.add_constructor('!merge', _merge_constructor)
yaml.add_constructor('!append', _append_constructor)
yaml.add_multi_constructor('!metadata:', _metadata_constructor)
yaml.add_constructor('!include', _include_constructor)
yaml.add_constructor('!prev', _prev_node_constructor)
yaml.add_constructor('!xref', _xref_node_constructor)
yaml.add_multi_constructor('!bind:', _bind_node_constructor)
yaml.add_constructor('!eval', _eval_node_constructor)
yaml.add_constructor('!fstr', _fstr_node_constructor)
yaml.add_implicit_resolver('!fstr', _fstr_regex)

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
    for token in tokenize.tokenize(_readline):
        if token.type == 53 and token.string == '}':
            if last_close:
                end = _beg
                break
            else:
                last_close = True
        else:
            last_close = False

    return end

def _get_metadata_content(data):
    _metadata_tag = '!metadata'
    curr_pos = data.find(_metadata_tag)
    while curr_pos != -1:
        beg = curr_pos + len(_metadata_tag)
        if data[beg] != ':':
            if data[beg:beg+2] != '{{':
                raise ValueError(f'Metadata tag should be followed by "{{{{" at character: {curr_pos}')
            end = _get_metadata_end(data, beg)
            if end is None:
                raise ValueError(f'Cannot find the end of a !metadata node which begins at: {curr_pos}')
            
            yield beg, end

        curr_pos = data.find(_metadata_tag, end+1)

def _encode_metadata(data):
    import pickle

    ranges = list(_get_metadata_content(data))
    offset = 0
    for beg, end in ranges:
        beg += offset
        end += offset

        repl = ':' + pickle.dumps(eval(data[beg+1:end-1])).hex()
        orig_len = end-beg
        repl_len = len(repl)
        data = data[:beg] + repl + data[end:]
        offset += repl_len - orig_len

    return data


def parse(data, builder):
    if not isinstance(data, str):
        data = data.read()
    
    #print(data)
    data = _encode_metadata(data)
    def get_loader(stream):
        loader = yaml.Loader(stream)
        loader.context = builder
        return loader

    for raw in yaml.load_all(data, Loader=get_loader):
        yield ConfigNode(raw)
