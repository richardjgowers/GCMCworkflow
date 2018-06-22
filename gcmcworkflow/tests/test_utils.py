import numpy as np
import os
import pandas as pd
from pandas.testing import assert_series_equal
import pytest

import gcmcworkflow as gcwf


def test_save_csv(in_temp_dir):
    time = np.linspace(0, 100, 25)
    results = np.sin(np.linspace(0, 10, 25))

    df = pd.Series(results, index=time)
    df.name = 'density'
    df.index.name = 'time'

    gcwf.utils.save_csv(df, 'out.csv')
    assert os.path.exists('out.csv')

    new = gcwf.utils.read_csv('out.csv')
    assert_series_equal(df, new)


def test_slurp_contents(sample_input, template_contents):
    slurped = gcwf.utils.slurp_directory('template')

    assert isinstance(slurped, dict)
    for fn in template_contents:
        assert fn in slurped
        with open(os.path.join('template', fn), 'r') as fh:
            assert fh.read() == slurped[fn]


def test_dump_directory(sample_input, template_contents):
    slurped = gcwf.utils.slurp_directory('template')

    new = gcwf.utils.dump_directory('thisplace', slurped)

    assert isinstance(new, str)
    assert os.path.isdir(new)
    for fn in template_contents:
        with open(os.path.join('template', fn), 'r') as original,\
             open(os.path.join('thisplace', fn), 'r') as newone:
            assert original.read() == newone.read()

def test_pickling_type():
    def magic(a, b):
        import numpy as np

        return np.abs(a * b + 10)

    pickstr = gcwf.utils.pickle_func(magic)

    assert isinstance(pickstr, str)


def test_pickling_roundtrip():
    def magic(a, b):
        import numpy as np

        return np.abs(a * b + 10)

    pickstr = gcwf.utils.pickle_func(magic)

    new = gcwf.utils.unpickle_func(pickstr)

    assert new(1, 2) == 12

def test_gen_sim_path():
    pth = gcwf.utils.gen_sim_path(
        'hash123', 123.0, 200.0, 1, 2)

    assert pth == 'simhash123_T123.0_P200.0_gen1_v2'


@pytest.mark.parametrize('dirname', [
    'sim1234567_T12.0_P24.0_gen5_v0',
    'sim1234567_T12_P24.0_gen5_v0',
    'sim1234567_T12.0_P24_gen5_v0',
])
def test_parse_sim_path(dirname):
    res = gcwf.utils.parse_sim_path(dirname)

    assert res.simhash == '1234567'
    assert res.T == 12.0
    assert res.P == 24.0
    assert res.gen_id == 5
    assert res.parallel_id == 0
