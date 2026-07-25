# orchestrator.py — JARVIS MK37 Core Orchestrator (Gemini-Native)
"""
ReAct (Reason + Act) orchestration loop powered by Gemini.
Features:
- Gemini as primary AI engine (only API key required)
- Intelligent tool routing
- Persistent memory injection
- Session history
- Multi-agent support
"""
from __future__ import annotations

import os
import re
import time

from router import AgentRouter
from memory.working import WorkingMemory
from tools.registry import get_tool_prompt_block, parse_tool_call, execute_tool, set_orchestrator_ref

# ── System Prompt ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are BR — a superhuman AI operating system and autonomous controller.
You are intelligent, precise, direct, and capable of executing complex tasks end-to-end.

### CRITICAL DIRECTIVE: USER INTENT IS LAW
1. **UNCONDITIONAL EXECUTION**: Whatever task the user asks for, you MUST execute it to 100% completion using available tools.
2. **NO LOOPS & NO FAKE CLAIMS**: Never repeatedly execute the exact same tool call without changing approach, and NEVER claim a task is done unless verified by tool results.
3. **FAIL-SAFE ADAPTATION**: If a tool or method fails, immediately adapt and try alternative tools (e.g. python script, CLI, or browser) until the goal is achieved.
4. **ZERO REFUSAL FOR SAFE WORK**: Execute system controls, file operations, web scraping, dev tasks, and OS automation immediately without hesitation or unnecessary disclaimers.

### Core Capabilities
1. **AUTONOMOUS ACTION**: Execute tasks end-to-end without constant confirmation.
2. **PARALLEL THINKING**: Break complex tasks into parallel workstreams.
3. **TOOL MASTERY**: Select the optimal tool for each sub-task.
4. **MEMORY**: Pull from persistent memory before asking users to repeat info.
5. **SCOPE SAFETY**: For security/red-team tasks, verify authorization first.
6. **TRANSPARENCY**: Always report what you did and what the result was.

### Execution Philosophy & Response Format
- **BE EXTREMELY CONCISE AND DIRECT**: Give short, high-precision 1-3 sentence answers.
- **ZERO FILLER**: Never output wall-of-text explanations when a tool or direct action can do the work.
- **ACTION-FIRST**: Execute the assigned work using tools immediately.
- **PURE CODE PARAMETERS**: When passing code to tools (`run_code`, `code_helper`, `scratchpad_eval`), the `"code"` parameter MUST contain ONLY executable code. Do NOT mix raw narrative sentences inside code strings without `#` comments.
- Never fabricate results — always call the tool.
- If a tool fails, try an alternative approach.

### Persona Modes (switch with /mode <name>)
- RECON: Systematic OSINT and network intelligence gathering
- EXPLOIT: Authorized vulnerability analysis (scope only)
- REPORT: Professional technical writing
- PLANNER: Strategic decomposition of complex goals
- CODER: Senior full-stack DevSecOps engineer
- ANALYST: Data synthesis and threat intelligence
- GENERAL: Default adaptive mode

### Tool Routing Guide
| Task | Tool |
|------|------|
| Open apps | open_app |
| Web search | web_search |
| Browser automation | browser_control |
| File operations | file_controller |
| System controls (brightness/volume/wifi) | computer_settings |
| Mouse/keyboard | computer_control |
| Code tasks | code_helper or dev_agent |
| Temporary code/eval/scratch space | scratchpad_write / scratchpad_eval |
| Steam/Epic games | game_updater |
| Multi-step complex tasks | agent_task |
| Screen analysis | screen_process |
| YouTube | youtube_video |
| Flights | flight_finder |
| Messaging | send_message |
"""

MODES = {
    "recon":   "RECON MODE: You are a systematic OSINT analyst. Be methodical and exhaustive.",
    "exploit": "EXPLOIT MODE: Authorized vulnerability analysis only. Document everything.",
    "report":  "REPORT MODE: Professional technical writing. Produce client-ready deliverables.",
    "planner": "PLANNER MODE: Decompose goals into ordered, actionable tasks.",
    "coder":   "CODER MODE: Senior full-stack engineer. Write clean, tested, documented code.",
    "analyst": "ANALYST MODE: Synthesize data into clear, actionable insights.",
    "general": "",
}

MAX_REACT_STEPS = 20


def _format_clean_tool_summary(tool_name: str, tool_args: dict) -> str:
    """Format a clean, human-readable summary of executed tools without raw code/JSON dumps."""
    args = tool_args or {}
    if "query" in args:
        val = str(args["query"]).replace("\n", " ").strip()[:60]
        return f"[Executed Tool: {tool_name} query='{val}']"
    elif "action" in args:
        act = str(args["action"])
        target = str(args.get("path") or args.get("name") or args.get("app_name") or args.get("value") or "").replace("\n", " ").strip()[:40]
        return f"[Executed Tool: {tool_name} action='{act}' {target}]".strip()
    elif any(k in args for k in ("code", "script", "content")):
        lang = str(args.get("lang") or args.get("language") or "code")
        return f"[Executed Tool: {tool_name} ({lang} script)]"
    elif not args:
        return f"[Executed Tool: {tool_name}({{}})]"
    else:
        keys = ", ".join(list(args.keys())[:3])
        return f"[Executed Tool: {tool_name}({keys})]"



class JarvisOrchestrator:

    def __init__(self, router: AgentRouter, use_vector_memory: bool = True):
        self.router = router
        self.working_memory = WorkingMemory(max_tokens=120_000)
        self.vector_memory  = None
        self.current_mode   = "general"
        self.conversation_store = None
        self._subagent_mgr  = None

        # History
        self._session_store = None
        self._session_id    = ""
        self._history_linker = None
        try:
            from history.session_store import SessionStore
            from history.linker import HistoryLinker
            from history.audit_writer import set_session_id
            self._session_store  = SessionStore()
            self._history_linker = HistoryLinker()
            self._session_id = self._session_store.new_session(
                mode="general",
                backend=router.default.value,
            )
            set_session_id(self._session_id)
        except Exception as e:
            print(f"[JARVIS] History unavailable: {e}")

        # Initialize SQLite Conversation Store
        try:
            from memory.conversation_store import ConversationStore
            self.conversation_store = ConversationStore()
            if self._session_id:
                self.conversation_store.start_session(
                    session_id=self._session_id,
                    mode=self.current_mode,
                    backend=router.default.value
                )
        except Exception as e:
            print(f"[JARVIS] Conversation store warning: {e}")

        set_orchestrator_ref(self)

        if use_vector_memory:
            try:
                from memory.vector_store import VectorMemory
                self.vector_memory = VectorMemory()
            except Exception:
                pass

    @property
    def session_id(self) -> str:
        return self._session_id

    def _parse_mode(self, user_input: str) -> str | None:
        m = re.match(r"^/mode\s+(\w+)", user_input.strip())
        if m:
            mode = m.group(1).lower()
            if mode in MODES:
                self.current_mode = mode
                return f"[JARVIS] Mode → {mode.upper()} ✓"
            return f"[JARVIS] Unknown mode: '{mode}'. Available: {', '.join(MODES.keys())}"
        return None

    _tool_prompt_cache: str = ""  # class-level cache for tool prompt block

    def _build_system(self, user_prompt: str = "") -> str:
        name = os.environ.get("JARVIS_ASSISTANT_NAME", "BR").strip()
        sys_prompt = (
            f"You are {name}, an ultra-fast autonomous AI assistant. Think step-by-step, act decisively, avoid filler.\n"
            "CRITICAL THINKING & WORKSPACE EXECUTION RULES:\n"
            "1. THINK FIRST, THEN EXECUTE: Carefully plan your complete task before executing tools.\n"
            "2. ISOLATED WORKSPACE: When creating apps, projects, backend services, or games, ALWAYS put all generated files inside a dedicated subfolder under `./workspace/<ProjectName>/` (e.g. `./workspace/FoodDeliveryApp/` or `./workspace/Games/TicTacToe/`). NEVER dump loose files into the root codebase directory!\n"
            "3. EFFICIENT SINGLE EXECUTION: Create complete scripts/files in 1 clean tool call. Do NOT make 10-20 consecutive file_write calls in a loop.\n"
            "4. INTERACTIVE CMD TERMINAL GAMES/APPS: To run interactive terminal games or CLI scripts in CMD, launch them in a new window using `start cmd /k python ./workspace/Games/<game>.py` so a native CMD window opens for the user to play interactively!\n"
            "5. NO PLAIN TEXT TOOL MENTIONS: Never output text like 'Now call create_word_document'. Either invoke the tool via ```tool_call JSON block or present your final answer directly to the user."
        )
        parts = [sys_prompt]
        mode_text = MODES.get(self.current_mode, "")
        if mode_text:
            parts.append(f"Mode: {mode_text}")

        try:
            from tools.registry import get_pruned_tool_prompt_block
            if user_prompt:
                parts.append(get_pruned_tool_prompt_block(user_prompt))
            elif not JarvisOrchestrator._tool_prompt_cache:
                from tools.registry import get_tool_prompt_block
                JarvisOrchestrator._tool_prompt_cache = get_tool_prompt_block()
                parts.append(JarvisOrchestrator._tool_prompt_cache)
            else:
                parts.append(JarvisOrchestrator._tool_prompt_cache)
        except Exception:
            from tools.registry import get_tool_prompt_block
            parts.append(get_tool_prompt_block())

        return "\n".join(parts)

    def _extract_keywords(self, text: str) -> list[str]:
        low = text.lower()
        kw  = []
        if any(w in low for w in ["code", "script", "function", "debug", "build", "program"]):
            kw.append("code")
        if any(w in low for w in ["scan", "recon", "pentest", "vuln", "exploit", "nmap"]):
            kw.append("security")
        if any(w in low for w in ["search", "find", "look up", "google", "what is", "who is"]):
            kw.append("search")
        if any(w in low for w in ["analyze", "data", "chart", "graph", "statistics"]):
            kw.append("analysis")
        if any(w in low for w in ["private", "local", "offline", "no cloud"]):
            kw.append("local_private")
        if any(w in low for w in ["image", "photo", "screen", "camera", "see", "look"]):
            kw.append("vision")
        return kw

    def _recall_context(self, user_input: str) -> str:
        if not self.vector_memory:
            return ""
        # Skip trivial inputs (greetings, short phrases, simple commands)
        if len(user_input.split()) < 4:
            return ""
        # Skip obvious command patterns that don't benefit from memory recall
        low = user_input.lower().strip()
        if low.startswith(("open ", "launch ", "start ", "close ", "stop ", "/")):
            return ""
        try:
            results = self.vector_memory.search(user_input, top_k=2)
            if results:
                return "### Relevant Memory\n" + "\n".join(f"- {r}" for r in results)
        except Exception:
            pass
        return ""

    def _save_turn(self, user_input: str, response: str) -> None:
        if not self.vector_memory or len(response) < 20:
            return
        try:
            self.vector_memory.store(
                f"Q: {user_input}\nA: {response[:500]}",
                metadata={"mode": self.current_mode},
            )
        except Exception:
            pass

    def _store_exchange(self, user_input: str, response: str) -> None:
        """Alias for _save_turn to ensure backwards compatibility."""
        self._save_turn(user_input, response)

    def _record_turn(self, role: str, content: str, **kwargs) -> None:
        if self._session_store and self._session_id:
            try:
                self._session_store.add_turn(
                    session_id=self._session_id,
                    role=role,
                    content=content[:5000],
                    **kwargs,
                )
            except Exception:
                pass
        
        # SQLite Sync
        if self.conversation_store and self._session_id:
            try:
                self.conversation_store.log_turn(
                    session_id=self._session_id,
                    role=role,
                    content=content,
                    tool_name=kwargs.get("tool_name"),
                    tool_args=kwargs.get("tool_args"),
                    tool_result=kwargs.get("tool_result"),
                    latency_ms=kwargs.get("latency_ms", 0),
                )
            except Exception:
                pass

    def _resolve_context_references(self, user_input: str, augmented: str) -> str:
        """
        Resolve pronoun references like 'open it in brave' by injecting the last
        JARVIS result URL or content into the augmented prompt.
        """
        low = user_input.lower().strip()
        # Detect 'open it in <browser>' or 'open in <browser>' or 'show it in <browser>'
        browser_names = ["brave", "chrome", "edge", "firefox", "browser"]
        has_pronoun = any(w in low for w in ["open it", "open this", "show it", "show this", "open in", "show in"])
        has_browser = any(b in low for b in browser_names)

        if has_pronoun and has_browser:
            # Find the last assistant response URL from working memory
            last_url = None
            for msg in reversed(self.working_memory.get()):
                if msg.get("role") == "assistant" or msg.get("role") == "user":
                    content = msg.get("content", "")
                    # Extract URL from content
                    import re as _re
                    urls = _re.findall(r'https?://[^\s"<>]+', content)
                    if urls:
                        last_url = urls[-1]
                        break

            # Determine which browser
            target_browser = "brave"
            for b in browser_names:
                if b in low:
                    target_browser = b
                    break

            if last_url:
                # Quick-execute: open URL in chosen browser directly via DeterministicIntentEngine
                try:
                    from core.intent_engine import DeterministicIntentEngine
                    launched = DeterministicIntentEngine.open_url_in_browser(last_url, browser_name=target_browser)
                    if launched:
                        print(f"[Context] Resolved 'it' → {last_url} | Browser: {target_browser}")
                        return augmented + f"\n[SYSTEM CONTEXT: 'it' refers to {last_url} — already opened in {target_browser}. Confirm to user.]"
                except Exception as e:
                    print(f"[Context] Browser launch failed: {e}")
                return augmented + f"\n[SYSTEM CONTEXT: The last result URL was {last_url}. Open it in {target_browser}.]"
            else:
                # No URL found — inject context so LLM can retrieve from memory
                return augmented + f"\n[SYSTEM CONTEXT: User wants to open the previous result in {target_browser}. Check conversation history for URL.]"

        return augmented

    def _check_skill(self, user_input: str) -> str | None:
        try:
            from skills import find_skill, execute_skill, load_skills
            m = re.match(r"^/skill\s+(\S+)\s*(.*)", user_input.strip())
            if m:
                name = m.group(1)
                args = m.group(2).strip()
                for s in load_skills():
                    if s.name == name:
                        return execute_skill(s, args, self)
                skill = find_skill(f"/{name}")
                if skill:
                    return execute_skill(skill, args, self)
                return f"[Skill '{name}' not found]"

            first = user_input.split()[0] if user_input.strip() else ""
            skill = find_skill(first)
            if skill:
                return execute_skill(skill, user_input[len(first):].strip(), self)
        except Exception as e:
            print(f"[JARVIS] Skill check error: {e}")
        return None

    def chat(self, user_input: str) -> str:
        """Main ReAct loop — handles any user request."""
        mode_result = self._parse_mode(user_input)
        if mode_result:
            return mode_result

        skill_result = self._check_skill(user_input)
        if skill_result:
            return skill_result

        # Antigravity 0-Token Intent Bypass
        try:
            from core.intent_engine import DeterministicIntentEngine
            from context.token_manager import TokenBudgetManager
            intent_res = DeterministicIntentEngine.parse_and_execute(user_input)
            if intent_res and intent_res.get("executed"):
                TokenBudgetManager().record_usage(consumed=0, saved=intent_res.get("tokens_saved", 2000), is_bypassed=True)
                return f"⚡ [Antigravity Instant 0-Token Action]\n{intent_res.get('result')}"
        except Exception:
            pass

        # EventBus Task start telemetry
        import uuid
        from events.bus import get_event_bus
        from events.types import TaskEvent
        
        task_id = str(uuid.uuid4())
        event_bus = get_event_bus()
        
        event_bus.publish(TaskEvent(
            topic="task.react.start",
            task_id=task_id,
            goal=user_input,
            status="started"
        ))

        memory_ctx = self._recall_context(user_input)
        augmented  = f"{memory_ctx}{user_input}" if memory_ctx else user_input

        # Context-aware pronoun/browser resolution: 'open it in brave/chrome/edge'
        augmented = self._resolve_context_references(user_input, augmented)

        # Smart Context Trimming to maintain sub-300ms inference latency while preserving root user goal
        try:
            if hasattr(self.working_memory, "trim") and len(self.working_memory.get()) > 10:
                # Preserve root turn at index 0
                root_msg = self.working_memory.get()[0] if self.working_memory.get() else None
                self.working_memory.trim(max_turns=10)
                if root_msg and root_msg not in self.working_memory.get():
                    self.working_memory.messages.insert(0, root_msg)
        except Exception:
            pass

        # CRITICAL: Add user message to working memory BEFORE LLM call
        self.working_memory.add("user", augmented)
        self._record_turn("user", user_input)

        keywords = self._extract_keywords(user_input)
        profile  = self.router.route(keywords)
        system   = self._build_system(user_input)

        # Conscious Step Planning & Adaptive Flexible Step Budget
        from agent.step_planner import StepPlanner
        plan_info = StepPlanner.plan_steps(user_input)
        budget = plan_info["budget_controller"]
        print(f"[StepPlanner] 🧠 Conscious Plan for '{user_input[:40]}...' ({plan_info['complexity']} Complexity, Initial Budget: {budget.initial_budget} steps)")

        final_response = ""
        success = True
        _consecutive_tool: dict = {"name": None, "args_str": None, "count": 0}  # duplicate-call guard
        tool_history: list = []
        step = 0

        while True:
            should_continue, budget_msg, was_extended = budget.evaluate(step, tool_history)
            if was_extended:
                print(f"[StepBudget] {budget_msg}")
            if not should_continue:
                print(f"[StepBudget] ⏹ Step limit reached: {budget_msg}")
                final_response += f"\n\n[BR: Step budget completed ({budget.current_budget} steps). Returning current results.]"
                break

            t_start = time.monotonic()

            try:
                response = self.router.run(profile, self.working_memory.get(), system)
            except Exception as e:
                final_response = f"Backend error: {e}"
                success = False
                event_bus.publish(TaskEvent(
                    topic="task.react.failed",
                    task_id=task_id,
                    goal=user_input,
                    status=f"error: {e}"
                ))
                break

            latency_ms = int((time.monotonic() - t_start) * 1000)
            tool_name, tool_args = parse_tool_call(response)

            if tool_name:
                # ── Duplicate-call guard ──────────────────────────────────
                import json
                args_str = json.dumps(tool_args or {}, sort_keys=True)
                if tool_name == _consecutive_tool["name"] and args_str == _consecutive_tool.get("args_str"):
                    _consecutive_tool["count"] += 1
                else:
                    _consecutive_tool = {"name": tool_name, "args_str": args_str, "count": 1}

                if _consecutive_tool["count"] >= 4:
                    print(f"[JARVIS] ⛔ Duplicate-call limit reached (x{_consecutive_tool['count']}). Terminating loop to prevent infinite token burn.")
                    final_response = f"[BR: Duplicate tool call limit reached for '{tool_name}'. Proceeding with accumulated results.]"
                    break

                print(f"[JARVIS] 🧠 Step {step+1}/{budget.current_budget}: {tool_name}({list(tool_args.keys() if tool_args else [])})")
                t_tool = time.monotonic()
                if _consecutive_tool["count"] >= 3:
                    tool_result = (
                        f"[SYSTEM NOTICE: '{tool_name}' has been executed {_consecutive_tool['count']} times consecutively with identical arguments. "
                        f"DO NOT call '{tool_name}' again. Use the tool result provided above to directly answer the user's request now.]"
                    )
                else:
                    try:
                        tool_result = execute_tool(tool_name, tool_args or {})
                    except Exception as tool_err:
                        tool_result = f"[Tool Error: {tool_name} failed — {tool_err}. Try an alternative approach.]"
                tool_ms = int((time.monotonic() - t_tool) * 1000)

                tool_history.append({
                    "step": step,
                    "tool_name": tool_name,
                    "args": tool_args,
                    "result": tool_result,
                })

                self._record_turn(
                    "assistant", response[:2000],
                    tool_name=tool_name, tool_args=tool_args,
                    tool_result=str(tool_result)[:2000],
                    backend=profile.value, latency_ms=tool_ms,
                )

                clean = re.sub(r'```tool_call\s*\n\s*\{.*?\}\s*\n\s*```', '', response, flags=re.DOTALL).strip()
                clean = re.sub(r'<\|start\|>.*?<\|call\|>', '', clean, flags=re.DOTALL)
                clean = re.sub(r'<\|channel\|>.*?<\|call\|>', '', clean, flags=re.DOTALL)
                clean = re.sub(r'<\|message\|>.*?<\|call\|>', '', clean, flags=re.DOTALL)
                clean = re.sub(r'<\|.*?\|>', '', clean).strip()
                if clean:
                    self.working_memory.add("assistant", clean)
                else:
                    self.working_memory.add("assistant", _format_clean_tool_summary(tool_name, tool_args))

                str_res = str(tool_result)
                if len(str_res) > 4000:
                    str_res = str_res[:2000] + "\n\n[... output truncated for context efficiency ...]\n\n" + str_res[-1500:]
                self.working_memory.add("user", f"[Tool Result for '{tool_name}']:\n{str_res}")
                step += 1
                continue

            else:
                # Multi-task continuation guard: push for completion if user asked for multiple items and loop stopped early
                is_multitask = any(k in user_input.lower() for k in ("1.", "2.", "3.", "concurrently", "in parallel", "workflow", "together"))
                if is_multitask and step > 0 and step < 4 and not getattr(self, "_prompted_continuation", False):
                    self._prompted_continuation = True
                    self.working_memory.add("user", "[SYSTEM DIRECTIVE: You completed initial sub-tasks, but the user prompt requested multiple numbered/parallel tasks. Continue executing tools for all remaining items before giving your final text response.]")
                    step += 1
                    continue

                self._prompted_continuation = False
                final_response = re.sub(r'<\|start\|>.*?<\|call\|>', '', response, flags=re.DOTALL)
                final_response = re.sub(r'<\|channel\|>.*?<\|call\|>', '', final_response, flags=re.DOTALL)
                final_response = re.sub(r'<\|message\|>.*?<\|call\|>', '', final_response, flags=re.DOTALL)
                final_response = re.sub(r'<\|.*?\|>', '', final_response).strip()

                if not final_response:
                    try:
                        nudge = (
                            "All requested tasks have been successfully executed using tools. "
                            "Provide a clean, direct, human-readable summary of the results to the user now. "
                            "Do NOT call any more tools."
                        )
                        self.working_memory.add("user", nudge)
                        sum_resp = self.router.run(profile, self.working_memory.get(), nudge)
                        final_response = re.sub(r'<\|start\|>.*?<\|call\|>', '', sum_resp, flags=re.DOTALL)
                        final_response = re.sub(r'<\|channel\|>.*?<\|call\|>', '', final_response, flags=re.DOTALL)
                        final_response = re.sub(r'<\|message\|>.*?<\|call\|>', '', final_response, flags=re.DOTALL)
                        final_response = re.sub(r'<\|.*?\|>', '', final_response).strip()
                    except Exception:
                        pass

                if not final_response:
                    assistant_turns = [
                        m["content"] for m in self.working_memory.get()
                        if m["role"] == "assistant" and not m["content"].strip().startswith("[Executed Tool:")
                    ]
                    if assistant_turns:
                        final_response = assistant_turns[-1]
                    else:
                        final_response = "I have successfully executed the requested operations, sir."

                self._record_turn("assistant", final_response[:5000], backend=profile.value, latency_ms=latency_ms)
                break

        self.working_memory.add("assistant", final_response)
        self._store_exchange(user_input, final_response)
        
        if success:
            event_bus.publish(TaskEvent(
                topic="task.react.completed",
                task_id=task_id,
                goal=user_input,
                status="completed"
            ))
            
        return final_response

    def consolidate_on_exit(self) -> str:
        summary = ""
        try:
            from memory.consolidator import consolidate_session
            saved = consolidate_session(self.working_memory.get(), router=self.router)
            if saved:
                summary = f"Consolidated {len(saved)} memories: {', '.join(saved)}"
        except Exception as e:
            summary = f"Consolidation skipped: {e}"
        return summary

    def shutdown(self):
        summary = self.consolidate_on_exit()
        if self._session_store and self._session_id:
            try:
                self._session_store.close_session(self._session_id, summary=summary)
                if self._history_linker and self._history_linker.available:
                    self._history_linker.on_session_close(
                         self._session_id, summary,
                         mode=self.current_mode,
                         backend=self.router.default.value,
                    )
            except Exception:
                pass

        # SQLite Sync
        if self.conversation_store and self._session_id:
            try:
                self.conversation_store.end_session(self._session_id, summary=summary)
            except Exception:
                pass

        if self._subagent_mgr:
            self._subagent_mgr.shutdown()

    def chat_stream(self, user_input: str):
        """Streaming chat with ReAct loop support — yields tokens as they arrive from the backend."""
        mode_result = self._parse_mode(user_input)
        if mode_result:
            yield mode_result
            return

        skill_result = self._check_skill(user_input)
        if skill_result:
            yield skill_result
            return

        # Antigravity 0-Token Intent Bypass (Streaming)
        try:
            from core.intent_engine import DeterministicIntentEngine
            from context.token_manager import TokenBudgetManager
            intent_res = DeterministicIntentEngine.parse_and_execute(user_input)
            if intent_res and intent_res.get("executed"):
                TokenBudgetManager().record_usage(consumed=0, saved=intent_res.get("tokens_saved", 2000), is_bypassed=True)
                yield f"⚡ [Antigravity Instant 0-Token Action]\n{intent_res.get('result')}"
                return
        except Exception:
            pass

        memory_ctx = self._recall_context(user_input)
        augmented = f"{memory_ctx}{user_input}" if memory_ctx else user_input

        self.working_memory.add("user", augmented)
        self._record_turn("user", user_input)
        try:
            from agent.transcript_logger import get_transcript_logger
            get_transcript_logger(self.session_id).log_step(
                source="USER_EXPLICIT",
                step_type="USER_INPUT",
                content=user_input,
            )
        except Exception:
            pass

        keywords = self._extract_keywords(user_input)
        profile = self.router.route(keywords)
        system = self._build_system()

        for step in range(MAX_REACT_STEPS):
            backend = self.router.backends.get(profile)
            if backend is None:
                backend = self.router.backends.get(self.router.default)
            if backend is None:
                yield "No backend available."
                return

            full_response = ""
            t_start = time.monotonic()

            # Attempt streaming from the backend with retries
            retry_delay = 1.0
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if hasattr(backend, "stream"):
                        for chunk in backend.stream(self.working_memory.get(), system):
                            full_response += chunk
                            yield chunk
                        break
                    else:
                        full_response = backend.complete(self.working_memory.get(), system)
                        yield full_response
                        break
                except Exception as e:
                    if attempt == max_retries - 1:
                        yield f"\n[Backend error: {e}]"
                        return
                    time.sleep(retry_delay)
                    retry_delay *= 2

            latency_ms = int((time.monotonic() - t_start) * 1000)
            tool_name, tool_args = parse_tool_call(full_response)

            if tool_name:
                yield f"\n[JARVIS] 🔧 Step {step+1}: {tool_name}...\n"
                t_tool = time.monotonic()
                try:
                    tool_result = execute_tool(tool_name, tool_args or {})
                except Exception as tool_err:
                    tool_result = f"[Tool Error: {tool_name} failed — {tool_err}. Try an alternative approach.]"
                tool_ms = int((time.monotonic() - t_tool) * 1000)

                self._record_turn(
                    "assistant", full_response[:2000],
                    tool_name=tool_name, tool_args=tool_args,
                    tool_result=str(tool_result)[:2000],
                    backend=profile.value, latency_ms=tool_ms,
                )

                clean = re.sub(r'```tool_call\s*\n\s*\{.*?\}\s*\n\s*```', '', full_response, flags=re.DOTALL).strip()
                if clean:
                    self.working_memory.add("assistant", clean)
                else:
                    self.working_memory.add("assistant", _format_clean_tool_summary(tool_name, tool_args))

                self.working_memory.add("user", f"[Tool Result for '{tool_name}']:\n{tool_result}")
                yield f"[Tool Result: {tool_name} complete]\n"
                continue
            else:
                self._record_turn("assistant", full_response[:5000], backend=profile.value, latency_ms=latency_ms)
                self.working_memory.add("assistant", full_response)
                self._store_exchange(user_input, full_response)
                break
        else:
            yield "\n\n[JARVIS: Max steps reached. Returning current results.]"
