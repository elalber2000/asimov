
from typing import Counter

from config import config
from utils.llm import LLM
from utils.models import Edits
from utils.utils import edit_text_tool, get_latest_axioms, load_axioms_from_file, check_solvability
from z3 import sat, unsat, unknown

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




def load_and_check_axioms(llm: LLM):
    for i in range(config.max_solv_retries):
        scaffolding, axioms = load_axioms_from_file(get_latest_axioms(config.axiom_folder))
        solv = check_solvability(scaffolding, axioms)
        if solv==sat:
            break
        with open(get_latest_axioms(config.axiom_folder)) as f:
            axioms_str = f.read()
        edits = llm.invoke(
            prompt=f"""
                Please give the edits to correct this z3 file
                as its returning {solv}
                
                # Axioms
                {axioms_str}
            """,
            output_format=Edits,
        )
        axioms_str = edit_text_tool(axioms_str, edits)
        with open(get_latest_axioms(config.axiom_folder), mode="w") as f:
            f.write(axioms_str)
    return axioms_str



llm = LLM()

for i in range(config.iteration_number):
    load_and_check_axioms(llm)
    counters: list[Counter] = llm.invoke(
        prompt=f"""
            Given the following axioms and scaffolding,
            generate ethic situations that can happen
            even following the ethic axioms and that have
            negative ethical consequences.
            
            # Axioms
            {axioms_str}
        """,
        output_format=Edits,
    )
    eval = eval_counters(axioms, counters)
    nl_axioms = generate_axioms(axioms, counters)
    axioms = nl_to_logic(nl_axioms)


from datetime import datetime, timezone

# Current Unix timestamp (seconds)
timestamp = datetime.now(timezone.utc).timestamp()
print(timestamp)