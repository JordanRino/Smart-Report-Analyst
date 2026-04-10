"""Strands chat history helpers."""

from smart_report_analyst.service.strands.utils import (
    split_history_for_turn,
)


def test_split_history_for_turn():
    h = [
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
    ]
    prior, cur = split_history_for_turn(h)
    assert prior == h[:-1]
    assert cur == "c"

