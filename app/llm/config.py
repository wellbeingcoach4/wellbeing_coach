"""
LLM Configuration and Handler for different LLM providers
Supports: Ollama, Groq, and Gemini
"""

import os
from enum import Enum
from typing import Any
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env
load_dotenv()

# Normalize environment keys and provide tolerant getters
# Some .env files may contain accidental spaces around keys or use alternate names
for _k in list(os.environ.keys()):
    if _k.strip() != _k:
        os.environ[_k.strip()] = os.environ[_k]
        try:
            del os.environ[_k]
        except Exception:
            pass


def _get_env(*names, default: str = "") -> str:
    """Return the first existing environment variable from names, stripped.

    This helper allows using alternate variable names (e.g. LOCAL_BASE_URL
    or LOCAL_BASE_URL) and strips accidental whitespace from values.
    """
    for name in names:
        val = os.getenv(name)
        if val is not None:
            return val.strip()
    return default


class LLMProvider(str, Enum):
    """Available LLM providers"""
    OLLAMA = "ollama"
    GROQ = "groq"
    GEMINI = "gemini"


class OllamaConfig(BaseModel):
    """Configuration for Ollama"""
    base_url: str
    model: str
    timeout: int = 180


class GroqConfig(BaseModel):
    """Configuration for Groq"""
    api_key: str
    base_url: str
    model: str
    timeout: int = 30


class GeminiConfig(BaseModel):
    """Configuration for Gemini"""
    api_key: str
    base_url: str
    model: str
    timeout: int = 30


class LLMConfig:
    """
    Master LLM configuration class
    """

    def __init__(self):

        # Providers (tolerant to slightly different env var names and spacing)
        self.provider = _get_env("LLM_PROVIDER", default="ollama").lower()
        self.fallback_provider = _get_env("LLM_FALLBACK_PROVIDER", default="groq").lower()

        # Provider Configurations (support alternate env names like LOCAL_...)
        self.ollama = OllamaConfig(
            base_url=_get_env("LOCAL_BASE_URL", "LOCAL_BASE_URL", default="http://localhost:11434"),
            model=_get_env("LOCAL_MODEL", "LOCAL_MODEL", default="llama3.1:8b"),
            timeout=int(_get_env("OLLAMA_TIMEOUT", default="180"))
        )

        self.groq = GroqConfig(
            api_key=_get_env("GROQ_API_KEY", "GROQ_APIKEY", default=""),
            base_url=_get_env("GROQ_BASE_URL", default="https://api.groq.com/openai/v1"),
            model=_get_env("GROQ_MODEL", "GROQ_MODEL_NAME", default="llama-3.1-8b-instant"),
            timeout=int(_get_env("GROQ_TIMEOUT", default="30"))
        )

        self.gemini = GeminiConfig(
            api_key=_get_env("GEMINI_API_KEY", default=""),
            base_url=_get_env("GEMINI_BASE_URL", default="https://generativelanguage.googleapis.com/v1beta/openai"),
            model=_get_env("GEMINI_MODEL", default="gemini-2.5-flash"),
            timeout=int(_get_env("GEMINI_TIMEOUT", default="30"))
        )

    def get_primary_provider(self) -> LLMProvider:
        """Get the primary LLM provider"""

        try:
            return LLMProvider(self.provider)
        except ValueError:
            return LLMProvider.OLLAMA

    def get_fallback_provider(self) -> LLMProvider:
        """Get the fallback LLM provider"""

        try:
            return LLMProvider(self.fallback_provider)
        except ValueError:
            return LLMProvider.GROQ

    def get_config_for_provider(
        self,
        provider: LLMProvider
    ) -> Any:
        """Get configuration for provider"""

        if provider == LLMProvider.OLLAMA:
            return self.ollama

        if provider == LLMProvider.GROQ:
            return self.groq

        if provider == LLMProvider.GEMINI:
            return self.gemini

        raise ValueError(f"Unknown provider: {provider}")


# Global configuration instance
llm_config = LLMConfig()