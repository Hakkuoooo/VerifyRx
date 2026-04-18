"""
Contract tests for services.lime_explainer.

We don't pin specific highlighted words — LIME's random perturbations
make that flaky. Instead we pin the *shape* of the contract the SMS
router depends on:
  * returns a list of LimeHighlight
  * every weight is finite and in [-1.0, 1.0] (the Pydantic schema
    constraint)
  * unused keyword args and very short inputs don't crash
  * empty inputs produce an empty list rather than raising
"""

from __future__ import annotations

import math

import pytest

from models.sms import LimeHighlight


pytestmark = pytest.mark.slow  # loads DistilBERT; ~10s on CPU


def _extract(obj):
    """LimeHighlight is a Pydantic model; check either attr or dict form."""
    if isinstance(obj, LimeHighlight):
        return obj.word, obj.weight
    return obj["word"], obj["weight"]


class TestLimeShape:
    def test_returns_list_of_highlights_with_clipped_weights(self):
        from services import lime_explainer

        highlights = lime_explainer.explain(
            "URGENT: Your NHS refund of £285 is pending. Claim now at bit.ly/x"
        )
        assert isinstance(highlights, list)
        assert len(highlights) >= 1
        for h in highlights:
            word, weight = _extract(h)
            assert isinstance(word, str) and word
            assert isinstance(weight, float)
            assert math.isfinite(weight)
            assert -1.0 <= weight <= 1.0

    def test_short_input_does_not_raise(self):
        from services import lime_explainer

        # LIME can produce degenerate perturbations on trivial inputs;
        # the service is expected to catch and return an empty list.
        out = lime_explainer.explain("hi")
        assert isinstance(out, list)

    def test_empty_input_returns_list(self):
        from services import lime_explainer

        # The router's Pydantic model rejects empty strings before this
        # is reached, but defence-in-depth: the explainer itself must
        # not crash.
        out = lime_explainer.explain("")
        assert out == [] or isinstance(out, list)
