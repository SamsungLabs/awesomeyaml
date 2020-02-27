__version__ = '0.1.0.dev0'
__repo__ = 'unknown'
__commit__ = 'unknown'

try:
    from . import _dist_info as info
    assert __version__ == info.__version__
    __repo__ = info.__repo__
    __commit__ = info.__commit__
except ImportError:
    try:
        import git
        from pathlib import Path

        r = git.Repo(Path(__file__).parent.parent.parent)
        if not r.remotes:
            __repo__ = 'local'
        else:
            __repo__ = r.remotes.origin.url

        __commit__ = r.head.commit.hexsha
        if r.is_dirty:
            __commit__ += ' (dirty)'

    except ImportError:
        pass

__all__ = ['__version__', '__repo__', '__commit__']
