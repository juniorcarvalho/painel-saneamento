"""Configuração do agente (Groq) carregada do .env."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Configuração ausente ou inválida."""


class ExternalServiceError(RuntimeError):
    """Falha do provedor externo de LLM."""


class LimiteExcedido(ExternalServiceError):
    """Limite de taxa do provedor atingido (HTTP 429)."""


@dataclass(frozen=True)
class Settings:
    groq_api_key: str = field(repr=False)
    model_name: str
    base_url: str
    temperature: float
    http_timeout: float

    def require_api_key(self) -> str:
        """Verificação preguiçosa: só ao construir o LLM."""
        if not self.groq_api_key:
            raise ConfigError("GROQ_API_KEY não definida. Copie .env.example para .env e preencha a chave.")
        return self.groq_api_key


def get_settings() -> Settings:
    try:
        temperature = float(os.environ.get("LLM_TEMPERATURE", "0"))
        http_timeout = float(os.environ.get("HTTP_TIMEOUT", "30"))
    except ValueError as exc:
        raise ConfigError(f"LLM_TEMPERATURE/HTTP_TIMEOUT devem ser numéricos: {exc}") from exc
    return Settings(
        groq_api_key=os.environ.get("GROQ_API_KEY", ""),
        model_name=os.environ.get("MODEL_NAME", "openai/gpt-oss-20b"),
        base_url=os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        temperature=temperature,
        http_timeout=http_timeout,
    )
