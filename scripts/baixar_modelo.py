"""Preparação explícita; nunca importada pelo startup da API."""
import json
import os
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.llm_config import MODELO, REVISAO, PADRAO_PATH

def main():
    destino = Path(os.getenv('SANEAMENTO_LLM_PATH', str(PADRAO_PATH)))
    try:
        snapshot_download(MODELO, revision=REVISAO, local_dir=destino, allow_patterns=['*.json', '*.safetensors', '*.txt', '*.jinja', 'LICENSE*', 'README.md'])
        (destino / 'manifesto.json').write_text(json.dumps({'modelo': MODELO, 'revisao': REVISAO, 'licenca': 'Apache-2.0'}, indent=2))
    except Exception as exc:
        raise SystemExit(f'Falha no download: {exc}. Verifique rede, permissões e espaço em disco.') from exc
    print(destino)

if __name__ == '__main__':
    main()
