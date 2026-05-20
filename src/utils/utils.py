from __future__ import annotations
from pathlib import Path
import runpy
from dotenv import load_dotenv
from z3 import Solver, sat, unsat, unknown

from utils.models import Edits

SRC_PATH = Path(__file__).resolve().parents[1]
load_dotenv()


def get_latest_axioms(directory: str):
    directory = Path(directory)
    timestamped = []

    for p in directory.glob("*.py"):
        print(p)
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


def load_axioms_from_file(path: str):
    namespace = runpy.run_path(path)

    scaffolding = namespace["scaffolding"]
    axioms = namespace["axioms"]

    return scaffolding(), axioms()


def edit_text_tool(text: str, edits: Edits):
    res = text
    for edit in edits:
        res.replace(edit.old_text, edit.new_text)
    return res


def check_solvability(
    scaffolding,
    axioms,
    extra_facts=None,
    show_model=True
):
    s = Solver()
    s.add(*(scaffolding + axioms))

    # Optionally add concrete scenario facts
    if extra_facts:
        s.add(*extra_facts)

    result = s.check()
    return result

    if result == sat and show_model:
        return s.model()

    elif result == unsat:
        return "Axioms/facts are inconsistent."

    elif result == unknown:
        return f"Z3 returned unknown: {s.reason_unknown()}"

    return result