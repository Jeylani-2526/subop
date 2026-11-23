"""tests/test_cdc_demo_changes.py — M8W28T4.

The --loop / --interval load generator for the latency KPI's active condition.
The action and the sleep are stand-ins, so no database is needed.
"""

from __future__ import annotations

import pytest

from services.cdc.cdc_demo_changes import _parse_args, run_loop


def test_loop_runs_count_rounds_and_sleeps_only_between_them():
    calls, sleeps = [], []
    done = run_loop(lambda: calls.append(1), 3, 2.0, sleep=sleeps.append)
    assert done == 3 and len(calls) == 3
    assert sleeps == [2.0, 2.0]


def test_loop_zero_runs_until_interrupted():
    calls = []

    def action():
        calls.append(1)
        if len(calls) == 5:
            raise KeyboardInterrupt

    assert run_loop(action, 0, 0.0, sleep=lambda s: None) == 4
    assert len(calls) == 5


def test_loop_flags_parse():
    args = _parse_args(["--insert", "--loop", "0", "--interval", "2"])
    assert (args.insert, args.loop, args.interval) == (True, 0, 2.0)
    assert _parse_args(["--all"]).loop is None


@pytest.mark.parametrize(
    "argv", [["--insert", "--loop", "-1"], ["--insert", "--interval", "-2"]]
)
def test_negative_loop_values_are_rejected(argv):
    with pytest.raises(SystemExit):
        _parse_args(argv)
