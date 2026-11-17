"""Topic table for the AI/ML Learnings library (AI-ML-Learnings/), built by tools/build_library.py.

Each lesson is one repo from github.com/scaler-content. A "group" puts a class with its pre-read and
post-read on one card. Repos the site already hosts point at our copy (SITE) instead of a second copy.
"""
import re

SOURCE_ORG = "https://github.com/scaler-content"

# Repos left out: empty, unbuilt React source (blank page even on Scaler's own site), or not a lesson.
SKIP = {
    "AI-infused-learning-proj1": "empty repo",
    "data-melting-process-data-transformation-flow": "empty repo",
    "identifying-missing-values-data-grid-with-highlighted-gaps": "unbuilt React source, no page to show",
    "interactive-type-casting-type-casting-storyboard": "unbuilt React source, no page to show",
    "DSML-curriculum": "a sales playbook, not a lesson",
}

# Same page as one this site already hosts: the card opens our copy.
SITE = {
    "your-first-agent": "AWS-Bootcamp/your-first-agent/",
    "giving-agents-tools": "AWS-Bootcamp/giving-agents-tools/",
    "Agents-that-remember": "AWS-Bootcamp/Agents-that-remember/",
    "How-agents-talk": "AWS-Bootcamp/How-agents-talk/",
    "shipping-agents-to-production": "AWS-Bootcamp/shipping-agents-to-production/",
    "evals-observability-governance": "AWS-Bootcamp/evals-observability-governance/",
    "senior-ai-engineer-interview": "Interview-Ready/questions/",
    "AI-infused-learning-6": "Learnings/Class-6-AI-infusion/",
    "class-2-AI-engg": "Learnings/Class-2-AI-infusion/",
    "class-3-AI-engg": "Learnings/Class-3-4-AI-infusion/",
}

# (slug, title, short line, [(section, [repo patterns in order])])
# A pattern is a repo name or a regex (with {n} for the class number, expanded 1..30).
TOPICS = [
    ("python", "Python & developer foundations",
     "Set up your laptop, learn Python from the first variable to classes and files, then write Python the way production AI code needs it: tested, validated and safe with secrets.",
     [("Setup & Git", ["python-git-starter"]),
      ("Python foundations", ["python-Foundations-{n}"]),
      ("Production Python", ["production-python-class{n}"]),
      ("Python for data science", ["DSML-Python-{n}"])]),
    ("genai", "GenAI & prompting",
     "What large language models are, how to call one, and how to write prompts that work: roles, few-shot examples, chain-of-thought, grounding and prompt injection.",
     [("Start here", ["AI-infused-session", "class-1-AI-engg", "Academy-AI-class-1", "AI-beginners-class1"]),
      ("Prompt engineering", ["Academy-AI-class-2", "AI-beginners-class2", "Academy-AI-class-3", "AI-beginners-class3"]),
      ("Prompt management", ["AI-beginners-class19"])]),
    ("ai-tools", "AI tools & coding with AI",
     "The assistants and tools around the models: saved instructions and projects, multimodal generation, content tools, vibe coding and the Claude ecosystem.",
     [("Assistants & saved instructions", ["Academy-AI-class-4", "AI-beginners-class4", "AI-beginners-class18", "scaler-claude-curriculum"]),
      ("Coding with AI", ["AI-beginners-class17"]),
      ("Content & multimodal", ["AI-beginners-class8", "AI-beginners-class9"])]),
    ("rag", "RAG & retrieval",
     "Give a model your own documents: embeddings, chunking, vector databases and grounded answers with citations.",
     [("RAG", ["Understanding-the-landscape-of-RAG-", "Academy-AI-class-5", "AI-beginners-class5", "class-3-AI-engg"]),
      ("Web research & citations", ["AI-beginners-class6"])]),
    ("agents", "AI agents",
     "From the think-act-observe loop to tools, memory, MCP and teams of agents, with and without code, up to agents on AWS.",
     [("What an agent is", ["Academy-AI-class-7", "AI-beginners-class13", "class-2-AI-engg"]),
      ("Tools, memory & MCP", ["AI-beginners-class14"]),
      ("Personal & multi-agent systems", ["AI-beginners-class16", "Academy-AI-class-9"]),
      ("Agents on AWS", ["class-5-AI-engg", "AI-infused-learning-6", "your-first-agent", "giving-agents-tools",
                         "Agents-that-remember", "How-agents-talk", "shipping-agents-to-production",
                         "evals-observability-governance"])]),
    ("automation", "No-code automation & chatbots",
     "Automate work without code: n8n and Zapier workflows, agents built from nodes, and no-code chatbots.",
     [("Workflow automation", ["AI-beginners-class10", "Academy-AI-class-6", "AI-beginners-class11", "AI-beginners-class12"]),
      ("No-code agents & chatbots", ["Academy-AI-class-8", "AI-beginners-class15", "AI-beginners-class7"])]),
    ("ai-engineering", "AI system design & deployment",
     "Design an AI system that holds up: chatbot vs workflow vs agent, evaluation and observability, then deploy it on a platform or on AWS. Ends with the senior AI engineer interview.",
     [("System design & evaluation", ["AI-beginners-class20"]),
      ("Deploying AI apps", ["AI-beginners-class21", "AI-beginners-class22", "AI-beginners-class23"]),
      ("Interview", ["senior-ai-engineer-interview"])]),
    ("fde", "Forward Deployed Engineering",
     "Case studies on taking AI from a demo to a customer's real data: why fluent output is not evidence, filters that drop cases, and saves you can trust.",
     [("Pre-reads", ["FDE-preRead-Class{n}"]),
      ("SQL for FDE", ["FDE-SQL-2"])]),
    ("mlops", "MLOps",
     "Run machine learning in production: Git, FastAPI services, experiment tracking, Docker, deploying APIs on AWS, CI/CD and SageMaker.",
     [("Foundations", ["MLOPS-1", "MLOPS-2", "MLOPS-3"]),
      ("Serving & tracking", ["MLOPS-4", "MLOPS-5", "MLOPS-6", "MLOPS-7"]),
      ("Deploy & CI/CD", ["MLOPS-8", "MLOPS-9", "MLOPS-10"]),
      ("SageMaker", ["MLOPS-11", "MLOPS-12", "MLOPS-13", "MLOPS-14"])]),
    ("ml", "Machine learning: supervised",
     "Learn from labelled data: regression, classification, model evaluation, cross-validation, trees and ensembles.",
     [("Regression", ["Intro-to-ML-engg-LR1", "ML-with-AI-workflows-1", "ML-with-AI-workflows-2", "ML-with-AI-workflows-3",
                      "ML-with-AI-workflows-4", "ML-with-AI-workflows-5", "ML-with-AI-workflows-6", "Linear-Regression-{n}",
                      "Maths-postread-Regression"]),
      ("Regularisation & validation", ["ML-with-AI-workflows-7", "sklearn-pipelines", "cross-validation-in-ML",
                                       "Maths-postread-Pipelines-CV"]),
      ("Classification & evaluation", ["ML-with-AI-workflows-8", "ML-with-AI-workflows-11", "logistic-regression",
                                       "ML-with-AI-workflows-9", "classification-metrics", "ML-with-AI-workflows-10",
                                       "Model-evaluation-and-Intro-to-KNN", "KNN-based-imputation-and-Decision-Trees-intro",
                                       "naive-bayes"]),
      ("Trees & ensembles", ["Decision-trees", "Ensembles", "bagging", "boosting"]),
      ("DSML supervised learning", ["DSML-SL-{n}"])]),
    ("ml-unsupervised", "Unsupervised learning, recommenders & time series",
     "Find structure without labels: clustering, dimensionality reduction and anomaly detection, then recommender systems and time-series forecasting.",
     [("Clustering", ["Intro-to-clustering-and-K-means", "K-means-and-K-means-Clustering", "Hierarchical-Clustering",
                      "DBSCAN", "Gaussian-Mixture-Models-"]),
      ("Dimensionality reduction & anomalies", ["Principal-Component-Analysis", "t-SNE-and-UMAP", "Anomaly-Detection"]),
      ("DSML unsupervised learning", ["DSML-UnSL-{n}"]),
      ("Recommender systems", ["Recommender-Systems-{n}", "LightFM-extra-read"]),
      ("Time series", ["Timeseries-{n}"])]),
    ("deep-learning", "Deep learning & neural networks",
     "How neural networks learn: neurons, backpropagation, optimisers, embeddings, PyTorch, autoencoders and explainability.",
     [("Neural networks", ["Neural-Networks-{n}"]),
      ("DSML neural networks", ["DSML-NN-{n}"])]),
    ("cv", "Computer vision",
     "Teach models to see: CNNs, transfer learning, image embeddings and similarity search, detection, segmentation and GANs.",
     [("Computer vision", ["AIML-CV-{n}"]),
      ("DSML computer vision", ["DSML-CV-{n}"])]),
    ("maths", "Maths & NumPy",
     "The maths behind the models, with NumPy to run it: vectors and matrices, optimisation, and array work through interactive simulations.",
     [("NumPy", ["NumPy-{n}", "DAV-1", "DAV---1-Numpy-2"]),
      ("Linear algebra", ["DSML-Lin-Alg-{n}"]),
      ("Optimisation", ["DSML-optmz-{n}"])]),
    ("data", "Data analytics",
     "Work with data: Pandas, SQL, Excel, Tableau dashboards and product analytics.",
     [("Pandas", ["DSML-Pandas-{n}"]),
      ("SQL", ["SQL", "Class2_SQL_postRead", "SQL-7-postread", "SQL-8-postread", "DSML-2026", "MySQL---BigQuery-data-interconverter"]),
      ("Excel", ["Excel-{n}-postread"]),
      ("Tableau", ["Tableau-{n}-postread"]),
      ("Product analytics", ["DSML-PA-{n}"])]),
]

# Pre-read / class / post-read suffixes that share one card.
PART = re.compile(r"^(?P<base>.+?)[-_]?(?P<part>pre[-_]?read|post[-_]?read)$", re.I)


def group_key(repo):
    """Card key and part ("pre", "class", "post") for a repo name."""
    m = PART.match(repo)
    if m:
        part = "pre" if m.group("part").lower().startswith("pre") else "post"
        base = m.group("base")
    else:
        part, base = "class", repo
    base = re.sub(r"^beginner-(\d+)$", r"AI-beginners-class\1", base)
    return base, part


def assign(repos):
    """Map every repo to (topic slug, section, order). Unassigned repos are returned separately."""
    keys = {}
    for r in repos:
        keys.setdefault(group_key(r)[0], []).append(r)
    placed, order = {}, 0
    for slug, _t, _d, sections in TOPICS:
        for section, pats in sections:
            for pat in pats:
                if "{n}" in pat:
                    names = [pat.format(n=n) for n in range(1, 31)]
                else:
                    names = [pat]
                for name in names:
                    for base in (name, group_key(name)[0]):
                        for r in keys.get(base, []):
                            if r not in placed:
                                order += 1
                                placed[r] = (slug, section, order)
    rest = [r for r in repos if r not in placed and r not in SKIP]
    return placed, rest


# Deeper Study: hand-picked cards (card keys, see group_key) in a suggested order.
DEEPER = [
    ("basics", "Basics", "Start here",
     "The foundation the AI lessons assume: a working laptop and Git, enough Python, how LLMs and prompts work, and what an agent is.",
     ["python-git-starter", "production-python-class1", "production-python-class2", "python-Foundations-1",
      "python-Foundations-5", "python-Foundations-10", "AI-infused-session", "AI-beginners-class1",
      "Academy-AI-class-2", "AI-beginners-class2", "Academy-AI-class-3", "Academy-AI-class-7",
      "AI-beginners-class13", "AI-beginners-class21", "AI-beginners-class22"]),
    ("advanced", "Advanced", "Build it properly",
     "Engineering depth for AI apps and agents: production Python, RAG, coding with AI, system design, MLOps and taking AI to a customer.",
     ["production-python-class4", "production-python-class5", "production-python-class7", "production-python-class8",
      "production-python-class9", "Academy-AI-class-5", "Understanding-the-landscape-of-RAG-", "AI-beginners-class14",
      "AI-beginners-class17", "AI-beginners-class18", "AI-beginners-class19", "AI-beginners-class20",
      "MLOPS-1", "MLOPS-4", "MLOPS-7", "MLOPS-8", "MLOPS-9", "MLOPS-10", "FDE-preRead-Class1", "FDE-preRead-Class3"]),
    ("deeper", "Deeper", "Under the hood",
     "The maths and machine learning under the models: vectors, neural networks and embeddings, similarity search, evaluation metrics and data work.",
     ["DSML-Lin-Alg-1", "NumPy-3", "Neural-Networks-1", "Neural-Networks-2", "Neural-Networks-4", "Neural-Networks-7",
      "DSML-NN-10", "AIML-CV-4", "AIML-CV-5", "Model-evaluation-and-Intro-to-KNN", "classification-metrics",
      "ML-with-AI-workflows-9", "cross-validation-in-ML", "Recommender-Systems-3", "Principal-Component-Analysis",
      "t-SNE-and-UMAP", "Anomaly-Detection", "DSML-PA-10", "SQL-7", "SQL-8"]),
]

# AWS Bootcamp add-ons: for each bootcamp lesson or capstone page, the cards that prepare for it or go deeper.
ADDONS = [
    ("Before Lesson 1 · Your first AI agent", "AWS-Bootcamp/your-first-agent/",
     ["python-git-starter", "production-python-class2", "Academy-AI-class-2", "Academy-AI-class-7"]),
    ("Giving agents tools · Tool calling basics", "AWS-Bootcamp/tool-calling-basics/",
     ["production-python-class5", "Class2_SQL", "SQL-8"]),
    ("Agents that remember · Memory explained", "AWS-Bootcamp/memory-explained/",
     ["AI-beginners-class14", "Recommender-Systems-3"]),
    ("Shipping agents to production", "AWS-Bootcamp/shipping-agents-to-production/",
     ["MLOPS-4", "MLOPS-7", "MLOPS-8", "AI-beginners-class21"]),
    ("Evals, observability and governance", "AWS-Bootcamp/ai-evals-why/",
     ["classification-metrics", "ML-with-AI-workflows-9", "MLOPS-1", "DSML-PA-10", "AI-beginners-class19",
      "AI-beginners-class20", "Anomaly-Detection"]),
    ("Embeddings, reranking and chunking", "AWS-Bootcamp/embeddings-reranking/",
     ["AIML-CV-4", "AIML-CV-5", "Model-evaluation-and-Intro-to-KNN", "NumPy-3", "Neural-Networks-7",
      "Principal-Component-Analysis"]),
    ("Guardrails", "AWS-Bootcamp/guardrails-explained/",
     ["Academy-AI-class-3", "AI-beginners-class3"]),
    ("Capstone · Inventory agent on AWS", "AWS-Capstone/inventory-aws-understand/",
     ["AI-beginners-class22", "AI-beginners-class23", "MLOPS-2", "MLOPS-9", "MLOPS-10"]),
    ("Capstone · Live auction house with AI coding agents", "AWS-Capstone/live-auction-setup/",
     ["AI-beginners-class17", "AI-beginners-class18", "production-python-class7"]),
]

# Broken links in Scaler's own pages, pointed at the library copy of the lesson they meant: (repo, href) -> repo.
LINK_FIX = {
    ("DSML-SL-2", "k-nearest-neighbors-1-post-read.html"): "DSML-SL-1",
}

# Demo "leaked key" strings in Scaler's pages that match real key formats (GitHub push protection
# blocks them): swapped for obvious placeholders so the lesson still reads the same.
SCRUB = [
    (r"AIza[0-9A-Za-z_-]{30,}", "AIzaSy-EXAMPLE-not-a-real-key"),
    (r"sk_live_[A-Za-z0-9]{10,}", "sk_live_EXAMPLE_not_a_real_key"),
]
