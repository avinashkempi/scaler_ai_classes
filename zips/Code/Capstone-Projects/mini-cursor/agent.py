"""
agent.py - the agent loop: ask the model, run the tools it asks for, repeat.

Author: Shivank Agrawal
Project: Mini Cursor (coding agent in your terminal) - Future with Shivank

    you: "the tests fail, fix it"
        |
        v
    model (gpt-5.4-mini) --function_call--> our code runs the tool (with guards)
        ^                                         |
        +----------- function_call_output --------+
        |
        (repeat until the model answers with text, max MAX_STEPS rounds)
        v
    final answer

We use OpenAI's Responses API. Each request passes `previous_response_id`, so
OpenAI keeps the conversation (and the model's reasoning) on its side; we only
send what is NEW: the user's message, or the results of the tools it asked for.
"""

import json
from pathlib import Path
from typing import Callable

from openai import OpenAI

from tools import TOOL_SCHEMAS, Toolbox

MAX_STEPS = 12  # tool rounds per question; stops a confused model from looping forever

SYSTEM_PROMPT = """You are Mini Cursor, a careful coding agent working inside the
folder {workspace}. All paths are relative to that folder.

How to work:
1. Explore before you change anything: list_files, find_files, read_file.
2. To change code, call write_file with the COMPLETE new file content.
   The user reviews a diff and may reject it.
3. Verify: after a change, run the tests with `pytest -q` when tests exist.
4. Use web_search only for facts that may be newer than your training data
   (latest versions, recent API changes).
5. Never try to read secrets (.env, keys) or work outside the workspace. If a
   tool returns an error, read it, adjust, and try a different approach.

Answer briefly: what you found, what you changed, and the result."""


class CodingAgent:
    def __init__(self, workspace: Path, model: str, approve: Callable[[str], bool],
                 on_step: Callable[[str, dict], None]):
        self.client = OpenAI()  # reads OPENAI_API_KEY from the environment
        self.model = model
        self.tools = Toolbox(workspace, approve)
        self.instructions = SYSTEM_PROMPT.format(workspace=self.tools.root.name)
        self.on_step = on_step  # callback so the CLI can show each step live
        self.last_response_id = None  # conversation memory lives on OpenAI's side

    def new_conversation(self) -> None:
        self.last_response_id = None

    def _call_model(self, input_items, previous_id, allow_tools: bool = True):
        # instructions are NOT carried over by previous_response_id, so send them every time
        return self.client.responses.create(
            model=self.model,
            instructions=self.instructions,
            input=input_items,
            tools=TOOL_SCHEMAS,
            tool_choice="auto" if allow_tools else "none",
            previous_response_id=previous_id,
        )

    def ask(self, user_message: str) -> str:
        """Handle one user message: loop until the model gives a final answer."""
        response = self._call_model(user_message, self.last_response_id)

        for _ in range(MAX_STEPS):
            # Hosted web searches already happened on OpenAI's side; just show them.
            for item in response.output:
                if item.type == "web_search_call":
                    query = getattr(getattr(item, "action", None), "query", "") or ""
                    self.on_step("web_search", {"query": query})

            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                break  # no more tool requests: the model has answered

            outputs = []
            for call in calls:  # the model may ask for several tools at once
                args = json.loads(call.arguments)
                self.on_step("tool_call", {"name": call.name, "args": args})
                result = self.tools.run(call.name, args)
                self.on_step("tool_result", {"name": call.name, "result": result})
                outputs.append({"type": "function_call_output", "call_id": call.call_id, "output": result})

            response = self._call_model(outputs, response.id)
        else:
            # Step limit hit: answer the pending calls and force a text-only reply,
            # so the conversation is never left with unanswered tool calls.
            calls = [item for item in response.output if item.type == "function_call"]
            outputs = [{"type": "function_call_output", "call_id": c.call_id,
                        "output": "Step limit reached. Do not call tools; summarise progress for the user."}
                       for c in calls]
            if outputs:
                response = self._call_model(outputs, response.id, allow_tools=False)

        self.last_response_id = response.id
        return response.output_text
