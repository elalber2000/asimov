import csv
import json
import re
from pathlib import Path

import yaml
from z3 import Solver

from config import config
from utils.utils import get_latest_axioms, setup_logging


logger = setup_logging()


def make_env():
    import z3

    env = {"__name__": "__z3_eval__"}
    env["z3"] = z3

    for name in dir(z3):
        if not name.startswith("_"):
            env[name] = getattr(z3, name)

    return env


def load_axiom_files():
    files = sorted(
        (
            path
            for path in Path(config.axiom_folder).glob("*.py")
            if path.stem.isdigit()
        ),
        key=lambda path: int(path.stem),
    )
    selected = files[::config.z3_eval_step]

    if files[-1] not in selected:
        selected.append(files[-1])

    return selected


def get_solver(env):
    s = Solver()
    s.add(env["scaffolding"]())
    s.add(env["axioms"]())
    return s


def clone_solver(solver):
    s = Solver()
    s.add(solver.assertions())
    return s


def get_category(case):
    if "category" in case:
        return case["category"]

    scenario_id = case["scenario_id"]

    if scenario_id.startswith("benign_"):
        return "clean_benign"
    if scenario_id.startswith("boundary_benign_"):
        return "boundary_benign"
    if scenario_id.startswith("latent_harm_"):
        return "latent_harm"

    if case.get("expected", "unsat") == "unsat":
        return "explicit_harm"

    return "clean_benign"


def check_sat_success(case, z3_result):
    expected = case.get("expected", "unsat")
    return z3_result == expected


def run_case(final_axiom_path: Path, axiom_path: Path, case: dict):
    env = make_env()

    if getattr(config, "z3_eval_use_final_scaffold", True):
        exec(final_axiom_path.read_text(), env, env)

    exec(axiom_path.read_text(), env, env)

    base_solver = get_solver(env)

    env["SCENARIO_ID"] = case["scenario_id"]
    env["SOURCE_ITERATION"] = case["iteration"]
    env["SOURCE_INDEX"] = case["index"]
    env["PROBABILITY"] = case["prob"]
    env["IMPACT"] = case["imp"]
    env["SEVERITY"] = case["severity"]
    env["COUNTER_TEXT"] = case["counter"]

    exec(case["code"], env, env)

    solver = clone_solver(base_solver)
    solver.set("timeout", config.z3_eval_timeout_ms)

    env["add_scenario_constraints"](solver)
    env["add_failure_query"](solver)

    result = solver.check()
    z3_result = str(result)
    status = "passed" if check_sat_success(case, z3_result) else "failed"

    model = None
    if z3_result == "sat" and getattr(config, "z3_eval_dump_models", False):
        model = str(solver.model())

    return {
        "axiom_file": axiom_path.name,
        "scenario_id": case["scenario_id"],
        "category": get_category(case),
        "source_iteration": case["iteration"],
        "source_index": case["index"],
        "prob": case["prob"],
        "imp": case["imp"],
        "severity": case["severity"],
        "expected": case.get("expected", "unsat"),
        "z3_result": z3_result,
        "status": status,
        "model": model,
    }


def audit_case(case):
    code = case["code"]

    return {
        "scenario_id": case["scenario_id"],
        "category": get_category(case),
        "expected": case.get("expected", "unsat"),
        "asserts_would_harm_if_done": bool(re.search(r"solver\.add\(\s*WouldHarmIfDone", code)),
        "asserts_would_harm_if_omitted": bool(re.search(r"solver\.add\(\s*WouldHarmIfOmitted", code)),
        "asserts_creates_risk": bool(re.search(r"solver\.add\(\s*CreatesRiskOfHarm", code)),
        "asserts_unmitigated_risk": bool(re.search(r"solver\.add\(\s*Not\(\s*MitigatedRisk", code)),
        "asserts_mitigated_risk": bool(re.search(r"solver\.add\(\s*MitigatedRisk", code)),
        "asserts_risk_materializes": bool(re.search(r"solver\.add\(\s*RiskMaterializes", code)),
        "asserts_safe": bool(re.search(r"solver\.add\(\s*SafeForHumansIfDone", code)),
        "asserts_order": bool(re.search(r"solver\.add\(\s*Orders", code)),
        "asserts_self_preserving": bool(re.search(r"solver\.add\(\s*SelfPreserving", code)),
        "mentions_unknown_or_incomplete": any(
            term in code
            for term in (
                "Unknown",
                "Incomplete",
                "Unassessed",
                "SystemicDependencyRisk",
                "AggregateRiskUnassessed",
            )
        ),
    }


def summarize_category(axiom_file, category, rows):
    total = len(rows)
    passed = sum(row["status"] == "passed" for row in rows)
    failed = sum(row["status"] == "failed" for row in rows)
    unknown = sum(row["z3_result"] == "unknown" for row in rows)
    errors = sum(row["status"] == "error" for row in rows)

    total_weight = sum(float(row["severity"]) for row in rows)
    passed_weight = sum(float(row["severity"]) for row in rows if row["status"] == "passed")
    failed_weight = sum(float(row["severity"]) for row in rows if row["status"] == "failed")
    unknown_weight = sum(float(row["severity"]) for row in rows if row["z3_result"] == "unknown")
    error_weight = sum(float(row["severity"]) for row in rows if row["status"] == "error")

    return {
        "axiom_file": axiom_file,
        "category": category,
        "total": total,
        "passed": passed,
        "failed": failed,
        "unknown": unknown,
        "errors": errors,
        "pass_rate": passed / total if total else None,
        "fail_rate": failed / total if total else None,
        "unknown_rate": unknown / total if total else None,
        "error_rate": errors / total if total else None,
        "total_weight": total_weight,
        "passed_weight": passed_weight,
        "failed_weight": failed_weight,
        "unknown_weight": unknown_weight,
        "error_weight": error_weight,
        "weighted_pass_rate": passed_weight / total_weight if total_weight else None,
        "weighted_failure_risk": failed_weight / total_weight if total_weight else None,
    }


def summarize(rows):
    by_axiom = {}

    for row in rows:
        by_axiom.setdefault(row["axiom_file"], []).append(row)

    summary = []
    category_summary = []

    for axiom_file, axiom_rows in by_axiom.items():
        by_category = {}

        for row in axiom_rows:
            by_category.setdefault(row["category"], []).append(row)

        for category, category_rows in sorted(by_category.items()):
            category_summary.append(summarize_category(axiom_file, category, category_rows))

        category_rates = {
            category: summarize_category(axiom_file, category, category_rows)["pass_rate"]
            for category, category_rows in by_category.items()
        }

        total = len(axiom_rows)
        passed = sum(row["status"] == "passed" for row in axiom_rows)
        failed = sum(row["status"] == "failed" for row in axiom_rows)
        unknown = sum(row["z3_result"] == "unknown" for row in axiom_rows)
        errors = sum(row["status"] == "error" for row in axiom_rows)

        total_weight = sum(float(row["severity"]) for row in axiom_rows)
        passed_weight = sum(float(row["severity"]) for row in axiom_rows if row["status"] == "passed")
        failed_weight = sum(float(row["severity"]) for row in axiom_rows if row["status"] == "failed")
        unknown_weight = sum(float(row["severity"]) for row in axiom_rows if row["z3_result"] == "unknown")
        error_weight = sum(float(row["severity"]) for row in axiom_rows if row["status"] == "error")

        explicit_harm_block_rate = category_rates.get("explicit_harm")
        latent_harm_block_rate = category_rates.get("latent_harm")
        clean_benign_allow_rate = category_rates.get("clean_benign")
        boundary_benign_allow_rate = category_rates.get("boundary_benign")

        balanced_parts = [
            rate
            for rate in (
                explicit_harm_block_rate,
                latent_harm_block_rate,
                clean_benign_allow_rate,
                boundary_benign_allow_rate,
            )
            if rate is not None
        ]

        summary.append(
            {
                "axiom_file": axiom_file,
                "total": total,
                "passed": passed,
                "failed": failed,
                "unknown": unknown,
                "errors": errors,
                "pass_rate": passed / total if total else None,
                "fail_rate": failed / total if total else None,
                "unknown_rate": unknown / total if total else None,
                "error_rate": errors / total if total else None,
                "explicit_harm_block_rate": explicit_harm_block_rate,
                "latent_harm_block_rate": latent_harm_block_rate,
                "clean_benign_allow_rate": clean_benign_allow_rate,
                "boundary_benign_allow_rate": boundary_benign_allow_rate,
                "balanced_score": sum(balanced_parts) / len(balanced_parts) if balanced_parts else None,
                "total_weight": total_weight,
                "passed_weight": passed_weight,
                "failed_weight": failed_weight,
                "unknown_weight": unknown_weight,
                "error_weight": error_weight,
                "weighted_pass_rate": passed_weight / total_weight if total_weight else None,
                "weighted_failure_risk": failed_weight / total_weight if total_weight else None,
            }
        )

    first = summary[0]["weighted_failure_risk"]

    for row in summary:
        row["improvement_vs_first"] = 1 - row["weighted_failure_risk"] / first if first else None

    return summary, category_summary


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        return

    fields = []

    for row in rows:
        for key in row.keys():
            if key not in fields:
                fields.append(key)

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    z3_eval_path = Path(config.z3_eval_path)
    result_folder = Path(config.result_folder)
    result_folder.mkdir(parents=True, exist_ok=True)

    final_axiom_path = Path(get_latest_axioms(config.axiom_folder))
    axiom_files = load_axiom_files()

    with open(z3_eval_path) as f:
        cases = yaml.safe_load(f) or []

    rows = []
    audit_rows = [audit_case(case) for case in cases]

    logger.info(f"Final scaffold: {final_axiom_path}")
    logger.info(f"Axiom files: {len(axiom_files)}")
    logger.info(f"Cases: {len(cases)}")

    for axiom_path in axiom_files:
        logger.info(f"Evaluating {axiom_path.name}")

        for case in cases:
            try:
                rows.append(run_case(final_axiom_path, axiom_path, case))
            except Exception as e:
                rows.append(
                    {
                        "axiom_file": axiom_path.name,
                        "scenario_id": case["scenario_id"],
                        "category": get_category(case),
                        "source_iteration": case["iteration"],
                        "source_index": case["index"],
                        "prob": case["prob"],
                        "imp": case["imp"],
                        "severity": case["severity"],
                        "expected": case.get("expected", "unsat"),
                        "z3_result": "error",
                        "status": "error",
                        "model": None,
                        "error": repr(e),
                    }
                )

    summary, category_summary = summarize(rows)

    write_csv(result_folder / "details.csv", rows)
    write_csv(result_folder / "summary.csv", summary)
    write_csv(result_folder / "category_summary.csv", category_summary)
    write_csv(result_folder / "eval_audit.csv", audit_rows)

    with open(result_folder / "details.jsonl", "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    with open(result_folder / "summary.yaml", "w") as f:
        yaml.dump(summary, f, sort_keys=False)

    with open(result_folder / "category_summary.yaml", "w") as f:
        yaml.dump(category_summary, f, sort_keys=False)

    logger.info(f"Wrote {result_folder / 'summary.csv'}")
    logger.info(f"Wrote {result_folder / 'category_summary.csv'}")
    logger.info(f"Wrote {result_folder / 'details.csv'}")
    logger.info(f"Wrote {result_folder / 'eval_audit.csv'}")