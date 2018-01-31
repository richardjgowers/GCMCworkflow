import os
import pandas as pd
import pytest
import subprocess

import gcmcworkflow as gcwf


def test_binary_working(sample_input):
    # check that running a raspa simulation even works..
    # 'template' is ready to run
    os.chdir('template')

    assert os.path.exists('run.sh')
    p = subprocess.run('./run.sh',
                       check=True,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)

    assert os.path.exists('Output')


def test_simple_parser(successful_raspa):
    res = gcwf.raspatools.parse_results_simple(successful_raspa)

    assert res == 18.4858270635


def test_parser_name(successful_raspa):
    res = gcwf.raspatools.parse_results(successful_raspa)
    assert isinstance(res, pd.Series)
    assert res.name == 'density'
    assert res.index.name == 'time'


def test_parser(successful_raspa):
    res = gcwf.raspatools.parse_results(successful_raspa)

    assert isinstance(res, pd.Series)
    # number of results, from `grep '^Current cyc' * | wc -l`
    assert len(res) == 101
    # from visual inspection:
    assert res.iloc[0] == pytest.approx(2.9830315349)  # 147 mol/uc
    assert res.iloc[1] == pytest.approx(2.6380550989)  # 130
    assert res.iloc[-2] == pytest.approx(2.8815678772)  # 142
    assert res.iloc[-1] == pytest.approx(2.6989332935)  # 133

    assert res.index[0] == 0
    assert res.index[1] == 673
    assert res.index[-2] == 66627
    assert res.index[-1] == 67300

    # regression test
    assert res.mean() == pytest.approx(3.0010234057, abs=0.02)
