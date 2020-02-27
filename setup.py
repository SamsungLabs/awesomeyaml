#!/usr/bin/env python

from setuptools import setup, find_packages

import os
import importlib.util
from pathlib import Path

version_file = Path(__file__).parent.joinpath('src', 'yamlfig', 'version.py')
_dist_file = version_file.parent.joinpath('_dist_info.py')

spec = importlib.util.spec_from_file_location('yamlfig_version', version_file)
yamlfig_version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(yamlfig_version)

if not _dist_file.exists():
    with open(_dist_file, 'w') as df:
        df.write('\n'.join(map(lambda dname: dname+' = '+repr(getattr(yamlfig_version, dname)), yamlfig_version.__all__)) + '\n')

setup(name='YamlFig',
      version=yamlfig_version.__version__,
      description='Config-building Utilities Using YAML',
      author='Łukasz Dudziak (SAIC-Cambridge, On-Device Team)',
      author_email='l.dudziak@samsung.com',
      url='https://github.sec.samsung.net/l-dudziak/yamlfig',
      download_url='https://github.sec.samsung.net/l-dudziak/yamlfig',
      python_requires='>=3.6.0',
      install_requires=[
          'pyyaml'
      ],
      packages=find_packages(where='src'),
      package_dir={ '': 'src' }
)
