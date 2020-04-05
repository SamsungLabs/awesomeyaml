#!/usr/bin/env python

from setuptools import setup, find_packages
from setuptools.command.install import install

import importlib.util
from pathlib import Path

package_name = 'yamlfig'

version_file = Path(__file__).parent.joinpath(package_name, 'version.py')
spec = importlib.util.spec_from_file_location('{}.version'.format(package_name), version_file)
package_version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package_version)

class build_maybe_inplace(install):
    def run(self):
        _dist_file = version_file.parent.joinpath('_dist_info.py')
        assert not _dist_file.exists()
        #if not _dist_file.exists():
        with open(_dist_file, 'w') as df:
            df.write('\n'.join(map(lambda attr_name: attr_name+' = '+repr(getattr(package_version, attr_name)), package_version.__all__)) + '\n')

        return super().run()


setup(name='YamlFig',
      version=package_version.version,
      description='Config-building Utilities Using YAML',
      author='Łukasz Dudziak (SAIC-Cambridge, On-Device Team)',
      author_email='l.dudziak@samsung.com',
      url='https://github.sec.samsung.net/l-dudziak/yamlfig',
      download_url='https://github.sec.samsung.net/l-dudziak/yamlfig',
      python_requires='>=3.6.0',
      install_requires=[
          'pyyaml'
      ],
      packages=find_packages(where='.', exclude=['tests']),
      package_dir={ '': '.' },
      cmdclass={
          'install': build_maybe_inplace
      }
)
