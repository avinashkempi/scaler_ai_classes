"""
tools.py - the agent's hands: what it may do on your machine, and the guards.

Author: Shivank Agrawal
Project: Mini Cursor (coding agent in your terminal) - Future with Shivank

The model never touches your computer directly. It can only ASK for one of
these tools by name. Our code checks the request and then runs it:

    list_files(path)          list a folder
    read_file(path)           read a text file
    find_files(pattern)       glob search, e.g. "**/*.py"
    write_file(path, content) create/overwrite a file  -> you approve a diff first
    run_command(command)      read-only commands run freely; pytest needs approval
    web_search                hosted by OpenAI (no code here, see TOOL_SCHEMAS)

Guards, because the model's requests are untrusted input:
    1. Workspace jail : every path must resolve INSIDE the workspace folder.
    2. Secret files   : .env, keys, .ssh, .aws, .git are never read or listed.
    3. No shell       : commands run as an argv list (shell=False); characters
                        like | ; & > < ` $ are rejected, so no chaining/redirects.
    4. Allow-list     : only a few read-only programs, plus pytest with approval.
    5. Human approval : every file write and every test run is shown to you first.
    6. Limits         : timeouts and output size caps.
"""

import difflib
import shlex
import subprocess
from pathlib import Path
from typing import Callable

MAX_OUTPUT_CHARS = 10_000  # long outputs are cut so they don't flood the model's context
COMMAND_TIMEOUT = 30  # seconds

READ_ONLY_COMMANDS = {"ls", "cat", "head", "tail", "wc", "grep", "find", "pwd"}
APPROVAL_COMMANDS = {"pytest"}  # runs project code, so you approve each run
FORBIDDEN_CHARS = set("|;&<>`$\n")
BLOCKED_FIND_OPTIONS = {"-exec", "-execdir", "-delete", "-ok", "-okdir", "-fprint", "-fprintf", "-fls"}
SECRET_NAMES = {".env", ".ssh", ".aws", ".git", "id_rsa", "id_ed25519"}
SECRET_SUFFIXES = (".pem", ".key")


class ToolError(Exception):
    """A request the guards refused. The message is sent back to the model."""


# ---------------------------------------------------------------------------
# Tool descriptions for the model (Responses API format).
# strict=True: the model must send exactly these arguments, all of them.
# ---------------------------------------------------------------------------
def _function(name: str, description: str, properties: dict) -> dict:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        },
    }


PATH = {"type": "string", "description": "Path relative to the workspace root, e.g. 'src/app.py' or '.'"}

TOOL_SCHEMAS = [
    _function("list_files", "List the files and folders inside a folder of the workspace.", {"path": PATH}),
    _function("read_file", "Read a text file from the workspace.", {"path": PATH}),
    _function("find_files", "Find files by glob pattern, e.g. '**/*.py' or 'tests/test_*.py'.",
              {"pattern": {"type": "string", "description": "Glob pattern relative to the workspace root"}}),
    _function("write_file", "Create or overwrite a file with the FULL new content. The user must approve the change.",
              {"path": PATH, "content": {"type": "string", "description": "The complete new file content"}}),
    _function("run_command",
              "Run one command in the workspace. Allowed: ls, cat, head, tail, wc, grep, find, pwd, "
              "and pytest (the user must approve). No pipes, redirects or chaining.",
              {"command": {"type": "string", "description": "A single command, e.g. 'pytest -q' or 'grep -n def app.py'"}}),
    {"type": "web_search"},  # hosted tool: OpenAI runs the search, our code does nothing
]


class Toolbox:
    def __init__(self, workspace: Path, approve: Callable[[str], bool]):
        self.root = workspace.resolve()
        self.approve = approve  # asks the human; returns True/False

    # -- guards --------------------------------------------------------------
    def safe_path(self, path: str) -> Path:
        """Resolve a path and make sure it stays inside the workspace and isn't a secret."""
        resolved = (self.root / path).resolve()
        if not resolved.is_relative_to(self.root):
            raise ToolError(f"'{path}' is outside the workspace. Use paths inside {self.root.name}/.")
        relative_parts = resolved.relative_to(self.root).parts
        if any(part in SECRET_NAMES or part.endswith(SECRET_SUFFIXES) for part in relative_parts):
            raise ToolError(f"'{path}' looks like a secret (keys, .env, .git). Access denied.")
        return resolved

    def is_secret(self, path: Path) -> bool:
        return any(part in SECRET_NAMES or part.endswith(SECRET_SUFFIXES)
                   for part in path.relative_to(self.root).parts)

    # -- tools ---------------------------------------------------------------
    def list_files(self, path: str) -> str:
        folder = self.safe_path(path)
        if not folder.is_dir():
            raise ToolError(f"'{path}' is not a folder.")
        entries = []
        for item in sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name)):
            if self.is_secret(item) or item.name in ("__pycache__", ".pytest_cache"):
                continue
            entries.append(f"{item.name}/" if item.is_dir() else f"{item.name}  ({item.stat().st_size} bytes)")
        return "\n".join(entries) or "(empty folder)"

    def read_file(self, path: str) -> str:
        file = self.safe_path(path)
        if not file.is_file():
            raise ToolError(f"'{path}' does not exist or is not a file.")
        return file.read_text(encoding="utf-8", errors="replace")

    def find_files(self, pattern: str) -> str:
        if pattern.startswith("/") or ".." in pattern:
            raise ToolError("Patterns must be relative to the workspace (no '/' at the start, no '..').")
        matches = [p for p in sorted(self.root.glob(pattern))
                   if p.is_file() and not self.is_secret(p) and "__pycache__" not in p.parts]
        return "\n".join(str(p.relative_to(self.root)) for p in matches[:200]) or "(no matches)"

    def write_file(self, path: str, content: str) -> str:
        file = self.safe_path(path)
        old = file.read_text(encoding="utf-8") if file.exists() else ""
        if old == content:
            return f"No change: {path} already has this content."
        # Show the human exactly what will change, as a unified diff.
        diff = "".join(difflib.unified_diff(
            old.splitlines(keepends=True), content.splitlines(keepends=True),
            fromfile=f"a/{path}" if old else "/dev/null", tofile=f"b/{path}"))
        if not self.approve(f"write {path}\n{diff}"):
            return f"The user REJECTED the change to {path}. Ask what they want instead."
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
        return f"Wrote {path} ({len(content.splitlines())} lines)."

    def run_command(self, command: str) -> str:
        if any(ch in FORBIDDEN_CHARS for ch in command):
            raise ToolError("Pipes, redirects, chaining (; && |) and $ are not allowed. Send one simple command.")
        argv = shlex.split(command)
        if not argv:
            raise ToolError("Empty command.")
        program = argv[0]
        if program not in READ_ONLY_COMMANDS | APPROVAL_COMMANDS:
            allowed = ", ".join(sorted(READ_ONLY_COMMANDS | APPROVAL_COMMANDS))
            raise ToolError(f"'{program}' is not allowed. Allowed commands: {allowed}.")
        if program == "find" and BLOCKED_FIND_OPTIONS & set(argv):
            raise ToolError("find may only search (no -exec, -delete or -fprint).")
        if program == "grep":  # a recursive grep must not read secret files
            argv[1:1] = ["--exclude=.env*", "--exclude=*.pem", "--exclude=*.key", "--exclude=id_*",
                         "--exclude-dir=.git", "--exclude-dir=.ssh", "--exclude-dir=.aws"]
        for arg in argv[1:]:  # any argument that looks like a path must stay inside the workspace
            if not arg.startswith("-") and ("/" in arg or arg.startswith(".") or (self.root / arg).exists()):
                self.safe_path(arg)
        if program in APPROVAL_COMMANDS and not self.approve(f"run `{command}`"):
            return f"The user REJECTED running `{command}`."
        completed = subprocess.run(argv, cwd=self.root, capture_output=True, text=True,
                                   timeout=COMMAND_TIMEOUT, shell=False)
        output = (completed.stdout + completed.stderr).strip() or "(no output)"
        if len(output) > MAX_OUTPUT_CHARS:
            output = output[:MAX_OUTPUT_CHARS] + "\n[output truncated]"
        return f"exit code {completed.returncode}\n{output}"

    # -- dispatcher ----------------------------------------------------------
    def run(self, name: str, args: dict) -> str:
        """Run a tool by name. Errors become text the model can read and react to."""
        tool = {"list_files": self.list_files, "read_file": self.read_file, "find_files": self.find_files,
                "write_file": self.write_file, "run_command": self.run_command}.get(name)
        if tool is None:
            return f"error: unknown tool '{name}'"
        try:
            result = tool(**args)
        except ToolError as error:
            return f"error: {error}"
        except subprocess.TimeoutExpired:
            return f"error: command timed out after {COMMAND_TIMEOUT}s"
        except (OSError, ValueError) as error:  # ValueError: bad quotes in shlex
            return f"error: {error}"
        if len(result) > MAX_OUTPUT_CHARS:
            result = result[:MAX_OUTPUT_CHARS] + "\n[output truncated]"
        return result
