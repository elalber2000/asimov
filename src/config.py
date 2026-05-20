from pydantic import BaseModel
from utils.utils import SRC_PATH

class Config(BaseModel):
    iteration_number: int = 10
    axiom_folder: str = SRC_PATH / "data" / "axioms"
    max_solv_retries: int = 10


config = Config()