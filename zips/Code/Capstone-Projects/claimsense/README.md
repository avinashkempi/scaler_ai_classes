# ClaimSense — Agentic Motor Insurance Claims Processor

**Author:** Shivank Agrawal

A multi-step AI agent that processes Indian private-car insurance claims end to end:
it reads the claim PDFs, checks the policy, decides coverage by citing policy clauses,
calculates the payable amount, scores fraud risk, auto-approves small clean claims and
routes everything else to a human adjuster or the Special Investigation Unit (SIU).

- Problem statement: `docs/problem.html`
- Full solution walkthrough (design choices, code runs, interview questions): `docs/solution.html`

```
intake -> policy_check -+-> coverage_check -> assess_amount -+-> fraud_check -> route_claim -+-> finalize
 (LLM)     (Python)     |     (RAG + LLM)       (Python)     |   (LLM+Python)    (Python)    |    (LLM letter)
                        +------- policy failed --------------+                               +-> human_review -> finalize
                                                                                                (pauses for adjuster/SIU)
```

## Tech stack
OpenAI `gpt-4.1-mini` (PDF reading, structured outputs) · `text-embedding-3-small` · LangGraph (state machine,
human-in-the-loop, SQLite checkpoints) · FastAPI · Streamlit · SQLite · Docker · Terraform on AWS ECS Fargate.

## Quick start (local, ~5 minutes)
Needs Python 3.11+ and an OpenAI API key.

```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                      # then put your OPENAI_API_KEY in .env

python -m scripts.generate_data                           # DB + 20 sample claim PDFs (no API key needed)
python -m scripts.process_claim CLM-1001 CLM-1014 CLM-1019 # watch the agent work step by step
python -m scripts.review_claim CLM-1014 REJECT 0 "Asha Verma (Adjuster)"
python -m evals.run_evals                                 # accuracy, fraud recall, cost per claim
```

### Run the API and the portal
```bash
uvicorn app.api:app --port 8000          # terminal 1 -> http://localhost:8000/docs
streamlit run ui/portal.py               # terminal 2 -> http://localhost:8501
```

### Run with Docker
```bash
docker compose up --build                # portal :8501, API :8000
```

## Deploy to AWS (ECS Fargate, ap-south-1 by default)
Needs AWS CLI v2 (logged in), Terraform >= 1.5 and Docker.
```bash
export OPENAI_API_KEY=sk-...
bash deploy/deploy.sh      # prints the portal and API URLs at the end
bash deploy/destroy.sh     # deletes EVERY resource it created (do this after your demo)
```
Approximate cost while running: 1 Fargate task (1 vCPU, 2 GB) + public IP, roughly USD 1–2 per day.

## Project structure
```
app/
  config.py      settings, model names, prices, business thresholds
  schemas.py     Pydantic schemas the LLM must fill (structured outputs)
  llm.py         the only file that calls OpenAI; tracks tokens and cost per call
  intake.py      PDF -> typed JSON (one LLM call per document)
  policy_rag.py  clause-level retrieval over the policy wording
  judgments.py   coverage decision, cross-document consistency, customer letter
  rules.py       deterministic money + fraud + routing rules (no LLM)
  graph.py       LangGraph state machine with human-in-the-loop
  service.py     process / review functions shared by API, CLI and evals
  db.py          SQLite: policies, garages, claims, audit log
  api.py         FastAPI endpoints
ui/portal.py     Streamlit: claimant, adjuster, SIU, dashboard
scripts/         generate_data, process_claim, review_claim
evals/           run_evals.py (labels in data/eval_labels.csv)
data/            policy_wording.md, claims.db, sample_claims/CLM-1001..1020
deploy/          deploy.sh, destroy.sh, terraform/
docs/            problem.html, solution.html
```

All companies, people, garages and documents in this project are fictional and for teaching only.
