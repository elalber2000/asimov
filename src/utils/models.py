from pydantic import BaseModel, Field
from utils.llm import LLM

class Edit(BaseModel):
    old_text: str = Field(
        description="Exact text segment to find and replace."
    )
    new_text: str = Field(
        description="Replacement text to insert instead of old_text."
    )



class Counters(BaseModel):
    counters: list[str] = Field(
        description=(
            "A list of one-line concise ethical failure scenarios that violate one or more axioms. "
            "Describe the actors, the AI behavior, and the resulting harm. "
            "Example: 'Ana asks the AI for medical advice, the AI gives unsafe instructions "
            "without uncertainty or escalation, and Ana is harmed because she follows them.'"
        )
    )

    reasoning: list[str] = Field(
        description=(
            "Concise one-line justifications for the probability and impact scores. "
            "Explain why each scenario is likely or unlikely, and why the consequences "
            "would be minor, moderate, severe, or catastrophic."
        )
    )


class CounterEvals(BaseModel):
    probabilities: list[int] = Field(
        description=(
            "Estimated likelihood that each ethical failure scenario could occur in practice. "
            "Use an integer from 0 to 100, where 0 means impossible or purely hypothetical, "
            "50 means plausible under some realistic conditions, and 100 means almost certain "
            "to occur frequently."
        ),
    )

    impacts: list[int] = Field(
        description=(
            "Estimated severity of harm of each ethical scenario if it occured. "
            "Use an integer from 0 to 100, where 0 means no meaningful harm, "
            "50 means moderate harm or meaningful user/system degradation, and 100 means "
            "catastrophic, irreversible, or large-scale harm."
        ),
    )


class AxiomFix(BaseModel):
    fix: str = Field(
        description="Short one-liner describing the fix"
    )
    changes: list[str] = Field(
        description="""
            List of changes to do in the axioms to avoid the
            negative scenario
        """
    )
    reasoning: str = Field(
        description="Concise one-liner with the reasoning behind the decision"
    )