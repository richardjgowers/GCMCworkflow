import os
from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst'), 'r') as f:
    long_description = f.read()

setup(
    name='GCMCworkflow',
    version='0.0.1',
    long_description=long_description,

    packages=find_packages(),
    include_package_data=True,

    scripts = ['bin/make_workflow.py'],
)
