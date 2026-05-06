"""Cycle 11 pilot — invariant suite over committed regression fixtures.

This file is the binary pass/fail gate for the cycle. Each invariant
test runs against both fixtures. All-green = ship. Any-red = the
failing IDs name Cycle 12's scope.

Tests are added one at a time as the invariants land. Fixture-load
smoke tests run first so a malformed fixture surfaces immediately.
"""

from __future__ import annotations

import json
import pathlib

import pytest

FIXTURES = {
    "1099b152_airline": (
        pathlib.Path(__file__).parent / "fixtures" / "run_1099b152_airline.json"
    ),
    "3b050ec5_7now": (
        pathlib.Path(__file__).parent / "fixtures" / "run_3b050ec5_7now.json"
    ),
}


@pytest.fixture(params=sorted(FIXTURES.keys()))
def fixture(request) -> dict:
    path = FIXTURES[request.param]
    if not path.exists():
        pytest.fail(
            f"Committed regression fixture missing at {path}. "
            "This file must always be present — do not delete it."
        )
    return json.loads(path.read_text())


def test_fixture_loads_with_iterations(fixture):
    assert isinstance(fixture.get("iterations"), list)
    assert len(fixture["iterations"]) >= 1
