from scripts.package_audio import group_in_order


def item(identifier, duration):
    return {"id": identifier, "after": {"duration_seconds": duration}}


def test_grouping_preserves_order_and_splits_at_limit():
    groups, overflow = group_in_order([item(1, 3000), item(2, 2400), item(3, 10)], 5400)
    assert [[entry["id"] for entry in group] for group in groups] == [[1, 2], [3]]
    assert overflow == []


def test_single_package_moves_excess_to_overflow():
    groups, overflow = group_in_order([item(1, 5000), item(2, 500), item(3, 300)], 5400, True)
    assert [[entry["id"] for entry in group] for group in groups] == [[1, 3]]
    assert [entry["id"] for entry in overflow] == [2]


def test_single_item_over_limit_is_always_overflow():
    groups, overflow = group_in_order([item(1, 5401), item(2, 2)], 5400)
    assert [[entry["id"] for entry in group] for group in groups] == [[2]]
    assert [entry["id"] for entry in overflow] == [1]

