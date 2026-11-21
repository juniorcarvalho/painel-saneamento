"""Preparação explícita; nunca importada pelo startup da API."""
import argparse
import json
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.llm_config import CATALOGO_MODELOS, MODELO, resolver_modelo

def baixar(modelo=None):
    identificador, revisao, destino = resolver_modelo(modelo)
    try:
        snapshot_download(identificador, revision=revisao, local_dir=destino, allow_patterns=['*.json', '*.safetensors', '*.txt', '*.jinja', 'LICENSE*', 'README.md'])
        (destino / 'manifesto.json').write_text(json.dumps({'modelo': identificador, 'revisao': revisao, 'licenca': 'Apache-2.0'}, indent=2))
    except Exception as exc:
        raise SystemExit(f'Falha no download de {identificador}: {exc}. Verifique rede, permissões e espaço em disco.') from exc
    print(destino)

def main():
    parser = argparse.ArgumentParser(description='Baixa pesos locais fixados por revisão.')
    parser.add_argument('--modelo', choices=list(CATALOGO_MODELOS), default=None)
    parser.add_argument('--todos', action='store_true', help='Baixa todos os candidatos do catálogo.')
    args = parser.parse_args()
    if args.todos:
        for item in CATALOGO_MODELOS:
            baixar(item)
    else:
        baixar(args.modelo or MODELO)

if __name__ == '__main__':
    main()
