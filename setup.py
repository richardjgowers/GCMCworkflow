import os
import re
from setuptools import setup, find_packages
import versioneer

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md'), 'r') as f:
    long_description = f.read()

setup(
    name='gcmcworkflow',
    version=versioneer.get_version(),
    long_description=long_description,

    packages=find_packages(),
    include_package_data=True,
    cmdclass=versioneer.get_cmdclass(),

    scripts = ['bin/gcmcworkflow'],
)
