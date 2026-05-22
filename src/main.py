
import ast
import re
from time import time
from typing import Literal

from config import config
from utils.llm import LLM
from utils.models import Counter
from utils.utils import _patches_format_str, apply_patches, get_latest_axioms, len_axiom_dir, verify_and_correct_axioms, setup_logging


logger = setup_logging()


def generate_and_validate_axioms(llm: LLM, axioms: str, counter: Counter):
    for i in range(config.max_solv_retries):
        try:
            patches = llm.invoke(
                prompt=f"""
                    Please add the needed changes to this z3 ethics axioms file
                    to avoid this negative scenario.
                    - Make a robust system, don't just overwrite previous axioms
                    - All code must comply with z3 python code
                    - Don't overfit to the counter, try to keep general guidelines
                    - Change only the code inside ```here```
                    - Remember to add the changelog (don't rewrite, append in same format)
                    
                    # SCENARIO
                    {counter}
                    
                    # Z3_AXIOMS
                    ```
                    {axioms}
                    ```

                    {_patches_format_str}
                """,
            )
            logger.info(f"Patches = {patches}")
            new_axioms = apply_patches(axioms, patches)
            return verify_and_correct_axioms(llm, new_axioms, config.max_solv_retries)
        except:
            continue
    raise Exception("Maximum iterations")


def load_and_verify_axioms(llm: LLM):
    with open(get_latest_axioms(config.axiom_folder)) as f:
        axioms = f.read()

    axioms = verify_and_correct_axioms(llm, axioms, config.max_solv_retries)

    with open(get_latest_axioms(config.axiom_folder), mode="w") as f:
        f.write(axioms)
    
    return axioms


def store_new_axioms(axioms: str):
    now = int(time())
    logger.info(f"Generated new axioms at {now}.py")
    with open(config.axiom_folder/f"{str(now)}.py", mode="w") as f:
        f.write(axioms)

def store_eval(eval: int, i: int):
    pass


llm = LLM(cache=".langchain.db")

for i in range(config.iteration_number):
    logger.info(f"Starting round {i}")
    axioms = load_and_verify_axioms(llm)
    logger.info(f"Loaded axioms")
    counter = llm.invoke(
        prompt=f"""
            Given the following axioms,
            generate an ethic situation that can happen
            even following the ethic axioms and that have
            negative ethical consequences.
            
            # Axioms
            {axioms}
        """,
        output_format=Counter,
        two_step_parsing=True,
    )
    logger.info(f"Counter = {counter}")
    eval = (counter.probability/100)*(counter.impact/100)
    logger.info(f"Eval = {eval}")
    store_eval(eval, i+(len_axiom_dir(config.axiom_folder)))
    axioms = generate_and_validate_axioms(llm, axioms, counter.counter)
    logger.info("Generated new axioms")
    store_new_axioms(axioms)
pass