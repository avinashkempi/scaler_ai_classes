"""
kb_shell.py - a safe, read-only "terminal" over the knowledge base.

Author: Shivank Agrawal
Project: AI Tutor (Agentic RAG) - Future with Shivank

The agent may run ONE command at a time from a small allow-list
(rg, grep, find, ls, sed, head, cat, wc) inside data/kb/. Letting an LLM run
shell commands is dangerous, so every command passes these guards first:

    1. No shell at all: the command is split with shlex and run as an argv
       list (subprocess with shell=False). Pipes, redirects, `;`, `&&`, `$()`
       and backticks are rejected before anything runs.
    2. Program allow-list: only the 8 read-only programs above.
    3. Option allow-list per program: e.g. `find -exec` or `sed -i` (which
       would execute or write) are simply not accepted.
    4. Path jail: every path must resolve INSIDE data/kb/ (no "/etc/passwd",
       no "../../.env").
    5. Limits: timeout, output size cap, and broad searches must use -m.
"""

import json
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache

from app.config import KB_COMMAND_TIMEOUT, KB_DIR, KB_MAX_OUTPUT_CHARS

FORBIDDEN_CHARS = set("|;&<>`$\n")

# Options each program may use. FLAGS take no value; VALUE options take one.
FLAGS = {
    "rg": {"-n", "-i", "-S", "-F", "-w", "-l", "-c"},
    "grep": {"-n", "-i", "-w", "-F", "-E", "-l", "-c", "-r"},
    "ls": {"-1", "-a", "-l", "-la"},
    "wc": {"-l", "-w", "-c"},
}
VALUE_OPTIONS = {
    "rg": {"-m", "-g"},
    "grep": {"-m"},
}
FIND_OPTIONS = {"-maxdepth", "-mindepth", "-type", "-name", "-iname"}

USAGE = (
    "Allowed forms: rg [-n -i -S -F -w -l -c] [-m N] [-g GLOB] PATTERN [PATH...] | "
    "grep [-n -i -w -F -E -l -c -r] [-m N] PATTERN [PATH...] | "
    "find [PATH] [-maxdepth N] [-type f|d] [-name GLOB] | ls [-1 -a -l] [PATH...] | "
    "sed -n START,ENDp FILE | head [-n N] FILE | cat FILE [FILE...] | wc [-l -w -c] FILE"
)


class KbCommandError(ValueError):
    """Raised when a command breaks one of the safety rules."""


@dataclass
class KbResult:
    command: str
    output: str
    exit_code: int
    read_paths: list[str] = field(default_factory=list)  # raw/ files that were read


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
def jail_path(path: str) -> str:
    """Accept a path only if it stays inside the KB folder."""
    if path.startswith(("/", "~")):
        raise KbCommandError(f"absolute paths are not allowed: {path} (use paths like raw/docs/...)")
    resolved = (KB_DIR / path).resolve()
    if not resolved.is_relative_to(KB_DIR.resolve()):
        raise KbCommandError(f"path escapes the knowledge base: {path}")
    return path


def split_options(program: str, args: list[str]) -> tuple[list[str], list[str]]:
    """Separate allowed options from positional arguments; reject anything else."""
    options, positional, i = [], [], 0
    while i < len(args):
        arg = args[i]
        if arg == "--":  # everything after -- is positional
            positional.extend(args[i + 1:])
            break
        if arg.startswith("-") and not positional:
            if arg in FLAGS.get(program, set()):
                options.append(arg)
            elif arg in VALUE_OPTIONS.get(program, set()) and i + 1 < len(args):
                options.extend([arg, args[i + 1]])
                i += 1
            else:
                raise KbCommandError(f"option {arg} is not allowed for {program}. {USAGE}")
        else:
            positional.append(arg)
        i += 1
    return options, positional


def build_argv(command: str) -> tuple[list[str], list[str]]:
    """Validate a command and return (argv to execute, raw/ files it reads)."""
    if not command.strip():
        raise KbCommandError("empty command")
    if any(ch in FORBIDDEN_CHARS for ch in command):
        raise KbCommandError("pipes, redirects, chaining and $ are not allowed. One command per call.")
    tokens = shlex.split(command)
    program, args = tokens[0], tokens[1:]

    if program in ("rg", "grep"):
        options, positional = split_options(program, args)
        if not positional:
            raise KbCommandError(f"{program} needs a PATTERN. {USAGE}")
        pattern, paths = positional[0], [jail_path(p) for p in positional[1:]]
        # "Broad" = no path, or a folder under raw/ (thousands of possible hits).
        broad = not paths or any(p.startswith("raw") and (KB_DIR / p).is_dir() for p in paths)
        if broad and "-m" not in options:
            raise KbCommandError(f"broad {program} searches must limit matches with -m N (e.g. -m 20)")
        if program == "grep" and paths and any((KB_DIR / p).is_dir() for p in paths) and "-r" not in options:
            options.append("-r")  # grep needs -r to search inside a folder
        return [program, *options, "--", pattern, *paths], []

    if program == "find":
        argv, i = ["find"], 0
        if args and not args[0].startswith("-"):
            argv.append(jail_path(args[0]))
            i = 1
        else:
            argv.append(".")
        while i < len(args):
            option = args[i]
            if option not in FIND_OPTIONS or i + 1 >= len(args):
                raise KbCommandError(f"find only accepts -maxdepth/-mindepth/-type/-name/-iname. {USAGE}")
            value = args[i + 1]
            if option == "-type" and value not in ("f", "d"):
                raise KbCommandError("find -type must be f or d")
            if option in ("-maxdepth", "-mindepth") and not value.isdigit():
                raise KbCommandError(f"find {option} needs a number")
            argv.extend([option, value])
            i += 2
        return argv, []

    if program == "ls":
        options, positional = split_options(program, args)
        return ["ls", *options, *[jail_path(p) for p in positional]], []

    if program == "sed":
        if len(args) != 3 or args[0] != "-n" or not re.fullmatch(r"\d+,\d+p", args[1]):
            raise KbCommandError("sed is only allowed as: sed -n START,ENDp FILE")
        path = jail_path(args[2])
        return ["sed", "-n", args[1], path], [path]

    if program == "head":
        lines, files = "40", list(args)
        if files and files[0] == "-n" and len(files) > 1:
            lines, files = files[1], files[2:]
        elif files and re.fullmatch(r"-\d+", files[0]):
            lines, files = files[0][1:], files[1:]
        if not lines.isdigit() or not files:
            raise KbCommandError("head is only allowed as: head -n N FILE")
        paths = [jail_path(p) for p in files]
        return ["head", "-n", lines, *paths], paths

    if program == "cat":
        if not 1 <= len(args) <= 3 or any(a.startswith("-") for a in args):
            raise KbCommandError("cat takes 1 to 3 files and no options")
        paths = [jail_path(p) for p in args]
        return ["cat", *paths], paths

    if program == "wc":
        options, positional = split_options(program, args)
        return ["wc", *options, *[jail_path(p) for p in positional]], []

    raise KbCommandError(f"'{program}' is not allowed. {USAGE}")


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
def execute_kb_command(command: str) -> KbResult:
    """Validate, run and return the (size-capped) output of one KB command."""
    try:
        argv, read_paths = build_argv(command)
    except (KbCommandError, ValueError) as error:  # ValueError: bad quoting in shlex
        return KbResult(command, f"$ {command}\nerror: {error}", exit_code=2)

    try:
        completed = subprocess.run(
            argv, cwd=KB_DIR, capture_output=True, text=True,
            timeout=KB_COMMAND_TIMEOUT, shell=False,  # shell=False: no shell features at all
        )
    except FileNotFoundError:
        return KbResult(command, f"$ {command}\nerror: {argv[0]} is not installed here. "
                                 "Use grep -rn -m 20 PATTERN PATH instead.", exit_code=127)
    except subprocess.TimeoutExpired:
        return KbResult(command, f"$ {command}\nerror: timed out after {KB_COMMAND_TIMEOUT}s; "
                                 "narrow the path or add -m.", exit_code=124)

    output = completed.stdout + completed.stderr
    if completed.returncode == 1 and not output.strip():
        output = "(no matches)"
    if len(output) > KB_MAX_OUTPUT_CHARS:
        output = output[:KB_MAX_OUTPUT_CHARS] + "\n[output truncated: use sed -n or head to read a smaller part]"
    raw_reads = [p for p in read_paths if p.startswith("raw/")]
    return KbResult(command, f"$ {command}\n{output}", completed.returncode, raw_reads)


@lru_cache(maxsize=1)
def manifest_by_path() -> dict[str, dict]:
    """raw/ path -> {title, url, source}, used to turn files read into citations."""
    rows = (json.loads(line) for line in (KB_DIR / "generated/corpus_manifest.jsonl").open(encoding="utf-8"))
    return {row["path"]: row for row in rows}
