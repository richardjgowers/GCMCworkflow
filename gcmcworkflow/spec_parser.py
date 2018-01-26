import yaml
import os

from hydraspa import util


def generate_spec():
    """Create a blank specfile"""
    with open('workflow_spec.yml', 'w') as out:
        out.write('name:                    # name of the workflow, must be unique on launchpad\n')
        out.write('template:                # path to directory to use as template\n')
        out.write('workdir:                 # path to store results in\n')
        out.write('pressures: [1k, 2k, 3k]  # list of pressures to run, can use k/M suffix \n')
        out.write('temperatures: [1, 2, 3]  # list of temperatures to run\n')
        out.write('nparallel: 1             # how many replicas of each T&P to run\n')
        out.write('ncycles:                 # length of each simulation\n')


def read_spec(path):
    """Read a spec file, return a dict of what it means

    output dict:
    {
    template: absolute path to template to use
    name: name of workflow
    pressures: list of pressures as floats, or [None]
    temperatures: list of temps as floats, or [None]
    ncycles: int of ncycles or None
    nparallel: int or 1
    }
    """
    with open(path, 'r') as inf:
        raw = yaml.load(inf)
    # convert all fields to correct types
    # if not present, replace with ``None``
    output = {}
    output['template'] = os.path.abspath(raw['template'])
    try:
        output['name'] = raw['name']
    except KeyError:
        output['name'] = 'GCMCWorkflow'
    try:
        workdir = raw['workdir']
    except KeyError:
        output['workdir'] = ''
    else:
        output['workdir'] = os.path.abspath(workdir)

    try:
        output['pressures'] = [util.conv_to_number(str(v), float)
                               for v in raw['pressures']]
    except KeyError:
        output['pressures'] = [None]
    try:
        output['temperatures'] = [float(v) for v in raw['temperatures']]
    except KeyError:
        output['temperatures'] = [None]
    try:
        output['nparallel'] = int(raw['nparallel'])
    except KeyError:
        output['nparallel'] = 1
    try:
        output['ncycles'] = int(raw['ncycles'])
    except KeyError:
        output['ncycles'] = None

    return output
