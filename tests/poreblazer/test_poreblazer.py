import os
import pytest

from gcmcworkflow import PoreblazerTask


@pytest.fixture(scope='session')
def IRMOF1(IRMOF1_case_study):
    PoreblazerTask.run_poreblazer()

    yield


def test_output(IRMOF1):
    assert os.path.exists('stdout.txt')
    assert os.path.exists('stderr.txt')


def test_output2(IRMOF1):
    assert os.path.exists('psd.txt')
