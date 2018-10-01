import gcmcworkflow as gcwf
import itertools
import os
import pytest
import numpy as np
from numpy.testing import assert_almost_equal


@pytest.fixture(params=[
    {'grid': False, 'fn': 'simple_spec.yml'},
    {'grid': True, 'fn': 'grid_spec.yml'}])
def SIMPLE_SPEC(request, spec_input_dir):
    spec = request.param
    ref =  {
        'temperatures': [205.0, 210.0, 215.0],
        'pressures': [10.0, 20.0, 30.0],
        'template': os.path.join(os.getcwd(), 'here'),
        'ncycles': 1000000,
        'use_grid': spec['grid'],
    }
    fn = os.path.join(spec_input_dir, spec['fn'])

    return fn, ref


@pytest.fixture
def spec_input_dir():
    thisdir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(thisdir, 'spec_inputs')


def test_read_spec(spec_input_dir, SIMPLE_SPEC):
    FN, REF_SPEC = SIMPLE_SPEC
    spec = gcwf.read_spec(FN)

    for k in ('template', 'ncycles', 'use_grid'):
        assert spec[k] == REF_SPEC[k]
    assert len(spec['conditions']) == 9
    ref = sorted((T, [P], 0) for T, P in itertools.product(
        REF_SPEC['temperatures'], REF_SPEC['pressures']))
    assert sorted(spec['conditions']) == ref


def test_read_logspace_spec(spec_input_dir):
    spec = gcwf.read_spec(os.path.join(spec_input_dir, 'log_spec.yml'))

    assert len(spec['conditions']) == 1
    c = spec['conditions'][0]
    assert c[0] == 400.0
    assert c[-1] == 0
    assert_almost_equal(c[1],
                        # 100^2, 100^4
                        np.logspace(2, 4, 5),
                        decimal=3)

def test_adaptive_spec(spec_input_dir):
    spec = gcwf.read_spec(os.path.join(spec_input_dir, 'adaptive_spec.yml'))

    assert len(spec['conditions']) == 2
    T1, T2 = sorted(spec['conditions'])

    assert T1[0] == 200.0
    assert len(T1[1]) == 5
    assert T1[2] == 5

    assert T2[0] == 300.0
    assert len(T2[1]) == 5
    assert T2[2] == 5
