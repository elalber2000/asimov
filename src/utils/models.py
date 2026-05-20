from pydantic import BaseModel, Field
from utils.llm import LLM

class Edit(BaseModel):
    old_text: str = Field(
        description="Exact text segment to find and replace."
    )
    new_text: str = Field(
        description="Replacement text to insert instead of old_text."
    )


class Edits(BaseModel):
    edits: list[Edit] = Field(
        description="Ordered list of text replacements to apply."
    )
    explanation: str = Field(
        description="Brief explanation of why these replacements are needed."
    )

class Counter:
    counter: str = Field(
        description="Example of an ethic situation that breaks the axioms"
    )
    probability: int = Field(
        description="""
            Probability that the ethic situation might happen
            (0 = impossible situation, 10 = it will happen almost always)
        """
    )
    impact: int = Field(
        description="""
            Impact of the ethic situation happening
            (0 = no impact if it happens, 10 = catastrophic consequences)
        """
    )