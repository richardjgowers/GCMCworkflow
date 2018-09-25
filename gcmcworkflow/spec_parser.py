from collections import namedtuple
import itertools
import yaml
import re
import numpy as np
import os

from . import utils

Condition = namedtuple('Condition', ['temperature',
                                     'pressures',
                                     'adaptive'])


def generate_spec():
    """Create a blank specfile"""
    with open('workflow_spec.yml', 'w') as out:
        out.write('name:                    # name of the workflow, must be unique on launchpad\n')
        out.write('template:                # path to directory to use as template\n')
        out.write('workdir:                 # path to store results in\n')
        out.write('pressures: [1k, 2k, 3k]  # list of pressures to run, can use k/M suffix \n')
        out.write('temperatures: [1, 2, 3]  # list of temperatures to run\n')


def read_spec(path):
    """Read a spec file, return a dict of what it means

    output dict:
    {
      template: absolute path to template to use
      name: name of workflow
      ncycles: int of ncycles or None
      nparallel: int or 1

      pressures: list of pressures as floats, or [None]
      temperatures: list of temps as floats, or [None]
    }
    """
    # Read raw yaml, then process it slightly...
    with open(path, 'r') as inf:
        raw = yaml.load(inf)

    output = {}
    # General Workflow settings
    if raw['template'].startswith('Hydraspa('):
        # special case for Hydraspa template creation
        output['template'] = raw['template']
    else:
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

    # Simulation conditions
    output['conditions'] = []
    for entry in raw['conditions']:
        # TODO: alias temperature/temperatures to T?
        # Validate each condition
        try:
            temperatures = entry['temperatures']
            pressures = entry['pressures']
        except KeyError:
            raise ValueError("Each condition must specify both T & P")

        if not isinstance(temperatures, list):
            temperatures = [temperatures]
        if not isinstance(pressures, list):
            pressures = [pressures]
        # Multiply out condition
        # convert to [(T1, Prange, nadaptive), (T2, Prange, nadaptive), etc]
        for T, P_entry in itertools.product(temperatures, pressures):
            T = float(T)
            if str(P_entry).startswith(('linspace', 'logspace', 'adaptive')):
                adaptive = P_entry.startswith('adaptive')

                # deal with range of values
                start, stop, number = re.match(utils.RANGE_PAT, P_entry).groups()
                start, stop = utils.conv_to_number(start), utils.conv_to_number(stop)
                number = int(number)
                if adaptive:
                    # half now, half after seeing results
                    number //= 2
                    adaptive = number
                else:
                    adaptive = 0

                # grab function to generate pressure values
                func = (np.linspace if P_entry.startswith('lin')
                        else utils.logspace)
                P = func(start, stop, number)
            else:
                P = [utils.conv_to_number(P_entry)]
                adaptive = 0

            output['conditions'].append((T, P, adaptive))

    try:
        output['nparallel'] = int(raw['nparallel'])
    except KeyError:
        output['nparallel'] = 1

    try:
        output['ncycles'] = int(raw['ncycles'])
    except KeyError:
        output['ncycles'] = None

    try:
        output['max_iterations'] = int(raw['max_iterations'])
    except KeyError:
        pass

    # kinda weird, but sometimes bool sometimes string, so force to string
    output['use_grid'] = str(raw.get('use_grid', False)).lower().startswith('t')

    return output
