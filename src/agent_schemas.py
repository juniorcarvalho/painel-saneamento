"""Contratos da rota do agente."""

from pydantic import BaseModel, ConfigDict, Field


class PerguntaEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mensagem: str = Field(min_length=2, max_length=2000)
    thread_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class PassoSaida(BaseModel):
    ferramenta: str
    entrada: dict
    saida: str


class RespostaAgenteSaida(BaseModel):
    resposta: str
    passos: list[PassoSaida]
    modelo: str
    thread_id: str
    tempo_processamento_ms: int = Field(ge=0)
