from . import hotel
from .schemas import Availability, Source


class Evidence:
    def __init__(self):
        self.sources: dict[str, Source] = {}
        self.calls = 0
        self.availability: Availability | None = None

    def admit_call(self):
        self.calls += 1
        if self.calls > 8:
            raise RuntimeError("Tool call limit reached")


def policy_tools(db, evidence: Evidence, settings):
    async def search_policies(query: str) -> dict:
        """Find public hotel policy evidence with a short, focused query."""
        evidence.admit_call()
        try:
            passages = await hotel.search_policies(db, query)
        except Exception:
            return {"outcome": "unavailable", "passages": []}
        for passage in passages:
            source = Source.model_validate(passage["source"])
            evidence.sources[str(source.id)] = source
        return {"outcome": "ok" if passages else "no_matches", "passages": passages}

    async def get_villa(villa_slug: str) -> dict:
        """Read public details of a villa using a slug from the supplied catalogue."""
        evidence.admit_call()
        try:
            villa = await hotel.get_villa(db, villa_slug)
            return {
                "outcome": "ok" if villa else "not_found",
                "villa": villa.model_dump(mode="json") if villa else None,
            }
        except Exception:
            return {"outcome": "unavailable", "villa": None}

    async def check_availability(check_in: str, check_out: str, guests: int) -> dict:
        """Check a whole stay for exact YYYY-MM-DD dates and total guests. Never reserve rooms."""
        evidence.availability = None
        evidence.admit_call()
        try:
            result = await hotel.check_availability(db, settings, check_in, check_out, guests)
            evidence.availability = result
            return result.model_dump(mode="json")
        except ValueError:
            return {
                "outcome": "invalid_input",
                "message": "Provide exact future dates, 1–30 nights and 1–8 guests.",
            }
        except Exception:
            return {"outcome": "unavailable", "message": "Availability could not be checked."}

    return [search_policies, get_villa, check_availability]
