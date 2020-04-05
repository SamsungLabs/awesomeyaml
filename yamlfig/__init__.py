from . import config
from . import builder
from . import eval_context

Config = config.Config


from .utils import add_module_properties, staticproperty


def _get_version():
    from . import version
    return version.version

def _get_has_repo():
    from . import version
    return version.has_repo

def _get_repo():
    from . import version
    return version.repo

def _get_commit():
    from . import version
    return version.commit


add_module_properties(__name__, {
    '__version__': staticproperty(_get_version),
    '__has_repo__': staticproperty(_get_has_repo),
    '__repo__': staticproperty(_get_repo),
    '__commit__': staticproperty(_get_commit)
})
