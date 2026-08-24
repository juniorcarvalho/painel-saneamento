"""Normalização e priorização determinística dos dados de saneamento."""

from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = {
    "UF",
    "Sigla",
    "Regiao",
    "Atendimento_Agua",
    "Atendimento_Esgoto",
    "Pop_Sem_Saneamento_Milhoes",
}

URBAN_CSV_FIELDS = (
    "ano",
    "sigla_uf",
    "populacao_urbana_residente_agua",
    "populacao_urbana_atendida_agua",
    "populacao_urbana_residente_esgoto",
    "populacao_urbana_atendida_esgoto",
)

REGIAO_POR_UF = {
    **dict.fromkeys(("AC", "AP", "AM", "PA", "RO", "RR", "TO"), "Norte"),
    **dict.fromkeys(("AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"), "Nordeste"),
    **dict.fromkeys(("ES", "MG", "RJ", "SP"), "Sudeste"),
    **dict.fromkeys(("PR", "RS", "SC"), "Sul"),
    **dict.fromkeys(("DF", "GO", "MS", "MT"), "Centro-Oeste"),
}


def _to_float(value: Any) -> float:
    if isinstance(value, str):
        value = value.strip()
        if "," in value:
            value = value.replace(".", "").replace(",", ".")
    return float(value)


def _optional_float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return _to_float(value)
    except (TypeError, ValueError):
        return None


def consolidar_dados_urbanos(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Agrega o CSV municipal em indicadores urbanos por UF e ano.

    Os percentuais são ponderados pela população residente informada pelo
    SNIS, e não calculados como média simples dos municípios.
    """

    grupos: dict[tuple[int, str], dict[str, float]] = {}
    for row in rows:
        if any(field not in row for field in URBAN_CSV_FIELDS):
            raise ValueError("CSV sem uma ou mais colunas urbanas obrigatórias.")
        try:
            ano = int(row["ano"])
        except (TypeError, ValueError):
            continue
        sigla = str(row["sigla_uf"]).strip().upper()
        if not sigla:
            continue
        key = (ano, sigla)
        grupo = grupos.setdefault(
            key,
            {
                "residente_agua": 0.0,
                "atendida_agua": 0.0,
                "residente_esgoto": 0.0,
                "atendida_esgoto": 0.0,
            },
        )
        for source, target in (
            ("populacao_urbana_residente_agua", "residente_agua"),
            ("populacao_urbana_atendida_agua", "atendida_agua"),
            ("populacao_urbana_residente_esgoto", "residente_esgoto"),
            ("populacao_urbana_atendida_esgoto", "atendida_esgoto"),
        ):
            value = _optional_float(row[source])
            if value is not None and value >= 0:
                grupo[target] += value

    registros = []
    for (ano, sigla), grupo in sorted(grupos.items()):
        if grupo["residente_agua"] <= 0 or grupo["residente_esgoto"] <= 0:
            continue
        agua = min(100.0, grupo["atendida_agua"] / grupo["residente_agua"] * 100)
        esgoto = min(100.0, grupo["atendida_esgoto"] / grupo["residente_esgoto"] * 100)
        atendida_completa = min(grupo["atendida_agua"], grupo["atendida_esgoto"])
        residente_completa = min(grupo["residente_agua"], grupo["residente_esgoto"])
        registros.append(
            {
                "Ano": ano,
                "UF": sigla,
                "Sigla": sigla,
                "Regiao": REGIAO_POR_UF.get(sigla, "Não informada"),
                "Atendimento_Agua": round(agua, 2),
                "Atendimento_Esgoto": round(esgoto, 2),
                "Pop_Sem_Saneamento_Milhoes": round(
                    max(residente_completa - atendida_completa, 0) / 1_000_000, 4
                ),
            }
        )
    return registros


def normalizar_registros(registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Converte valores numéricos e rejeita registros estruturalmente inválidos."""

    normalizados = []
    for registro in registros:
        missing = REQUIRED_FIELDS - registro.keys()
        if missing:
            raise ValueError(f"Campos ausentes para {registro.get('UF', '?')}: {sorted(missing)}")

        item = dict(registro)
        for field in ("Atendimento_Agua", "Atendimento_Esgoto", "Pop_Sem_Saneamento_Milhoes"):
            item[field] = _to_float(item[field])
        if not 0 <= item["Atendimento_Agua"] <= 100:
            raise ValueError(f"Atendimento de água inválido para {item['UF']}")
        if not 0 <= item["Atendimento_Esgoto"] <= 100:
            raise ValueError(f"Atendimento de esgoto inválido para {item['UF']}")
        if item["Pop_Sem_Saneamento_Milhoes"] < 0:
            raise ValueError(f"População inválida para {item['UF']}")
        normalizados.append(item)
    return normalizados


def consolidar_dados_api(
    dados_snis: list[dict[str, Any]], dados_ibge: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Consolida respostas tabulares do SNIS e IBGE por sigla da UF.

    O adaptador aceita os nomes oficiais ``IN055``/``IN056`` e aliases em
    minúsculas para facilitar o uso com exportações JSON distintas.
    """

    populacao_por_sigla = {}
    for item in dados_ibge:
        sigla = str(item.get("Sigla", item.get("sigla", ""))).upper()
        populacao = item.get("Populacao", item.get("populacao"))
        if sigla and populacao is not None:
            populacao_por_sigla[sigla] = _to_float(populacao)

    consolidados = []
    for item in dados_snis:
        sigla = str(item.get("Sigla", item.get("sigla", ""))).upper()
        agua = item.get("IN055", item.get("Atendimento_Agua"))
        esgoto = item.get("IN056", item.get("Atendimento_Esgoto"))
        if not sigla or agua is None or esgoto is None:
            raise ValueError("Registro SNIS sem sigla, IN055 ou IN056.")

        agua = _to_float(agua)
        esgoto = _to_float(esgoto)
        populacao = item.get("Populacao", item.get("populacao"))
        if populacao is None:
            populacao = populacao_por_sigla.get(sigla)
        if populacao is None:
            raise ValueError(f"População IBGE ausente para {sigla}.")
        populacao = _to_float(populacao)
        nome = item.get("UF", item.get("uf", sigla))
        regiao = item.get("Regiao", item.get("regiao", "Não informada"))
        sem_saneamento = item.get("Pop_Sem_Saneamento_Milhoes")
        if sem_saneamento is None:
            sem_saneamento = populacao * (1 - min(agua, esgoto) / 100) / 1_000_000

        consolidados.append(
            {
                "UF": nome,
                "Sigla": sigla,
                "Regiao": regiao,
                "Atendimento_Agua": agua,
                "Atendimento_Esgoto": esgoto,
                "Pop_Sem_Saneamento_Milhoes": sem_saneamento,
            }
        )
    return normalizar_registros(consolidados)


def calcular_prioridade(registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Calcula prioridade: 40% déficit de água e 60% déficit de esgoto.

    A população sem atendimento permanece disponível como impacto absoluto e
    desempate, evitando misturar escalas sem uma regra de negócio documentada.
    """

    resultado = []
    for registro in normalizar_registros(registros):
        deficit_agua = 100 - registro["Atendimento_Agua"]
        deficit_esgoto = 100 - registro["Atendimento_Esgoto"]
        item = dict(registro)
        item["Deficit_Agua"] = round(deficit_agua, 2)
        item["Deficit_Esgoto"] = round(deficit_esgoto, 2)
        item["Score_Prioridade"] = round(0.4 * deficit_agua + 0.6 * deficit_esgoto, 2)
        resultado.append(item)
    return sorted(
        resultado,
        key=lambda item: (
            -item["Score_Prioridade"],
            -item["Pop_Sem_Saneamento_Milhoes"],
            item["UF"],
        ),
    )
