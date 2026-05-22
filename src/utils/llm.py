import os
from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache


SRC_PATH = Path(__file__).resolve().parents[0]
load_dotenv()

OutputSchemaT = TypeVar("OutputSchemaT", bound=BaseModel)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


def _env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _is_openrouter_model(model_id: str) -> bool:
    return model_id.strip().lower().startswith("openrouter/")


class LLM:
    def __init__(
        self,
        default_model_id: str = "openrouter/free",
        batch_size: int = 8,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.0,
        max_retries: int = 2,
        max_completion_tokens: int = 4096,
        cache: str | None = None
    ):
        self.default_model_id = default_model_id
        self.batch_size = batch_size
        self.base_url = base_url
        self.api_key = api_key
        self.temperature = temperature
        self.max_retries = max_retries
        self.max_completion_tokens = max_completion_tokens
        if cache is not None:
            set_llm_cache(SQLiteCache(database_path=cache))

    def _make_client(self, model_id: str) -> ChatOpenAI:
        model_id = model_id.strip()

        if _is_openrouter_model(model_id):
            if model_id != "openrouter/free":
                raise ValueError(
                    "OpenRouter is restricted to the free router only. "
                    f"Use model_id='{"openrouter/free"}', got '{model_id}'."
                )

            api_key = self.api_key or _env("OPENROUTER-KEY")

            if not api_key:
                raise RuntimeError("Missing OPENROUTER-KEY")

            return ChatOpenAI(
                model="openrouter/free",
                base_url=OPENROUTER_BASE_URL,
                api_key=api_key,
                temperature=self.temperature,
                max_retries=self.max_retries,
                max_tokens=self.max_completion_tokens,
                default_headers={
                    k: v
                    for k, v in {
                        "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER"),
                        "X-Title": os.getenv("OPENROUTER_APP_TITLE"),
                    }.items()
                    if v
                }
                or None,
            )

        api_key = self.api_key or _env("NVIDIA-KEY")

        if not api_key:
            raise RuntimeError("Missing NVIDIA-KEY")

        return ChatOpenAI(
            model=model_id,
            base_url=self.base_url or NVIDIA_BASE_URL,
            api_key=api_key,
            temperature=self.temperature,
            max_retries=self.max_retries,
            max_tokens=self.max_completion_tokens,
        )

    def invoke(
        self,
        prompt: str,
        model_id: str | None = None,
        output_format: type[OutputSchemaT] | None = None,
        two_step_parsing: bool = False
    ) -> str | OutputSchemaT:
        if two_step_parsing and output_format is None:
            Warning("Two-step-parsing only available if output_format is not None")

        resolved_model_id = model_id or self.default_model_id
        llm = self._make_client(resolved_model_id)

        if output_format is not None:
            if two_step_parsing:
                print(', '.join(f'{name}: [{field.description}]'
                            for name, field
                            in output_format.model_fields.items()))
                first_step_res = self.invoke(
                    prompt=f"""
                        {prompt}

                        You need to return the following:
                        {
                            ', '.join(f'{name} ({field.description})'
                            for name, field
                            in output_format.model_fields.items())
                        }

                        Be concise!
                    """,
                    model_id=model_id,
                )
                print(first_step_res)
                return llm.with_structured_output(output_format).invoke(
                    f"""
                        Parse the following text into the given json:
                        "{first_step_res}"

                        Remember to be concise
                    """
                    )
            return llm.with_structured_output(output_format).invoke(prompt)

        response = llm.invoke(prompt)
        return str(response.content)