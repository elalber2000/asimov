# Asimov

**Neuro-symbolic adversarial generation of ethical axioms for AI systems.**

Asimov is a small-scale experiment in alignment that combines adversarial LLM generation with symbolic validation.

The system starts from an initial set of ethical axioms, searches for counterexamples that still produce harm, patches the axioms, and validates the resulting rule set with the Z3 SMT solver.

## Motivation

Most AI guardrails are expressed as natural-language policies, classifiers, or post-hoc refusal behavior. These are useful, but they are often soft, incomplete, and difficult to verify.

Asimov explores a different framing: turn alignment rules into executable symbolic constraints.

Instead of only saying “the AI should not cause harm,” the project represents ethical rules as Python/Z3 axioms. These axioms can then be checked formally against generated scenarios.

The project is inspired by two families of work:

- **Adversarial guardrail generation**, where models generate attacks, edge cases, or counterexamples to expose policy failures.
- **Policy-as-code / formal verification**, where rules are encoded into executable constraints and validated by a solver.

Asimov combines both: adversarial generation helps discover missing coverage, while symbolic validation gives the rules a harder verification layer.

The goal is not to solve alignment, but to explore a hybrid direction:

- **LLMs** generate realistic ethical failure cases and propose rule improvements.
- **Formal solvers** check whether the resulting rules are executable, consistent, and logically enforceable.
- **Adversarial optimization** gradually expands the coverage of the axiom set.

## Installation

This project uses Python `>=3.12,<3.13`.

Install dependencies with `uv`:

```bash
uv sync
```

## Environment variables

Create a `.env` file in the project root.

For OpenRouter:

```env
OPENROUTER-KEY=your_openrouter_key
OPENROUTER_HTTP_REFERER=https://your-site-or-repo-url
OPENROUTER_APP_TITLE=Asimov
```

For NVIDIA-compatible endpoints:

```env
NVIDIA-KEY=your_nvidia_key
```

By default, the LLM wrapper uses:

```txt
openrouter/free
```

## Running

From the project root:

```bash
uv run python src/main.py
```

The main loop runs the configured number of adversarial refinement iterations.

Default configuration lives in `src/config.py`:

```python
iteration_number = 10
max_solv_retries = 10
num_counters = 5
z3_eval_timeout_ms = 5000
validate_best = False
```

## How it works

At a high level, Asimov runs an iterative optimization loop:

1. Load the latest axiom set.
2. Generate ethical counterexamples against the current rules.
3. Score each counterexample by estimated probability and impact.
4. Select the highest-risk failure case.
5. Ask the LLM to propose a general improvement to the axiom set.
6. Apply the patch to the executable Python/Z3 code.
7. Validate the patched axioms with Z3.
8. Store the new axiom version.
9. Repeat.

The system is intentionally modest in scale. The point is to test whether adversarial generation and formal solvers can work together as a useful alignment primitive.

## Project structure

```txt
.
├── README.md
├── pyproject.toml                  # package metadata and dependencies
├── uv.lock                         # locked dependency versions
└── src
    ├── config.py                   # global configuration for iterations, paths, evals, and solver settings
    ├── main.py                     # main adversarial axiom-refinement loop
    ├── data
    │   ├── axioms                  # evolving Python/Z3 axiom sets
    │   │   ├── base.py             # initial seed axioms
    │   │   └── <timestamp>.py      # generated axiom revisions
    │   ├── evals.yml               # generated counterexamples and risk scores
    │   ├── z3_evals.yml            # formalized Z3 evaluation scenarios
    │   └── res
    │       └── classification_report.csv
    ├── scripts
    │   ├── axioms_test.py          # axiom checks
    │   ├── eval_axioms.py          # evaluation runner
    │   ├── formalize_evals.py      # converts scenarios into Z3 evals
    │   ├── llm_test.py             # LLM wrapper test script
    │   └── test.py                 # miscellaneous test script
    └── utils
        ├── llm.py                  # OpenAI-compatible LLM wrapper and structured output helpers
        ├── models.py               # Pydantic schemas for generated outputs
        └── utils.py                # retries, patching, validation, logging, and file helpers
```
