import yaml

from .basic_nodes import *
from .basic_nodes import _fstr_regex
from .dynamic_nodes import *
from .config import Config


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

yaml.add_multi_representer(Dynamic, _dynamic_representer)
yaml.add_representer(FailIfUsed, _unused_representer)
yaml.add_representer(_Config, _config_representer)
yaml.add_representer(Del, _del_representer)
yaml.add_representer(Weak, _weak_representer)

def parse_config(data):
    return tuple(yaml.load_all(data, loader=yaml.Loader))
