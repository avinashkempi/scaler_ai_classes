# Mini Cursor: a coding agent in your terminal

**Author:** Shivank Agrawal · Future with Shivank

Chat with an AI agent that works on a folder of code. It explores the files,
finds bugs, writes fixes, runs the tests and searches the web. Every file
change and every test run is shown to you first and needs your "y".

- **Model:** OpenAI `gpt-5.4-mini` through the Responses API
- **Tools:** `list_files`, `read_file`, `find_files`, `write_file`, `run_command`, plus OpenAI's hosted `web_search`
- **Safety:** workspace jail, secret-file blocking, no shell, command allow-list, human approval for writes and test runs

## Project layout

```
main.py        terminal app: chat loop, shows every step, asks for approvals
agent.py       the agent loop (Responses API + tool calls + step limit)
tools.py       tool definitions, implementations and safety guards
sample_project/
  bill_splitter.py        a tiny bill-splitting module (it has a bug)
  test_bill_splitter.py   its pytest tests
```

## Run it

Requires Python 3.10+ and an OpenAI API key.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then put your OPENAI_API_KEY in .env

# chat with the agent about the sample project
python main.py --workspace sample_project

# or ask one-off questions
python main.py --workspace sample_project "What does this project do?"
python main.py --workspace sample_project "The tests are failing. Find the bug and fix it."
```

Inside the chat, type `new` for a fresh conversation and `exit` to quit.
Point `--workspace` at any folder you want the agent to work in. It can't see
or touch anything outside that folder.

---

Idea inspired by Towards AI's open-source local-cursor (which runs on a local
Ollama model). This is an independent, OpenAI-based implementation for learning.
