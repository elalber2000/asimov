from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, TypeVar

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

SRC_PATH = Path(__file__).resolve().parents[0]
load_dotenv()

OutputSchemaT = TypeVar("OutputSchemaT", bound=BaseModel)


class LLM:
    def __init__(
        self,
        default_model_id: str = "minimaxai/minimax-m2.7",
        batch_size: int = 8,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        api_key: str | None = None,
        temperature: float = 0.0,
        max_retries: int = 2,
    ):
        self.url = base_url
        self.default_model_id = default_model_id
        self.batch_size = batch_size
        self.temperature = temperature
        self.max_retries = max_retries

        self.api_key = (
            api_key
            or os.getenv("NVIDIA_KEY")
            or os.getenv("NVIDIA-KEY")
        )

        if not self.api_key:
            raise ValueError(
                "Missing NVIDIA API key. Set NVIDIA_KEY or NVIDIA-KEY."
            )

    def _get_model(
        self,
        model_id: str | None = None,
        output_format: type[OutputSchemaT] | None = None,
    ):
        model = ChatOpenAI(
            model=model_id or self.default_model_id,
            base_url=self.url,
            api_key=self.api_key,
            temperature=self.temperature,
            max_retries=self.max_retries,
        )

        if output_format is not None:
            return model.with_structured_output(
                output_format,
                method="function_calling",
            )

        return model

    @staticmethod
    def _extract_text(response: Any) -> str:
        content = getattr(response, "content", response)

        if isinstance(content, str):
            return content
        elif isinstance(content, list) and isinstance(content[-1], str):
            return content[-1]

        raise Exception(f"Error content of type {type(content)}")

    @staticmethod
    def _run_async_sync(coro):
        """
        Runs async code from a sync function.

        Works both in normal Python scripts and environments that already have
        a running event loop, such as notebooks.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(coro))
            return future.result()

    def invoke(
        self,
        prompt: str,
        model_id: str | None = None,
        output_format: type[OutputSchemaT] | None = None,
    ) -> str | OutputSchemaT:
        model = self._get_model(
            model_id=model_id,
            output_format=output_format,
        )

        response = model.invoke(prompt)

        if output_format is not None:
            return response

        return self._extract_text(response)

    async def _async_invoke_impl(
        self,
        prompts: list[str],
        model_id: str | None = None,
        output_format: type[OutputSchemaT] | None = None,
    ) -> list[str | OutputSchemaT]:
        
        model = self._get_model(
            model_id=model_id,
            output_format=output_format,
        )

        results: list[str | OutputSchemaT] = []

        for i in range(0, len(prompts), self.batch_size):
            batch = prompts[i : i + self.batch_size]

            responses = await asyncio.gather(
                *(model.ainvoke(prompt) for prompt in batch)
            )

            if output_format is not None:
                results.extend(responses)
            else:
                results.extend(self._extract_text(response) for response in responses)

        return results

    def async_invoke(
        self,
        prompts: list[str],
        model_id: str | None = None,
        output_format: type[OutputSchemaT] | None = None,
    ) -> list[str | OutputSchemaT]:
        """
        Sync public method.

        Internally uses LangChain ainvoke() concurrently in batches.
        Call this WITHOUT await.
        """
        return self._run_async_sync(
            self._async_invoke_impl(
                prompts=prompts,
                model_id=model_id,
                output_format=output_format,
            )
        )