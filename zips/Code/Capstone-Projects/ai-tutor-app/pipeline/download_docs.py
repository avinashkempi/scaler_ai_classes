"""
Step 1 of the data pipeline: download the documentation markdown from GitHub.

Author: Shivank Agrawal
Project: AI Tutor (Agentic RAG) - Future with Shivank

For every source in config.SOURCES we do a "sparse" git clone, which pulls
only the docs folder instead of the whole repository, then copy the .md/.mdx
files into data/docs/<source>/ keeping their folder structure.

Run from the project root:
    python -m pipeline.download_docs
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from app.config import DOCS_DIR, ROOT, SOURCES


def is_excluded(relative_path: str, exclude_prefixes: list[str]) -> bool:
    """True if the file sits under a folder we decided to skip (e.g. translations)."""
    return any(relative_path.startswith(prefix) for prefix in exclude_prefixes)


def download_source(key: str, cfg: dict) -> int:
    """Sparse-clone one repo into a temp folder and copy its markdown docs."""
    target = DOCS_DIR / key
    if target.exists() and any(target.rglob("*.md*")):
        print(f"[{key}] already downloaded -> skipping")
        return len(list(target.rglob("*.md*")))

    # The clone lives in a temp folder that is deleted automatically afterwards.
    with tempfile.TemporaryDirectory() as tmp:
        clone_dir = Path(tmp) / key
        # --depth 1          : only the latest commit
        # --filter=blob:none : don't download file contents until needed
        # --sparse           : start with an empty working tree
        subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1", "--filter=blob:none",
             "--sparse", cfg["repo"], str(clone_dir)],
            check=True,
        )
        # Now ask git to materialise only the docs folder.
        subprocess.run(
            ["git", "-C", str(clone_dir), "sparse-checkout", "set", cfg["docs_path"]],
            check=True,
        )

        docs_root = clone_dir / cfg["docs_path"]
        copied = 0
        for file in sorted(docs_root.rglob("*")):
            if file.suffix not in {".md", ".mdx"} or not file.is_file():
                continue
            relative = file.relative_to(docs_root).as_posix()
            if is_excluded(relative, cfg["exclude"]):
                continue
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, destination)
            copied += 1

    print(f"[{key}] copied {copied} markdown files -> {target.relative_to(ROOT)}")
    return copied


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    total = sum(download_source(key, cfg) for key, cfg in SOURCES.items())
    print(f"Done. {total} markdown files across {len(SOURCES)} sources.")


if __name__ == "__main__":
    main()
