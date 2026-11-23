"""Agente ReAct (Groq) com memória por thread, usando as ferramentas determinísticas."""

import re
from dataclasses import dataclass, field
from typing import Any

import openai
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from src.agent_config import ExternalServiceError, LimiteExcedido, Settings, get_settings
from src.agent_tools import get_tools

SYSTEM_PROMPT = """Você é um analista de saneamento e ESG que apoia gestores públicos e responde em português do Brasil.
Regras:
- Nunca invente indicadores, posições, scores ou variações: use sempre as ferramentas. Não calcule números você mesmo.
- As ferramentas usam siglas de UF com 2 letras: converta nomes de estados (ex.: Maranhão = MA) antes de chamá-las.
- Cite sempre o ano e a fonte dos dados (SNIS, cobertura urbana por UF).
- O último ano válido da base é 2021. Se o usuário pedir um ano sem dados (ex.: 2023), diga isso, use 2021 e informe que é o último disponível.
- Em perguntas de acompanhamento, reutilize do histórico a UF, o ano e a região que o usuário omitiu.
- Verifique a premissa da pergunta com as ferramentas antes de responder (ex.: se a UF já está fora do top 5) e corrija premissas falsas logo no início.
- Toda resposta sobre indicadores deve seguir a estrutura: Diagnóstico, Evidência (números, posições e scores retornados pelas ferramentas, com ano e fonte), Recomendação e Limitações.
- Nunca proponha metas numéricas, valores ou conclusões causais (ex.: "os investimentos não geram resultado") que não venham das ferramentas; use apenas o ritmo exigido e o histórico que elas retornam.
- Posição 1 é a de maior prioridade: subir no ranking significa piorar a situação da UF, e cair de posição significa melhorar.
- Se o usuário não citar UF e não houver UF no histórico, não assuma nenhuma e não peça a UF antes de agir: responda no nível nacional com as ferramentas (ex.: resumo_regional ou ranking_prioridade) e, se o ano pedido não existir, diga isso logo no início.
- Déficit é 100 menos a cobertura. Ganhos de cobertura REDUZEM o déficit e o score. Em cenários, descreva o efeito em termos de cobertura e compare a posição antes e depois; se a UF já estava fora do top 5, diga isso no Diagnóstico.
- Descreva a evolução pelo sinal real das variações: se uma variação for negativa, diga que o indicador piorou.
- O score de prioridade é 0,4 x déficit de água + 0,6 x déficit de esgoto; maior score significa maior prioridade.
- A meta de referência é a universalização de 2033 do Marco Legal do Saneamento (99% água e 90% esgoto), alinhada à ODS 6.1 e 6.2.
- Se uma ferramenta devolver "ERRO:", explique o problema ao usuário sem inventar valores.
- Para perguntas conceituais, responda diretamente, sem ferramentas.
- Responda em texto simples, sem LaTeX nem fórmulas.
- Lembre que suas respostas apoiam a decisão, mas não substituem um estudo técnico."""


@dataclass
class Passo:
    ferramenta: str
    entrada: dict
    saida: str = ""


@dataclass
class RespostaAgente:
    texto: str
    passos: list[Passo] = field(default_factory=list)


def build_llm(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.model_name,
        temperature=settings.temperature,
        api_key=settings.require_api_key(),
        base_url=settings.base_url,
        timeout=settings.http_timeout,
        max_retries=2,
    )


def build_agent(llm: Any = None, tools: list | None = None, checkpointer: Any = None):
    """Monta o agente; os parâmetros permitem injetar fakes nos testes."""
    return create_agent(
        model=llm if llm is not None else build_llm(get_settings()),
        tools=tools if tools is not None else get_tools(),
        checkpointer=checkpointer if checkpointer is not None else InMemorySaver(),
        system_prompt=SYSTEM_PROMPT,
    )


def _extrair_passos(messages: list[Any]) -> list[Passo]:
    """Rastro ReAct apenas do turno atual, pareando chamada e resultado por tool_call_id."""
    ultimo = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=-1)
    passos: dict[str, Passo] = {}
    for m in messages[ultimo + 1:]:
        if isinstance(m, AIMessage):
            for tc in m.tool_calls:
                passos[tc["id"]] = Passo(ferramenta=tc["name"], entrada=tc["args"])
        elif isinstance(m, ToolMessage) and m.tool_call_id in passos:
            passos[m.tool_call_id].saida = str(m.content)
    return list(passos.values())


LIMITES = {
    "TPD": "diário de tokens",
    "TPM": "de tokens por minuto",
    "RPD": "diário de requisições",
    "RPM": "de requisições por minuto",
}


def _mensagem_limite(exc: openai.RateLimitError) -> str:
    """Traduz o corpo do 429 do provedor em tipo de limite e tempo de espera."""
    corpo = exc.body if isinstance(exc.body, dict) else {}
    detalhe = str(corpo.get("message", ""))
    tipo = re.search(r"\((TPD|TPM|RPD|RPM)\)", detalhe)
    espera = re.search(r"try again in (\d[\w.]*\w)", detalhe)
    texto = f"Limite {LIMITES[tipo.group(1)]} do provedor atingido" if tipo else "Limite de requisições do provedor atingido"
    if espera:
        return f"{texto}. Tente novamente em {espera.group(1)}."
    return f"{texto}. Tente novamente em instantes."


TENTATIVAS_GERACAO = 3


def _falha_de_geracao(exc: openai.APIStatusError) -> bool:
    """O provedor devolve 400 quando o modelo gera uma chamada de ferramenta malformada (falha transitória)."""
    return exc.status_code == 400 and "Parsing failed" in str(exc)


def _invocar(agent, mensagem: str, config: dict):
    for tentativa in range(1, TENTATIVAS_GERACAO + 1):
        try:
            return agent.invoke({"messages": [{"role": "user", "content": mensagem}]}, config=config)
        except openai.BadRequestError as exc:
            if not _falha_de_geracao(exc) or tentativa == TENTATIVAS_GERACAO:
                raise


def perguntar(agent, mensagem: str, thread_id: str) -> RespostaAgente:
    """O thread_id seleciona o histórico (memória) da conversa."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        resultado = _invocar(agent, mensagem, config)
    except openai.AuthenticationError as exc:
        raise ExternalServiceError("Chave da API inválida (GROQ_API_KEY).") from exc
    except openai.RateLimitError as exc:
        raise LimiteExcedido(_mensagem_limite(exc)) from exc
    except openai.APIConnectionError as exc:
        raise ExternalServiceError("Não foi possível conectar ao provedor do LLM.") from exc
    except openai.APIError as exc:
        raise ExternalServiceError(f"Erro do provedor do LLM: {exc}") from exc
    msgs = resultado["messages"]
    texto = msgs[-1].text.strip()
    if not texto:
        raise ExternalServiceError("O modelo retornou uma resposta vazia. Reenvie a pergunta.")
    return RespostaAgente(texto=texto, passos=_extrair_passos(msgs))
