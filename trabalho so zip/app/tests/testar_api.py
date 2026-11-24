import time
import os
import uuid
import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://127.0.0.1:8000"

COUCHDB_URL = os.getenv("COUCHDB_URL")
COUCHDB_USER = os.getenv("COUCHDB_USER")
COUCHDB_PASSWORD = os.getenv("COUCHDB_PASSWORD")
COUCHDB_DATABASE = os.getenv("COUCHDB_DATABASE")

COUCHDB_AUTH = (COUCHDB_USER, COUCHDB_PASSWORD)
BASE_COUCHDB_URL = f"{COUCHDB_URL}/{COUCHDB_DATABASE}"

cliente = httpx.Client(base_url=API_URL, timeout=10)

produto_id = None
testes_aprovados = 0
testes_falhos = 0


def testar(nome, funcao):
    global testes_aprovados, testes_falhos

    inicio = time.perf_counter()

    try:
        funcao()
        duracao = time.perf_counter() - inicio
        testes_aprovados += 1
        print(f"PASSOU | {nome} | {duracao:.2f}s")

    except Exception as erro:
        duracao = time.perf_counter() - inicio
        testes_falhos += 1
        print(
            f"FALHOU | {nome} | "
            f"{type(erro).__name__}: {repr(erro)} | "
            f"{duracao:.2f}s"
        )


def verificar_status():
    resposta = cliente.get("/status")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "online"


def verificar_inicio():
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert "mensagem" in resposta.json()


def cadastrar_produto():
    global produto_id

    dados = {
        "nome": "Produto Teste API",
        "descricao": "Produto temporário para testes",
        "preco": 12.00,
        "quantidade": 10,
        "estoque_minimo": 2
    }

    resposta = cliente.post("/produtos", json=dados)

    assert resposta.status_code == 201, resposta.text

    produto_id = resposta.json()["produto"]["id"]

    assert produto_id.startswith("produto_")


def consultar_produto():
    resposta = cliente.get(f"/produtos/{produto_id}")

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Produto Teste API"
    assert resposta.json()["quantidade"] == 10


def listar_produtos():
    resposta = cliente.get("/produtos")

    assert resposta.status_code == 200
    assert any(
        produto["_id"] == produto_id
        for produto in resposta.json()
    )


def atualizar_produto():
    resposta = cliente.put(
        f"/produtos/{produto_id}",
        json={
            "nome": "Produto Teste API Atualizado",
            "preco": 12.00,
            "estoque_minimo": 13
        }
    )

    assert resposta.status_code == 200

    produto = cliente.get(f"/produtos/{produto_id}").json()

    assert produto["nome"] == "Produto Teste API Atualizado"
    assert produto["preco"] == 12.00
    assert produto["quantidade"] == 10
    assert produto["estoque_minimo"] == 13


def impedir_atualizacao_quantidade():
    resposta = cliente.put(
        f"/produtos/{produto_id}",
        json={"quantidade": 100}
    )

    assert resposta.status_code == 400


def registrar_entrada():
    resposta = cliente.post(
        "/estoque/entrada",
        json={
            "produto_id": produto_id,
            "quantidade": 5
        }
    )

    assert resposta.status_code == 200
    assert resposta.json()["estoque_atual"] == 15


def consultar_estoque_apos_entrada():
    resposta = cliente.get(f"/estoque/{produto_id}")

    assert resposta.status_code == 200
    assert resposta.json()["quantidade"] == 15


def registrar_saida():
    resposta = cliente.post(
        "/estoque/saida",
        json={
            "produto_id": produto_id,
            "quantidade": 3
        }
    )

    assert resposta.status_code == 200
    assert resposta.json()["estoque_atual"] == 12


def consultar_estoque_apos_saida():
    resposta = cliente.get(f"/estoque/{produto_id}")

    assert resposta.status_code == 200
    assert resposta.json()["quantidade"] == 12


def impedir_estoque_negativo():
    resposta = cliente.post(
        "/estoque/saida",
        json={
            "produto_id": produto_id,
            "quantidade": 100
        }
    )

    assert resposta.status_code == 400

    estoque = cliente.get(f"/estoque/{produto_id}").json()

    assert estoque["quantidade"] == 12


def verificar_estoque_baixo():
    resposta = cliente.get("/estoque/baixo")

    assert resposta.status_code == 200

    assert any(
        item["produto_id"] == produto_id
        for item in resposta.json()
    )


def listar_movimentacoes():
    resposta = cliente.get(
        "/movimentacoes",
        params={"produto_id": produto_id}
    )

    assert resposta.status_code == 200
    assert len(resposta.json()) == 2


def registrar_venda():
    resposta = cliente.post(
        "/vendas",
        json={
            "itens": [
                {
                    "produto_id": produto_id,
                    "quantidade": 2
                }
            ]
        }
    )

    assert resposta.status_code == 201, resposta.text

    venda = resposta.json()["venda"]

    assert venda["total"] == 24.00
    assert venda["status"] == "concluida"


def consultar_estoque_apos_venda():
    resposta = cliente.get(f"/estoque/{produto_id}")

    assert resposta.status_code == 200
    assert resposta.json()["quantidade"] == 10


def listar_vendas():
    resposta = cliente.get("/vendas")

    assert resposta.status_code == 200

    assert any(
        any(
            item["produto_id"] == produto_id
            for item in venda.get("itens", [])
        )
        for venda in resposta.json()
    )


def consultar_venda():
    vendas = cliente.get("/vendas").json()

    venda = next(
        venda
        for venda in vendas
        if any(
            item["produto_id"] == produto_id
            for item in venda.get("itens", [])
        )
    )

    venda_id = venda["_id"]

    resposta = cliente.get(f"/vendas/{venda_id}")

    assert resposta.status_code == 200
    assert resposta.json()["_id"] == venda_id


def consultar_itens_venda():
    vendas = cliente.get("/vendas").json()

    venda = next(
        venda
        for venda in vendas
        if any(
            item["produto_id"] == produto_id
            for item in venda.get("itens", [])
        )
    )

    resposta = cliente.get(f"/vendas/{venda['_id']}/itens")

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert resposta.json()[0]["quantidade"] == 2


def impedir_venda_sem_estoque():
    resposta = cliente.post(
        "/vendas",
        json={
            "itens": [
                {
                    "produto_id": produto_id,
                    "quantidade": 100
                }
            ]
        }
    )

    assert resposta.status_code == 400

    estoque = cliente.get(f"/estoque/{produto_id}").json()

    assert estoque["quantidade"] == 10


def impedir_exclusao_com_historico():
    resposta = cliente.delete(f"/produtos/{produto_id}")

    assert resposta.status_code == 400

    consulta = cliente.get(f"/produtos/{produto_id}")

    assert consulta.status_code == 200


def limpar_dados_teste():
    if not produto_id:
        return

    print("\nLimpando documentos temporários...")

    resposta = httpx.get(
        f"{BASE_COUCHDB_URL}/_all_docs",
        params={"include_docs": "true"},
        auth=COUCHDB_AUTH,
        timeout=10
    )

    resposta.raise_for_status()

    documentos = [
        linha["doc"]
        for linha in resposta.json()["rows"]
        if linha.get("doc")
    ]

    ids_para_excluir = []

    for documento in documentos:
        if documento["_id"] == produto_id:
            ids_para_excluir.append(documento)

        elif documento.get("produto_id") == produto_id:
            ids_para_excluir.append(documento)

        elif documento.get("tipo") == "venda":
            if any(
                item.get("produto_id") == produto_id
                for item in documento.get("itens", [])
            ):
                ids_para_excluir.append(documento)

    for documento in ids_para_excluir:
        httpx.delete(
            f"{BASE_COUCHDB_URL}/{documento['_id']}",
            params={"rev": documento["_rev"]},
            auth=COUCHDB_AUTH,
            timeout=10
        ).raise_for_status()

    print(f"Documentos temporários removidos: {len(ids_para_excluir)}")


try:
    print("\n===== TESTES DA API =====\n")

    testar("Rota inicial", verificar_inicio)
    testar("Status da API", verificar_status)
    testar("Cadastro de produto", cadastrar_produto)

    if produto_id:
        testar("Consulta de produto", consultar_produto)
        testar("Listagem de produtos", listar_produtos)
        testar("Atualização de produto", atualizar_produto)
        testar("Bloqueio de atualização da quantidade", impedir_atualizacao_quantidade)

        testar("Registro de entrada", registrar_entrada)
        testar("Consulta após entrada", consultar_estoque_apos_entrada)
        testar("Registro de saída", registrar_saida)
        testar("Consulta após saída", consultar_estoque_apos_saida)
        testar("Bloqueio de estoque negativo", impedir_estoque_negativo)
        testar("Verificação de estoque baixo", verificar_estoque_baixo)
        testar("Listagem de movimentações", listar_movimentacoes)

        testar("Registro de venda", registrar_venda)
        testar("Consulta de estoque após venda", consultar_estoque_apos_venda)
        testar("Listagem de vendas", listar_vendas)
        testar("Consulta de venda", consultar_venda)
        testar("Consulta de itens da venda", consultar_itens_venda)
        testar("Bloqueio de venda sem estoque", impedir_venda_sem_estoque)
        testar("Bloqueio de exclusão com histórico", impedir_exclusao_com_historico)

finally:
    try:
        limpar_dados_teste()
    except Exception as erro:
        print(f"ATENÇÃO: não foi possível limpar os dados: {erro}")

    cliente.close()

    print("\n===== RESULTADO FINAL =====")
    print(f"Testes aprovados: {testes_aprovados}")
    print(f"Testes com falha: {testes_falhos}")
    print(f"Total executado: {testes_aprovados + testes_falhos}")
