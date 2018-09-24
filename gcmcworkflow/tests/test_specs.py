import gcmcworkflow as gcwf
import os
import pytest
import numpy as np
from numpy.testing import assert_almost_equal


@pytest.fixture
def SIMPLE_SPEC():
    return {
        'pressures': [10.0, 20.0, 30.0],
        'temperatures': [205.0, 210.0, 215.0],
        'template': os.path.join(os.getcwd(), 'here'),
        'ncycles': 1000000,
        'use_grid': False,
    }

@pytest.fixture
def GRID_SPEC(SIMPLE_SPEC):
    SIMPLE_SPEC['use_grid'] = True
    return SIMPLE_SPEC


@pytest.fixture
def spec_input_dir():
    thisdir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(thisdir, 'spec_inputs')


def test_read_spec(spec_input_dir, SIMPLE_SPEC):
    spec = gcwf.read_spec(os.path.join(spec_input_dir, 'simple_spec.yml'))

    for k, v in SIMPLE_SPEC.items():
        assert spec[k] == v


def test_read_grid_spec(spec_input_dir, GRID_SPEC):
    spec = gcwf.read_spec(os.path.join(spec_input_dir, 'grid_spec.yml'))

    for k, v in GRID_SPEC.items():
        assert spec[k] == v

def test_read_logspace_spec(spec_input_dir):
    spec = gcwf.read_spec(os.path.join(spec_input_dir, 'log_spec.yml'))


    assert spec['temperatures'] == [400.0]
    assert_almost_equal(spec['pressures'],
                        # 100^2, 100^4
                        np.logspace(2, 4, 5),
                        decimal=3)
