from uuid import uuid4

from app.conexao import (
    obter_documento,
    criar_documento,
    atualizar_documento,
    excluir_documento,
    listar_documentos,
)


def cadastrar_produto(nome, descricao, preco, quantidade, estoque_minimo):
    if not isinstance(nome, str) or nome.strip() == "":
        raise ValueError("O nome do produto não pode ficar vazio.")

    if not isinstance(descricao, str):
        raise ValueError("A descrição deve ser um texto.")

    if type(preco) not in (int, float) or preco < 0:
        raise ValueError("O preço deve ser um número maior ou igual a zero.")

    if type(quantidade) != int or quantidade < 0:
        raise ValueError("A quantidade deve ser um número inteiro maior ou igual a zero.")

    if type(estoque_minimo) != int or estoque_minimo < 0:
        raise ValueError("O estoque mínimo deve ser um número inteiro maior ou igual a zero.")

    produto = {
        "_id": "produto_" + uuid4().hex,
        "tipo": "produto",
        "nome": nome.strip(),
        "descricao": descricao,
        "preco": preco,
        "quantidade": quantidade,
        "estoque_minimo": estoque_minimo,
    }

    produto_salvo = criar_documento(produto)

    return {
        "mensagem": "Produto cadastrado com sucesso",
        "produto": produto_salvo,
    }


def listar_produtos():
    return listar_documentos("produto")


def buscar_produto(produto_id):
    produto = obter_documento(produto_id)

    if produto is None or produto.get("tipo") != "produto":
        raise LookupError("Produto não encontrado.")

    return produto


def atualizar_produto(produto_id, dados):
    if not isinstance(dados, dict) or len(dados) == 0:
        raise ValueError("Informe os dados que deseja atualizar.")

    campos_permitidos = ["nome", "descricao", "preco", "estoque_minimo"]

    for campo in dados:
        if campo not in campos_permitidos:
            raise ValueError("Não é permitido atualizar o campo: " + campo)

    if "nome" in dados:
        if not isinstance(dados["nome"], str) or dados["nome"].strip() == "":
            raise ValueError("O nome do produto não pode ficar vazio.")
        dados["nome"] = dados["nome"].strip()

    if "descricao" in dados and not isinstance(dados["descricao"], str):
        raise ValueError("A descrição deve ser um texto.")

    if "preco" in dados:
        if type(dados["preco"]) not in (int, float) or dados["preco"] < 0:
            raise ValueError("O preço deve ser um número maior ou igual a zero.")

    if "estoque_minimo" in dados:
        if type(dados["estoque_minimo"]) != int or dados["estoque_minimo"] < 0:
            raise ValueError("O estoque mínimo deve ser um número inteiro maior ou igual a zero.")

    produto = buscar_produto(produto_id)

    for campo in dados:
        produto[campo] = dados[campo]

    produto_atualizado = atualizar_documento(produto)

    return {
        "mensagem": "Produto atualizado com sucesso",
        "produto": produto_atualizado,
    }


def excluir_produto(produto_id):
    produto = buscar_produto(produto_id)

    movimentacoes = listar_documentos("movimentacao")

    for movimentacao in movimentacoes:
        if movimentacao.get("produto_id") == produto_id:
            raise ValueError("Não é possível excluir um produto com movimentações.")

    vendas = listar_documentos("venda")

    for venda in vendas:
        for item in venda.get("itens", []):
            if item.get("produto_id") == produto_id:
                raise ValueError("Não é possível excluir um produto com vendas.")

    excluir_documento(produto["_id"], produto["_rev"])

    return {"mensagem": "Produto excluído com sucesso"}
  