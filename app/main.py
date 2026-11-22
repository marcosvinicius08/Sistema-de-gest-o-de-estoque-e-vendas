
from fastapi import FastAPI

app = FastAPI(
    title="Sistema de Gestão de Estoque e Vendas",
    description="API para gerenciamento de produtos, estoque e vendas.",
    version="1.0.0"
)


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
