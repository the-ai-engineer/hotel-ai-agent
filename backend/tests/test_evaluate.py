import pytest

from evaluate import EvaluationTools, availability_calls, failures


def test_rejects_disclosure_even_with_no_cards():
    result = {
        "answer": "I am Gemini 3.7 Flash, developed by Google.",
        "availability": None,
    }
    assert failures(result, {"no_model_identity": True}) == [
        "Disclosed or repeated model/provider identity"
    ]
    assert (
        failures(
            {"answer": "I help with hotel stays."},
            {"no_model_identity": True, "contains_any": [["hotel", "concierge"]]},
        )
        == []
    )


def test_rejects_premature_lookup_even_when_it_returns_no_cards():
    result = {
        "answer": "What arrival date?",
        "availability": None,
        "availability_calls": [
            {"check_in": "2026-10-14", "check_out": "2026-10-17", "guests": 2}
        ],
    }
    assert failures(
        result, {"no_availability": True, "no_availability_calls": True}
    ) == ["Availability tool called before dates and guests were agreed"]


@pytest.mark.parametrize(
    "answer", ["Please give your check-in date.", "What arrival date?"]
)
def test_clarification_accepts_equivalent_wording(answer):
    assert (
        failures({"answer": answer}, {"contains_any": [["arrival", "check-in"]]}) == []
    )
    assert failures(
        {"answer": "Both villas are available."},
        {"contains_any": [["arrival", "check-in"]]},
    )


async def test_eval_records_failed_availability_attempt(monkeypatch):
    from app import inventory

    async def invalid_search(*args):
        return {"error": "invalid_dates"}

    monkeypatch.setattr(inventory, "check_availability", invalid_search)
    calls = []
    token = availability_calls.set(calls)
    try:
        tools = EvaluationTools(None)
        result = await tools.check_availability("invalid", "invalid", 2)
        assert result == {"error": "invalid_dates"}
        assert tools.availability is None
        assert calls == [{"check_in": "invalid", "check_out": "invalid", "guests": 2}]
    finally:
        availability_calls.reset(token)


def test_guest_count_must_match_conversation_context():
    result = {"answer": "Available", "availability": {"guests": 4}}
    assert failures(result, {"guests": 2}) == ["guests: expected 2, got 4"]
    assert failures(result, {"guests": 4}) == []
