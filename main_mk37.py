# main_mk37.py — JARVIS MK37 Interactive CLI Orchestrator REPL
"""
Interactive CLI REPL for BR JARVIS MK37.
Features:
- Gemini-native ReAct orchestration loop with streaming response
- Parallel goal execution (/run goal1 | goal2 | goal3)
- Slash commands: /mode, /tasks, /skills, /memory, /install-skills, /clear, /help, /quit
- Rich terminal UI with fallback support
"""
from __future__ import annotations

import os
import sys
import time
import re
from pathlib import Path

# Ensure root in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Setup UTF-8 console output on Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Load .env
try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]
    _env_path = BASE_DIR / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass

# Rich imports with fallbacks
try:
    from rich.console import Console  # type: ignore[import-not-found]
    from rich.panel import Panel  # type: ignore[import-not-found]
    from rich.table import Table  # type: ignore[import-not-found]
    from rich.prompt import Prompt  # type: ignore[import-not-found]
    from rich.markdown import Markdown  # type: ignore[import-not-found]
    _HAS_RICH = True
    console = Console()
except ImportError:
    _HAS_RICH = False
    console = None

from core.bootstrap import build_assistant_runtime
from router import AgentRouter, get_router
from orchestrator import JarvisOrchestrator, MODES
from agent.executor import ParallelGoalExecutor


def _print_banner():
    if _HAS_RICH:
        banner = """[bold cyan]⚡ BR JARVIS — AI OPERATING SYSTEM ⚡[/bold cyan]
[dim]ReAct Terminal Orchestrator | MARK XXXVII CLI[/dim]
[cyan]Type your request or use slash commands. Type [bold]/help[/bold] for command list, [bold]/quit[/bold] to exit.[/cyan]"""
        console.print(Panel(banner, border_style="cyan", expand=False))
    else:
        print("=========================================================")
        print("⚡ BR JARVIS — AI OPERATING SYSTEM ⚡")
        print("ReAct Terminal Orchestrator | MARK XXXVII CLI")
        print("Type your request or use slash commands (/help, /quit)")
        print("=========================================================\n")


def _print_help():
    if _HAS_RICH:
        table = Table(title="Available Slash Commands", border_style="cyan")
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Example", style="dim")
        table.add_row("/run <g1> | <g2>", "Run multiple goals in parallel", "/run check ram | open chrome")
        table.add_row("/plan <goal>", "Generate implementation_plan.md artifact", "/plan Refactor Memory Engine")
        table.add_row("/scratch", "Inspect Antigravity Scratchpad workspace", "/scratch")
        table.add_row("/walkthrough", "Generate walkthrough.md artifact", "/walkthrough")
        table.add_row("/goal <desc>", "Execute long-running goal", "/goal Build REST API")
        table.add_row("/mode <persona>", "Switch AI persona mode", "/mode coder")
        table.add_row("/tasks", "Show active and queued task status", "/tasks")
        table.add_row("/skills", "List all available skills", "/skills")
        table.add_row("/memory", "Display memory telemetry & working context", "/memory")
        table.add_row("/install-skills <hub>", "Install external skills from GitHub", "/install-skills openclaw-master")
        table.add_row("/clear", "Clear screen and reset working memory", "/clear")
        table.add_row("/help", "Show this help menu", "/help")
        table.add_row("/quit or /exit", "Exit CLI orchestrator", "/quit")
        console.print(table)
    else:
        print("\nSlash Commands:")
        print("  /run <g1> | <g2>        Run goals in parallel (e.g. /run check ram | open chrome)")
        print("  /plan <goal>            Generate implementation_plan.md artifact")
        print("  /scratch                Inspect Antigravity Scratchpad workspace")
        print("  /walkthrough            Generate walkthrough.md artifact")
        print("  /goal <desc>            Execute long-running goal")
        print("  /mode <persona>         Switch persona (coder, recon, exploit, report, planner, analyst, general)")
        print("  /tasks                  Show active task queue")
        print("  /skills                 List registered skills")
        print("  /memory                 Display memory status")
        print("  /install-skills <hub>   Install external skills")
        print("  /clear                  Clear terminal & working memory")
        print("  /help                   Show this menu")
        print("  /quit                   Exit\n")


def _handle_parallel_run(cmd_text: str):
    raw_goals = cmd_text[4:].strip()
    if not raw_goals:
        print("[JARVIS] Error: Specify at least one goal. Example: /run search news | open browser")
        return

    goals = [g.strip() for g in raw_goals.split("|") if g.strip()]
    if not goals:
        print("[JARVIS] Error: No valid goals found.")
        return

    if _HAS_RICH:
        console.print(f"\n[bold cyan]🚀 Parallel Execution:[/] Running {len(goals)} goals simultaneously...")
    else:
        print(f"\n🚀 Parallel Execution: Running {len(goals)} goals simultaneously...")

    executor = ParallelGoalExecutor(max_concurrent=min(len(goals), 5))
    results = executor.execute_all(goals)

    if _HAS_RICH:
        table = Table(title="Parallel Execution Summary", border_style="green")
        table.add_column("Goal", style="cyan")
        table.add_column("Result", style="white")
        for g, r in results.items():
            short_r = str(r)[:150] + ("..." if len(str(r)) > 150 else "")
            table.add_row(g, short_r)
        console.print(table)
    else:
        print("\nParallel Results:")
        for g, r in results.items():
            print(f"  • {g}: {str(r)[:150]}")


def _list_skills(category: str = None):
    try:
        from skills.registry import get_skills_by_category, list_skill_categories, get_all_skills
        all_skills = get_all_skills()
        categories = list_skill_categories()
        
        if _HAS_RICH:
            console.print(f"\n[bold cyan]⚡ BR JARVIS Skill Ecosystem ({len(all_skills)} Active Skills Across {len(categories)} Categories)[/bold cyan]")
            table = Table(title="Domain Skill Categories", border_style="cyan")
            table.add_column("Category", style="cyan")
            table.add_column("Skill Count", style="yellow")
            table.add_column("Sample Skills", style="white")
            
            by_cat = get_skills_by_category()
            for cat_name, count in categories.items():
                if category and category.lower() not in cat_name.lower():
                    continue
                sample = ", ".join([s.name for s in by_cat.get(cat_name, [])[:4]])
                table.add_row(cat_name, str(count), sample)
            console.print(table)
            console.print("[dim]Use /search-skills <query> to search or /skill <name> to execute.[/dim]\n")
        else:
            print(f"\nBR JARVIS Skills ({len(all_skills)} Total):")
            for cat_name, count in categories.items():
                print(f"  • {cat_name}: {count} skills")
    except Exception as e:
        print(f"[JARVIS] Skills lookup failed: {e}")


def _search_skills(query: str):
    try:
        from skills.registry import search_skills
        results = search_skills(query)
        if not results:
            print(f"[JARVIS] No skills matching '{query}' found.")
            return

        if _HAS_RICH:
            table = Table(title=f"Search Results for '{query}' ({len(results)} matches)", border_style="cyan")
            table.add_column("Skill Name", style="cyan")
            table.add_column("Category", style="yellow")
            table.add_column("Description", style="white")
            for s in results:
                table.add_row(s.name, s.category, s.description[:75])
            console.print(table)
        else:
            print(f"\nSearch Results for '{query}':")
            for s in results:
                print(f"  • {s.name} [{s.category}]: {s.description[:60]}")
    except Exception as e:
        print(f"[JARVIS] Search skills failed: {e}")


def _show_tasks():
    try:
        from agent.task_queue import get_task_queue
        tq = get_task_queue()
        active = tq.list_tasks() if hasattr(tq, "list_tasks") else []
        if not active:
            print("[JARVIS] Task Queue: No active background tasks.")
        else:
            if _HAS_RICH:
                table = Table(title="Active Task Queue", border_style="yellow")
                table.add_column("Task ID", style="cyan")
                table.add_column("Goal", style="white")
                table.add_column("Status", style="yellow")
                for t in active:
                    tid = getattr(t, "id", str(t))
                    goal = getattr(t, "goal", "")
                    status = getattr(t, "status", "running")
                    table.add_row(tid, goal[:60], status)
                console.print(table)
            else:
                print("\nActive Tasks:")
                for t in active:
                    print(f"  • {getattr(t, 'id', str(t))}: {getattr(t, 'goal', '')[:50]}")
    except Exception as e:
        print(f"[JARVIS] Task queue query failed: {e}")


def main():
    """Main interactive REPL entry point for JARVIS CLI."""
    _print_banner()

    runtime = build_assistant_runtime()
    orchestrator = runtime.orchestrator

    try:
        while True:
            try:
                mode_str = f"[{orchestrator.current_mode.upper()}]"
                if _HAS_RICH:
                    user_input = Prompt.ask(f"\n[bold cyan]BR[/bold cyan] [dim]{mode_str}[/dim] >").strip()
                else:
                    user_input = input(f"\nBR {mode_str} > ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n[JARVIS] Shutting down...")
                break

            if not user_input:
                continue

            # Command dispatch
            cmd_lower = user_input.lower()

            if cmd_lower in ("/quit", "/exit", "quit", "exit"):
                if _HAS_RICH:
                    console.print("[yellow]Shutting down JARVIS Orchestrator... Goodbye, sir.[/yellow]")
                else:
                    print("Shutting down JARVIS Orchestrator... Goodbye, sir.")
                break

            if cmd_lower == "/help":
                _print_help()
                continue

            if cmd_lower == "/clear":
                if sys.platform == "win32":
                    os.system("cls")
                else:
                    os.system("clear")
                orchestrator.working_memory.clear()
                _print_banner()
                continue

            if cmd_lower.startswith("/run "):
                _handle_parallel_run(user_input)
                continue

            if cmd_lower.startswith("/mode"):
                res = orchestrator._parse_mode(user_input)
                print(res or f"[JARVIS] Active mode: {orchestrator.current_mode.upper()}")
                continue

            if cmd_lower.startswith("/search-skills") or cmd_lower.startswith("/search_skills"):
                q = user_input.partition(" ")[2].strip()
                _search_skills(q)
                continue

            if cmd_lower.startswith("/skill "):
                skill_query = user_input[7:].strip()
                from skills.loader import find_skill
                from skills.executor import execute_skill
                target_skill = find_skill(skill_query)
                if target_skill:
                    print(f"[JARVIS] Executing Skill '{target_skill.name}' ({target_skill.category})...")
                    args_text = skill_query[len(target_skill.name):].strip()
                    res = execute_skill(target_skill, args_text, orchestrator)
                    print(f"\n{res}\n")
                else:
                    print(f"[JARVIS] Skill '{skill_query}' not found. Use /search-skills to search.")
                continue

            if cmd_lower == "/skills" or cmd_lower.startswith("/skills "):
                cat_filter = user_input[7:].strip() if len(user_input) > 7 else None
                _list_skills(category=cat_filter)
                continue

            if cmd_lower == "/tasks":
                _show_tasks()
                continue

            if cmd_lower == "/memory":
                tokens = orchestrator.working_memory.get_token_count() if hasattr(orchestrator.working_memory, "get_token_count") else 0
                history_len = len(orchestrator.working_memory.get()) if hasattr(orchestrator.working_memory, "get") else 0
                print(f"[JARVIS] Working Memory: {history_len} messages stored (~{tokens} tokens). Session ID: {orchestrator.session_id}")
                continue

            if cmd_lower.startswith("/plan"):
                goal_text = user_input[5:].strip() or "General Task Plan"
                try:
                    from agent.planning_mode import get_planning_engine
                    pe = get_planning_engine()
                    p_path = pe.generate_implementation_plan(
                        goal=goal_text,
                        proposed_changes=[{"component": "System Architecture", "files": [{"tag": "MODIFY", "path": "main_mk37.py", "description": "CLI orchestrator execution"}]}],
                        verification_steps=["pytest tests/test_antigravity_system.py"]
                    )
                    print(f"[JARVIS] 📋 Implementation plan generated: {p_path}")
                except Exception as pe_err:
                    print(f"[JARVIS] Plan generation failed: {pe_err}")
                continue

            if cmd_lower in ("/scratch", "/scratchpad"):
                try:
                    from agent.scratchpad import get_scratchpad
                    sp = get_scratchpad()
                    files = sp.list_files()
                    notes = sp.get_notes()
                    print(f"[JARVIS] 📝 Scratchpad Workspace ({len(files)} files, {len(notes)} active notes)")
                    for f in files[:5]:
                        print(f"  • File: {f['name']} ({f['size_bytes']} bytes)")
                    for n in notes[:5]:
                        print(f"  • Note: {n}")
                except Exception as sp_err:
                    print(f"[JARVIS] Scratchpad lookup failed: {sp_err}")
                continue

            if cmd_lower == "/walkthrough":
                try:
                    from agent.planning_mode import get_planning_engine
                    pe = get_planning_engine()
                    wt_path = pe.generate_walkthrough("CLI Work Session", accomplishments=["Executed CLI session", "Validated system tools"])
                    print(f"[JARVIS] 📄 Walkthrough generated: {wt_path}")
                except Exception as wt_err:
                    print(f"[JARVIS] Walkthrough generation failed: {wt_err}")
                continue

            if cmd_lower.startswith("/install-skills"):
                parts = user_input.split(maxsplit=1)
                hub = parts[1] if len(parts) > 1 else "claude-skills"
                try:
                    from skills.installer import install_skills
                    print(f"[JARVIS] Installing skills from '{hub}'...")
                    res = install_skills(hub)
                    print(f"[JARVIS] Result: {res}")
                except Exception as ie:
                    print(f"[JARVIS] Skill installation failed: {ie}")
                continue

            # Default: execute chat stream through ReAct orchestrator loop
            try:
                if _HAS_RICH:
                    console.print("\n[bold green]BR >[/bold green] ", end="")
                else:
                    print("\nBR > ", end="")
                sys.stdout.flush()

                for chunk in orchestrator.chat_stream(user_input):
                    if _HAS_RICH:
                        console.print(chunk, end="", highlight=False)
                    else:
                        print(chunk, end="")
                    sys.stdout.flush()
                print()
            except Exception as chat_err:
                print(f"\n[JARVIS Error]: {chat_err}")

    finally:
        orchestrator.shutdown()


if __name__ == "__main__":
    main()
