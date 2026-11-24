"""Versioned per-request choices. No shell fragments or implicit fallback."""

import copy
import re

EFFORTS = {
    "codex": ("", "low", "medium", "high", "xhigh", "max", "ultra"),
    "claude": ("", "low", "medium", "high", "max"),
    "antigravity": ("", "low", "medium", "high", "xhigh", "max"),
}


def validate_pipeline(value):
    if not isinstance(value, dict) or set(value) != {"planning", "ui", "coding"}:
        raise ValueError("pipeline precisa conter planning, ui e coding.")
    result = copy.deepcopy(value)
    for stage, settings in result.items():
        if not isinstance(settings, dict):
            raise ValueError("Configuração de etapa inválida.")
        agent = settings.get("agent")
        if agent not in EFFORTS or (stage == "planning" and agent == "claude"):
            raise ValueError("Agente não suportado nesta etapa.")
        if set(settings) - {"agent", "model", "effort", "enabled"}:
            raise ValueError("Campo de etapa desconhecido.")
        model = settings.get("model", "")
        if not isinstance(model, str) or (
            model and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}", model)
        ):
            raise ValueError("Identificador de modelo inválido.")
        effort = settings.get("effort", "")
        if effort not in EFFORTS[agent]:
            raise ValueError("Esforço não suportado pelo agente.")
        if type(settings.get("enabled", True)) is not bool:
            raise ValueError("enabled precisa ser booleano.")
        if stage != "ui" and settings.get("enabled") is False:
            raise ValueError("Somente UI pode ser desativada.")
        settings.update(
            model=model, effort=effort, enabled=settings.get("enabled", True)
        )
    return result


def model_flags(agent, model="", effort=""):
    validate_pipeline(
        {
            k: {
                "agent": agent if k != "planning" or agent != "claude" else "codex",
                "model": model,
                "effort": effort,
            }
            for k in ("planning", "ui", "coding")
        }
    )
    # Gemini in Antigravity exposes effort-specific model IDs.
    if agent == "antigravity" and model.startswith("gemini-") and effort:
        if effort not in ("low", "medium", "high"):
            raise ValueError("Este Gemini suporta low, medium e high.")
        model = re.sub(r"-(low|medium|high)$", "", model) + "-" + effort
    args = ["--model", model] if model else []
    if effort:
        args += (
            ["-c", f'model_reasoning_effort="{effort}"']
            if agent == "codex"
            else ["--effort", effort]
        )
    return args


def pipeline_schema(schema, pipeline):
    schema = copy.deepcopy(schema)
    task = schema["properties"]["plan"]["properties"]["tasks"]["items"]
    stages = ["ui", "coding"] if pipeline["ui"]["enabled"] else ["coding"]
    task["properties"]["stage"] = {"type": "string", "enum": stages}
    task["required"] = [*task["required"], "stage"]
    task["properties"]["agent"]["enum"] = list(
        dict.fromkeys(pipeline[s]["agent"] for s in stages)
    )
    return schema


def check_pipeline_tasks(plan, pipeline):
    problems = []
    tasks = plan.get("tasks") or []
    ui_keys = [t.get("key") for t in tasks if t.get("stage") == "ui"]
    for task in tasks:
        stage = task.get("stage")
        if stage not in ("ui", "coding") or (
            stage == "ui" and not pipeline["ui"]["enabled"]
        ):
            problems.append("Etapa inválida ou UI desativada.")
        elif task.get("agent") != pipeline[stage]["agent"]:
            problems.append("Agente da tarefa não corresponde à etapa escolhida.")
        if stage == "ui" and any(d not in ui_keys for d in task.get("depends_on", [])):
            problems.append("UI não pode depender da etapa posterior de código.")
    return problems
