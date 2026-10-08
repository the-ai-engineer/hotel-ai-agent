from pathlib import Path

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from app import agent
from app.settings import Settings


class ScriptedModel(BaseLlm):
    """A deterministic model exercises the real ADK tool dispatch, not inference quality."""

    step: int = 0
    saw_history: bool = False

    async def generate_content_async(self, llm_request, stream=False):
        prompt = (Path(__file__).resolve().parents[1] / "prompts" / "concierge.md").read_text(encoding="utf-8")
        assert str(llm_request.config.system_instruction).startswith(prompt + "\n")
        assert (
            "Current property date: 2026-10-06 (Tuesday), timezone Asia/Makassar"
            in str(llm_request.config.system_instruction)
        )
        self.saw_history |= any(
            "Previous guest question" in (part.text or "")
            for content in llm_request.contents
            for part in content.parts or []
        )
        if self.step == 0:
            part = types.Part(
                function_call=types.FunctionCall(name="list_documents", args={})
            )
        elif self.step == 1:
            part = types.Part(
                function_call=types.FunctionCall(
                    name="read_document",
                    args={"document_id": "dining-policy", "revision": 2},
                )
            )
        else:
            evidence = [
                part.function_response.response
                for content in llm_request.contents
                for part in content.parts or []
                if part.function_response
                and part.function_response.name == "read_document"
            ]
            assert evidence and "body" in evidence[-1]
            part = types.Part(text="Deterministic final answer")
        self.step += 1
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


async def test_actual_adk_tool_dispatch_and_isolated_working_history(pool, monkeypatch):
    monkeypatch.setattr(
        agent,
        "current_date_context",
        lambda: "Current property date: 2026-10-06 (Tuesday), timezone Asia/Makassar",
    )
    models = []

    def fake_gemini(**kwargs):
        model = ScriptedModel(model="test")
        models.append(model)
        return model

    monkeypatch.setattr(agent, "Gemini", fake_gemini)
    settings = Settings(database_url="postgresql://unused")
    events = [
        event
        async for event in agent.answer(
            pool,
            settings,
            [{"question": "Previous guest question", "answer": "Previous answer"}],
            "Current question",
        )
    ]
    assert events[-1]["answer"] == "Deterministic final answer"
    assert events[-1]["sources"][0]["url"] == "/api/sources/dining-policy/2"
    assert models[0].saw_history
    await anext(agent.answer(pool, settings, [], "Another guest"))
    assert not models[1].saw_history


def test_weekend_context_rolls_across_week_and_year():
    from datetime import date

    for today, friday, sunday in [
        (date(2026, 10, 7), "2026-10-09", "2026-10-11"),
        (date(2026, 10, 9), "2026-10-16", "2026-10-18"),
        (date(2026, 10, 11), "2026-10-16", "2026-10-18"),
        (date(2026, 12, 31), "2027-01-01", "2027-01-03"),
    ]:
        context = agent.current_date_context(today)
        assert f"check-in {friday}, check-out {sunday}" in context
        assert "not booking consent" in context
