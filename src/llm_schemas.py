"""Contratos de resumo e proveniência declarada."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FonteTexto(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    titulo: str = Field(strict=True, min_length=1, max_length=200)
    origem: str = Field(strict=True, min_length=1, max_length=500)


class TextoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    texto: str = Field(strict=True, min_length=50, max_length=8000)
    tipo_analise: Literal["resumo"] = "resumo"
    fonte: FonteTexto

    @field_validator("texto", mode="before")
    @classmethod
    def normalizar(cls, value):
        if isinstance(value, str):
            return value.replace("\r\n", "\n").replace("\r", "\n").strip()
        return value


class TextoResposta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    texto_processado: str
    tipo_analise: Literal["resumo"] = "resumo"
    resultado: str = Field(min_length=1, max_length=4000)
    modelo: str = Field(min_length=1)
    revisao: str = Field(min_length=1)
    fonte: FonteTexto
    tempo_processamento_ms: int = Field(strict=True, ge=0)
