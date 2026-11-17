"""
main.py - the terminal app: chat with the coding agent, see every step,
approve every change.

Author: Shivank Agrawal
Project: Mini Cursor (coding agent in your terminal) - Future with Shivank

Usage (from this folder):
    python main.py --workspace sample_project                 # interactive chat
    python main.py --workspace sample_project "What does this project do?"
                                                               # ask, then exit
Inside the chat: type `new` for a fresh conversation, `exit` to quit.
"""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from agent import CodingAgent

# ANSI colours for the terminal (only for display; the model never sees them)
GREEN, CYAN, YELLOW, RED, DIM, BOLD, RESET = (
    "\033[32m", "\033[36m", "\033[33m", "\033[31m", "\033[2m", "\033[1m", "\033[0m")


def show_step(kind: str, data: dict) -> None:
    """Print each agent step as it happens."""
    if kind == "tool_call":
        args = ", ".join(f"{k}={json.dumps(v)[:60]}" for k, v in data["args"].items() if k != "content")
        print(f"{CYAN}  -> {data['name']}({args}){RESET}")
    elif kind == "tool_result":
        lines = data["result"].splitlines() or [""]
        failed = lines[0].startswith("error") or "REJECTED" in lines[0]
        if failed:
            summary = lines[0]
        elif data["name"] == "read_file":
            summary = f"read {len(lines)} lines"
        elif data["name"] == "run_command":
            summary = f"{lines[0]} · {lines[-1]}"  # e.g. "exit code 1 · 1 failed, 3 passed in 0.02s"
        else:
            summary = lines[0] + (f"  (+{len(lines) - 1} more lines)" if len(lines) > 1 else "")
        print(f"{RED if failed else DIM}  <- {summary[:110]}{RESET}")
    elif kind == "web_search":
        print(f"{CYAN}  -> web_search({json.dumps(data['query'])}){RESET}")


def approve(request: str) -> bool:
    """Ask the human before a file write or a test run. Shows the diff in colour."""
    title, _, diff = request.partition("\n")
    print(f"\n{YELLOW}{BOLD}  Approval needed: {title}{RESET}")
    for line in diff.splitlines():
        colour = GREEN if line.startswith("+") else RED if line.startswith("-") else DIM
        print(f"  {colour}{line}{RESET}")
    return input(f"{YELLOW}  Allow? [y/N] {RESET}").strip().lower() in ("y", "yes")


def main() -> None:
    load_dotenv(Path(__file__).parent / ".env")  # OPENAI_API_KEY
    parser = argparse.ArgumentParser(description="Mini Cursor: a coding agent in your terminal")
    parser.add_argument("questions", nargs="*", help="optional questions to ask, then exit")
    parser.add_argument("--workspace", default=".", help="folder the agent may work in")
    parser.add_argument("--model", default=os.getenv("CHAT_MODEL", "gpt-5.4-mini"))
    args = parser.parse_args()

    workspace = Path(args.workspace)
    agent = CodingAgent(workspace, args.model, approve=approve, on_step=show_step)
    print(f"{BOLD}Mini Cursor{RESET} · model {args.model} · workspace {workspace.resolve()}")

    def handle(question: str) -> None:
        print(f"\n{GREEN}{BOLD}you>{RESET} {question}")
        answer = agent.ask(question)
        print(f"\n{BOLD}agent>{RESET} {answer}")

    if args.questions:  # one-shot mode: same conversation for all questions
        for question in args.questions:
            handle(question)
        return

    print(f"{DIM}Type 'new' for a fresh conversation, 'exit' to quit.{RESET}")
    while True:
        try:
            question = input(f"\n{GREEN}{BOLD}you>{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in ("exit", "quit"):
            break
        if question.lower() == "new":
            agent.new_conversation()
            print(f"{DIM}(new conversation){RESET}")
            continue
        if question:
            answer = agent.ask(question)
            print(f"\n{BOLD}agent>{RESET} {answer}")


if __name__ == "__main__":
    main()
