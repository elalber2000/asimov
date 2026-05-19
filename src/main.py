
from config import config
from utils.utils import get_latest_axioms, load_axioms_from_file, check_solvability

def llm_convert(x):
    pass

def z3_validate(x):
    pass

def nl_to_logic(axioms):
    while True:
        logic_axioms = llm_convert(axioms)
        if z3_validate(logic_axioms):
            break
    return logic_axioms

def llm_counters(logic_axioms):
    pass


class Counter:
    counter: str
    logic_counter: str
    probability: int
    importance: int


def eval_counter(axioms):
    pass

def eval_counters(axioms, counters):
    eval = 0
    for i in counters:
        if eval_counter(axioms, i):
            eval += i.probability * i.importance
    return eval / len(counters)

def generate_axioms(axioms, counters):
    pass


for i in range(config.iteration_number):
    scaffolding, axioms = load_axioms_from_file(get_latest_axioms(config.axiom_folder))
    check_solvability(scaffolding, axioms)
    break
    counters: list[Counter] = llm_counters(axioms)
    eval = eval_counters(axioms, counters)
    nl_axioms = generate_axioms(axioms, counters)
    axioms = nl_to_logic(nl_axioms)


from datetime import datetime, timezone

# Current Unix timestamp (seconds)
timestamp = datetime.now(timezone.utc).timestamp()
print(timestamp)