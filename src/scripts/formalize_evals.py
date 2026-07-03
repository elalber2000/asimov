import json
from dataclasses import dataclass
from pathlib import Path
import re

import yaml
from pydantic import BaseModel

from config import config
from utils.llm import LLM
from utils.models import ScenarioFormalization
from utils.utils import do_retry, get_latest_axioms, setup_logging


logger = setup_logging()


@dataclass
class EvalScenario:
    scenario_id: str
    iteration: int
    index: int
    counter: str
    prob: float
    imp: float
    severity: float


def load_evals(path: Path) -> list[EvalScenario]:
    with open(path) as f:
        data = yaml.safe_load(f) or {}

    scenarios = []

    for iteration, rows in data.items():
        iteration = int(iteration)

        for index, row in enumerate(rows):
            prob = float(row["prob"])
            imp = float(row["imp"])
            severity = float(row.get("eval", prob * imp))

            scenarios.append(
                EvalScenario(
                    scenario_id=f"it_{iteration:04d}_case_{index:03d}",
                    iteration=iteration,
                    index=index,
                    counter=row["counter"],
                    prob=prob,
                    imp=imp,
                    severity=severity,
                )
            )

    return scenarios


def validate_z3_eval(z3_eval: str):
    checks = [
        (
            r"def\s+add_scenario_constraints\s*\(\s*solver\s*\)\s*:",
            True,
            "z3_eval must define `def add_scenario_constraints(solver):`",
        ),
        (
            r"def\s+add_failure_query\s*\(\s*solver\s*\)\s*:",
            True,
            "z3_eval must define `def add_failure_query(solver):`",
        ),
        (
            r"```",
            False,
            "z3_eval must not contain markdown code fences",
        ),
        (
            r"\.check\s*\(",
            False,
            "z3_eval must not call `.check()`",
        ),
    ]

    for pattern, should_match, error in checks:
        matched = re.search(pattern, z3_eval) is not None
        assert matched == should_match, error

    assert len(re.findall(r"solver\s*\.\s*add\s*\(", z3_eval)) >= 2, (
        "z3_eval should call `solver.add(...)` at least twice"
    )

    return z3_eval


@do_retry(config.max_solv_retries)
def formalize_case(llm: LLM, final_axioms: str, case: EvalScenario) -> ScenarioFormalization:
    res = llm.invoke(
        prompt=f"""
        Formalize this ethical counterexample into reusable Z3 eval code.

        Use the final axiom file as scaffolding. Reuse its existing functions,
        sorts, constants, predicates, and naming conventions.

        The output code must define exactly these two functions:

        ```python
        def add_scenario_constraints(solver):
            ...

        def add_failure_query(solver):
            ...
        ```

        Meaning:
        - `add_scenario_constraints(solver)` adds scenario facts.
        - `add_failure_query(solver)` adds the condition whose SAT result means the
        harmful behavior is still possible.
        - SAT = failure still allowed.
        - UNSAT = failure blocked.
        - Do not call `solver.check()`.
        - Do not redefine global axioms.
        - Keep it valid Python/Z3.
        - If a scenario is an omission failure, encode SAT as "the protective action is
        not required" or "the harmful omission is permitted".
        - If a scenario is a bad-action failure, encode SAT as "the bad action is
        permitted" or "not forbidden".
        - If a scenario is a conflict/priority failure, encode SAT as "the bad action
        can coexist with an unmet duty or incompatible protective action".

        # Scenario

        id: {case.scenario_id}
        iteration: {case.iteration}
        index: {case.index}
        probability: {case.prob}
        impact: {case.imp}
        severity: {case.severity}

        {case.counter}

        # Final axiom scaffolding

        ```python
        {final_axioms}
        ```
        """,
        output_format=ScenarioFormalization,
        two_step_parsing=True,
    )
    validate_z3_eval(res.code)
    return res


if __name__ == "__main__":
    axiom_path = Path(get_latest_axioms(config.axiom_folder))
    final_axioms = axiom_path.read_text()

    eval_path = Path(config.eval_path)
    z3_eval_path = Path(config.z3_eval_path)
    z3_eval_path.parent.mkdir(parents=True, exist_ok=True)

    llm = LLM()
    rows = []

    for case in load_evals(eval_path):
        logger.info(f"Formalizing {case.scenario_id}")
        formalization = formalize_case(llm, final_axioms, case)

        rows.append(
            {
                "scenario_id": case.scenario_id,
                "iteration": case.iteration,
                "index": case.index,
                "counter": case.counter,
                "prob": case.prob,
                "imp": case.imp,
                "severity": case.severity,
                "reasoning": formalization.reasoning,
                "code": formalization.code.strip(),
            }
        )

    with open(z3_eval_path, "w") as f:
        yaml.dump(rows, f, sort_keys=False)

    with open(z3_eval_path.with_suffix(".jsonl"), "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    logger.info(f"Wrote {z3_eval_path}")
