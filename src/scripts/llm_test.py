from pydantic import BaseModel, Field
from utils.llm import LLM

class Answer(BaseModel):
    answer: str = Field(description="The direct answer")
    confidence: float = Field(description="Confidence from 0 to 1")

llm = LLM()

result = llm.invoke(
    prompt="What is 2 + 2?",
    output_format=Answer,
)
print(result)

# results = llm.async_invoke(
#     prompts=[
#         "Summarize LangChain in one sentence.",
#         "Summarize Pydantic in one sentence.",
#         "Summarize FastAPI in one sentence.",
#         "Summarize Docker in one sentence.",
#         "Summarize Kubernetes in one sentence.",
#         "Summarize PostgreSQL in one sentence.",
#     ],
#     model_id="mistralai/mistral-nemotron",
#     output_format=Answer,
# )
# print(results)