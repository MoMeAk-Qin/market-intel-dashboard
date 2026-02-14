from __future__ import annotations

import random

import pytest

from app.services.seed import _pick, _pick_many


def test_pick_returns_item_from_sequence() -> None:
    rng = random.Random(7)
    items = ["US", "HK", "FX"]
    picked = _pick(rng, items)
    assert picked in items


def test_pick_many_returns_unique_values_within_bounds() -> None:
    rng = random.Random(11)
    items = ["A", "B", "C"]
    picked = _pick_many(rng, items, 1, 3)
    assert 1 <= len(picked) <= 3
    assert len(set(picked)) == len(picked)
    assert all(item in items for item in picked)


def test_pick_rejects_empty_sequence() -> None:
    rng = random.Random(3)
    with pytest.raises(ValueError, match="items must not be empty"):
        _pick(rng, [])
