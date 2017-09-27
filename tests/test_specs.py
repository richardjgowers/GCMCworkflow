import gcmcworkflow as gcwf
import os
import pytest

@pytest.fixture
def REQUIRED_FIELDS():
    # all required fields and their default value
    return [
        ('pressures', [None]),
        ('temperatures', [None]),
        ('ncycles', None),
        ('template', None),
    ]
             

@pytest.fixture
def SIMPLE_SPEC():
    return {
        'pressures': [10.0, 20.0, 30.0],
        'temperatures': [205.0, 210.0, 215.0],
        'template': os.path.join(os.getcwd(), 'here'),
        'ncycles': 1000000
    }


@pytest.fixture
def spec_input_dir():
    thisdir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(thisdir, 'spec_inputs')

def test_read_spec(spec_input_dir, REQUIRED_FIELDS, SIMPLE_SPEC):
    spec = gcwf.read_spec(os.path.join(spec_input_dir, 'simple_spec.yml'))

    for k, d in REQUIRED_FIELDS:
        assert k in spec
    for k, v in SIMPLE_SPEC.items():
        assert spec[k] == v

