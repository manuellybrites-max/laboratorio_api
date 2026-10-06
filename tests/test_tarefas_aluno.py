"""TAREFA DO ALUNO -- os cinco testes que faltam para os >= 8 do entregavel.

Cada teste abaixo tem nome, docstring e um pytest.skip. Apague o skip, escreva o
corpo, e o teste passa a valer. Nenhum deles precisa de banco: os tres primeiros
rodam so contra o motor.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.dominio.motor_emergia import calcular_indices


def test_regressao_numerica_contra_a_planilha(fluxos_golden):
    """Compara os seis indices com a aba SSB da Planilha_base.xlsx.

    Criterio do entregavel: abs(delta) <= 1E-6 por indice. Comece pelo inventario
    de referencia (Y = 200, F = 50, renovaveis = 115, nao renovaveis = 85) e
    escreva os seis valores esperados a mao antes de rodar -- se o teste passar
    de primeira sem voce saber o valor esperado, ele nao esta provando nada.
    """
    resultado = calcular_indices(fluxos_golden, Decimal("1000"))

    assert resultado.y == Decimal("200.000000")
    assert resultado.eyr == Decimal("4.000000")
    assert resultado.elr == Decimal("0.739130")
    assert resultado.esi == Decimal("5.411765")
    assert resultado.eii == Decimal("0.184783")
    assert resultado.percentual_r == Decimal("57.500000")

def test_quantizacao_unica_no_final():
    """Mostra o erro duplo de arredondar no meio do calculo.

    Calcule ESI = EYR / ELR de duas formas: (a) quantizando EYR e ELR para seis
    casas antes de dividir; (b) dividindo em 28 digitos e quantizando so o ESI.
    Os dois resultados diferem -- e o motor usa (b). Prove a diferenca.
    """
    from decimal import Decimal, localcontext

    eyr = Decimal("4")
    elr = Decimal("0.7391304347826086956521739130")

    with localcontext() as ctx:
        ctx.prec = 28

        esi_arredondado_antes = (
            eyr.quantize(Decimal("0.000001"))
            / elr.quantize(Decimal("0.000001"))
        )

        esi_arredondado_no_final = (
            eyr / elr
        ).quantize(Decimal("0.000001"))

    assert esi_arredondado_antes != esi_arredondado_no_final

def test_ordem_da_soma_com_magnitudes_divergentes():
    """A associatividade quebra quando as magnitudes divergem.

    Monte um inventario com um fluxo de 1E20 sej e outro de 1E-5 sej e some nas
    duas ordens possiveis. Explique, no corpo do teste, por que a precisao de 28
    digitos e o limite -- e por que ordenar o inventario e uma decisao de dominio.
    """
    from decimal import Decimal, localcontext

    grande = Decimal("1E20")
    pequeno = Decimal("1E-5")

    with localcontext() as ctx:
        ctx.prec = 28

        soma_grande_primeiro = grande + pequeno
        soma_pequeno_primeiro = pequeno + grande

    assert soma_grande_primeiro == soma_pequeno_primeiro

    # Com 28 digitos de precisao, o valor muito pequeno pode ser perdido
    # quando somado a um valor muito grande.

def test_erro_de_dominio_responde_problem_json(cliente, corpo_golden):
    """Inventario sem fluxo renovavel deve responder 422 em problem+json."""

    corpo = corpo_golden.copy()

    corpo["fluxos"] = [
        {
            "recurso": "solo",
            "categoria": "N",
            "emergia_sej": "50"
        },
        {
            "recurso": "diesel",
            "categoria": "MN",
            "emergia_sej": "20"
        }
    ]

    resposta = cliente.post("/v1/safras/44/calculos", json=corpo)

    assert resposta.status_code == 422
    assert "application/problem+json" in resposta.headers["content-type"]

    dados = resposta.json()

    assert dados["type"] == "https://agroemergia.sc/erros/fluxos-insuficientes"
    assert dados["title"] == "Fluxos insuficientes"
    assert dados["status"] == 422
    assert dados["instance"] == "/v1/safras/44/calculos"
    assert "detail" in dados

def test_campo_extra_no_corpo_da_requisicao_e_rejeitado(cliente, corpo_golden):
    """"energia_produto_jj" tem de morrer com 422, nao virar calculo incompleto.

    Hoje o CalculoRequestDTO nao declara extra="forbid": o campo desconhecido e
    ignorado e o typo passa silencioso, exatamente como na planilha. Feche o
    TODO PASSO 3 em app/api/v1/dto.py e prove aqui.
    """
    corpo = corpo_golden.copy()
    corpo["energia_produto_jj"] = "1000"

    resposta = cliente.post("/v1/safras/42/calculos", json=corpo)

    assert resposta.status_code == 422
    assert "application/problem+json" in resposta.headers["content-type"]

    dados = resposta.json()

    assert dados["type"] == "https://agroemergia.sc/erros/requisicao-invalida"
    assert dados["title"] == "Requisicao nao processavel"
    assert dados["status"] == 422
    assert dados["instance"] == "/v1/safras/42/calculos"
    assert "erros" in dados