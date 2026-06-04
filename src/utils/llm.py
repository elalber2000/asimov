import inspect
import os
from pathlib import Path
import re
from time import sleep
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
    
    @staticmethod
    def extract_json(text: str) -> str:
        """
        Priority:
        1. ```json { ... } ```
        2. ``` { ... } ```
        3. Raw { ... }
        """

        def _biggest(items: list[str]) -> str | None:
            return max(items, key=len) if items else None
        
        def _extract_balanced_braces(text: str, start: int) -> str | None:
            if start >= len(text) or text[start] != "{":
                return None

            depth = 0
            in_string = escape = False

            for i, ch in enumerate(text[start:], start):
                if in_string:
                    escape = ch == "\\" and not escape
                    if ch == '"' and not escape:
                        in_string = False
                    elif ch != "\\":
                        escape = False
                    continue

                if ch == '"':
                    in_string = True
                    continue

                if ch in "{}":
                    depth += 1 if ch == "{" else -1
                    if depth == 0:
                        return text[start : i + 1]

            return None

        # 1. Fenced ```json ... ```
        json_fence_matches = []
        for match in re.finditer(r"```\s*json\b\s*", text, flags=re.IGNORECASE):
            brace_match = re.search(r"\{", text[match.end() :])
            if not brace_match:
                continue

            start = match.end() + brace_match.start()
            extracted = _extract_balanced_braces(text, start)

            if extracted is not None:
                rest = text[start + len(extracted) :]
                if re.match(r"\s*```", rest):
                    json_fence_matches.append(extracted)

        result = _biggest(json_fence_matches)
        if result is not None:
            return result

        # 2. Fenced ``` ... ```
        plain_fence_matches = []
        for match in re.finditer(r"```\s*", text):
            after_fence = text[match.end() :]
            if re.match(r"json\b", after_fence, flags=re.IGNORECASE):
                continue

            brace_match = re.search(r"\{", after_fence)
            if not brace_match:
                continue

            start = match.end() + brace_match.start()
            extracted = _extract_balanced_braces(text, start)

            if extracted is not None:
                rest = text[start + len(extracted) :]
                if re.match(r"\s*```", rest):
                    plain_fence_matches.append(extracted)

        result = _biggest(plain_fence_matches)
        if result is not None:
            return result

        # 3. Raw { ... }
        raw_matches = []
        for match in re.finditer(r"\{", text):
            extracted = _extract_balanced_braces(text, match.start())
            if extracted is not None:
                raw_matches.append(extracted)

        result = _biggest(raw_matches)
        if result is not None:
            return result

        raise Exception("No valid code found")

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
                return self.invoke(
                    prompt=f"""
                        Parse the following text into the given json:
                        "{first_step_res}"

                        Remember to be concise
                    """,
                    model_id=model_id,
                    output_format=output_format,
                    two_step_parsing=False,
                )
            else:
                response = self.invoke(
                    prompt=(
                        prompt+
                        f"""
                        \n\n# Format
                        Return your output inside a md code block
                        ```here``` as a json with the format
                        The json should have a format as
                        {inspect.getsource(output_format)}
                        """),
                    model_id=model_id,
                    output_format=None,
                    two_step_parsing=False,
                )
                json = self.extract_json(response)
                return output_format.model_validate_json(json)

        response = llm.invoke(prompt)
        return str(response.content)