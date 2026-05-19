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
