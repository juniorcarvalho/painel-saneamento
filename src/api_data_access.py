"""Persistência complementar isolada do cache oficial, para uma instância da API."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock

from src.data_access import PROJECT_ROOT, carregar_dados_processados
from src.data_processing import calcular_prioridade

COMPLEMENTARY_PATH = PROJECT_ROOT / "data" / "processed" / "dados_complementares.json"
_lock = Lock()


def carregar_dados_complementares(path: Path = COMPLEMENTARY_PATH) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    if not isinstance(payload, dict) or not isinstance(payload.get("registros"), list):
        raise ValueError("Arquivo complementar inválido: esperada lista em registros.")
    registros = calcular_prioridade(payload["registros"])
    for item in registros:
        if "Ano" not in item or not isinstance(item.get("Importado_Em"), str):
            raise ValueError("Registro complementar sem ano ou data de importação.")
        item["Origem"] = "complementar"
    return registros


def adicionar_dados_complementares(
    registros: list[dict], path: Path = COMPLEMENTARY_PATH
) -> list[dict]:
    if not registros or any("Ano" not in item for item in registros):
        raise ValueError("Envie registros com ano de referência.")
    novos = calcular_prioridade(registros)
    instante = datetime.now(timezone.utc).isoformat()
    for item in novos:
        item["Origem"] = "complementar"
        item["Importado_Em"] = instante
    with _lock:
        existentes = carregar_dados_complementares(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporario = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
                temporario = Path(file.name)
                json.dump({"registros": existentes + novos}, file, ensure_ascii=False, indent=2, allow_nan=False)
            os.replace(temporario, path)
        finally:
            if temporario is not None:
                temporario.unlink(missing_ok=True)
    return novos


def montar_registros(carregar_oficiais=None, carregar_complementares=None) -> tuple[list[str], list[dict]]:
    """Carrega o cache oficial e os lotes complementares, com Origem e prioridade.

    Os carregadores são injetáveis para que a API e os testes usem as próprias funções.
    """
    payload = (carregar_oficiais or carregar_dados_processados)()
    fontes = payload.get("fontes", [])
    if not isinstance(fontes, list) or any(not isinstance(fonte, str) for fonte in fontes):
        raise ValueError("Fontes inválidas no cache oficial.")
    oficiais = calcular_prioridade(payload["registros"])
    for item in oficiais:
        item["Origem"] = "oficial"
        item.pop("Importado_Em", None)
    complementares = (carregar_complementares or carregar_dados_complementares)()
    return fontes, calcular_prioridade(oficiais + complementares)
