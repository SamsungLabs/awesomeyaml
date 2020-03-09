__version__ = '0.1.0.dev0'
__repo__ = 'unknown'
__commit__ = 'unknown'
__has_repo__ = False

try:
    import git
    from pathlib import Path

    try:
        r = git.Repo(Path(__file__).parents[1])
        __has_repo__ = True

        if not r.remotes:
            __repo__ = 'local'
        else:
            __repo__ = r.remotes.origin.url

        __commit__ = r.head.commit.hexsha
        if r.is_dirty():
            __commit__ += ' (dirty)'
    except git.InvalidGitRepositoryError:
        raise ImportError()
except ImportError:
    pass

try:
    from . import _dist_info as info
    assert not __has_repo__, '_dist_info should not exist when repo is in place'
    assert __version__ == info.__version__
    __repo__ = info.__repo__
    __commit__ = info.__commit__
except ImportError:
    pass

__all__ = ['__version__', '__repo__', '__commit__', '__has_repo__']
