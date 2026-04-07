"""Strands chat history helpers."""

from smart_report_analyst.service.strands.utils import (
    chainlit_history_to_strands_messages,
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


def test_chainlit_history_to_strands_messages():
    h = [{"role": "user", "content": "hi"}, {"role": "system", "content": "x"}]
    m = chainlit_history_to_strands_messages(h)
    assert len(m) == 1
    assert m[0]["role"] == "user"
    assert m[0]["content"] == [{"text": "hi"}]
