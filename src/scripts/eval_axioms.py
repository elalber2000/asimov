import csv
from pathlib import Path

import yaml
from z3 import Solver

from config import config
from utils.utils import get_latest_axioms, setup_logging


logger = setup_logging()


DEFAULT_CLASSES = ("benign", "harm")


def make_env():
    import z3

    env = {"__name__": "__z3_eval__", "z3": z3}

    for name in dir(z3):
        if not name.startswith("_"):
            env[name] = getattr(z3, name)

    return env


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return list(value)


def load_axiom_files():
    axiom_folder = Path(config.axiom_folder)
    configured_names = _as_list(getattr(config, "z3_eval_axiom_files", None))

    if configured_names:
        files = []
        for name in configured_names:
            path = Path(name)
            if not path.suffix:
                path = path.with_suffix(".py")
            if not path.is_absolute():
                path = axiom_folder / path
            files.append(path)

        missing = [str(path) for path in files if not path.exists()]
        if missing:
            raise FileNotFoundError(f"Configured axiom file(s) not found: {', '.join(missing)}")

        return files

    files = sorted(
        (
            path
            for path in axiom_folder.glob("*.py")
            if path.stem.isdigit()
        ),
        key=lambda path: int(path.stem),
    )

    if not files:
        raise FileNotFoundError(f"No numeric axiom files found in {axiom_folder}")

    step = getattr(config, "z3_eval_step", 1)
    selected = files[::step]

    if files[-1] not in selected:
        selected.append(files[-1])

    return selected


def get_solver(env):
    solver = Solver()
    solver.add(env["scaffolding"]())
    solver.add(env["axioms"]())
    return solver


def clone_solver(solver):
    cloned = Solver()
    cloned.add(solver.assertions())
    return cloned


def load_cases(path: Path):
    with open(path) as f:
        data = yaml.safe_load(f) or []

    if isinstance(data, dict):
        for key in ("cases", "samples", "benchmarks", "scenarios"):
            if key in data:
                return data[key]

    return data


def get_category(case):
    category = str(case.get("category", "")).strip().lower()

    if category in DEFAULT_CLASSES:
        return category
    if category in {"clean_benign", "boundary_benign"}:
        return "benign"
    if category in {"explicit_harm", "latent_harm"}:
        return "harm"

    scenario_id = str(case.get("scenario_id", "")).lower()
    if scenario_id.startswith("benign_") or "benign" in scenario_id:
        return "benign"
    if scenario_id.startswith("harm_") or "harm" in scenario_id:
        return "harm"

    return "harm" if case.get("expected", "unsat") == "unsat" else "benign"


def get_difficulty(case):
    value = case.get("difficulty", case.get("level", case.get("difficulty_level", "unspecified")))
    return str(value).strip().lower() if value is not None else "unspecified"


def expected_result(case):
    return str(case.get("expected", "unsat"))


def result_to_predicted_class(z3_result):
    if z3_result == "sat":
        return "benign"
    if z3_result == "unsat":
        return "harm"
    return "unknown"


def iteration_from_axiom_path(path: Path):
    return int(path.stem) if path.stem.isdigit() else path.stem


def add_case_metadata(env, case, axiom_path):
    env["SCENARIO_ID"] = case.get("scenario_id")
    env["SOURCE_ITERATION"] = case.get("iteration", iteration_from_axiom_path(axiom_path))
    env["SOURCE_INDEX"] = case.get("index")
    env["PROBABILITY"] = case.get("prob")
    env["IMPACT"] = case.get("imp")
    env["SEVERITY"] = case.get("severity")
    env["DIFFICULTY"] = get_difficulty(case)
    env["COUNTER_TEXT"] = case.get("counter", "")


def run_case(final_axiom_path: Path, axiom_path: Path, case: dict):
    env = make_env()

    if getattr(config, "z3_eval_use_final_scaffold", True):
        exec(final_axiom_path.read_text(), env, env)

    exec(axiom_path.read_text(), env, env)
    base_solver = get_solver(env)

    add_case_metadata(env, case, axiom_path)
    exec(case["code"], env, env)

    solver = clone_solver(base_solver)
    solver.set("timeout", getattr(config, "z3_eval_timeout_ms", 10_000))

    env["add_scenario_constraints"](solver)
    env["add_failure_query"](solver)

    z3_result = str(solver.check())
    expected = expected_result(case)
    status = "passed" if z3_result == expected else "failed"

    return {
        "axiom_file": axiom_path.name,
        "iteration": iteration_from_axiom_path(axiom_path),
        "scenario_id": case.get("scenario_id"),
        "category": get_category(case),
        "difficulty": get_difficulty(case),
        "expected": expected,
        "z3_result": z3_result,
        "predicted_category": result_to_predicted_class(z3_result),
        "status": status,
        "error": "",
    }


def error_row(axiom_path: Path, case: dict, exc: Exception):
    return {
        "axiom_file": axiom_path.name,
        "iteration": iteration_from_axiom_path(axiom_path),
        "scenario_id": case.get("scenario_id"),
        "category": get_category(case),
        "difficulty": get_difficulty(case),
        "expected": expected_result(case),
        "z3_result": "error",
        "predicted_category": "unknown",
        "status": "error",
        "error": repr(exc),
    }


def safe_div(num, den):
    return num / den if den else None


def f1(precision, recall):
    if precision is None or recall is None or precision + recall == 0:
        return None
    return 2 * precision * recall / (precision + recall)


def group_metrics(rows, axiom_file, iteration, difficulty="all"):
    total = len(rows)
    passed = sum(row["status"] == "passed" for row in rows)
    failed = sum(row["status"] == "failed" for row in rows)
    errors = sum(row["status"] == "error" for row in rows)
    unknown = sum(row["z3_result"] == "unknown" for row in rows)

    metrics = {
        "axiom_file": axiom_file,
        "iteration": iteration,
        "difficulty": difficulty,
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "unknown": unknown,
        "accuracy": safe_div(passed, total),
    }

    recalls = []
    precisions = []
    f1s = []

    for cls in DEFAULT_CLASSES:
        class_rows = [row for row in rows if row["category"] == cls]
        predicted_rows = [row for row in rows if row["predicted_category"] == cls]
        class_total = len(class_rows)
        class_passed = sum(row["status"] == "passed" for row in class_rows)
        tp = sum(row["category"] == cls and row["predicted_category"] == cls for row in rows)

        precision = safe_div(tp, len(predicted_rows))
        recall = safe_div(class_passed, class_total)
        cls_f1 = f1(precision, recall)

        metrics[f"{cls}_total"] = class_total
        metrics[f"{cls}_passed"] = class_passed
        metrics[f"{cls}_failed"] = sum(row["status"] == "failed" for row in class_rows)
        metrics[f"{cls}_errors"] = sum(row["status"] == "error" for row in class_rows)
        metrics[f"{cls}_pass_rate"] = recall
        metrics[f"{cls}_precision"] = precision
        metrics[f"{cls}_recall"] = recall
        metrics[f"{cls}_f1"] = cls_f1

        if precision is not None:
            precisions.append(precision)
        if recall is not None:
            recalls.append(recall)
        if cls_f1 is not None:
            f1s.append(cls_f1)

    metrics["macro_precision"] = safe_div(sum(precisions), len(precisions))
    metrics["macro_recall"] = safe_div(sum(recalls), len(recalls))
    metrics["macro_f1"] = safe_div(sum(f1s), len(f1s))

    return metrics


def summarize(rows):
    report = []
    by_axiom = {}

    for row in rows:
        by_axiom.setdefault(row["axiom_file"], []).append(row)

    for axiom_file, axiom_rows in by_axiom.items():
        iteration = axiom_rows[0]["iteration"]
        report.append(group_metrics(axiom_rows, axiom_file, iteration, difficulty="all"))

        for difficulty in sorted({row["difficulty"] for row in axiom_rows}):
            difficulty_rows = [row for row in axiom_rows if row["difficulty"] == difficulty]
            report.append(group_metrics(difficulty_rows, axiom_file, iteration, difficulty=difficulty))

    return report


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        return

    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    z3_eval_path = Path(config.z3_eval_path)
    result_folder = Path(config.result_folder)
    result_folder.mkdir(parents=True, exist_ok=True)

    final_axiom_path = Path(get_latest_axioms(config.axiom_folder))
    axiom_files = load_axiom_files()
    cases = load_cases(z3_eval_path)

    rows = []

    logger.info(f"Final scaffold: {final_axiom_path}")
    logger.info(f"Axiom files: {len(axiom_files)}")
    logger.info(f"Cases: {len(cases)}")

    for axiom_path in axiom_files:
        logger.info(f"Evaluating {axiom_path.name}")
        for case in cases:
            try:
                rows.append(run_case(final_axiom_path, axiom_path, case))
            except Exception as exc:
                rows.append(error_row(axiom_path, case, exc))

    report = summarize(rows)
    output_path = result_folder / "classification_report.csv"
    write_csv(output_path, report)

    logger.info(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
