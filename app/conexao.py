import os
import httpx
from dotenv import load_dotenv


load_dotenv()

COUCHDB_URL = os.getenv("COUCHDB_URL")
COUCHDB_USER = os.getenv("COUCHDB_USER")
COUCHDB_PASSWORD = os.getenv("COUCHDB_PASSWORD")
COUCHDB_DATABASE = os.getenv("COUCHDB_DATABASE")

BASE_URL = f"{COUCHDB_URL}/{COUCHDB_DATABASE}"

AUTH = (COUCHDB_USER, COUCHDB_PASSWORD)


def verificar_conexao():
    resposta = httpx.get(
        COUCHDB_URL,
        auth=AUTH,
        timeout=10
    )
    resposta.raise_for_status()
    return resposta.json()


def obter_documento(documento_id):
    resposta = httpx.get(
        f"{BASE_URL}/{documento_id}",
        auth=AUTH,
        timeout=10
    )

    if resposta.status_code == 404:
        raise LookupError("Documento não encontrado.")

    resposta.raise_for_status()
    return resposta.json()


def criar_documento(dados):
    resposta = httpx.post(
        BASE_URL,
        json=dados,
        auth=AUTH,
        timeout=10
    )
    resposta.raise_for_status()
    return resposta.json()


def atualizar_documento(dados):
    documento_id = dados.get("_id")

    if not documento_id or not dados.get("_rev"):
        raise ValueError("Documento precisa conter _id e _rev.")

    resposta = httpx.put(
        f"{BASE_URL}/{documento_id}",
        json=dados,
        auth=AUTH,
        timeout=10
    )
    resposta.raise_for_status()
    return resposta.json()


def excluir_documento(documento_id, revisao):
    resposta = httpx.delete(
        f"{BASE_URL}/{documento_id}",
        params={"rev": revisao},
        auth=AUTH,
        timeout=10
    )
    resposta.raise_for_status()
    return resposta.json()


def listar_documentos(tipo):
    resposta = httpx.get(
        BASE_URL,
        params={
            "include_docs": "true",
            "startkey": f'"{tipo}"',
            "endkey": f'"{tipo}\ufff0"'
        },
        auth=AUTH,
        timeout=10
    )
    resposta.raise_for_status()

    documentos = resposta.json()["rows"]

    return [
        item["doc"]
        for item in documentos
        if item.get("doc", {}).get("tipo") == tipo
    ]
