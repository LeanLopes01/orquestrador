import os

from conftest import copy_fixture, wait_for


def test_watcher_create_rename_delete_and_burst(make_rag):
    rag = make_rag(watch=True)
    scripts = rag.config.scripts_root
    assert wait_for(lambda: rag.watcher.state == "running")
    path = copy_fixture("NetworkManager.cs", scripts / "NetworkManager.cs")
    for i in range(20):  # rajada: coalescida pelo debounce
        path.write_text(path.read_text(encoding="utf-8") + f"\n// {i}", encoding="utf-8")
    assert wait_for(lambda: rag.store.count("dicevtt", "code_pointer") == 1)
    renamed = scripts / "Rede" / "NetworkManager.cs"
    renamed.parent.mkdir()
    os.replace(path, renamed)
    assert wait_for(lambda: [m["filepath"] for m in rag.store.get(where=rag.store.where("dicevtt", "code_pointer"))["metadatas"]]
                    == [str(renamed.resolve())])
    renamed.unlink()
    assert wait_for(lambda: rag.store.count("dicevtt", "code_pointer") == 0)


def test_atomic_save_through_temp_file(make_rag):
    rag = make_rag(watch=True)
    scripts = rag.config.scripts_root
    assert wait_for(lambda: rag.watcher.state == "running")
    tmp = scripts / "Salvo.cs.tmp"
    tmp.write_text("/// Salvo atomicamente.\npublic class Salvo {}", encoding="utf-8")
    os.replace(tmp, scripts / "Salvo.cs")
    assert wait_for(lambda: rag.store.count("dicevtt", "code_pointer") == 1)
    meta = rag.store.get(where=rag.store.where("dicevtt", "code_pointer"))["metadatas"][0]
    assert meta["filename"] == "Salvo.cs"


def test_directory_move_reconciles_descendants(make_rag):
    rag = make_rag(watch=True)
    scripts = rag.config.scripts_root
    copy_fixture("SemComentario.cs", scripts / "A" / "SemComentario.cs")
    rag.submit_index("code").result()
    assert wait_for(lambda: rag.watcher.state == "running")
    os.replace(scripts / "A", scripts / "B")
    assert wait_for(lambda: [m["filepath"] for m in rag.store.get(where=rag.store.where("dicevtt", "code_pointer"))["metadatas"]]
                    == [str((scripts / "B" / "SemComentario.cs").resolve())], timeout=8)


def test_queue_saturation_requests_reconcile(make_rag):
    rag = make_rag()
    from unity_rag.watcher import ScriptWatcher

    watcher = ScriptWatcher(rag.code, rag.worker.submit, debounce_ms=10_000, queue_limit=3)
    for i in range(5):
        watcher.record("modified", str(rag.config.scripts_root / f"X{i}.cs"))
    due, reconcile = watcher._take_due()
    assert reconcile and not due
