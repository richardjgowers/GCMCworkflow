"""Tests for genetic algorithm components


"""
from unittest import mock
import pytest
import random



from gcmcworkflow.genetics import VaryCandidates


@pytest.fixture
def varycls():
    return VaryCandidates(
        **VaryCandidates.default_params,
        bounds=((10.0, 30.0),)
    )



@pytest.mark.parametrize('val,lo,hi,exp', [
    (10, 5, 20, 10),
    (22, 5, 20, 20),
    (4, 5, 20, 5),
])
def test_clamp(val, lo, hi, exp, varycls):
    assert varycls.clamp(val, lo, hi) == exp


def test_crossover_return_types(varycls):
    mum = (15.0,)
    dad = (25.0,)
    ret = varycls.blend_crossover([mum, dad])

    assert len(ret) == 2
    assert len(ret[0]) == 1
    assert type(ret[0]) == tuple


@pytest.mark.parametrize('randseq,mum,dad,child1,child2', [
    # randseq - (probability of performing crossover,
    #            child1 position, child2 position)
    ((0.0, 0.0, 0.0), (15.0,), (25.0,), (14.0,), (14.0,)),
    ((0.0, 1.0, 0.0), (15.0,), (25.0,), (26.0,), (14.0,)),
    ((0.0, 1.0, 0.5), (15.0,), (25.0,), (26.0,), (20.0,)),
    ((1.0, 1.0, 1.0), (15.0,), (25.0,), (15.0,), (25.0,)),  # check no crossover
])
@mock.patch('random.random')
def test_crossover(mp, randseq, mum, dad, child1, child2, varycls):
    mp.side_effect = (val for val in randseq)

    ret = varycls.blend_crossover([mum, dad])

    assert ret[0] == child1
    assert ret[1] == child2


@pytest.mark.parametrize('randseq,gaussseq,candidates,exp', [
    # rolls for EACH candidate
    # case1: no mutation applied
    ((1.0, 1.0, 1.0), (None,), [(11.0,), (12.0,), (13.0,)], [(11.0,), (12.0,), (13.0,)]),
    # gauss tries to add 10 each time, but only first time happens
    ((0.0, 1.0), (10.0, 10.0), [(10.0,), (15.0,)], [(20.0,), (15.0,)]),
])
@mock.patch('random.random')
@mock.patch('random.gauss')
def test_mutation(mockgauss, mockrand,
                  randseq, gaussseq, candidates, exp, varycls):
    mockrand.side_effect = (val for val in randseq)
    mockgauss.side_effect = (val for val in gaussseq)

    new = varycls.gaussian_mutation(candidates)
    assert new == exp
