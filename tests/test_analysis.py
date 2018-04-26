import pytest

import gcmcworkflow as gcwf
from gcmcworkflow import analysis


def test_rsp_equil(rsp_ts):
    assert analysis.find_eq(rsp_ts) == 0

def test_dlm_equil(dlm_ts):
    assert analysis.find_eq(dlm_ts) == 1718000

def test_twh_equil(twh_ts):
    assert analysis.find_eq(twh_ts) == 130791

def test_rsp_g(rsp_ts):
    eq = analysis.find_eq(rsp_ts)
    assert analysis.find_g(rsp_ts.loc[eq:]) == 28

def test_dlm_g(dlm_ts):
    eq = analysis.find_eq(dlm_ts)
    assert analysis.find_g(dlm_ts.loc[eq:]) == 470806

def test_twh_g(twh_ts):
    eq = analysis.find_eq(twh_ts)
    assert analysis.find_g(twh_ts.loc[eq:]) == 38997
