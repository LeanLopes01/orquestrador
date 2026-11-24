"""The primary PC must be running its local UI before accepting new project work.

The answer also says which planners this helper runs, so the server announces
planner routing only when both sides support it.
"""

import aiohttp

from . import agent_jobs
from .agent_jobs import PLANNERS, ROUTING_VERSION

EXECUTORS = getattr(agent_jobs, "EXECUTORS", ("claude", "antigravity", "codex"))
ROUTING = {
    "routing_version": ROUTING_VERSION,
    "pipeline_version": 1,
    "planning_agents": list(PLANNERS),
    "execution_agents": list(EXECUTORS),
}


async def runtime_status(params=None):
    try:
        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as http,
            http.get(
                "http://127.0.0.1:1420/api/orchestrator/health", allow_redirects=False
            ) as response,
        ):
            data = await response.json()
            online = (
                response.status == 200
                and data.get("service") == "dicevtt-orchestrator"
                and data.get("online") is True
            )
            return {"online": online, "host": "BATCOMPUTADOR", **ROUTING}
    except (aiohttp.ClientError, TimeoutError, ValueError):
        return {
            "online": False,
            "host": "BATCOMPUTADOR",
            "reason": "local_runtime_offline",
            **ROUTING,
        }
