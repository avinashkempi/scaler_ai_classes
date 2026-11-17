"""Build the AI/ML Learnings library (AI-ML-Learnings/) from the scaler-content repos.

    python -I tools/build_library.py --src DIR   # copy each repo from DIR (a folder of clones), then build
    python -I tools/build_library.py             # rebuild the main, topic and Agentic AI in-Depth pages and the lesson bars

Topics, sections, Agentic AI in-Depth and the AWS add-ons live in tools/library_topics.py; card titles,
summaries, levels and tags in tools/library_cards.json. Lesson pages are Scaler's own pages, copied
as they are into AI-ML-Learnings/pages/<repo>/; the only change is a nav bar at the top and a source
note at the bottom, between <!-- aml:bar --> / <!-- aml:foot --> markers (safe to rebuild).
"""
import html
import json
import os
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIB = ROOT / "AI-ML-Learnings"
PAGES = LIB / "pages"
sys.path.insert(0, str(ROOT / "tools"))
from library_topics import ADDONS, DEEPER, LINK_FIX, SCRUB, SITE, SKIP, SOURCE_ORG, TOPICS, assign, group_key  # noqa: E402

CARDS = json.loads((ROOT / "tools" / "library_cards.json").read_text(encoding="utf-8"))
ISSUES = "https://github.com/balajiraghuram92/balajiraghuram92.github.io/issues"
PART_LABEL = {"pre": "Pre-read", "class": "Class", "post": "Post-read"}
LEVEL_LABEL = {"basic": "Basic", "intermediate": "Intermediate", "advanced": "Advanced"}
TOPIC = {t[0]: t for t in TOPICS}
e = html.escape


def rel(target, frm):
    """Relative URL from the folder of page `frm` to `target` (a path under ROOT; folders end with /)."""
    r = os.path.relpath(ROOT / target, (ROOT / frm).parent).replace(os.sep, "/")
    return r + "/" if str(target).endswith("/") and not r.endswith("/") else r


# ---------- catalogue ----------

def catalogue():
    """Cards in topic order: [{key, topic, section, parts: {part: repo}, ...card text}]."""
    repos = sorted(p.name for p in PAGES.iterdir() if p.is_dir()) if PAGES.exists() else []
    repos += [r for r in SITE if r not in repos]
    placed, rest = assign(repos)
    if rest:
        sys.exit(f"repos with no topic (add them to TOPICS in library_topics.py): {rest}")
    cards = {}
    for repo, (slug, section, order) in sorted(placed.items(), key=lambda kv: kv[1][2]):
        key, part = group_key(repo)
        c = cards.setdefault(key, {"key": key, "topic": slug, "section": section, "parts": {}})
        c["parts"][part] = repo
    for c in cards.values():
        meta = CARDS.get(c["key"])
        if not meta:
            sys.exit(f"no card text for {c['key']} in tools/library_cards.json")
        c.update(title=meta["title"], summary=meta["summary"], level=meta["level"], tags=meta.get("tags", []))
        c["parts"] = {p: c["parts"][p] for p in ("pre", "class", "post") if p in c["parts"]}
    return list(cards.values())


def repo_url(repo):
    """Site path of a repo's page: our existing copy, or the library copy."""
    return SITE.get(repo, f"AI-ML-Learnings/pages/{repo}/")


def main_part(c):
    return c["parts"].get("class") or next(iter(c["parts"].values()))


# ---------- shared page parts ----------

def sitebar(frm, where):
    p = lambda t: rel(t, frm)  # noqa: E731
    cur = ' aria-current="page"'
    return (f'<nav class="sitebar{" sitebar-bottom" if where == "bottom" else ""}" aria-label="Site ({where})">'
            f'<a class="sb-home" href="{p("index.html").replace("index.html", "") or "./"}">⌂ AI-Infusion</a>'
            f'<a href="{p("AWS-Bootcamp/")}">Scaler AWS AI Bootcamp</a><a href="{p("AWS-Capstone/")}">AWS AI Capstone</a>'
            f'<a href="{p("AI-Infusion/")}">AI-Infusion lessons</a><a href="{p("AI-ML-Learnings/")}"{cur}>AI/ML Learnings</a>'
            f'<a href="{p("Interview-Ready/")}">Interview Ready</a><a class="sb-help" href="{p("help/")}"><span>Help</span></a></nav>')


def disclaimer(frm):
    return (f'<aside class="aml-disc" id="source"><h2>About this material</h2>'
            f'<p>The lessons here are Scaler course material, made by Scaler and published at '
            f'<a href="{SOURCE_ORG}" target="_blank" rel="noopener">github.com/scaler-content</a>. This site does not own '
            f'them: it is a personal index that makes them easier to find and follow. Each lesson page is kept as Scaler '
            f'published it and links back to its source repo. If you are from Scaler and would like anything changed or '
            f'removed, please <a href="{ISSUES}" target="_blank" rel="noopener">open an issue</a> and it will be done.</p></aside>')


def page(frm, title, desc, eyebrow, h1, standfirst, body, script=""):
    css = rel("assets/", frm)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Instrument+Serif:ital@0;1&family=Public+Sans:wght@400;500;700&display=swap">
<link rel="stylesheet" href="{css}hub.css">
<link rel="stylesheet" href="{css}site.css">
<link rel="stylesheet" href="{css}library.css">
</head>
<body>
{sitebar(frm, "top")}
<header>
  <div class="wide">
    <p class="eyebrow">{eyebrow}</p>
    <h1>{h1}</h1>
    <p class="standfirst">{standfirst}</p>
  </div>
</header>

<main class="wide">
{body}
{disclaimer(frm)}
</main>
{sitebar(frm, "bottom")}
{script}</body>
</html>
"""


def level_badge(level):
    return f'<span class="lv lv-{level}">{LEVEL_LABEL[level]}</span>'


def card_html(c, frm, n=None, show_topic=False):
    main = rel(repo_url(main_part(c)), frm)
    parts = ""
    if len(c["parts"]) > 1:
        parts = '<div class="lc-go">' + "".join(
            f'<a href="{rel(repo_url(r), frm)}">{PART_LABEL[p]}</a>' for p, r in c["parts"].items()) + "</div>"
    onsite = any(r in SITE for r in c["parts"].values())
    top = level_badge(c["level"])
    if show_topic:
        top += f'<a class="lc-topic" href="{rel(f"AI-ML-Learnings/lessons/{c["topic"]}/", frm)}">{e(TOPIC[c["topic"]][1])}</a>'
    if onsite:
        top += '<span class="lc-site">On this site</span>'
    num = f'<span class="lc-n">{n:02d}</span>' if n is not None else ""
    tags = "".join(f"<li>{e(t)}</li>" for t in c["tags"])
    return (f'<article class="lc" data-level="{c["level"]}">{num}<div class="lc-top">{top}</div>'
            f'<h3><a href="{main}">{e(c["title"])}</a></h3><p>{e(c["summary"])}</p>'
            f'<ul class="tags">{tags}</ul>{parts}</article>')


# ---------- pages ----------

def build_lessons(cards):
    frm = "AI-ML-Learnings/index.html"
    tiles = []
    for slug, title, line, sections in TOPICS:
        mine = [c for c in cards if c["topic"] == slug]
        lv = {k: sum(c["level"] == k for c in mine) for k in LEVEL_LABEL}
        mix = "".join(f'<li class="lv-{k}">{v} {LEVEL_LABEL[k].lower()}</li>' for k, v in lv.items() if v)
        secs = " · ".join(e(s) for s, _ in sections if any(c["section"] == s for c in mine))
        tiles.append(f'<a class="tc" href="lessons/{slug}/"><p class="tc-k">{len(mine)} lessons</p><h2>{e(title)}</h2>'
                     f'<p>{e(line)}</p><p class="tc-s">{secs}</p><ul>{mix}</ul><span class="go">Open →</span></a>')
    index = [{"t": c["title"], "s": c["summary"], "g": " ".join(c["tags"]), "l": c["level"],
              "o": TOPIC[c["topic"]][1], "u": rel(repo_url(main_part(c)), frm)} for c in cards]
    body = (f'<div class="aml-search"><label for="q">Search all {len(cards)} lessons</label>'
            f'<input id="q" type="search" placeholder="e.g. embeddings, docker, prompt, sql" autocomplete="off">'
            f'<ol id="hits" class="hits" hidden></ol></div>\n<div class="tcs">{"".join(tiles)}</div>')
    script = ("<script>\nconst L=" + json.dumps(index, ensure_ascii=False) + ";\n"
              "(function(){const q=document.getElementById('q'),o=document.getElementById('hits');"
              "const esc=s=>s.replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));"
              "q.addEventListener('input',()=>{const w=q.value.toLowerCase().split(/\\s+/).filter(Boolean);"
              "if(!w.length){o.hidden=true;o.innerHTML='';return}"
              "const r=L.filter(x=>{const h=(x.t+' '+x.s+' '+x.g+' '+x.o).toLowerCase();return w.every(v=>h.includes(v))}).slice(0,40);"
              "o.innerHTML=r.length?r.map(x=>'<li><a href=\"'+x.u+'\">'+esc(x.t)+'</a><span>'+esc(x.o)+' · '+x.l+'</span><p>'+esc(x.s)+'</p></li>').join(''):'<li class=\"none\">No lesson matches.</li>';"
              "o.hidden=false})})();\n</script>\n")
    picks = sum(len(x[4]) for x in DEEPER)
    body += (f'\n<p class="aml-note">Want a shorter path? <a href="deeper/">Agentic AI in-Depth</a> hand-picks {picks} of these lessons '
             f'at three levels (basics, advanced, deeper), with add-ons for each AWS Bootcamp lesson.</p>')
    out = page(frm, "AI/ML Learnings", f"AI/ML Learnings: all {len(cards)} Scaler AI and ML lessons, sorted into {len(TOPICS)} topics, with search.",
               "AI/ML Learnings · the Scaler library", "AI/ML <em>Lessons</em>",
               f"{len(cards)} lessons in {len(TOPICS)} topics. Open a topic to see its lessons grouped by sub-topic, with a level and a one-line summary for each.",
               body, script)
    (LIB / "index.html").write_text(out, encoding="utf-8")
    # the old address of this page
    (LIB / "lessons").mkdir(parents=True, exist_ok=True)
    (LIB / "lessons" / "index.html").write_text(
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>AI/ML Lessons · AI/ML Learnings</title>\n<meta name="description" content="Moved to the AI/ML Learnings main page.">\n'
        '<meta http-equiv="refresh" content="0; url=../">\n<link rel="canonical" href="../">\n</head>\n'
        '<body><p>AI/ML Lessons is now the <a href="../">AI/ML Learnings</a> main page.</p></body>\n</html>\n', encoding="utf-8")


FILTER_JS = """<script>
(function(){const bs=document.querySelectorAll('.lvf button');bs.forEach(b=>b.addEventListener('click',()=>{
bs.forEach(x=>x.setAttribute('aria-pressed',x===b));const v=b.dataset.v;
document.querySelectorAll('.lc').forEach(c=>c.hidden=v!=='all'&&c.dataset.level!==v);
document.querySelectorAll('.lsec').forEach(s=>{s.hidden=!s.querySelector('.lc:not([hidden])');const a=document.querySelector('.aml-toc a[href="#'+s.id+'"]');if(a)a.hidden=s.hidden;});}))})();
</script>
"""


def build_topic(cards, i):
    slug, title, line, sections = TOPICS[i]
    frm = f"AI-ML-Learnings/lessons/{slug}/index.html"
    mine = [c for c in cards if c["topic"] == slug]
    secs, toc = [], []
    for n, (s, _) in enumerate(sections):
        sc = [c for c in mine if c["section"] == s]
        if not sc:
            continue
        sid = f"s{n + 1}"
        toc.append(f'<a href="#{sid}">{e(s)} <span>{len(sc)}</span></a>')
        secs.append(f'<section class="lsec" id="{sid}"><h2>{e(s)}</h2><div class="lcs">'
                    + "".join(card_html(c, frm) for c in sc) + "</div></section>")
    have = [k for k in LEVEL_LABEL if any(c["level"] == k for c in mine)]
    filt = ('<div class="lvf" role="group" aria-label="Filter by level"><button type="button" data-v="all" aria-pressed="true">All</button>'
            + "".join(f'<button type="button" data-v="{k}" aria-pressed="false">{LEVEL_LABEL[k]}</button>' for k in have) + "</div>")
    prev_t, next_t = TOPICS[i - 1] if i else None, TOPICS[i + 1] if i + 1 < len(TOPICS) else None
    pn = '<nav class="aml-pn" aria-label="Topics">'
    pn += f'<a href="../{prev_t[0]}/">← {e(prev_t[1])}</a>' if prev_t else '<a href="../../">← All topics</a>'
    pn += f'<a href="../{next_t[0]}/">{e(next_t[1])} →</a>' if next_t else '<a href="../../deeper/">Agentic AI in-Depth →</a>'
    pn += "</nav>"
    body = f'<nav class="aml-toc" aria-label="Sub-topics">{"".join(toc)}</nav>\n{filt}\n' + "\n".join(secs) + "\n" + pn
    out = page(frm, f"{title} · AI/ML Learnings", f"{title}: {len(mine)} Scaler lessons. {line}",
               f'<a href="../../">AI/ML Learnings</a> · Topic {i + 1} of {len(TOPICS)}',
               e(title), e(line), body, FILTER_JS)
    (LIB / "lessons" / slug).mkdir(parents=True, exist_ok=True)
    (LIB / "lessons" / slug / "index.html").write_text(out, encoding="utf-8")


def build_deeper(cards):
    """Agentic AI in-Depth: a main page (what it is + one card per level) and one page per level."""
    by = {c["key"]: c for c in cards}
    picks = sum(len(x[4]) for x in DEEPER)
    title = "Agentic AI in-Depth"
    # (slug, name, kicker, line, html builder)
    levels = [(sid, name, kicker, line, keys) for sid, name, kicker, line, keys in DEEPER]
    aws_line = ("For each bootcamp lesson or capstone project, the library lessons that prepare you for it or take it further. "
                "The heading opens the bootcamp page; each tag opens the library lesson.")
    pages = [(sid, name, kicker, line, len(keys)) for sid, name, kicker, line, keys in levels]
    pages.append(("aws", "AWS Bootcamp add-ons", "For the bootcamp", aws_line, len(ADDONS)))

    # ---- one page per level
    for i, (sid, name, kicker, line, count) in enumerate(pages):
        frm = f"AI-ML-Learnings/deeper/{sid}/index.html"
        if sid == "aws":
            rows = []
            for aname, target, keys in ADDONS:
                chips = "".join(f'<a class="chip" href="{rel(repo_url(main_part(by[k])), frm)}">{level_badge(by[k]["level"])}{e(by[k]["title"])}</a>'
                                for k in keys)
                rows.append(f'<div class="addon"><h3><a href="{rel(target, frm)}">{e(aname)} <span>↗</span></a></h3><div class="chips">{chips}</div></div>')
            inner = "".join(rows)
        else:
            keys = levels[i][4]
            inner = '<div class="lcs">' + "".join(card_html(by[k], frm, n + 1, show_topic=True) for n, k in enumerate(keys)) + "</div>"
        prev_p = pages[i - 1] if i else None
        next_p = pages[i + 1] if i + 1 < len(pages) else None
        pn = '<nav class="aml-pn" aria-label="Levels">'
        pn += f'<a href="../{prev_p[0]}/">← {e(prev_p[1])}</a>' if prev_p else f'<a href="../">← {title}</a>'
        pn += f'<a href="../{next_p[0]}/">{e(next_p[1])} →</a>' if next_p else f'<a href="../">{title} →</a>'
        pn += "</nav>"
        body = f'<section class="dsec dsec-{sid}">{inner}</section>\n{pn}'
        unit = "lessons and projects" if sid == "aws" else "lessons"
        out = page(frm, f"{name} · {title} · AI/ML Learnings",
                   f"{title} · {name}: {count} {unit}. {line}",
                   f'<a href="../../">AI/ML Learnings</a> · <a href="../">{title}</a> · {e(kicker)}',
                   e(name), f"{e(line)} {count} {unit}" + ("; the numbers are a suggested order." if sid != "aws" else "."), body)
        (LIB / "deeper" / sid).mkdir(parents=True, exist_ok=True)
        (LIB / "deeper" / sid / "index.html").write_text(out, encoding="utf-8")

    # ---- the main page
    frm = "AI-ML-Learnings/deeper/index.html"
    tiles = []
    for i, (sid, name, kicker, line, count) in enumerate(pages):
        if sid == "aws":
            mix = f"<li>{len(ADDONS)} bootcamp lessons and projects</li>"
            unit = "groups"
        else:
            ks = levels[i][4]
            lv = {k: sum(by[x]["level"] == k for x in ks) for k in LEVEL_LABEL}
            mix = "".join(f'<li class="lv-{k}">{v} {LEVEL_LABEL[k].lower()}</li>' for k, v in lv.items() if v)
            unit = "lessons"
        tiles.append(f'<a class="tc dl dl-{sid}" href="{sid}/"><p class="tc-k">{e(kicker)} · {count} {unit}</p><h2>{e(name)}</h2>'
                     f'<p>{e(line)}</p><ul>{mix}</ul><span class="go">Open {e(name)} →</span></a>')
    about = (f'<section class="dabout" aria-labelledby="about-h"><h2 id="about-h">What this page is</h2>'
             f'<div class="dabout-g">'
             f'<div><h3>A study path for agentic AI</h3><p>The Scaler library has {len(cards)} lessons. To build and ship AI agents you '
             f'don\'t need all of them, so this page hand-picks the {picks} that matter most and puts them in order, at three levels. '
             f'Every one of them is also in <a href="../">AI/ML Learnings</a>.</p></div>'
             f'<div><h3>Who it is for</h3><p>Anyone doing the Scaler AWS AI Bootcamp or the AWS AI Capstone who wants to fill a gap '
             f'or go further than a lesson did: from your first Python script to the maths under embeddings.</p></div>'
             f'<div><h3>How to use it</h3><ol><li>Pick a level below. Start with Basics if anything in it is new to you.</li>'
             f'<li>Work through its lessons in number order; the number is a suggested order.</li>'
             f'<li>Each lesson card shows its level and topic and opens the Scaler lesson.</li>'
             f'<li>Doing the bootcamp? Open <a href="aws/">AWS Bootcamp add-ons</a> for the lessons that go with each bootcamp lesson.</li></ol></div>'
             f'</div></section>')
    body = about + '\n<h2 class="dpick">Pick a level</h2>\n<div class="tcs dls">' + "".join(tiles) + "</div>"
    # old links such as deeper/#basics open the level's own page
    script = ("<script>(function(){var h=location.hash.slice(1);if(" + json.dumps([p[0] for p in pages])
              + ".indexOf(h)>=0)location.replace(h+'/');})();</script>\n")
    out = page(frm, f"{title} · AI/ML Learnings",
               f"{title}: {picks} hand-picked Scaler lessons for building AI agents, at three levels (basics, advanced, deeper), plus add-ons for each AWS AI Bootcamp lesson.",
               f'<a href="../">AI/ML Learnings</a> · {title}', "Agentic AI <em>in-Depth</em>",
               "A guided path through the Scaler library for people building AI agents: the lessons that matter most, in order, at the level you need.",
               body, script)
    (LIB / "deeper").mkdir(parents=True, exist_ok=True)
    (LIB / "deeper" / "index.html").write_text(out, encoding="utf-8")


# ---------- lesson pages ----------

BAR_CSS = ("#aml-bar{all:initial;display:flex;flex-wrap:wrap;align-items:center;gap:6px 14px;box-sizing:border-box;width:100%;"
           "padding:9px 16px;background:#0E1530;color:#EEF1FB;font:600 12.5px/1.4 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;"
           "position:relative;z-index:2147483000;border-bottom:2px solid #F2A93B}"
           "#aml-bar a{all:unset;cursor:pointer;color:#EEF1FB;text-decoration:none;opacity:.85}"
           "#aml-bar a:hover,#aml-bar a:focus-visible{opacity:1;text-decoration:underline;outline:none}"
           "#aml-bar .h{color:#F2A93B;opacity:1}#aml-bar .t{color:#A9B2D6;font-weight:400}"
           "#aml-bar .p{display:inline-flex;gap:4px}#aml-bar .p a,#aml-bar .p b{padding:2px 8px;border-radius:5px;border:1px solid #2A3768}"
           "#aml-bar .p b{background:#F2A93B;color:#0E1530;border-color:#F2A93B}"
           "#aml-bar .pn{margin-left:auto;display:inline-flex;gap:14px}"
           "#aml-foot{all:initial;display:block;box-sizing:border-box;padding:14px 16px;background:#0E1530;color:#A9B2D6;"
           "font:400 12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;text-align:center}"
           "#aml-foot a{all:unset;cursor:pointer;color:#F2A93B;text-decoration:underline}")
# Pages whose <body> is a flex or grid layout would squeeze the bar into a column: move it just outside <body>.
OUTSIDE_JS = ("(function(){var n=document.getElementById('%s'),d=getComputedStyle(document.body).display;"
              "if(/flex|grid/.test(d))document.documentElement.%s})();")
BLOCK = re.compile(r"\n?<!-- aml:(bar|foot) -->.*?<!-- /aml:\1 -->\n?", re.S)


def lesson_bar(c, repo, f, prev, nxt):
    frm = f.relative_to(ROOT).as_posix()
    top = rel(f"AI-ML-Learnings/lessons/{c['topic']}/", frm)
    parts = ""
    if len(c["parts"]) > 1:
        parts = '<span class="p">' + "".join(
            f'<b>{PART_LABEL[p]}</b>' if r == repo and f.name == "index.html" and f.parent.name == repo
            else f'<a href="{rel(repo_url(r), frm)}">{PART_LABEL[p]}</a>' for p, r in c["parts"].items()) + "</span>"
    sub = "" if (f.name == "index.html" and f.parent.name == repo) else f'<a href="{rel(repo_url(repo), frm)}">↑ Lesson page</a>'
    pn = ('<span class="pn">'
          + (f'<a href="{rel(repo_url(main_part(prev)), frm)}" title="{e(prev["title"])}">← Prev</a>' if prev else "")
          + (f'<a href="{rel(repo_url(main_part(nxt)), frm)}" title="{e(nxt["title"])}">Next →</a>' if nxt else "")
          + "</span>")
    bar = (f'<!-- aml:bar --><style>{BAR_CSS}</style><nav id="aml-bar" aria-label="AI/ML Learnings">'
           f'<a class="h" href="{rel("AI-ML-Learnings/", frm)}">⌂ AI/ML Learnings</a><span>›</span>'
           f'<a href="{top}">{e(TOPIC[c["topic"]][1])}</a><span class="t">· {e(c["title"])}</span>{parts}{sub}{pn}</nav>'
           f'<script>{OUTSIDE_JS % ("aml-bar", "insertBefore(n,document.body)")}</script><!-- /aml:bar -->')
    foot = (f'<!-- aml:foot --><div id="aml-foot">Scaler course material, kept as published at '
            f'<a href="{SOURCE_ORG}/{repo}" target="_blank" rel="noopener">github.com/scaler-content/{e(repo)}</a> · '
            f'<a href="{rel("AI-ML-Learnings/#source", frm)}">about this library</a></div>'
            f'<script>{OUTSIDE_JS % ("aml-foot", "appendChild(n)")}</script><!-- /aml:foot -->')
    return bar, foot


def wire_lessons(cards):
    for slug, *_ in TOPICS:
        mine = [c for c in cards if c["topic"] == slug]
        for i, c in enumerate(mine):
            prev, nxt = (mine[i - 1] if i else None), (mine[i + 1] if i + 1 < len(mine) else None)
            for repo in c["parts"].values():
                if repo in SITE:
                    continue
                for f in sorted((PAGES / repo).rglob("*.html")):
                    t = BLOCK.sub("", f.read_text(encoding="utf-8", errors="replace"))
                    for pat, sub in SCRUB:
                        t = re.sub(pat, sub, t)
                    for (r, href), to in LINK_FIX.items():
                        if r == repo:
                            t = t.replace(f'href="{href}"', f'href="{rel(repo_url(to), f.relative_to(ROOT).as_posix())}"')
                    bar, foot = lesson_bar(c, repo, f, prev, nxt)
                    m = re.search(r"<body\b[^>]*>", t, re.I)
                    t = t[:m.end()] + "\n" + bar + t[m.end():] if m else bar + "\n" + t
                    j = t.lower().rfind("</body>")
                    t = t[:j] + foot + "\n" + t[j:] if j >= 0 else t + "\n" + foot
                    f.write_text(t, encoding="utf-8")


def copy_repos(src):
    src = pathlib.Path(src)
    PAGES.mkdir(parents=True, exist_ok=True)
    n = 0
    for d in sorted(p for p in src.iterdir() if p.is_dir()):
        if d.name in SKIP or d.name in SITE or not any(d.rglob("*.html")):
            continue
        dest = PAGES / d.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(d, dest, ignore=shutil.ignore_patterns(".git", ".github", ".DS_Store", "README.md"))
        n += 1
    print(f"copied {n} repos into {PAGES.relative_to(ROOT)}")


def wire_sitebars():
    """Add the AI/ML Learnings link to the site bar on every hub page that has one."""
    for f in ROOT.glob("**/index.html"):
        rp = f.relative_to(ROOT).as_posix()
        if rp.startswith(("AI-ML-Learnings/", "data-dump/", "zips/")):
            continue
        t = f.read_text(encoding="utf-8")
        if 'class="sitebar' not in t or "AI/ML Learnings</a>" in t:
            continue
        t2 = re.sub(r'(<a href="([^"]*)Interview-Ready/"( aria-current="page")?>Interview Ready</a>)',
                    lambda m: f'<a href="{m.group(2)}AI-ML-Learnings/">AI/ML Learnings</a>{m.group(1)}', t)
        if t2 != t:
            f.write_text(t2, encoding="utf-8")
            print("site bar:", rp)


def main():
    if "--src" in sys.argv:
        copy_repos(sys.argv[sys.argv.index("--src") + 1])
    cards = catalogue()
    build_lessons(cards)
    for i in range(len(TOPICS)):
        build_topic(cards, i)
    build_deeper(cards)
    wire_lessons(cards)
    wire_sitebars()
    print(f"{len(cards)} lessons, {sum(len(c['parts']) for c in cards)} pages, {len(TOPICS)} topics")


if __name__ == "__main__":
    main()
