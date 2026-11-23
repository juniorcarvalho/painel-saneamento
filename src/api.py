"""API local de consulta e importação de indicadores consolidados."""

import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import Body, FastAPI, HTTPException, Path, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.agent_config import ConfigError, ExternalServiceError, LimiteExcedido, get_settings
from src.agent_schemas import PassoSaida, PerguntaEntrada, RespostaAgenteSaida
from src.agent_service import build_agent, perguntar
from src.llm_schemas import TextoEntrada, TextoResposta
from src.llm_service import (
    EntradaLonga,
    Indisponivel,
    Ocupado,
    ServicoResumoLocal,
    TempoExcedido,
)
from src.api_data_access import adicionar_dados_complementares, carregar_dados_complementares, montar_registros
from src.data_access import carregar_dados_processados
from src.data_processing import normalizar_registros

logger = logging.getLogger(__name__)
Regiao = Literal["Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"]


class RegistroEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)

    Ano: int = Field(ge=1, le=9999, strict=True)
    UF: str = Field(min_length=1)
    Sigla: str = Field(min_length=2, max_length=2)
    Regiao: Regiao
    Atendimento_Agua: float = Field(ge=0, le=100, strict=True)
    Atendimento_Esgoto: float = Field(ge=0, le=100, strict=True)
    Pop_Sem_Saneamento_Milhoes: float = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def validar_registro(self):
        normalizado = normalizar_registros([self.model_dump()])[0]
        self.Sigla = normalizado["Sigla"]
        return self


class RegistroSaida(RegistroEntrada):
    Deficit_Agua: float
    Deficit_Esgoto: float
    Score_Prioridade: float
    Origem: Literal["oficial", "complementar"]
    Importado_Em: str | None = None


class DadosResposta(BaseModel):
    fontes: list[str]
    registros: list[RegistroSaida]


@asynccontextmanager
async def lifespan(app):
    app.state.llm = None
    app.state.agente = None
    app.state.modelo_agente = None
    try:
        app.state.agente = build_agent()
        app.state.modelo_agente = get_settings().model_name
    except ConfigError as exc:
        logger.warning("Agente desativado: %s", exc)
    except Exception:
        logger.exception("Agente indisponível no carregamento")
    try:
        servico = ServicoResumoLocal()
        servico.carregar()
        app.state.llm = servico
    except Exception:
        logger.exception("Modelo local indisponível no carregamento")
    try:
        yield
    finally:
        if app.state.llm is not None:
            app.state.llm.fechar()


app = FastAPI(lifespan=lifespan, title="Saneamento em Foco", version="4.0.0", description="Consulta de indicadores urbanos e importação complementar, com proveniência explícita.")


@app.exception_handler(RequestValidationError)
async def entrada_invalida(request, exc):
    # Não ecoar valores como NaN/Infinity, que não podem ser serializados em JSON.
    detalhes = [
        {campo: erro[campo] for campo in ("loc", "msg", "type")}
        for erro in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": detalhes})


@app.get("/dados", response_model=DadosResposta, responses={503: {"description": "Cache oficial ausente"}, 500: {"description": "Falha de leitura ou formato inválido"}})
def consultar_dados(
    ano: Annotated[int | None, Query(ge=1, le=9999)] = None,
    regiao: Regiao | None = None,
):
    """Consulta dados oficiais e complementares sem executar coleta externa."""
    try:
        fontes, registros = montar_registros(carregar_dados_processados, carregar_dados_complementares)
        resposta = DadosResposta(fontes=fontes, registros=registros)
    except FileNotFoundError as exc:
        raise HTTPException(503, "Cache oficial ausente. Execute a preparação dos dados.") from exc
    except (OSError, ValueError) as exc:
        logger.exception("Falha ao ler dados de saneamento")
        raise HTTPException(500, "Não foi possível ler os arquivos de dados; verifique formato e permissões.") from exc
    resposta.registros = [item for item in resposta.registros if (ano is None or item.Ano == ano) and (regiao is None or item.Regiao == regiao)]
    return resposta


@app.post("/dados", status_code=201, response_model=DadosResposta, responses={500: {"description": "Falha de leitura ou gravação complementar"}})
def importar_dados(registros: Annotated[list[RegistroEntrada], Body(min_length=1)]):
    """Acrescenta um lote complementar; repetições geram novos registros."""
    try:
        novos = adicionar_dados_complementares([item.model_dump() for item in registros])
    except (OSError, ValueError) as exc:
        logger.exception("Falha ao persistir dados complementares")
        raise HTTPException(500, "Não foi possível persistir o lote complementar; verifique formato e permissões.") from exc
    return {"fontes": ["Importação complementar via API"], "registros": novos}


@app.post(
    "/processar_texto",
    response_model=TextoResposta,
    responses={
        422: {"description": "Entrada inválida"},
        503: {"description": "Modelo indisponível ou ocupado"},
        504: {"description": "Prazo excedido"},
        500: {"description": "Falha interna"},
    },
)
def processar_texto(entrada: TextoEntrada):
    inicio = time.monotonic()
    try:
        servico = getattr(app.state, "llm", None)
        if servico is None:
            raise Indisponivel(
                "Modelo indisponível. Execute make download-model e reinicie a API."
            )
        resultado = servico.resumir(entrada.texto)
        return TextoResposta(
            texto_processado=entrada.texto,
            resultado=resultado,
            fonte=entrada.fonte,
            modelo=servico.modelo,
            revisao=servico.revisao,
            tempo_processamento_ms=int((time.monotonic() - inicio) * 1000),
        )
    except (Indisponivel, Ocupado) as exc:
        raise HTTPException(503, str(exc)) from exc
    except EntradaLonga as exc:
        raise HTTPException(422, str(exc)) from exc
    except TempoExcedido as exc:
        raise HTTPException(504, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Falha interna na inferência")
        raise HTTPException(500, "Falha interna ao gerar resumo.") from exc
    finally:
        logger.info("Processamento de resumo encerrado em %.3fs", time.monotonic() - inicio)


@app.post(
    "/agente",
    response_model=RespostaAgenteSaida,
    responses={
        422: {"description": "Entrada inválida"},
        429: {"description": "Limite de requisições do provedor"},
        502: {"description": "Falha do provedor de LLM"},
        503: {"description": "Agente não configurado"},
        500: {"description": "Falha interna"},
    },
)
def consultar_agente(entrada: PerguntaEntrada):
    inicio = time.monotonic()
    agente = getattr(app.state, "agente", None)
    if agente is None:
        raise HTTPException(503, "Configure GROQ_API_KEY no .env e reinicie a API.")
    try:
        resposta = perguntar(agente, entrada.mensagem, entrada.thread_id)
    except LimiteExcedido as exc:
        raise HTTPException(429, str(exc)) from exc
    except ExternalServiceError as exc:
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        logger.exception("Falha interna no agente")
        novo = uuid4().hex
        raise HTTPException(500, f"Falha interna no agente. Inicie uma nova conversa (thread_id sugerido: {novo}).") from exc
    return RespostaAgenteSaida(
        resposta=resposta.texto,
        passos=[PassoSaida(ferramenta=p.ferramenta, entrada=p.entrada, saida=p.saida) for p in resposta.passos],
        modelo=getattr(app.state, "modelo_agente", None) or get_settings().model_name,
        thread_id=entrada.thread_id,
        tempo_processamento_ms=int((time.monotonic() - inicio) * 1000),
    )


@app.delete("/agente/{thread_id}", status_code=204, responses={503: {"description": "Agente não configurado"}})
def limpar_agente(thread_id: Annotated[str, Path(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]):
    """Descarta a memória de uma conversa."""
    agente = getattr(app.state, "agente", None)
    if agente is None:
        raise HTTPException(503, "Configure GROQ_API_KEY no .env e reinicie a API.")
    agente.checkpointer.delete_thread(thread_id)
