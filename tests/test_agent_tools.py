import json

import pytest

from src import agent_tools as t
from src.data_processing import calcular_prioridade


def reg(sigla, regiao, ano, agua, esgoto, pop=1.0, origem="oficial"):
    return {"Ano": ano, "UF": sigla, "Sigla": sigla, "Regiao": regiao, "Atendimento_Agua": agua,
            "Atendimento_Esgoto": esgoto, "Pop_Sem_Saneamento_Milhoes": pop, "Origem": origem}


BASE = [
    *[reg("MA", "Nordeste", a, 70 + (a - 2015) * 2, 20 + (a - 2015) * 2) for a in range(2015, 2022)],
    *[reg("PI", "Nordeste", a, 80, 30) for a in range(2015, 2022)],
    *[reg("SP", "Sudeste", a, 98, 90) for a in range(2015, 2022)],
    *[reg("AC", "Norte", a, 50, 10) for a in range(2015, 2022)],
    reg("AC", "Norte", 2021, 50, 10, origem="complementar"),
]


@pytest.fixture(autouse=True)
def dados(monkeypatch):
    monkeypatch.setattr(t, "montar_registros", lambda: ([], calcular_prioridade(BASE)))


def run(tool, **kw):
    return tool._run(**kw)


def test_ranking_ordem_limite_e_padrao():
    r = json.loads(run(t.RankingTool(), limite=2))
    assert r["ano"] == 2021
    assert [i["sigla"] for i in r["ranking"]] == ["AC", "PI"]
    assert [i["posicao_nacional"] for i in r["ranking"]] == [1, 2]


def test_ranking_ignora_complementares_e_filtra_regiao():
    r = json.loads(run(t.RankingTool(), regiao="Nordeste", limite=5))
    assert [i["sigla"] for i in r["ranking"]] == ["PI", "MA"]
    assert [i["posicao_nacional"] for i in r["ranking"]] == [2, 3]
    assert len(json.loads(run(t.RankingTool(), limite=27))["ranking"]) == 4


def test_erros():
    assert run(t.IndicadoresTool(), sigla="XX").startswith("ERRO:")
    assert run(t.IndicadoresTool(), sigla="SP", ano=1999).startswith("ERRO:")
    assert "2021" in run(t.RankingTool(), ano=2023)
    assert run(t.RankingTool(), regiao="Marte").startswith("ERRO:")
    assert run(t.DistanciaMetaTool()).startswith("ERRO:")
    assert run(t.CompararTool(), siglas=["MA", "MA"]).startswith("ERRO:")


def test_indicadores_posicoes():
    r = json.loads(run(t.IndicadoresTool(), sigla="pi"))
    assert r["posicao_nacional"] == 2 and r["posicao_regional"] == 1 and r["ufs_na_regiao"] == 2


def test_evolucao_variacao_pp():
    r = json.loads(run(t.EvolucaoTool(), sigla="MA", ano_inicio=2015))
    assert r["variacao_agua_pp"] == 12 and r["variacao_esgoto_pp"] == 12
    assert len(r["serie"]) == 7
    assert run(t.EvolucaoTool(), sigla="MA", ano_inicio=2021).startswith("ERRO:")


def test_comparar_media_nacional():
    r = json.loads(run(t.CompararTool(), siglas=["MA", "SP"]))
    media = (82 + 80 + 98 + 50) / 4
    assert r["media_nacional_agua"] == round(media, 2)
    assert r["ufs"][0]["dif_agua_media_nacional_pp"] == round(82 - media, 2)


def test_resumo_regional():
    r = json.loads(run(t.ResumoRegionalTool()))
    ne = next(i for i in r["regioes"] if i["regiao"] == "Nordeste")
    assert ne["ufs"] == 2 and ne["agua"] == 81 and ne["pop_sem_saneamento_milhoes"] == 2


def test_distancia_meta():
    r = json.loads(run(t.DistanciaMetaTool(), sigla="MA"))
    uf = r["ufs"][0]
    assert uf["lacuna_agua_pp"] == 17 and uf["lacuna_esgoto_pp"] == 58
    assert uf["anos_restantes"] == 12
    assert uf["ritmo_exigido_agua_pp_ano"] == round(17 / 12, 2)
    assert uf["ritmo_historico_agua_pp_ano"] == 2.0
    assert uf["no_ritmo_agua"] is True      # 2,0 >= 1,42
    assert uf["no_ritmo_esgoto"] is False   # 2,0 < 4,83
    sp = json.loads(run(t.DistanciaMetaTool(), sigla="SP"))["ufs"][0]
    assert sp["lacuna_esgoto_pp"] == 0 and sp["no_ritmo_esgoto"] is True
    assert len(json.loads(run(t.DistanciaMetaTool(), regiao="Nordeste"))["ufs"]) == 2


def test_simular_cenario_teto_e_posicao():
    r = json.loads(run(t.SimularCenarioTool(), sigla="MA", delta_esgoto_pp=20))
    assert r["antes"]["posicao"] == 3 and r["depois"]["posicao"] == 3
    assert r["depois"]["esgoto"] == 52 and r["depois"]["score"] < r["antes"]["score"]
    r = json.loads(run(t.SimularCenarioTool(), sigla="MA", delta_agua_pp=18, delta_esgoto_pp=68))
    assert r["depois"]["posicao"] == 4
    r = json.loads(run(t.SimularCenarioTool(), sigla="SP", delta_agua_pp=10, delta_esgoto_pp=50))
    assert r["depois"]["agua"] == 100 and r["depois"]["esgoto"] == 100 and r["depois"]["score"] == 0


def test_simular_nao_altera_dados_base():
    run(t.SimularCenarioTool(), sigla="MA", delta_esgoto_pp=20)
    assert json.loads(run(t.IndicadoresTool(), sigla="MA"))["esgoto"] == 32


def test_cache_ausente(monkeypatch):
    def falha():
        raise FileNotFoundError
    monkeypatch.setattr(t, "montar_registros", falha)
    assert run(t.RankingTool()).startswith("ERRO:")


def test_get_tools():
    assert len(t.get_tools()) == 7


def test_comparar_ufs_siglas_em_caixa_mista():
    with pytest.raises(t.ErroFerramenta):
        t.comparar_ufs(BASE, ["MA", "ma"])
    assert [u["sigla"] for u in t.comparar_ufs(BASE, ["ma", "Pi"])["ufs"]] == ["MA", "PI"]


def test_regiao_normaliza_e_lista_validas(monkeypatch):
    monkeypatch.setattr(t, "montar_registros", lambda: (None, BASE))
    assert json.loads(t.RankingTool()._run(regiao="nordeste"))["regiao"] == "Nordeste"
    assert "Use Norte" in t.DistanciaMetaTool()._run(regiao="Atlantida")


def test_excecao_inesperada_vira_erro(monkeypatch):
    def quebra():
        raise KeyError("x")

    monkeypatch.setattr(t, "montar_registros", quebra)
    assert t.IndicadoresTool()._run(sigla="MA") == "ERRO: falha interna na ferramenta."
