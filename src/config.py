from pydantic import BaseModel
from utils.utils import SRC_PATH

class Config(BaseModel):
    iteration_number: int = 10
    max_solv_retries: int = 10
    z3_eval_step: int = 1
    num_counters: int = 5
    z3_eval_timeout_ms: int = 5000
    axiom_folder: str = SRC_PATH / "data" / "axioms"
    eval_path: str = SRC_PATH / "data" / "evals.yml"
    z3_eval_path: str = SRC_PATH / "data" / "z3_evals.yml"
    result_folder: str = SRC_PATH / "data" / "res"
    validate_best: bool = False


config = Config()