import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.events import Event
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.tools import HotelTools

INSTRUCTION = (Path(__file__).resolve().parents[1] / "prompts" / "concierge.md").read_text(
    encoding="utf-8"
)


def current_date_context(today=None):
    today = today or datetime.now(ZoneInfo("Asia/Makassar")).date()
    friday = today + timedelta(days=(4 - today.weekday()) % 7 or 7)
    sunday = friday + timedelta(days=2)
    return (
        f"Current property date: {today:%Y-%m-%d} ({today:%A}), timezone Asia/Makassar. "
        "Use this for relative dates, not training knowledge. "
        f"Default next weekend: check-in {friday:%Y-%m-%d}, check-out {sunday:%Y-%m-%d} "
        "(Friday to Sunday, two nights). This is a stated search assumption, not booking consent."
    )


async def answer(pool, settings, history, question, guest=None):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
    os.environ["GOOGLE_CLOUD_PROJECT"] = settings.google_cloud_project
    os.environ["GOOGLE_CLOUD_LOCATION"] = settings.google_cloud_location
    tools = HotelTools(pool, guest)
    agent = Agent(
        name="sanctuary_concierge",
        model=Gemini(
            model=settings.gemini_model,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
        instruction=INSTRUCTION + "\n" + current_date_context(),
        tools=[
            tools.list_documents,
            tools.read_document,
            tools.get_villa,
            tools.check_availability,
            tools.lookup_booking,
            tools.prepare_hotel_request,
        ],
        generate_content_config=types.GenerateContentConfig(
            max_output_tokens=2048,
            thinking_config=types.ThinkingConfig(thinking_level="LOW"),
        ),
    )
    service = InMemorySessionService()
    session = await service.create_session(app_name="hotel", user_id="guest")
    for turn in history:
        for author, role, text in [
            ("user", "user", turn["question"]),
            ("sanctuary_concierge", "model", turn["answer"]),
        ]:
            await service.append_event(
                session,
                Event(
                    invocation_id=str(uuid.uuid4()),
                    author=author,
                    content=types.Content(role=role, parts=[types.Part(text=text)]),
                ),
            )
    runner = Runner(agent=agent, app_name="hotel", session_service=service)
    final = ""
    async for event in runner.run_async(
        user_id="guest",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=question)]),
        run_config=RunConfig(streaming_mode=StreamingMode.SSE, max_llm_calls=8),
    ):
        if event.error_code:
            raise RuntimeError("Model invocation failed")
        text = (
            "".join(
                part.text
                for part in (event.content.parts or [])
                if part.text and not part.thought
            )
            if event.content
            else ""
        )
        if event.partial and text:
            yield {"type": "text", "text": text}
        if event.is_final_response() and text:
            final = text
    if not final:
        raise RuntimeError("No final model answer")
    yield {
        "type": "result",
        "answer": final,
        "sources": list(tools.sources.values()),
        "availability": tools.availability,
        "hotel_request": tools.hotel_request,
    }
