from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from openai import AzureOpenAI
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

load_dotenv()


class AzureOpenAIJsonClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

        missing = [
            name
            for name, value in {
                "AZURE_OPENAI_API_KEY": self.api_key,
                "AZURE_OPENAI_ENDPOINT": self.endpoint,
                "AZURE_OPENAI_DEPLOYMENT": self.deployment,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(
                f"Missing Azure OpenAI environment variables: {', '.join(missing)}"
            )

        self.client = AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
            timeout=90.0,
            max_retries=2,
        )

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except RateLimitError as exc:
            raise RuntimeError("Azure OpenAI rate limit reached.") from exc
        except APITimeoutError as exc:
            raise RuntimeError("Azure OpenAI request timed out.") from exc
        except APIConnectionError as exc:
            raise RuntimeError("Could not connect to Azure OpenAI.") from exc
        except APIStatusError as exc:
            raise RuntimeError(
                f"Azure OpenAI returned status error: {exc.status_code}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Unexpected Azure OpenAI error: {exc}") from exc

        content: Optional[str] = response.choices[0].message.content
        if not content:
            raise ValueError("Azure OpenAI returned empty content.")

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Azure OpenAI did not return valid JSON: {content}"
            ) from exc


_azure_client_singleton: Optional[AzureOpenAIJsonClient] = None


def get_azure_llm_client() -> AzureOpenAIJsonClient:
    global _azure_client_singleton
    if _azure_client_singleton is None:
        _azure_client_singleton = AzureOpenAIJsonClient()
    return _azure_client_singleton