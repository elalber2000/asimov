from __future__ import annotations
from functools import wraps
from pathlib import Path
import re
import runpy
import traceback
from typing import Literal
from dotenv import load_dotenv
from z3 import Solver, sat, unsat, unknown
import logging

from utils.llm import LLM

SRC_PATH = Path(__file__).resolve().parents[1]
load_dotenv()


def do_retry(retries: int, *, raise_after: bool = True):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for i in range(retries):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    print(f"[do_retry] {fn.__name__} failed on attempt {i + 1}/{retries}: {type(e).__name__}: {e}")
                    traceback.print_exc()
                    continue
            print(f"[do_retry] {fn.__name__} failed after {retries} attempts.")
            if raise_after:
                raise Exception("Maximum iterations")
            return None
        return wrapper
    return decorator


search_str = "<<<<<<< SEARCH"

_patches_format_str = """
    \n\n# Format
    Return the results with the following patch format

    ```
    <<<<<<< SEARCH
    exact text copied verbatim from the original input
    =======
    replacement text
    >>>>>>> REPLACE

    <<<<<<< SEARCH
    another text that we want to change
    =======
    replacement text
    >>>>>>> REPLACE

    ...
    ```

    Only apply needed patches, not the whole thing
    Use the exact same format!!!
    Return ONLY one or more patches in the exact SEARCH/REPLACE format below.
"""


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


def len_axiom_dir(axiom_folder: str):
    return len(list(Path(axiom_folder).iterdir()))


def get_latest_axioms(directory: str):
    directory = Path(directory)
    timestamped = []

    for p in directory.glob("*.py"):
        if p.name == "base.py":
            continue

        try:
            ts = float(p.stem)
        except ValueError:
            continue

        timestamped.append((ts, p))

    if timestamped:
        return max(timestamped)[1]

    base = directory / "base.py"
    if base.exists():
        return base

    raise FileNotFoundError("No timestamped .py file or base.py found")


def get_latest_it(text: str):
    nums = [int(m.group(1)) for m in re.finditer(r"# Iteration (\d+):", text)]
    return max(nums, default=None)


def remove_changelog_patches(patches: str) -> str:
    blocks = patches.split(search_str)
    kept = [blocks[0]]

    for block in blocks[1:]:
        full_block = search_str + block
        if "# CHANGELOG" not in full_block and "# Iteration" not in full_block:
            kept.append(full_block)

    return "\n\n".join(i.strip() for i in kept if i.strip())


def add_changelog(patches: str, changelog: str) -> str:
    blocks = patches.split("<<<<<<< SEARCH")
    kept = [blocks[0]]

    for block in blocks[1:]:
        full_block = "<<<<<<< SEARCH" + block
        if "# CHANGELOG" not in full_block and "# Iteration" not in full_block:
            kept.append(full_block)

    clean_patches = "\n\n".join(i.strip() for i in kept if i.strip())

    changelog_patch = f"""
{search_str}
# CHANGELOG

=======
# CHANGELOG

{changelog}
>>>>>>> REPLACE
""".strip()

    return "\n\n".join(p for p in [changelog_patch, clean_patches] if p.strip())


def apply_patches(text: str, patches: str) -> str:
    pattern = re.compile(
        r"<<<<<<< SEARCH[ \t]*\n"
        r"(?P<old>.*?)\n"
        r"=======[ \t]*\n"
        r"(?P<new>.*?)\n"
        r">>>>>>>(?: REPLACE)?[ \t]*(?:\n|$)",
        flags=re.DOTALL,
    )

    changes = [match.groupdict() for match in pattern.finditer(patches)]

    if not changes:
        raise ValueError("No changes found.")

    for i, change in enumerate(changes, start=1):
        old = change["old"]
        new = change["new"]

        if old not in text:
            raise ValueError(f"Change {i} failed: search text not found:\n{old}")

        text = text.replace(old, new, 1)

    return text


def verify_and_correct_axioms(
    llm: LLM,
    axioms: str,
    max_solv_retries: int = 10,
):
    last_error = None

    for _ in range(max_solv_retries):
        try:
            solv = check_solvability(axioms)

            if solv == sat:
                return axioms

            diagnostic = f"Z3 returned {solv}"

        except Exception as e:
            diagnostic = (
                f"{type(e).__name__}: {e}\n\n"
                f"Traceback:\n{traceback.format_exc(limit=3)}"
            )

        patches = llm.invoke(
            prompt=f"""
                The following Z3 Python axiom file failed validation.

                Diagnostic:
                {diagnostic}

                Return minimal exact search-and-replace patches to fix it.

                Rules:
                - Do not rewrite the whole file.
                - Use the smallest exact substrings possible.
                - Preserve the public structure: scaffolding() and axioms().
                - The corrected file must be valid Python and valid Z3 code.

                # Axioms
                {axioms}

                {_patches_format_str}
            """,
        )

        axioms = apply_patches(axioms, patches)

        last_error = diagnostic

    raise RuntimeError(
        f"Maximum validation retries reached. Last diagnostic:\n{last_error}"
    )


def check_solvability(
    axioms: str,
    extra_facts=None,
):
    ns = {}
    exec(compile(axioms, "<axioms>", "exec"), ns, ns)
    s = Solver()

    if "scaffolding" in ns:
        s.add(*ns["scaffolding"]())

    if "axioms" in ns:
        s.add(*ns["axioms"]())

    if extra_facts:
        s.add(*extra_facts)

    return s.check()
