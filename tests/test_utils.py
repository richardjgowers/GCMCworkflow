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
