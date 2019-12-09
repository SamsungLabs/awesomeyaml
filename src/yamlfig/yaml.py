import yaml
import re
import tokenize

#from .nodes.basic_nodes import *
#from .basic_nodes import _fstr_regex
#from .nodes.dynamic_nodes import *
from .config import Config
from .nodes.node import ConfigNode


_fstr_regex = re.compile(r"^\s*f(['\"]).*\1\s*$")


def _maybe_parse_scalar(loader, node, reparse=True):
    ret = loader.construct_scalar(node)
    if reparse and isinstance(ret, str) and not ret.strip().startswith('!'):
        ret = yaml.safe_load(ret)

    return ret


def _eval_contructor(loader, node):
    return _make_obj(loader, node, Eval)

def _fstr_constructor(loader, node):
    return _make_obj(loader, node, FStr)

def _bind_contructor(loader, node):
    func = None
    args = None
    if isinstance(node, yaml.MappingNode):
        value = loader.construct_mapping(node, deep=True)
    else:
        value = { 'func': Lazy('!name ' + loader.construct_scalar(node)) }

    assert len(value) <= 2
    assert 'func' in value
    func = value['func']
    if len(value) == 2:
        assert 'args' in value
        args = value['args']

    return Bind(func, args)

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

def _required_constructor(loader, node):
    return _make_obj(loader, node, FailIfUnset)

def _unused_constructor(loader, node):
    return _make_obj(loader, node, FailIfUsed)

def _xref_constructor(loader, node):
    return _make_obj(loader, node, XRef)

def _lazy_constructor(loader, node):
    return _make_obj(loader, node, Lazy)

def _lazy_name_constructor(loader, node):
    name = loader.construct_scalar(node)
    return Lazy('!!python/name:' + name.strip())

def _lazy_module_constructor(loader, node):
    name = loader.construct_scalar(node)
    return Lazy('!!python/module:' + name.strip())

def _config_constructor(loader, node):
    if not isinstance(node, yaml.MappingNode):
        scalar = loader.construct_scalar(node)
        assert not scalar
        return {}
        
    return loader.construct_mapping(node)

def _implies_constructor(loader, node):
    return _make_obj(loader, node, Implies)

def _ops_constructor(loader, node):
    return _make_obj(loader, node, Ops)

def _del_constructor(loader, node):
    return _make_obj(loader, node, Del)

def _append_constructor(loader, node):
    args = []
    if isinstance(node, yaml.SequenceNode):
        args = loader.construct_sequence(node, deep=True)
    else:
        args = [_maybe_parse_scalar(loader, node)]

    return DynClass.Append(args)

def _weak_constructor(loader, node):
    if isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node, deep=True)
    elif isinstance(node, yaml.ScalarNode):
        value = _maybe_parse_scalar(loader, node)
    else:
        raise ValueError('Unsupported PyYaml node type')

    return Weak(value)

def _include_constructor(loader, node):
    from .config import Config
    value = loader.construct_scalar(node)
    return IncludeNode(value)

def _metadata_constructor(loader, tag_sufix, node):
    data = None
    if isinstance(node, yaml.MappingNode):
        data = loader.construct_mapping(node, deep=True)
    elif isinstance(node, yaml.SequenceNode):
        data = loader.construct_sequence(node, deep=True)
    elif isinstance(node, yaml.ScalarNode):
        data = _maybe_parse_scalar(loader, node, reparse=False)

    import pickle
    return ConfigNode(data, idx=loader.context.get_current_stage_idx(), metadata=pickle.loads(bytes.fromhex(tag_sufix)))

yaml.add_constructor('!eval', _eval_contructor)
yaml.add_implicit_resolver('!fstr', _fstr_regex)
yaml.add_constructor('!fstr', _fstr_constructor)
yaml.add_constructor('!bind', _bind_contructor)
yaml.add_constructor('!required', _required_constructor)
yaml.add_constructor('!unused', _unused_constructor)
yaml.add_constructor('!xref', _xref_constructor)
yaml.add_constructor('!lazy', _lazy_constructor)
yaml.add_constructor('!name', _lazy_name_constructor)
yaml.add_constructor('!module', _lazy_module_constructor)
yaml.add_constructor('!config', _config_constructor)
yaml.add_constructor('!implies', _implies_constructor)
yaml.add_constructor('!ops', _ops_constructor)
yaml.add_constructor('!del', _del_constructor)
yaml.add_constructor('!append', _append_constructor)
yaml.add_constructor('!weak', _weak_constructor)
yaml.add_constructor('!include', _include_constructor)
yaml.add_multi_constructor('!metadata', _metadata_constructor)


def _dynamic_representer(dumper, data):
    return data._represent(dumper)

def _unused_representer(dumper, data):
    return dumper.represent_scalar('!unused', '')

def _config_representer(dumper, data):
    return dumper.represent_mapping('!config' if not data._override_on_merge else '!del', data._fields)

def _del_representer(dumper, data):
    if not data._fields:
        return dumper.represent_scalar('!del', '')
    else:
        return dumper.represent_mapping('!del', data._fields)

def _weak_representer(dumper, data):
    if isinstance(data, collections.Sequence):
        return dumper.represent_sequence('!weak', data.value)
    else:
        return dumper.represent_scalar('!weak', data.value)

#yaml.add_multi_representer(DynamicNode, _dynamic_representer)
#yaml.add_representer(FailIfUsedNode, _unused_representer)
#yaml.add_representer(_Config, _config_representer)
#yaml.add_representer(DelNode, _del_representer)
#yaml.add_representer(WeakNode, _weak_representer)

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
        return ret
         
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

def _get_metadatas_content(data):
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

    ranges = list(_get_metadatas_content(data))
    offset = 0
    for beg, end in ranges:
        beg += offset
        end += offset

        repl = ':' + pickle.dumps(eval(data[beg:end])).hex()
        orig_len = end-beg
        repl_len = len(repl)
        data[beg:end] = repl
        offset += repl_len - orig_len

    return data

class YamlfigLoader(yaml.Loader):
    def construct_document(self, node):
        return Config(super().construct_document(node))

def parse(data, builder):
    if not isinstance(data, str):
        data = data.read()
    
    data = _encode_metadata(data)
    def get_loader(stream):
        loader = yaml.Loader(stream)
        loader.context = builder
        return loader

    return yaml.load_all(data, Loader=get_loader)
