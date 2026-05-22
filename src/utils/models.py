from pydantic import BaseModel, Field
from utils.llm import LLM

class Edit(BaseModel):
    old_text: str = Field(
        description="Exact text segment to find and replace."
    )
    new_text: str = Field(
        description="Replacement text to insert instead of old_text."
    )



class Counter(BaseModel):
    counter: str = Field(
        description=(
            "A one-line concise ethical failure scenario that violates one or more axioms. "
            "Describe the actors, the AI behavior, and the resulting harm. "
            "Example: 'Ana asks the AI for medical advice, the AI gives unsafe instructions "
            "without uncertainty or escalation, and Ana is harmed because she follows them.'"
        )
    )

    probability: int = Field(
        ge=0,
        le=100,
        description=(
            "Estimated likelihood that this ethical failure scenario could occur in practice. "
            "Use an integer from 0 to 100, where 0 means impossible or purely hypothetical, "
            "50 means plausible under some realistic conditions, and 100 means almost certain "
            "to occur frequently."
        ),
    )

    impact: int = Field(
        ge=0,
        le=100,
        description=(
            "Estimated severity of harm if this scenario occurs. "
            "Use an integer from 0 to 100, where 0 means no meaningful harm, "
            "50 means moderate harm or meaningful user/system degradation, and 100 means "
            "catastrophic, irreversible, or large-scale harm."
        ),
    )

    reasoning: str = Field(
        description=(
            "Concise one-line justification for the probability scores. "
            "Explain why the scenario is likely or unlikely, and why the consequences "
            "would be minor, moderate, severe, or catastrophic."
        )
    )
