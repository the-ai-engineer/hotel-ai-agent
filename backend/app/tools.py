from . import hotel
from .schemas import Source


class Evidence:
    def __init__(self):
        self.sources: dict[str, Source] = {}
        self.calls = 0

    def admit_call(self):
        self.calls += 1
        if self.calls > 8:
            raise RuntimeError("Tool call limit reached")


def policy_tools(db, evidence: Evidence):
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

    return [search_policies]
