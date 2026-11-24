import json

from conftest import FIXTURES

from rag_ingestion.acquisition import HttpResponse, now_iso
from rag_ingestion.events import EventLog
from rag_ingestion.models import RawSource, RetryableFailure, SourceFailure, Status
from rag_ingestion.pipeline import Pipeline
from rag_ingestion.repository import Repository
from rag_ingestion.storage import sha256_file

ARTICLE = (FIXTURES / "artigo.html").read_bytes()


class FakeWeb:
    def __init__(self, plan):
        self.plan = plan  # url -> lista de respostas/erros em ordem
        self.calls: list[str] = []

    def __call__(self, url, policy, deadline):
        self.calls.append(url)
        outcome = self.plan[url].pop(0) if len(self.plan[url]) > 1 else self.plan[url][0]
        if isinstance(outcome, Exception):
            raise outcome
        return HttpResponse(200, url, "text/html", "utf-8", outcome, now_iso(), [])


def transcript(video_id, languages, policy):
    return {"schema_version": 1, "video_id": video_id, "language_code": "pt", "language": "Português",
            "is_generated": False, "segments": [{"text": "conteúdo da legenda de teste", "start": 1.0, "duration": 2.0}]}


def make(config, web, **kw):
    repo = Repository(config.state_path)
    return Pipeline(config, repo, EventLog(config.log_path), fetch_page=web, fetch_transcript=kw.get("yt", transcript),
                    sleep=lambda s: None), repo


def run(pipeline, repo, urls, mode="online"):
    batch = repo.create_batch("dicevtt", mode, [RawSource(u) for u in urls])
    return pipeline.run_batch(batch)


def test_mixed_batch_isolates_failures(config):
    web = FakeWeb({
        "https://ok.example/doc": [ARTICLE],
        "https://blocked.example/": [SourceFailure(Status.FAILED, "access_blocked", "HTTP 403")],
    })
    pipeline, repo = make(config, web)
    report = run(pipeline, repo, ["https://ok.example/doc", "https://blocked.example/", "nao-e-url",
                                  "https://ok.example/doc#outra-ancora", "https://www.youtube.com/watch?v=tywt9tOubEY"])
    by = {i["raw_url"]: i for i in report["items"]}
    assert by["https://ok.example/doc"]["status"] == "completed"
    assert by["https://blocked.example/"]["result"]["reason_code"] == "access_blocked"
    assert web.calls.count("https://blocked.example/") == 1  # 403 sem retry
    assert by["nao-e-url"]["result"]["reason_code"] == "invalid_url"
    assert by["https://ok.example/doc#outra-ancora"]["result"]["reason_code"] == "duplicate"
    assert by["https://www.youtube.com/watch?v=tywt9tOubEY"]["status"] == "completed"
    assert report["state"] == "completed_with_errors" and report["counts"]["completed"] == 2
    files = sorted(p.name for p in config.output_root.iterdir())
    assert files[-1] == "video-tywt9tOubEY.md" and files[0].startswith("artigo-")
    text = (config.output_root / files[0]).read_text(encoding="utf-8")
    assert text.startswith("Fonte: https://ok.example/doc\nTipo: Artigo\nData de Extração: ")
    manifest = json.loads((config.manifests_root / f"{report['id']}.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "rag-ingestion-report/v1"


def test_transient_errors_retry_then_succeed(config):
    web = FakeWeb({"https://flaky.example/": [RetryableFailure("transient_network", "HTTP 503"), ARTICLE]})
    pipeline, repo = make(config, web)
    report = run(pipeline, repo, ["https://flaky.example/"])
    assert report["items"][0]["status"] == "completed" and report["items"][0]["result"]["attempts"] == 2


def test_retry_after_above_budget_is_not_cut_short(config):
    web = FakeWeb({"https://slow.example/": [RetryableFailure("rate_limited", "HTTP 429", retry_after=3600)]})
    pipeline, repo = make(config, web)
    result = run(pipeline, repo, ["https://slow.example/"])["items"][0]["result"]
    assert result["reason_code"] == "retry_budget_exceeded"
    assert any(w.startswith("retry_after_at=") for w in result["warnings"])
    assert web.calls == ["https://slow.example/"]


def test_offline_uses_only_cache_and_is_idempotent(config):
    web = FakeWeb({"https://ok.example/doc": [ARTICLE]})
    pipeline, repo = make(config, web)
    run(pipeline, repo, ["https://ok.example/doc"])
    document = next(config.output_root.glob("artigo-*.md"))
    first_hash = sha256_file(document)

    def no_network(*args, **kwargs):
        raise AssertionError("modo offline não pode acessar a rede")

    offline, repo2 = make(config, no_network, yt=no_network)
    report = run(offline, repo2, ["https://ok.example/doc", "https://never.example/"], mode="offline")
    by = {i["raw_url"]: i["result"] for i in report["items"]}
    assert by["https://ok.example/doc"]["noop"] is True  # mesmo cache e opções: preserva data/hash
    assert sha256_file(document) == first_hash
    assert by["https://never.example/"]["reason_code"] == "offline_cache_miss"


def test_failed_recollection_preserves_previous_document(config):
    web = FakeWeb({"https://ok.example/doc": [ARTICLE]})
    pipeline, repo = make(config, web)
    run(pipeline, repo, ["https://ok.example/doc"])
    document = next(config.output_root.glob("artigo-*.md"))
    before = document.read_bytes()
    web.plan["https://ok.example/doc"] = [(FIXTURES / "vazio.html").read_bytes()]
    result = run(pipeline, repo, ["https://ok.example/doc"])["items"][0]["result"]
    assert result["reason_code"] == "content_unavailable"
    assert document.read_bytes() == before


def test_missing_captions_are_skipped_not_failed(config):
    def no_captions(video_id, languages, policy):
        raise SourceFailure(Status.SKIPPED, "language_unavailable", "Sem legenda em pt-BR, pt, en.")

    pipeline, repo = make(config, FakeWeb({}), yt=no_captions)
    report = run(pipeline, repo, ["https://youtu.be/dtpthaIYa8g"])
    assert report["items"][0]["status"] == "skipped" and report["state"] == "completed"
    assert not list(config.output_root.glob("*.md")) if config.output_root.exists() else True


def test_crash_between_publish_and_confirmation_recovers(config):
    repo = Repository(config.state_path)
    config.output_root.mkdir(parents=True)
    target = config.output_root / "artigo-x.md"
    target.write_text("conteúdo", encoding="utf-8")
    repo.begin_write("x", str(target), sha256_file(target), None, None)
    batch = repo.create_batch("dicevtt", "online", [RawSource("https://a.example/")])
    repo.set_batch_state(batch, "running")
    repo.set_item(batch, 0, "fetching")
    summary = repo.recover()
    assert summary == {"confirmed_writes": 1, "interrupted_items": 1}
    assert target.read_text(encoding="utf-8") == "conteúdo"  # versão boa preservada
    assert repo.batch(batch)["state"] == "interrupted" and repo.resume(batch)
