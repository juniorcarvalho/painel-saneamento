"""Ferramentas determinísticas do agente sobre os indicadores SNIS.

O LLM apenas escolhe as ferramentas e redige o texto: todos os números vêm daqui.
Cada ferramenta devolve JSON compacto ou "ERRO: ...".
"""

import json
import logging
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.api_data_access import montar_registros
from src.data_processing import REGIAO_POR_UF, calcular_prioridade

logger = logging.getLogger(__name__)

META_ANO = 2033
META_AGUA = 99.0
META_ESGOTO = 90.0
REGIOES = ("Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste")


class ErroFerramenta(ValueError):
    """Entrada válida para o schema, mas sem dados correspondentes."""


def _oficiais() -> list[dict]:
    _, registros = montar_registros()
    return [item for item in registros if item.get("Origem") == "oficial"]


def _json(dados) -> str:
    return json.dumps(dados, ensure_ascii=False, separators=(",", ":"))


def _ano_padrao(registros: list[dict], ano: int | None) -> int:
    if ano is not None:
        return ano
    if not registros:
        raise ErroFerramenta("Sem dados oficiais disponíveis.")
    return max(item["Ano"] for item in registros)


def _do_ano(registros: list[dict], ano: int) -> list[dict]:
    """Registros do ano ordenados por prioridade, com a posição nacional."""
    lista = [dict(item) for item in registros if item["Ano"] == ano]
    if not lista:
        raise ErroFerramenta(f"Sem dados oficiais para {ano}. Último ano válido: {max(i['Ano'] for i in registros)}.")
    lista = calcular_prioridade(lista)
    for posicao, item in enumerate(lista, 1):
        item["Posicao_Nacional"] = posicao
    return lista


def _sigla(valor: str) -> str:
    sigla = valor.strip().upper()
    if sigla not in REGIAO_POR_UF:
        raise ErroFerramenta(f"Sigla de UF inválida: {valor!r}.")
    return sigla


def _regiao(valor: str | None) -> str | None:
    """Valida a região, normalizando a capitalização (nordeste -> Nordeste)."""
    if valor is None:
        return None
    for regiao in REGIOES:
        if regiao.lower() == valor.strip().lower():
            return regiao
    raise ErroFerramenta(f"Região inválida: {valor!r}. Use {', '.join(REGIOES)}.")


def _uf(lista: list[dict], sigla: str, ano: int) -> dict:
    for item in lista:
        if item["Sigla"] == sigla:
            return item
    raise ErroFerramenta(f"Sem dados oficiais de {sigla} em {ano}.")


def _registro(item: dict) -> dict:
    return {
        "sigla": item["Sigla"], "regiao": item["Regiao"], "ano": item["Ano"],
        "agua": item["Atendimento_Agua"], "esgoto": item["Atendimento_Esgoto"],
        "score": item["Score_Prioridade"], "pop_sem_saneamento_milhoes": item["Pop_Sem_Saneamento_Milhoes"],
        "posicao_nacional": item.get("Posicao_Nacional"),
    }


def _serie(registros: list[dict], sigla: str) -> list[dict]:
    serie = sorted((i for i in registros if i["Sigla"] == sigla), key=lambda i: i["Ano"])
    if not serie:
        raise ErroFerramenta(f"Sem dados oficiais de {sigla}.")
    return serie


# --- funções puras ---------------------------------------------------------

def ranking_prioridade(registros, ano=None, regiao=None, limite=5) -> dict:
    ano = _ano_padrao(registros, ano)
    lista = _do_ano(registros, ano)
    if regiao is not None:
        lista = [i for i in lista if i["Regiao"] == regiao]
    return {"ano": ano, "regiao": regiao, "ranking": [_registro(i) for i in lista[:limite]]}


def indicadores_uf(registros, sigla, ano=None) -> dict:
    sigla = _sigla(sigla)
    ano = _ano_padrao(registros, ano)
    lista = _do_ano(registros, ano)
    item = _uf(lista, sigla, ano)
    regional = [i for i in lista if i["Regiao"] == item["Regiao"]]
    registro = _registro(item)
    registro["posicao_regional"] = next(p for p, i in enumerate(regional, 1) if i["Sigla"] == sigla)
    registro["ufs_na_regiao"] = len(regional)
    registro["ufs_no_ano"] = len(lista)
    return registro


def evolucao_uf(registros, sigla, ano_inicio=None, ano_fim=None) -> dict:
    sigla = _sigla(sigla)
    serie = _serie(registros, sigla)
    serie = [i for i in serie if (ano_inicio is None or i["Ano"] >= ano_inicio) and (ano_fim is None or i["Ano"] <= ano_fim)]
    if len(serie) < 2:
        raise ErroFerramenta(f"Menos de dois anos de dados de {sigla} no período pedido.")
    primeiro, ultimo = serie[0], serie[-1]
    return {
        "sigla": sigla, "uf": primeiro["UF"], "ano_inicio": primeiro["Ano"], "ano_fim": ultimo["Ano"],
        "serie": [{"ano": i["Ano"], "agua": i["Atendimento_Agua"], "esgoto": i["Atendimento_Esgoto"], "score": i["Score_Prioridade"]} for i in serie],
        "variacao_agua_pp": round(ultimo["Atendimento_Agua"] - primeiro["Atendimento_Agua"], 2),
        "variacao_esgoto_pp": round(ultimo["Atendimento_Esgoto"] - primeiro["Atendimento_Esgoto"], 2),
        "variacao_score_pp": round(ultimo["Score_Prioridade"] - primeiro["Score_Prioridade"], 2),
    }


def comparar_ufs(registros, siglas, ano=None) -> dict:
    siglas = list(dict.fromkeys(_sigla(s) for s in siglas))
    if not 2 <= len(siglas) <= 5:
        raise ErroFerramenta("Informe de 2 a 5 UFs distintas.")
    ano = _ano_padrao(registros, ano)
    lista = _do_ano(registros, ano)
    media_agua = sum(i["Atendimento_Agua"] for i in lista) / len(lista)
    media_esgoto = sum(i["Atendimento_Esgoto"] for i in lista) / len(lista)
    comparadas = []
    for sigla in siglas:
        registro = _registro(_uf(lista, sigla, ano))
        registro["dif_agua_media_nacional_pp"] = round(registro["agua"] - media_agua, 2)
        registro["dif_esgoto_media_nacional_pp"] = round(registro["esgoto"] - media_esgoto, 2)
        comparadas.append(registro)
    return {"ano": ano, "media_nacional_agua": round(media_agua, 2), "media_nacional_esgoto": round(media_esgoto, 2), "ufs": comparadas}


def resumo_regional(registros, ano=None) -> dict:
    ano = _ano_padrao(registros, ano)
    lista = _do_ano(registros, ano)
    regioes = []
    for regiao in REGIOES:
        grupo = [i for i in lista if i["Regiao"] == regiao]
        if not grupo:
            continue
        n = len(grupo)
        regioes.append({
            "regiao": regiao, "ufs": n,
            "agua": round(sum(i["Atendimento_Agua"] for i in grupo) / n, 2),
            "esgoto": round(sum(i["Atendimento_Esgoto"] for i in grupo) / n, 2),
            "score": round(sum(i["Score_Prioridade"] for i in grupo) / n, 2),
            "pop_sem_saneamento_milhoes": round(sum(i["Pop_Sem_Saneamento_Milhoes"] for i in grupo), 4),
        })
    return {"ano": ano, "criterio": "médias simples entre UFs; população somada", "regioes": regioes}


def _ritmo_historico(serie: list[dict], campo: str, janela: int = 5) -> float | None:
    recorte = serie[-(janela + 1):]
    if len(recorte) < 2:
        return None
    return round((recorte[-1][campo] - recorte[0][campo]) / (recorte[-1]["Ano"] - recorte[0]["Ano"]), 2)


def _meta_uf(registros, item: dict, ano: int) -> dict:
    anos = META_ANO - ano
    lacuna_agua = round(max(0.0, META_AGUA - item["Atendimento_Agua"]), 2)
    lacuna_esgoto = round(max(0.0, META_ESGOTO - item["Atendimento_Esgoto"]), 2)
    serie = [i for i in _serie(registros, item["Sigla"]) if i["Ano"] <= ano]
    resultado = {"sigla": item["Sigla"], "uf": item["UF"], "regiao": item["Regiao"], "ano": ano,
                 "agua": item["Atendimento_Agua"], "esgoto": item["Atendimento_Esgoto"],
                 "lacuna_agua_pp": lacuna_agua, "lacuna_esgoto_pp": lacuna_esgoto, "anos_restantes": anos}
    for nome, lacuna, campo in (("agua", lacuna_agua, "Atendimento_Agua"), ("esgoto", lacuna_esgoto, "Atendimento_Esgoto")):
        exigido = round(lacuna / anos, 2) if anos > 0 else (0.0 if lacuna == 0 else None)
        historico = _ritmo_historico(serie, campo)
        resultado[f"ritmo_exigido_{nome}_pp_ano"] = exigido
        resultado[f"ritmo_historico_{nome}_pp_ano"] = historico
        resultado[f"no_ritmo_{nome}"] = lacuna == 0 or (exigido is not None and historico is not None and historico >= exigido)
    return resultado


def distancia_meta(registros, sigla=None, regiao=None, ano=None) -> dict:
    ano = _ano_padrao(registros, ano)
    lista = _do_ano(registros, ano)
    if sigla:
        alvos = [_uf(lista, _sigla(sigla), ano)]
    elif regiao:
        alvos = [i for i in lista if i["Regiao"] == regiao]
    else:
        raise ErroFerramenta("Informe sigla ou regiao.")
    return {
        "meta": {"ano": META_ANO, "agua": META_AGUA, "esgoto": META_ESGOTO, "base": "Marco Legal do Saneamento (Lei 14.026/2020); ODS 6.1/6.2"},
        "ufs": [_meta_uf(registros, i, ano) for i in alvos],
    }


def simular_cenario(registros, sigla, delta_agua_pp=0.0, delta_esgoto_pp=0.0, ano=None) -> dict:
    sigla = _sigla(sigla)
    ano = _ano_padrao(registros, ano)
    antes_lista = _do_ano(registros, ano)
    antes = _uf(antes_lista, sigla, ano)
    copia = [dict(i) for i in registros if i["Ano"] == ano]
    for item in copia:
        if item["Sigla"] == sigla:
            item["Atendimento_Agua"] = min(100.0, item["Atendimento_Agua"] + delta_agua_pp)
            item["Atendimento_Esgoto"] = min(100.0, item["Atendimento_Esgoto"] + delta_esgoto_pp)
    depois_lista = calcular_prioridade(copia)
    posicao_depois = next(p for p, i in enumerate(depois_lista, 1) if i["Sigla"] == sigla)
    depois = next(i for i in depois_lista if i["Sigla"] == sigla)
    return {
        "ano": ano, "sigla": sigla, "uf": antes["UF"],
        "delta_agua_pp": delta_agua_pp, "delta_esgoto_pp": delta_esgoto_pp,
        "antes": {"agua": antes["Atendimento_Agua"], "esgoto": antes["Atendimento_Esgoto"], "score": antes["Score_Prioridade"], "posicao": antes["Posicao_Nacional"]},
        "depois": {"agua": depois["Atendimento_Agua"], "esgoto": depois["Atendimento_Esgoto"], "score": depois["Score_Prioridade"], "posicao": posicao_depois},
        "observacao": "Cenário hipotético; ganhos limitados a 100%. A população sem saneamento não é recalculada.",
    }


# --- BaseTool --------------------------------------------------------------

class _Base(BaseTool):
    def _executar(self, **kwargs) -> dict:
        raise NotImplementedError

    def _run(self, **kwargs) -> str:
        try:
            return _json(self._executar(**kwargs))
        except ErroFerramenta as exc:
            return f"ERRO: {exc}"
        except FileNotFoundError:
            return "ERRO: cache oficial de dados ausente."
        except (OSError, ValueError) as exc:
            return f"ERRO: falha ao ler os dados ({exc})."
        except Exception:
            logger.exception("Falha inesperada na ferramenta %s", self.name)
            return "ERRO: falha interna na ferramenta."


Sigla = Field(description="Sigla da UF com 2 letras, por exemplo MA")
AnoOpc = Field(default=None, ge=1995, le=2100, description="Ano de referência; omita para usar o último ano válido (2021)")


class RankingInput(BaseModel):
    ano: int | None = AnoOpc
    regiao: str | None = Field(default=None, description="Norte, Nordeste, Sudeste, Sul ou Centro-Oeste")
    limite: int = Field(default=5, ge=1, le=27, description="Quantidade de UFs (1 a 27)")


class RankingTool(_Base):
    name: str = "ranking_prioridade"
    description: str = "Ranking de prioridade de investimento em saneamento (score 40% água + 60% esgoto), opcionalmente por região. Maior score = maior prioridade."
    args_schema: Type[BaseModel] = RankingInput

    def _executar(self, ano=None, regiao=None, limite=5):
        return ranking_prioridade(_oficiais(), ano, _regiao(regiao), limite)


class IndicadoresInput(BaseModel):
    sigla: str = Sigla
    ano: int | None = AnoOpc


class IndicadoresTool(_Base):
    name: str = "indicadores_uf"
    description: str = "Indicadores de uma UF em um ano, com posição no ranking nacional e regional."
    args_schema: Type[BaseModel] = IndicadoresInput

    def _executar(self, sigla, ano=None):
        return indicadores_uf(_oficiais(), sigla, ano)


class EvolucaoInput(BaseModel):
    sigla: str = Sigla
    ano_inicio: int | None = Field(default=None, ge=1995, le=2100)
    ano_fim: int | None = Field(default=None, ge=1995, le=2100)


class EvolucaoTool(_Base):
    name: str = "evolucao_uf"
    description: str = "Série anual de água, esgoto e score de uma UF e a variação em pontos percentuais no período."
    args_schema: Type[BaseModel] = EvolucaoInput

    def _executar(self, sigla, ano_inicio=None, ano_fim=None):
        return evolucao_uf(_oficiais(), sigla, ano_inicio, ano_fim)


class CompararInput(BaseModel):
    siglas: list[str] = Field(min_length=2, max_length=5, description="2 a 5 siglas de UF")
    ano: int | None = AnoOpc


class CompararTool(_Base):
    name: str = "comparar_ufs"
    description: str = "Compara de 2 a 5 UFs lado a lado e a diferença para a média nacional."
    args_schema: Type[BaseModel] = CompararInput

    def _executar(self, siglas, ano=None):
        return comparar_ufs(_oficiais(), siglas, ano)


class ResumoRegionalInput(BaseModel):
    ano: int | None = AnoOpc


class ResumoRegionalTool(_Base):
    name: str = "resumo_regional"
    description: str = "Médias de água, esgoto e score e população sem saneamento somada por região."
    args_schema: Type[BaseModel] = ResumoRegionalInput

    def _executar(self, ano=None):
        return resumo_regional(_oficiais(), ano)


class DistanciaInput(BaseModel):
    sigla: str | None = Field(default=None, description="Sigla da UF")
    regiao: str | None = Field(default=None, description="Região, se não houver UF")
    ano: int | None = AnoOpc


class DistanciaMetaTool(_Base):
    name: str = "distancia_meta"
    description: str = "Lacuna até a meta de universalização de 2033 (99% água, 90% esgoto; Lei 14.026/2020) e ritmo anual necessário versus ritmo histórico dos últimos 5 anos."
    args_schema: Type[BaseModel] = DistanciaInput

    def _executar(self, sigla=None, regiao=None, ano=None):
        return distancia_meta(_oficiais(), sigla, _regiao(regiao), ano)


class SimularInput(BaseModel):
    sigla: str = Sigla
    delta_agua_pp: float = Field(default=0.0, ge=0, le=100, description="Ganho hipotético de água em pontos percentuais")
    delta_esgoto_pp: float = Field(default=0.0, ge=0, le=100, description="Ganho hipotético de esgoto em pontos percentuais")
    ano: int | None = AnoOpc


class SimularCenarioTool(_Base):
    name: str = "simular_cenario"
    description: str = "Recalcula score e posição de uma UF após um ganho hipotético de cobertura (teto de 100%)."
    args_schema: Type[BaseModel] = SimularInput

    def _executar(self, sigla, delta_agua_pp=0.0, delta_esgoto_pp=0.0, ano=None):
        return simular_cenario(_oficiais(), sigla, delta_agua_pp, delta_esgoto_pp, ano)


def get_tools() -> list[BaseTool]:
    return [RankingTool(), IndicadoresTool(), EvolucaoTool(), CompararTool(), ResumoRegionalTool(), DistanciaMetaTool(), SimularCenarioTool()]
