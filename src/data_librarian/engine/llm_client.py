"""LLM client for generating answers."""

from typing import Optional, Dict, Any
import openai
from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: Input prompt
            **kwargs: Additional provider-specific arguments

        Returns:
            Generated response text
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI API client."""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model name to use
        """
        self.api_key = api_key
        self.model = model
        openai.api_key = api_key

    def generate(self, prompt: str, messages: Optional[list] = None, **kwargs) -> str:
        """Generate a response using OpenAI API.

        Args:
            prompt: Input prompt (ignored if messages provided)
            messages: Optional chat messages format
            **kwargs: Additional OpenAI API arguments

        Returns:
            Generated response text
        """
        if messages:
            # Use chat completions API
            response = openai.chat.completions.create(
                model=self.model, messages=messages, **kwargs
            )
            return response.choices[0].message.content
        else:
            # Use chat completions with simple prompt
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            return response.choices[0].message.content


class DatabricksClient(LLMClient):
    """Databricks Foundation Model API client."""

    def __init__(self, host: str, token: str, model: str = "databricks-dbrx-instruct"):
        """Initialize Databricks client.

        Args:
            host: Databricks workspace URL
            token: Personal access token
            model: Model name to use
        """
        self.host = host.rstrip("/")
        self.token = token
        self.model = model

    def generate(self, prompt: str, messages: Optional[list] = None, **kwargs) -> str:
        """Generate a response using Databricks Foundation Model API.

        Args:
            prompt: Input prompt
            messages: Optional chat messages format
            **kwargs: Additional API arguments

        Returns:
            Generated response text
        """
        import requests

        # Construct API endpoint
        url = f"{self.host}/serving-endpoints/{self.model}/invocations"

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        # Prepare request body
        if messages:
            data = {"messages": messages, **kwargs}
        else:
            data = {"prompt": prompt, **kwargs}

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")


class LocalClient(LLMClient):
    """Fallback client that doesn't use an LLM."""

    def generate(self, prompt: str, **kwargs) -> str:
        """Return a message indicating local mode.

        Args:
            prompt: Input prompt (ignored)
            **kwargs: Additional arguments (ignored)

        Returns:
            Information message
        """
        return "LLM provider set to 'local'. Only retrieval results are shown. Set LLM_PROVIDER to 'openai' or 'databricks' for AI-generated responses."


def create_llm_client(
    provider: str,
    openai_api_key: Optional[str] = None,
    databricks_host: Optional[str] = None,
    databricks_token: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMClient:
    """Factory function to create an LLM client.

    Args:
        provider: LLM provider ('openai', 'databricks', or 'local')
        openai_api_key: OpenAI API key (required for openai provider)
        databricks_host: Databricks host (required for databricks provider)
        databricks_token: Databricks token (required for databricks provider)
        model: Optional model name override

    Returns:
        LLM client instance

    Raises:
        ValueError: If required credentials are missing
    """
    if provider == "openai":
        if not openai_api_key:
            raise ValueError("OpenAI API key required for openai provider")
        return OpenAIClient(api_key=openai_api_key, model=model or "gpt-3.5-turbo")

    elif provider == "databricks":
        if not databricks_host or not databricks_token:
            raise ValueError("Databricks host and token required for databricks provider")
        return DatabricksClient(
            host=databricks_host,
            token=databricks_token,
            model=model or "databricks-dbrx-instruct",
        )

    elif provider == "local":
        return LocalClient()

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
