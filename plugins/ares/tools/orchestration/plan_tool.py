from __future__ import annotations

import json

from plugins.ares.tools.base import json_result
from plugins.ares.state import engagement_store as store

TOOLSET = "ares_utility"


def _handle_create(args: dict, **kw) -> str:
    eng = store.get_engagement()
    if not eng:
        return json_result(False, error="No active engagement. Call engage_init first.")

    # Build plan from template
    template = args.get("template", "kill_chain")
    tasks_added = 0
    task_ids = []

    if template == "kill_chain":
        from plugins.ares.tools.orchestration.engage_tool import _KILL_CHAIN_TEMPLATE
        steps = _KILL_CHAIN_TEMPLATE
    else:
        steps = json.loads(template) if isinstance(template, str) else template

    for i, step in enumerate(steps):
        # Skip conditional steps if condition not met
        condition = step.get("condition")
        if condition:
            if condition == "http_found":
                http_entities = store.query_entities(eng.id, entity_type="service")
                has_http = any(
                    e.data.get("port") in (80, 443, 8080, 8443)
                    or "http" in e.data.get("protocol", "").lower()
                    for e in http_entities
                )
                if not has_http:
                    continue
            elif condition == "domain_in_scope":
                has_domain = any(
                    "." in t and not t.replace(".", "").isdigit()
                    for t in eng.scope
                )
                if not has_domain:
                    continue

        tid = store.create_task(
            engagement_id=eng.id,
            phase=step["phase"],
            step=step.get("step", i + 1),
            title=step["title"],
            description=step.get("description", ""),
            tool=step.get("tool"),
        )
        task_ids.append(tid)
        tasks_added += 1

    # Transition to recon phase
    store.transition_state(eng.id, "recon")

    return json_result(True, data={
        "engagement_id": eng.id,
        "tasks_created": tasks_added,
        "task_ids": task_ids,
        "state": "recon",
        "message": f"Plan created with {tasks_added} tasks. Use plan_next to start execution.",
    })


def _handle_update(args: dict, **kw) -> str:
    task_id = args.get("task_id")
    if not task_id:
        return json_result(False, error="task_id is required")
    status = args.get("status")
    result = args.get("result")
    confidence = args.get("confidence")
    ok = store.update_task(task_id, status=status, result=result, confidence=confidence)
    if not ok:
        return json_result(False, error="Task not found or invalid status")

    # Auto-transition engagement state based on completed task phase
    eng = store.get_engagement()
    if eng and status == "completed":
        task = store.get_next_task(eng.id)
        if task and task.phase != eng.state:
            store.transition_state(eng.id, task.phase)

    return json_result(True, data={"task_id": task_id, "status": status, "updated": True})


def _handle_next(args: dict, **kw) -> str:
    eng = store.get_engagement()
    if not eng:
        return json_result(False, error="No active engagement.")
    task = store.get_next_task(eng.id)
    if not task:
        plan = store.get_plan_summary(eng.id)
        if plan["pending"] == 0 and plan["completed"] > 0:
            return json_result(True, data={
                "message": "All tasks completed.",
                "plan_summary": plan,
                "next_action": "Review findings and generate report.",
            })
        return json_result(True, data={
            "message": "No tasks with met dependencies available. Some tasks may be blocked.",
            "plan_summary": plan,
        })
    return json_result(True, data={
        "task_id": task.id,
        "phase": task.phase,
        "step": task.step,
        "title": task.title,
        "description": task.description,
        "tool": task.tool,
        "depends_on": task.depends_on,
    })


def _handle_add(args: dict, **kw) -> str:
    eng = store.get_engagement()
    if not eng:
        return json_result(False, error="No active engagement.")
    phase = args.get("phase", eng.state)
    title = args.get("title", "")
    if not title:
        return json_result(False, error="title is required")
    description = args.get("description", "")
    tool = args.get("tool")
    depends_on = args.get("depends_on")
    # Auto-assign step number within phase
    existing = store.get_tasks(eng.id, phase=phase)
    step = len(existing) + 1
    tid = store.create_task(
        engagement_id=eng.id,
        phase=phase,
        step=step,
        title=title,
        description=description,
        tool=tool,
        depends_on=depends_on,
    )
    return json_result(True, data={"task_id": tid, "phase": phase, "step": step})


_CREATE_SCHEMA = {
    "name": "plan_create",
    "description": "Generate an engagement plan from the kill-chain template. Creates ordered tasks for recon, scanning, validation, and reporting. Conditional tasks are included based on scope (e.g. web tasks only if HTTP ports are found). Call after engage_init.",
    "parameters": {
        "type": "object",
        "properties": {
            "template": {
                "type": "string",
                "description": "Plan template: 'kill_chain' (default) or JSON array of custom tasks",
                "enum": ["kill_chain"],
                "default": "kill_chain",
            },
        },
    },
}

_UPDATE_SCHEMA = {
    "name": "plan_update",
    "description": "Update a plan task's status and result. Mark tasks as completed, failed, or skipped. Include a result summary describing what happened.",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "Task ID from plan_next"},
            "status": {
                "type": "string",
                "enum": ["completed", "failed", "skipped", "in_progress"],
                "description": "New task status",
            },
            "result": {"type": "string", "description": "Summary of what happened (e.g. 'Found 3 open ports: 22/ssh, 80/http, 443/https')"},
            "confidence": {"type": "number", "description": "Result confidence 0.0-1.0 (for findings)"},
        },
        "required": ["task_id", "status"],
    },
}

_NEXT_SCHEMA = {
    "name": "plan_next",
    "description": "Get the next pending task to execute. Respects task dependencies — only returns tasks whose prerequisites are completed. Call this before each tool execution.",
    "parameters": {"type": "object", "properties": {}},
}

_ADD_SCHEMA = {
    "name": "plan_add",
    "description": "Dynamically add a task to the plan. Use this when a discovery warrants additional work (e.g. found WordPress → add WPScan task). Tasks are auto-ordered within their phase.",
    "parameters": {
        "type": "object",
        "properties": {
            "phase": {"type": "string", "description": "Phase to add to (recon, scanning, enumeration, validation, exploitation, reporting). Defaults to current phase."},
            "title": {"type": "string", "description": "Task title"},
            "description": {"type": "string", "description": "Task description"},
            "tool": {"type": "string", "description": "Suggested tool to use"},
            "depends_on": {"type": "integer", "description": "Task ID this depends on (optional)"},
        },
        "required": ["title"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="plan_create",
        toolset=TOOLSET,
        schema=_CREATE_SCHEMA,
        handler=lambda args, **kw: _handle_create(args, **kw),
        emoji="📋",
    )
    ctx.register_tool(
        name="plan_update",
        toolset=TOOLSET,
        schema=_UPDATE_SCHEMA,
        handler=lambda args, **kw: _handle_update(args, **kw),
        emoji="✅",
    )
    ctx.register_tool(
        name="plan_next",
        toolset=TOOLSET,
        schema=_NEXT_SCHEMA,
        handler=lambda args, **kw: _handle_next(args, **kw),
        emoji="⏭️",
    )
    ctx.register_tool(
        name="plan_add",
        toolset=TOOLSET,
        schema=_ADD_SCHEMA,
        handler=lambda args, **kw: _handle_add(args, **kw),
        emoji="➕",
    )
