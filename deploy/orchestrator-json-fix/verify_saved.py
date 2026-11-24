"""Read all saved conversations with the selected source; never update the DB."""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
from jarvis_control.orchestrator import Orchestrator  # noqa: E402

orch = Orchestrator.__new__(Orchestrator)
orch._db = sqlite3.connect(
    "file:/var/lib/jarvis-control/orchestrator.db?mode=ro", uri=True
)
orch._db.row_factory = sqlite3.Row
count = recovered = unavailable = 0
for row in orch._rows("SELECT id FROM conversations"):
    view = orch.conversation(row["id"])
    # This also verifies that the public response is JSON serializable.
    json.dumps(view, ensure_ascii=False)
    count += 1
    for run in view["runs"]:
        for task in run["tasks"]:
            raw = orch._row("SELECT result FROM tasks WHERE id = ?", task["id"])
            old = orch._read_result(raw["result"])
            if old and old.get("error") == "invalid_stored_result":
                if task["result"].get("error") == "invalid_stored_result":
                    unavailable += 1
                else:
                    recovered += 1
orch._db.close()
print(json.dumps({"conversations_readable": count, "results_recovered_from_jobs": recovered,
                  "results_requiring_log_review": unavailable, "database_modified": False}))
