.DEFAULT_GOAL := help

PYTHON ?= python3
VENV ?= .venv
ENV_PYTHON := $(VENV)/bin/python
DEPENDENCIES := $(VENV)/.requirements-installed
API_HOST ?= 127.0.0.1
API_PORT ?= 8000
WEB_HOST ?= 127.0.0.1
WEB_PORT ?= 8501

.PHONY: help setup dev up api web prepare-data data scrape

help:
	@echo "make dev    Prepara o ambiente e inicia API + Streamlit (Ctrl+C encerra ambos)"
	@echo "make setup  Cria o ambiente virtual e instala as dependências"
	@echo "make api    Prepara os dados e inicia somente a API com recarga automática"
	@echo "make web    Inicia somente o Streamlit; requer a API em execução"
	@echo "make data   Regenera o cache oficial a partir do CSV municipal local"
	@echo "make scrape Coleta a referência completa de municípios na Wikipédia"
	@echo "Configuração: make dev API_PORT=8001 WEB_PORT=8502"

$(ENV_PYTHON):
	$(PYTHON) -m venv "$(VENV)"

$(DEPENDENCIES): requirements.txt $(ENV_PYTHON)
	"$(ENV_PYTHON)" -m pip install --no-cache-dir -r requirements.txt
	@touch "$(DEPENDENCIES)"

setup: $(DEPENDENCIES)

prepare-data: setup
	@if [ ! -f data/processed/dados_saneamento.json ]; then \
		if [ ! -f data/br_mdr_snis_municipio_agua_esgoto.csv ]; then \
			echo "CSV municipal ausente. Salve-o em data/br_mdr_snis_municipio_agua_esgoto.csv (instruções no README)." >&2; \
			exit 1; \
		fi; \
		"$(ENV_PYTHON)" -c 'from src.data_access import processar_csv_local; print(processar_csv_local())'; \
	fi

dev: prepare-data
	@"$(ENV_PYTHON)" scripts/dev.py --api-host "$(API_HOST)" --api-port "$(API_PORT)" --web-host "$(WEB_HOST)" --web-port "$(WEB_PORT)"

up: dev

api: prepare-data
	"$(ENV_PYTHON)" -m uvicorn src.api:app --host "$(API_HOST)" --port "$(API_PORT)" --reload --reload-dir src

web: setup
	SANEAMENTO_API_URL="http://127.0.0.1:$(API_PORT)" "$(ENV_PYTHON)" -m streamlit run app.py --server.address "$(WEB_HOST)" --server.port "$(WEB_PORT)"

data: setup
	"$(ENV_PYTHON)" -c 'from src.data_access import processar_csv_local; print(processar_csv_local())'

scrape: setup
	SCRAPE_MUNICIPIOS=1 "$(ENV_PYTHON)" src/data_access.py

.PHONY: download-model test
download-model: setup
	"$(ENV_PYTHON)" scripts/baixar_modelo.py

test: setup
	"$(ENV_PYTHON)" -m pytest -q
