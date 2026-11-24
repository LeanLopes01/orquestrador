"""Lets Jarvis consult the DiceVTT RAG on the user's primary PC: current C# scripts read
from disk and the indexed documentation, with their sources. Read-only.

The local generator (AirLLM) takes minutes on that PC, too slow for a call, so the voice
agent only retrieves sources and answers from them itself."""

from __future__ import annotations

from typing import Any

from livekit.agents import RunContext, function_tool
from livekit.agents.llm import ToolError

if __package__:
    from .desktop_link import DesktopLink, DesktopLinkError
else:
    from desktop_link import DesktopLink, DesktopLinkError

SOURCE_TEXT_LIMIT = 2500
TOTAL_TEXT_LIMIT = 9000


def condense(result: dict[str, Any]) -> dict[str, Any]:
    """Keep the tool result small enough for a voice turn."""
    sources = []
    budget = TOTAL_TEXT_LIMIT
    for source in result.get("sources") or []:
        text = str(source.get("text") or "")[: min(SOURCE_TEXT_LIMIT, max(budget, 0))]
        budget -= len(text)
        provenance = source.get("provenance") or {}
        sources.append(
            {
                "id": source.get("id"),
                "kind": "script"
                if source.get("kind") == "code_pointer"
                else "documentation",
                "file": source.get("relpath"),
                "class": provenance.get("main_class"),
                "section": source.get("section"),
                "origin": provenance.get("source_url"),
                "extracted_at": provenance.get("extracted_at"),
                "read_at": source.get("read_at") or None,
                "excerpt": text,
                "excerpt_truncated": len(text) < len(str(source.get("text") or "")),
            }
        )
    return {"sources": sources, "warnings": list(result.get("warnings") or [])[:6]}


class ProjectKnowledgeTools:
    def __init__(self, link: DesktopLink | None, available: bool) -> None:
        self._link = (
            link  # Check on invocation: the PC can reconnect during this conversation.
        )

    @property
    def tools(self) -> list:
        return [self.search_project_knowledge] if self._link is not None else []

    @function_tool()
    async def search_project_knowledge(
        self, context: RunContext, question: str
    ) -> dict[str, Any]:
        """Search the DiceVTT project knowledge on the user's main PC: its Unity C# scripts,
        read from disk right now, and the indexed documentation (Unity, Steamworks, grid
        algorithms), with the source of each excerpt.

        Use it when the user asks how something works or is implemented in DiceVTT, which
        script handles something, or what the collected documentation says about Unity,
        Steam lobbies or P2P networking.

        Args:
            question: The question in the user's words; Portuguese is fine.
        """
        assert self._link is not None
        try:
            result = await self._link.call(
                "rag.retrieve",
                {"query": question[:2000], "text_limit": SOURCE_TEXT_LIMIT},
                timeout=60,
            )
        except DesktopLinkError as exc:
            raise ToolError(str(exc)) from exc
        condensed = condense(result)
        if not condensed["sources"]:
            condensed["note"] = (
                "No indexed script or document matched; say so instead of guessing."
            )
        return condensed
