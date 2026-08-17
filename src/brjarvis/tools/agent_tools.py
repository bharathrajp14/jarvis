# tools/agent_tools.py — JARVIS MK37 Sub-Agent Tools Plugin
"""
Sub-agent management tools plugin for JARVIS MK37.
Allows spawning, message-passing, and monitoring autonomous sub-agents.
"""
from __future__ import annotations

from .registry import register_tool, get_orchestrator_ref


def _get_subagent_manager():
    from brjarvis.multi_agent.subagent import SubAgentManager
    # Safe singleton access
    import tools.registry
    mgr = getattr(tools.registry, "_subagent_mgr", None)
    if mgr is None:
        mgr = SubAgentManager()
        tools.registry._subagent_mgr = mgr
    return mgr


@register_tool(
    name="spawn_agent",
    description=(
        "Spawn a sub-agent to handle a task autonomously. "
        "NOTE: available in CLI mode (start.py cli). "
        "Types: general-purpose, coder, reviewer, researcher, tester, editor, sysadmin, devops."
    ),
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "agent_type": {"type": "string"},
            "name": {"type": "string"},
            "wait": {"type": "boolean"},
        },
        "required": ["prompt"],
    }
)
def tool_spawn_agent(args: dict) -> str:
    orch = get_orchestrator_ref()
    if orch is None:
        return (
            "Sub-agent spawning requires active orchestrator reference. "
            "Use the CLI interface (start.py cli) for this feature."
        )

    mgr = _get_subagent_manager()
    prompt = args["prompt"]
    wait = args.get("wait", True)
    agent_type = args.get("agent_type", "")
    agent_name = args.get("name", "")

    agent_def = None
    if agent_type:
        from brjarvis.multi_agent.subagent import get_agent_definition
        agent_def = get_agent_definition(agent_type)
        if agent_def is None:
            return f"Error: unknown agent_type '{agent_type}'. Use list_agent_types."

    task = mgr.spawn(
        prompt=prompt,
        orchestrator=orch,
        depth=0,
        agent_def=agent_def,
        name=agent_name,
    )

    if task.status == "failed":
        return f"Error spawning agent: {task.result}"

    if wait:
        mgr.wait(task.id, timeout=300)
        result = task.result or f"(no output — status: {task.status})"
        header = f"[Agent: {task.name}"
        if agent_type:
            header += f" ({agent_type})"
        header += "]"
        return f"{header}\n\n{result}"
    else:
        return f"Task ID: {task.id}\nName: {task.name}\nStatus: {task.status}\nUse check_agent to poll."


@register_tool(
    name="send_message",
    description="Send a follow-up message to a running background agent.",
    parameters={
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "message": {"type": "string"},
        },
        "required": ["to", "message"],
    }
)
def tool_send_message(args: dict) -> str:
    mgr = _get_subagent_manager()
    target = args["to"]
    message = args["message"]
    
    ok = mgr.send_message(target, message)
    if ok:
        return f"Message queued for agent '{target}'."
        
    task_id = mgr._by_name.get(target, target)
    task = mgr.tasks.get(task_id)
    if task is None:
        return f"Error: no agent found with id or name '{target}'"
    return f"Error: agent '{target}' is not running (status: {task.status})."


@register_tool(
    name="check_agent",
    description="Check the status and result of a spawned sub-agent task.",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "string"},
        },
        "required": ["task_id"],
    }
)
def tool_check_agent(args: dict) -> str:
    mgr = _get_subagent_manager()
    task_id = args["task_id"]
    task = mgr.tasks.get(task_id)
    
    if task is None:
        return f"Error: no task with id '{task_id}'"
        
    lines = [f"Status: {task.status}", f"Name: {task.name}"]
    if task.result:
        lines.append(f"\nResult:\n{task.result}")
    return "\n".join(lines)


@register_tool(
    name="list_agents",
    description="List all sub-agent tasks and their statuses.",
    parameters={}
)
def tool_list_agents(args: dict) -> str:
    mgr = _get_subagent_manager()
    tasks = mgr.list_tasks()
    
    if not tasks:
        return "No sub-agent tasks."
        
    lines = ["ID           | Name     | Status    | Prompt"]
    lines.append("-------------|----------|-----------|------")
    for t in tasks:
        prompt_short = t.prompt[:50] + ("..." if len(t.prompt) > 50 else "")
        lines.append(f"{t.id} | {t.name[:8]:8s} | {t.status:9s} | {prompt_short}")
    return "\n".join(lines)


@register_tool(
    name="list_agent_types",
    description="List all available agent types (built-in and custom).",
    parameters={}
)
def tool_list_agent_types(args: dict) -> str:
    from brjarvis.multi_agent.subagent import load_agent_definitions
    defs = load_agent_definitions()
    
    if not defs:
        return "No agent types available."
        
    lines = ["Available agent types:", ""]
    for aname, d in sorted(defs.items()):
        lines.append(f"  {aname:20s}  [{d.source:8s}]  {d.description}")
    lines.append("")
    lines.append("Create custom agents: place .md files in ~/.jarvis/agents/")
    return "\n".join(lines)
