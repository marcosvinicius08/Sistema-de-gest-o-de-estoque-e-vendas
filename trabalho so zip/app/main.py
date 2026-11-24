
from typing import Union

import httpx

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, StrictInt, StrictStr, StrictFloat

from app.produtos import (
    cadastrar_produto,
    listar_produtos,
    buscar_produto,
    atualizar_produto,
    excluir_produto,
)

from app.estoque import (
    registrar_entrada,
    registrar_saida,
    consultar_estoque,
    verificar_estoque_baixo,
    listar_movimentacoes,
)

from app.vendas import (
    registrar_venda,
    buscar_venda,
    listar_vendas,
    listar_itens_venda,
)


app = FastAPI(
    title="Sistema de Gestão de Estoque e Vendas",
    description="API para gerenciamento de produtos, estoque e vendas.",
    version="1.0.0"
)


class ProdutoEntrada(BaseModel):
    nome: StrictStr
    descricao: StrictStr
    preco: Union[StrictInt, StrictFloat]
    quantidade: StrictInt = Field(ge=0)
    estoque_minimo: StrictInt = Field(ge=0)


class ProdutoAtualizacao(BaseModel):
    nome: StrictStr | None = None
    descricao: StrictStr | None = None
    preco: Union[StrictInt, StrictFloat] | None = None
    estoque_minimo: StrictInt | None = Field(default=None, ge=0)


class MovimentacaoEntrada(BaseModel):
    produto_id: StrictStr
    quantidade: StrictInt = Field(gt=0)


class ItemVenda(BaseModel):
    produto_id: StrictStr
    quantidade: StrictInt = Field(gt=0)


class VendaEntrada(BaseModel):
    itens: list[ItemVenda]


def executar(funcao, *args):
    try:
        return funcao(*args)

    except LookupError as erro:
        raise HTTPException(status_code=404, detail=str(erro))

    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))

    except httpx.HTTPStatusError as erro:
        if erro.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Documento não encontrado no banco de dados."
            )

        raise HTTPException(
            status_code=502,
            detail="Erro na comunicação com o CouchDB."
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível conectar ao CouchDB."
        )

    except RuntimeError as erro:
        raise HTTPException(status_code=500, detail=str(erro))


@app.get("/")
def inicio():
    return {
        "mensagem": "Sistema de Gestão de Estoque e Vendas funcionando!"
    }


@app.get("/status")
def status():
    return {
        "status": "online"
    }


@app.post("/produtos", status_code=201)
def criar_produto(dados: ProdutoEntrada):
    return executar(
        cadastrar_produto,
        dados.nome,
        dados.descricao,
        dados.preco,
        dados.quantidade,
        dados.estoque_minimo
    )


@app.get("/produtos")
def obter_produtos():
    return executar(listar_produtos)


@app.get("/produtos/{produto_id}")
def obter_produto(produto_id: str):
    return executar(buscar_produto, produto_id)


@app.put("/produtos/{produto_id}")
def modificar_produto(
    produto_id: str,
    dados: ProdutoAtualizacao
):
    dados_atualizacao = dados.model_dump(exclude_unset=True)

    return executar(
        atualizar_produto,
        produto_id,
        dados_atualizacao
    )


@app.delete("/produtos/{produto_id}")
def remover_produto(produto_id: str):
    return executar(excluir_produto, produto_id)


@app.post("/estoque/entrada")
def entrada_estoque(dados: MovimentacaoEntrada):
    return executar(
        registrar_entrada,
        dados.produto_id,
        dados.quantidade
    )


@app.post("/estoque/saida")
def saida_estoque(dados: MovimentacaoEntrada):
    return executar(
        registrar_saida,
        dados.produto_id,
        dados.quantidade
    )


@app.get("/estoque/baixo")
def estoque_baixo():
    return executar(verificar_estoque_baixo)


@app.get("/estoque/{produto_id}")
def obter_estoque(produto_id: str):
    return executar(consultar_estoque, produto_id)


@app.get("/movimentacoes")
def obter_movimentacoes(produto_id: str | None = None):
    return executar(listar_movimentacoes, produto_id)


@app.post("/vendas", status_code=201)
def criar_venda(dados: VendaEntrada):
    itens = [
        item.model_dump()
        for item in dados.itens
    ]

    return executar(registrar_venda, itens)


@app.get("/vendas")
def obter_vendas():
    return executar(listar_vendas)


@app.get("/vendas/{venda_id}/itens")
def obter_itens_venda(venda_id: str):
    return executar(listar_itens_venda, venda_id)


@app.get("/vendas/{venda_id}")
def obter_venda(venda_id: str):
    return executar(buscar_venda, venda_id)
