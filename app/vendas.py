
from uuid import uuid4
from decimal import Decimal, InvalidOperation

from app.produtos import buscar_produto
from app.estoque import registrar_saida
from app.conexao import (
    criar_documento,
    obter_documento,
    listar_documentos,
)


def preparar_itens(itens):
    if not isinstance(itens, list) or len(itens) == 0:
        raise ValueError("A venda deve possuir pelo menos um item.")

    itens_preparados = []
    produtos = {}

    for item in itens:
        if not isinstance(item, dict):
            raise ValueError("Cada item da venda deve ser um dicionário.")

        produto_id = item.get("produto_id")
        quantidade = item.get("quantidade")

        if not isinstance(produto_id, str) or not produto_id.strip():
            raise ValueError("Informe um ID de produto válido.")

        if type(quantidade) != int or quantidade <= 0:
            raise ValueError("A quantidade deve ser um inteiro maior que zero.")

        produto = buscar_produto(produto_id)

        try:
            preco = Decimal(str(produto["preco"]))
        except (InvalidOperation, KeyError):
            raise ValueError("O produto possui um preço inválido.")

        if not preco.is_finite() or preco < 0:
            raise ValueError("O produto possui um preço inválido.")

        preco = preco.quantize(Decimal("0.01"))
        subtotal = preco * quantidade

        itens_preparados.append({
            "produto_id": produto_id,
            "nome": produto["nome"],
            "quantidade": quantidade,
            "preco_unitario": float(preco),
            "subtotal": float(subtotal),
        })

        if produto_id not in produtos:
            produtos[produto_id] = {
                "produto": produto,
                "quantidade_total": 0,
            }

        produtos[produto_id]["quantidade_total"] += quantidade

    return itens_preparados, produtos


def calcular_total(itens):
    itens_preparados, produtos = preparar_itens(itens)

    total = sum(
        Decimal(str(item["subtotal"]))
        for item in itens_preparados
    )

    return float(total.quantize(Decimal("0.01")))


def registrar_venda(itens):
    itens_preparados, produtos = preparar_itens(itens)

    total = sum(
        Decimal(str(item["subtotal"]))
        for item in itens_preparados
    )

    total = float(total.quantize(Decimal("0.01")))

    for produto_id, dados in produtos.items():
        quantidade_disponivel = dados["produto"]["quantidade"]
        quantidade_solicitada = dados["quantidade_total"]

        if quantidade_solicitada > quantidade_disponivel:
            raise ValueError(
                f"Estoque insuficiente para o produto "
                f"{dados['produto']['nome']}."
            )

    movimentacoes_realizadas = []

    try:
        for produto_id, dados in produtos.items():
            registrar_saida(
                produto_id,
                dados["quantidade_total"]
            )

            movimentacoes_realizadas.append({
                "produto_id": produto_id,
                "quantidade": dados["quantidade_total"],
            })

        venda = {
            "_id": "venda_" + uuid4().hex,
            "tipo": "venda",
            "itens": itens_preparados,
            "total": total,
            "status": "concluida",
        }

        resultado = criar_documento(venda)

        venda["_rev"] = resultado["rev"]

        return {
            "mensagem": "Venda registrada com sucesso.",
            "venda": venda,
        }

    except Exception as erro:
        falhas_compensacao = []

        for movimentacao in reversed(movimentacoes_realizadas):
            try:
                from app.estoque import registrar_entrada

                registrar_entrada(
                    movimentacao["produto_id"],
                    movimentacao["quantidade"]
                )

            except Exception as erro_compensacao:
                falhas_compensacao.append(str(erro_compensacao))

        if falhas_compensacao:
            raise RuntimeError(
                f"Falha na venda: {erro}. "
                f"Também houve falha ao restaurar o estoque: "
                f"{falhas_compensacao}"
            ) from erro

        raise


def buscar_venda(venda_id):
    venda = obter_documento(venda_id)

    if venda.get("tipo") != "venda":
        raise LookupError("Venda não encontrada.")

    return venda


def listar_vendas():
    return listar_documentos("venda")


def listar_itens_venda(venda_id):
    venda = buscar_venda(venda_id)

    return venda.get("itens", [])
