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

from . import config
from . import builder
from . import eval_context
from . import yaml
from . import errors

Config = config.Config
Builder = builder.Builder
EvalContext = eval_context.EvalContext


def set_default_eval_symbols(symbols):
    return EvalContext.set_default_eval_symbols(symbols)

def get_default_eval_symbols():
    return EvalContext.get_default_eval_symbols()

def set_default_safe_flag(flag):
    return Builder.set_default_safe_flag(flag)

def get_default_safe_flag():
    return Builder.get_default_safe_flag()


from .utils import add_module_properties
from .namespace import staticproperty, namespace


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
    '__version__': staticproperty(staticmethod(_get_version)),
    '__has_repo__': staticproperty(staticmethod(_get_has_repo)),
    '__repo__': staticproperty(staticmethod(_get_repo)),
    '__commit__': staticproperty(staticmethod(_get_commit))
})
