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

version = '1.1.1'
repo = 'unknown'
commit = 'unknown'
has_repo = False

try:
    import git
    from pathlib import Path

    try:
        r = git.Repo(Path(__file__).parents[1])
        has_repo = True

        if not r.remotes:
            repo = 'local'
        else:
            repo = r.remotes.origin.url

        commit = r.head.commit.hexsha
        status = []
        if r.is_dirty():
            status.append('dirty')
        if r.untracked_files:
            status.append(f'+{len(r.untracked_files)} untracked')
        if status:
            commit += f' ({",".join(status)})'
    except git.InvalidGitRepositoryError:
        raise ImportError()
except ImportError:
    pass

try:
    import importlib
    from pathlib import Path
    _dist_info_file = Path(__file__).parent.joinpath('_dist_info.py')
    if _dist_info_file.exists():
        _spec = importlib.util.spec_from_file_location('_dist_info', _dist_info_file)
        _dist_info = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_dist_info)
        assert not has_repo, '_dist_info should not exist when repo is in place'
        assert version == _dist_info.version
        repo = _dist_info.repo
        commit = _dist_info.commit
except (ImportError, SystemError):
    pass


def info():
    g = globals()
    return { k: g[k] for k in __all__ }


__all__ = ['version', 'repo', 'commit', 'has_repo']
