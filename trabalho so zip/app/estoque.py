
from uuid import uuid4

from app.produtos import buscar_produto, listar_produtos
from app.conexao import (
    atualizar_documento,
    criar_documento,
    listar_documentos,
)


def registrar_entrada(produto_id, quantidade):
    if type(quantidade) != int or quantidade <= 0:
        raise ValueError("A quantidade deve ser um inteiro maior que zero.")

    produto = buscar_produto(produto_id)

    produto["quantidade"] += quantidade

    atualizar_documento(produto)

    movimentacao = {
        "_id": "movimentacao_" + uuid4().hex,
        "tipo": "movimentacao",
        "produto_id": produto_id,
        "operacao": "entrada",
        "quantidade": quantidade,
        "estoque_anterior": produto["quantidade"] - quantidade,
        "estoque_atual": produto["quantidade"],
    }

    resultado = criar_documento(movimentacao)

    return {
        "mensagem": "Entrada registrada com sucesso",
        "movimentacao": resultado,
        "estoque_atual": produto["quantidade"],
    }


def registrar_saida(produto_id, quantidade):
    if type(quantidade) != int or quantidade <= 0:
        raise ValueError("A quantidade deve ser um inteiro maior que zero.")

    produto = buscar_produto(produto_id)

    if quantidade > produto["quantidade"]:
        raise ValueError("Estoque insuficiente para realizar a saída.")

    estoque_anterior = produto["quantidade"]
    produto["quantidade"] -= quantidade

    atualizar_documento(produto)

    movimentacao = {
        "_id": "movimentacao_" + uuid4().hex,
        "tipo": "movimentacao",
        "produto_id": produto_id,
        "operacao": "saida",
        "quantidade": quantidade,
        "estoque_anterior": estoque_anterior,
        "estoque_atual": produto["quantidade"],
    }

    resultado = criar_documento(movimentacao)

    return {
        "mensagem": "Saída registrada com sucesso",
        "movimentacao": resultado,
        "estoque_atual": produto["quantidade"],
    }


def consultar_estoque(produto_id):
    produto = buscar_produto(produto_id)

    return {
        "produto_id": produto_id,
        "nome": produto["nome"],
        "quantidade": produto["quantidade"],
        "estoque_minimo": produto["estoque_minimo"],
    }


def verificar_estoque_baixo(produto_id=None):
    if produto_id:
        produtos = [buscar_produto(produto_id)]
    else:
        produtos = listar_produtos()

    return [
        {
            "produto_id": produto["_id"],
            "nome": produto["nome"],
            "quantidade": produto["quantidade"],
            "estoque_minimo": produto["estoque_minimo"],
        }
        for produto in produtos
        if produto["quantidade"] <= produto["estoque_minimo"]
    ]


def listar_movimentacoes(produto_id=None):
    movimentacoes = listar_documentos("movimentacao")

    if produto_id:
        movimentacoes = [
            movimentacao
            for movimentacao in movimentacoes
            if movimentacao.get("produto_id") == produto_id
        ]

    return movimentacoes
