# tests/adversarial/test_tool_ranker_adversarial.py — 100-Case Hostile Tool Ranking Validation
from __future__ import annotations

import time
from typing import Dict, List, Tuple
import pytest

from tools.tool_ranker import ToolMetadata, ToolRanker


def _build_test_catalog() -> List[ToolMetadata]:
    """Build a realistic catalog of 40 tools."""
    return [
        ToolMetadata(name="web_search", description="Search Google or DuckDuckGo for live internet info", capabilities=["web", "search", "internet"]),
        ToolMetadata(name="web_extractor", description="Extract clean article text from a webpage URL", capabilities=["web", "scrape", "url"]),
        ToolMetadata(name="browser_action", description="Automate browser clicking, navigation, and typing in Chrome", capabilities=["browser", "web", "automation"]),
        ToolMetadata(name="file_read", description="Read content of local text or code file", capabilities=["file", "read", "filesystem"]),
        ToolMetadata(name="file_write", description="Create or overwrite files on disk", capabilities=["file", "write", "filesystem"]),
        ToolMetadata(name="fast_file_search", description="Search desktop for files by name or content", capabilities=["file", "search", "find"]),
        ToolMetadata(name="file_search_semantic", description="Semantic natural language file discovery", capabilities=["file", "search", "semantic"]),
        ToolMetadata(name="run_code", description="Execute sandboxed Python or Bash code", capabilities=["code", "execute", "python"]),
        ToolMetadata(name="code_refactor", description="Refactor and modernize codebases", capabilities=["code", "refactor"]),
        ToolMetadata(name="git_repo_tool", description="Git commit, branch, status, push operations", capabilities=["git", "code", "vcs"]),
        ToolMetadata(name="system_health", description="Check CPU, RAM, disk, and battery telemetry", capabilities=["system", "metrics", "health"]),
        ToolMetadata(name="window_manager", description="List or focus active desktop windows", capabilities=["window", "ui", "desktop"]),
        ToolMetadata(name="open_app", description="Launch or open desktop applications and executables", capabilities=["app", "launch", "desktop"]),
        ToolMetadata(name="send_email", description="Send emails via Gmail or SMTP", capabilities=["email", "communication"]),
        ToolMetadata(name="send_whatsapp", description="Send automated WhatsApp messages", capabilities=["whatsapp", "chat", "communication"]),
        ToolMetadata(name="create_calendar_event", description="Create schedule events on Google Calendar", capabilities=["calendar", "schedule"]),
        ToolMetadata(name="excel_analyze", description="Analyze Excel spreadsheets, formulas, CSV data", capabilities=["excel", "spreadsheet", "data"]),
        ToolMetadata(name="pdf_tools", description="Read, extract, or merge PDF documents", capabilities=["pdf", "document"]),
        ToolMetadata(name="longform_builder", description="Generate multi-volume documentation and books", capabilities=["doc", "book", "write"]),
        ToolMetadata(name="reminder", description="Set scheduled notifications and toast alarms", capabilities=["reminder", "alarm"]),
        ToolMetadata(name="port_scan", description="Scan TCP network ports on target host", capabilities=["network", "security"]),
        ToolMetadata(name="dns_enum", description="Enumerate DNS records for domains", capabilities=["dns", "network"]),
        ToolMetadata(name="headers_audit", description="Audit HTTP security headers of website", capabilities=["web", "security"]),
        ToolMetadata(name="system_optimizer", description="Clean temporary files and optimize RAM memory", capabilities=["system", "memory", "cleanup"]),
    ]


# 100+ Test cases mapping (query, expected_top_tool_in_top_3)
BENCHMARK_CASES: List[Tuple[str, str]] = [
    # 1-10 Web & Search
    ("search the web for the latest python 3.14 features", "web_search"),
    ("find news about Nvidia quarterly earnings", "web_search"),
    ("look up stock prices for Apple online", "web_search"),
    ("fetch the text from https://news.ycombinator.com", "web_extractor"),
    ("extract the article content from this blog url", "web_extractor"),
    ("scrape the main body text of the webpage", "web_extractor"),
    ("automate clicking the sign-in button in Chrome", "browser_action"),
    ("navigate to github in browser and submit the form", "browser_action"),
    ("open browser and fill in the web inputs", "browser_action"),
    ("search online documentation for react hooks", "web_search"),
    
    # 11-20 Files & Filesystem
    ("read the contents of main.py", "file_read"),
    ("open and inspect config.json", "file_read"),
    ("load the contents of README.md", "file_read"),
    ("write a new script to workspace/test.py", "file_write"),
    ("save this text into output.txt", "file_write"),
    ("create a markdown file named summary.md", "file_write"),
    ("find where database.sqlite is located on disk", "fast_file_search"),
    ("search for all .png files on my computer", "fast_file_search"),
    ("find files related to user authentication logic", "file_search_semantic"),
    ("locate the code dealing with payment processing", "file_search_semantic"),

    # 21-30 Code Execution & Development
    ("run this python script to calculate primes", "run_code"),
    ("execute the bash command to list processes", "run_code"),
    ("test this code snippet in sandbox", "run_code"),
    ("refactor this function to improve readability", "code_refactor"),
    ("clean up this spaghetti python code", "code_refactor"),
    ("commit all changes with message fix bug", "git_repo_tool"),
    ("check git status and current branch", "git_repo_tool"),
    ("push commits to remote origin main", "git_repo_tool"),
    ("create a new git branch called feature-ui", "git_repo_tool"),
    ("view uncommitted git diffs", "git_repo_tool"),

    # 31-40 System & Hardware
    ("how much RAM is currently being used?", "system_health"),
    ("check current CPU load and temperature", "system_health"),
    ("is my laptop battery plugged in?", "system_health"),
    ("diagnose system storage space", "system_health"),
    ("show all active desktop window titles", "window_manager"),
    ("bring VS Code window to the foreground", "window_manager"),
    ("switch focus to Spotify", "window_manager"),
    ("launch Visual Studio Code application", "open_app"),
    ("open Calculator app", "open_app"),
    ("launch VLC media player", "open_app"),

    # 41-50 Communication & Calendar
    ("send an email to boss@company.com with project updates", "send_email"),
    ("compose an email to client about invoice", "send_email"),
    ("email the daily report to my team", "send_email"),
    ("send a WhatsApp message to Alex saying hello", "send_whatsapp"),
    ("whatsapp mom that I will be late", "send_whatsapp"),
    ("message John on whatsapp", "send_whatsapp"),
    ("schedule a meeting with marketing for tomorrow 3pm", "create_calendar_event"),
    ("add a calendar event for doctor appointment on Friday", "create_calendar_event"),
    ("book a 30 minute calendar slot for project sync", "create_calendar_event"),
    ("set a reminder to take a break in 45 minutes", "reminder"),

    # 51-60 Office, Docs & Spreadsheets
    ("analyze the quarterly revenue in sales.xlsx", "excel_analyze"),
    ("calculate the average column in this excel spreadsheet", "excel_analyze"),
    ("parse data from the customer CSV file", "excel_analyze"),
    ("extract text from invoice.pdf", "pdf_tools"),
    ("merge two PDF documents into one", "pdf_tools"),
    ("read pages from the user manual pdf", "pdf_tools"),
    ("build a comprehensive multi-volume book on machine learning", "longform_builder"),
    ("generate a complete technical manual for our API", "longform_builder"),
    ("free up unused RAM memory and optimize cache", "system_optimizer"),
    ("clean system temporary files to speed up PC", "system_optimizer"),

    # 61-70 Security & Network
    ("scan open ports on 192.168.1.1", "port_scan"),
    ("check if port 8080 is open on the server", "port_scan"),
    ("enumerate DNS MX and TXT records for google.com", "dns_enum"),
    ("lookup DNS nameservers for example.com", "dns_enum"),
    ("audit HTTP security headers on https://stripe.com", "headers_audit"),
    ("check for missing HSTS and CSP headers on our website", "headers_audit"),
    ("set a reminder to submit the report at 5pm", "reminder"),
    ("notify me tomorrow at 9am about the standup", "reminder"),
    ("alarm me in 10 minutes", "reminder"),
    ("search web for recipes with chicken and rice", "web_search"),

    # 71-80 Mixed Complex Workflows
    ("extract data from the website https://example.com/data", "web_extractor"),
    ("find python scripts in the project directory", "fast_file_search"),
    ("run tests using python test runner", "run_code"),
    ("read server.log file to find error traceback", "file_read"),
    ("write documentation to docs/setup.md", "file_write"),
    ("switch to Chrome browser window", "window_manager"),
    ("open Notepad application", "open_app"),
    ("check system health metrics", "system_health"),
    ("send email reminder to accounting", "send_email"),
    ("send whatsapp confirmation to driver", "send_whatsapp"),

    # 81-90 Edge / Synonyms
    ("look for files named package.json", "fast_file_search"),
    ("read the first 50 lines of script.py", "file_read"),
    ("write unit tests to test_app.py", "file_write"),
    ("evaluate python expression 2 ** 32", "run_code"),
    ("format git commit on current branch", "git_repo_tool"),
    ("check available disk space on C drive", "system_health"),
    ("focus the terminal window", "window_manager"),
    ("open Paint app", "open_app"),
    ("draft an email to support", "send_email"),
    ("message colleague via whatsapp", "send_whatsapp"),

    # 91-105 Contextual / Semi-ambiguous Queries
    ("look up python documentation on the web", "web_search"),
    ("search online for postgres connection error", "web_search"),
    ("scrape the text of the tutorial", "web_extractor"),
    ("read my notes from notes.txt", "file_read"),
    ("save the logs to debug.log", "file_write"),
    ("find where images are saved on disk", "fast_file_search"),
    ("find code handling password reset", "file_search_semantic"),
    ("run the benchmark calculation", "run_code"),
    ("check cpu performance statistics", "system_health"),
    ("optimize memory cache now", "system_optimizer"),
    ("read the contract pdf", "pdf_tools"),
    ("analyze data from the spreadsheet", "excel_analyze"),
    ("schedule sync for next Monday", "create_calendar_event"),
    ("remind me to check oven in 20 minutes", "reminder"),
    ("scan host ports on localhost", "port_scan"),
]


def test_100_cases_tool_ranking_accuracy():
    ranker = ToolRanker()
    catalog = _build_test_catalog()
    for t in catalog:
        ranker.register_metadata(t)

    top_1_hits = 0
    top_3_hits = 0
    total_cases = len(BENCHMARK_CASES)
    latencies = []

    for query, expected_tool in BENCHMARK_CASES:
        t0 = time.perf_counter()
        ranked = ranker.rank_tools(query, available_tools=catalog, top_n=3)
        latencies.append((time.perf_counter() - t0) * 1000.0)

        ranked_names = [t.name for t in ranked]
        if ranked_names and ranked_names[0] == expected_tool:
            top_1_hits += 1
        if expected_tool in ranked_names:
            top_3_hits += 1

    top_1_acc = (top_1_hits / total_cases) * 100.0
    top_3_recall = (top_3_hits / total_cases) * 100.0
    wrong_tool_rate = 100.0 - top_3_recall
    avg_latency = sum(latencies) / len(latencies)

    print("\n" + "="*65)
    print(f"TOOL RANKER ADVERSARIAL EVALUATION ({total_cases} CASES)")
    print("="*65)
    print(f"  • Top-1 Accuracy : {top_1_acc:6.2f}% ({top_1_hits}/{total_cases})")
    print(f"  • Top-3 Recall   : {top_3_recall:6.2f}% ({top_3_hits}/{total_cases})")
    print(f"  • Wrong Tool Rate: {wrong_tool_rate:6.2f}%")
    print(f"  • Avg Latency    : {avg_latency:6.3f} ms")
    print("="*65)

    assert top_3_recall >= 90.0, f"Top-3 recall too low: {top_3_recall}%"
    assert avg_latency < 2.0, f"Average tool ranking latency too high: {avg_latency} ms"
