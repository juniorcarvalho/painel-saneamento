"""Coleta e persistência dos dados usados pelo painel.

O dashboard não faz chamadas externas. Este módulo é executado separadamente
para atualizar o cache local em ``data/processed``.
"""

from __future__ import annotations

import json
import os
import csv
import urllib.request
from pathlib import Path
from typing import Any

try:
    from src.data_processing import consolidar_dados_api, consolidar_dados_urbanos
except ModuleNotFoundError:  
    from data_processing import consolidar_dados_api, consolidar_dados_urbanos


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "dados_saneamento.json"
MUNICIPAL_CSV_PATH = PROJECT_ROOT / "data" / "br_mdr_snis_municipio_agua_esgoto.csv"
IBGE_POPULATION_URL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/1461/periodos/2010/"
    "variaveis/93?localidades=N3[all]"
)


def _get_json(url: str, timeout: int = 15) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"API retornou HTTP {response.status}: {url}")
        return json.loads(response.read().decode("utf-8"))


def coletar_dados_ibge_populacao(url: str = IBGE_POPULATION_URL) -> Any:
    """Coleta população das UFs na API SIDRA do IBGE."""

    return _get_json(url)


def coletar_dados_snis(url: str | None = None) -> Any:
    """Coleta dados do SNIS a partir de uma URL configurada pelo ambiente.

    O endpoint do SNIS pode variar por publicação. Por isso, a URL é
    configurável por ``SNIS_API_URL`` em vez de ficar embutida no dashboard.
    """

    endpoint = url or os.getenv("SNIS_API_URL")
    if not endpoint:
        raise RuntimeError("Defina SNIS_API_URL para executar a coleta do SNIS.")
    return _get_json(endpoint)


def salvar_dados_processados(registros: list[dict[str, Any]], fontes: list[str]) -> Path:
    """Salva registros consolidados e metadados no cache local."""

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"fontes": fontes, "registros": registros}
    PROCESSED_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return PROCESSED_PATH


def ler_csv_municipal(path: Path = MUNICIPAL_CSV_PATH) -> list[dict[str, str]]:
    """Lê o arquivo municipal SNIS preservando os valores como texto."""

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def processar_csv_local(path: Path = MUNICIPAL_CSV_PATH) -> Path:
    """Consolida o CSV urbano municipal e atualiza o cache do dashboard."""

    registros = consolidar_dados_urbanos(ler_csv_municipal(path))
    if not registros:
        raise ValueError("O CSV não produziu registros urbanos consolidados.")
    return salvar_dados_processados(
        registros,
        ["SNIS municipal: br_mdr_snis_municipio_agua_esgoto.csv"],
    )


def carregar_dados_processados(path: Path = PROCESSED_PATH) -> dict[str, Any]:
    """Carrega e valida o formato mínimo do cache local."""

    if not path.exists():
        raise FileNotFoundError(f"Cache de dados não encontrado: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("registros"), list):
        raise ValueError("Cache inválido: esperada uma lista em 'registros'.")
    return payload


def processar_e_salvar_dados() -> Path:
    """Atualiza o cache a partir das APIs configuradas.

    A resposta de cada API deve ser uma lista de registros tabulares. O
    formato é consolidado por ``consolidar_dados_api`` antes da persistência.
    """

    dados_snis = coletar_dados_snis()
    dados_ibge = coletar_dados_ibge_populacao()
    if not isinstance(dados_snis, list) or not isinstance(dados_ibge, list):
        raise ValueError("As APIs devem retornar listas de registros tabulares.")
    registros = consolidar_dados_api(dados_snis, dados_ibge)
    return salvar_dados_processados(
        registros,
        ["SNIS", "IBGE SIDRA"],
    )


if __name__ == "__main__":
    if MUNICIPAL_CSV_PATH.exists():
        print(processar_csv_local())
    else:
        print(processar_e_salvar_dados())
