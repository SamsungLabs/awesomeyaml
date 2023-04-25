# Copyright 2023 Samsung Electronics Co., Ltd.
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

import unittest

from .utils import setUpModule
from awesomeyaml.config import Config
from awesomeyaml.nodes import ConfigList
from awesomeyaml.yaml import make_node, add_constructor
from awesomeyaml import namespace

import yaml


class CustomNode(ConfigList):
    @namespace('ayns')
    def on_evaluate_impl(self, path, ctx):
        ctx.user_data.setdefault('custom', set()).add(str(path))
        return super().ayns.on_evaluate_impl(path, ctx)


def custom_constructor(loader, node):
    return make_node(loader, node, node_type=CustomNode, data_arg_name='value')


add_constructor('!custom', custom_constructor)


class ExternalDumpTest(unittest.TestCase):
    def test_simple(self):
        cfg = Config.build('''
        foo: 12
        ''')
        cfg2 = yaml.dump(cfg, default_flow_style=True).strip()
        self.assertEqual(cfg2, '{foo: 12}')

    def test_javiers_case(self):
        cfg = Config.build('''
        subcfg:
            bar: test
            params: !null
        foo:
            huu: !custom [1,12]
        ''')
        self.assertSetEqual(cfg.ayns.user_data.custom, { 'foo.huu' })

        params = {}
        for custom in cfg.ayns.user_data.custom:
            node = cfg.ayns.get_node(custom)
            params[custom] = { 'values': node }

        cfg.subcfg.params = params
        cfg2 = yaml.dump(cfg.subcfg, default_flow_style=True).strip()
        self.assertEqual(cfg2, '{bar: test, params: {foo.huu: {values: [1, 12]}}}')


if __name__ == '__main__':
    unittest.main()
