"""Tests Tournament task"""

from unittest import mock
import pytest
import random

from gcmcworkflow.genetics import Tournament


def test_nonrepeating():
    parents = [
        (1, 11),
        (2, 12),
        (3, 13),
        (4, 14),
    ]

    def sequence():
        # first candidate [0]
        yield parents[0], parents[1]
        # rerolled
        yield parents[0], parents[1]
        # second candidate [2]
        yield parents[2], parents[3]
        # third candidate [0]
        yield parents[0], parents[2]
        # fourth [1]
        yield parents[1], parents[3]

    with mock.patch('random.sample') as rs:
        rs.side_effect = sequence()

        ret = Tournament.tournament(parents)

    assert rs.call_count == 5
    assert len(ret) == len(parents)
    assert ret[0] == parents[0][0]
    assert ret[1] == parents[2][0]
    assert ret[2] == parents[0][0]
    assert ret[3] == parents[1][0]
