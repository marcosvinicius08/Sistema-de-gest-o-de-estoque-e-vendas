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
