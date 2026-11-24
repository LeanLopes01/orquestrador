"""Vídeos: legendas existentes via youtube-transcript-api. Sem áudio, sem tradução.

Seleção (rede) e formatação (offline) são separadas: a legenda escolhida vira um JSON
serializável no cache, nunca um objeto da biblioteca.
"""

from __future__ import annotations

import json
from typing import Any

from .config import NetworkPolicy
from .models import ExtractedDocument, RetryableFailure, SourceFailure, Status

TRANSCRIPT_SCHEMA = 1


def _session(policy: NetworkPolicy):
    import requests

    class TimeoutSession(requests.Session):
        def request(self, *args: Any, **kwargs: Any):  # type: ignore[override]
            kwargs.setdefault("timeout", policy.timeout_seconds)
            return super().request(*args, **kwargs)

    session = TimeoutSession()
    session.headers["User-Agent"] = policy.user_agent
    session.headers["Accept-Language"] = "pt-BR,pt;q=0.9,en;q=0.8"
    return session


def _map_error(exc: Exception) -> Exception:
    from youtube_transcript_api import _errors as errors

    name = type(exc).__name__
    if isinstance(exc, getattr(errors, "TranscriptsDisabled", ())):
        return SourceFailure(Status.SKIPPED, "captions_disabled", "Legendas desativadas neste vídeo.")
    if isinstance(exc, getattr(errors, "NoTranscriptFound", ())):
        return SourceFailure(Status.SKIPPED, "language_unavailable", "Sem legenda nos idiomas configurados.")
    blocked = tuple(getattr(errors, n) for n in ("RequestBlocked", "IpBlocked", "TooManyRequests") if hasattr(errors, n))
    if blocked and isinstance(exc, blocked):
        return SourceFailure(Status.FAILED, "youtube_blocked", "O YouTube bloqueou o acesso deste IP.")
    unavailable = tuple(
        getattr(errors, n)
        for n in ("VideoUnavailable", "VideoUnplayable", "AgeRestricted", "InvalidVideoId")
        if hasattr(errors, n)
    )
    if unavailable and isinstance(exc, unavailable):
        return SourceFailure(Status.SKIPPED, "video_unavailable", f"Vídeo indisponível ({name}).")
    if isinstance(exc, getattr(errors, "YouTubeRequestFailed", ())):
        return RetryableFailure("transient_network", "Falha temporária ao consultar o YouTube.")
    import requests

    if isinstance(exc, requests.RequestException):
        return RetryableFailure("transient_network", f"Falha de rede ({name}).")
    return SourceFailure(Status.FAILED, "internal_error", f"Erro inesperado da biblioteca de legendas: {name}.")


def select_and_fetch(video_id: str, languages: tuple[str, ...], policy: NetworkPolicy) -> dict[str, Any]:
    """Idioma por idioma: manual antes de automática. Retorna o JSON a cachear."""
    from youtube_transcript_api import YouTubeTranscriptApi

    try:
        api = YouTubeTranscriptApi(http_client=_session(policy))
        listing = api.list(video_id)
        chosen = None
        for language in languages:
            for finder in (listing.find_manually_created_transcript, listing.find_generated_transcript):
                try:
                    chosen = finder([language])
                    break
                except Exception as exc:  # NoTranscriptFound para esse idioma/tipo
                    if type(exc).__name__ != "NoTranscriptFound":
                        raise
            if chosen is not None:
                break
        if chosen is None:
            available = sorted({t.language_code for t in listing})
            if not available:
                raise SourceFailure(Status.SKIPPED, "no_captions", "O vídeo não tem legendas.")
            raise SourceFailure(
                Status.SKIPPED, "language_unavailable",
                f"Sem legenda em {', '.join(languages)} (disponíveis: {', '.join(available)}).",
            )
        fetched = chosen.fetch()
    except (SourceFailure, RetryableFailure):
        raise
    except Exception as exc:
        raise _map_error(exc) from None
    segments = [
        {"text": str(s.text), "start": float(s.start), "duration": float(s.duration)}
        for s in fetched.snippets
    ]
    return {
        "schema_version": TRANSCRIPT_SCHEMA,
        "video_id": video_id,
        "language_code": fetched.language_code,
        "language": getattr(fetched, "language", fetched.language_code),
        "is_generated": bool(fetched.is_generated),
        "segments": segments,
    }


def load_transcript(raw: bytes, video_id: str) -> dict[str, Any]:
    data = json.loads(raw.decode("utf-8"))
    if data.get("schema_version") != TRANSCRIPT_SCHEMA or data.get("video_id") != video_id:
        raise ValueError("legenda em cache com esquema ou vídeo diferente")
    if not isinstance(data.get("segments"), list):
        raise ValueError("legenda em cache sem segmentos")
    return data


def _stamp(seconds: float) -> str:
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def format_transcript(data: dict[str, Any], *, paragraph_seconds: float = 60.0) -> ExtractedDocument:
    """Parágrafos por janela de tempo com timestamp; remove só repetições consecutivas idênticas."""
    paragraphs: list[str] = []
    current: list[str] = []
    started: float | None = None
    previous = None
    for segment in data["segments"]:
        text = " ".join(str(segment.get("text", "")).split())
        if not text or text == previous:
            continue
        previous = text
        start = float(segment.get("start", 0.0))
        if started is None:
            started = start
        if current and start - started >= paragraph_seconds:
            paragraphs.append(f"[{_stamp(started)}] " + " ".join(current))
            current, started = [], start
        current.append(text)
    if current and started is not None:
        paragraphs.append(f"[{_stamp(started)}] " + " ".join(current))
    if not paragraphs:
        raise SourceFailure(Status.SKIPPED, "content_unavailable", "Legenda vazia.")
    caption = "automática" if data.get("is_generated") else "manual"
    body = "\n\n".join(paragraphs)
    if caption == "automática":
        body = "> Legenda automática do YouTube: pode conter erros de reconhecimento.\n\n" + body
    return ExtractedDocument(
        title=f"Vídeo {data['video_id']}",
        body=body,
        language=str(data.get("language_code") or "") or None,
        caption=caption,
    )
