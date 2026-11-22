import sys
import unittest
from types import ModuleType
from unittest.mock import patch

# Simula apenas a conexão com o banco. Não precisa ter CouchDB instalado.
conexao_teste = ModuleType("app.conexao")
conexao_teste.obter_documento = lambda produto_id: None
conexao_teste.criar_documento = lambda dados: dados
conexao_teste.atualizar_documento = lambda dados: dados
conexao_teste.excluir_documento = lambda produto_id, rev: True
conexao_teste.listar_documentos = lambda tipo: []
sys.modules["app.conexao"] = conexao_teste

from app import produtos


class TestarProdutos(unittest.TestCase):
    def setUp(self):
        self.produto = {
            "_id": "produto_001",
            "_rev": "1-abc",
            "tipo": "produto",
            "nome": "Teclado",
            "descricao": "Teclado USB",
            "preco": 80.0,
            "quantidade": 20,
            "estoque_minimo": 5,
        }

    def test_cadastrar_produto_valido(self):
        with patch.object(produtos, "criar_documento", side_effect=lambda dados: dados):
            resposta = produtos.cadastrar_produto("Mouse", "Mouse USB", 40, 10, 3)
        self.assertEqual(resposta["produto"]["nome"], "Mouse")
        self.assertEqual(resposta["produto"]["quantidade"], 10)
        self.assertTrue(resposta["produto"]["_id"].startswith("produto_"))

    def test_cadastrar_nome_vazio(self):
        with self.assertRaises(ValueError):
            produtos.cadastrar_produto("  ", "Mouse USB", 40, 10, 3)

    def test_cadastrar_preco_negativo(self):
        with self.assertRaises(ValueError):
            produtos.cadastrar_produto("Mouse", "Mouse USB", -10, 10, 3)

    def test_cadastrar_quantidade_negativa(self):
        with self.assertRaises(ValueError):
            produtos.cadastrar_produto("Mouse", "Mouse USB", 10, -1, 3)

    def test_listar_produtos(self):
        with patch.object(produtos, "listar_documentos", return_value=[self.produto]):
            resposta = produtos.listar_produtos()
        self.assertEqual(len(resposta), 1)
        self.assertEqual(resposta[0]["nome"], "Teclado")

    def test_buscar_produto_existente(self):
        with patch.object(produtos, "obter_documento", return_value=self.produto):
            resposta = produtos.buscar_produto("produto_001")
        self.assertEqual(resposta["nome"], "Teclado")

    def test_buscar_produto_inexistente(self):
        with patch.object(produtos, "obter_documento", return_value=None):
            with self.assertRaises(LookupError):
                produtos.buscar_produto("produto_999")

    def test_atualizar_produto(self):
        with patch.object(produtos, "obter_documento", return_value=self.produto.copy()):
            with patch.object(produtos, "atualizar_documento", side_effect=lambda dados: dados):
                resposta = produtos.atualizar_produto("produto_001", {"preco": 100})
        self.assertEqual(resposta["produto"]["preco"], 100)
        self.assertEqual(resposta["produto"]["quantidade"], 20)

    def test_impedir_alteracao_direta_da_quantidade(self):
        with self.assertRaises(ValueError):
            produtos.atualizar_produto("produto_001", {"quantidade": 100})

    def test_impedir_exclusao_com_movimentacao(self):
        movimento = {"produto_id": "produto_001", "tipo": "movimentacao"}
        with patch.object(produtos, "obter_documento", return_value=self.produto):
            with patch.object(produtos, "listar_documentos", return_value=[movimento]):
                with self.assertRaises(ValueError):
                    produtos.excluir_produto("produto_001")

    def test_impedir_exclusao_com_venda(self):
        venda = {"tipo": "venda", "itens": [{"produto_id": "produto_001"}]}
        with patch.object(produtos, "obter_documento", return_value=self.produto):
            with patch.object(produtos, "listar_documentos", side_effect=[[], [venda]]):
                with self.assertRaises(ValueError):
                    produtos.excluir_produto("produto_001")

    def test_excluir_produto_sem_historico(self):
        with patch.object(produtos, "obter_documento", return_value=self.produto):
            with patch.object(produtos, "listar_documentos", return_value=[]):
                with patch.object(produtos, "excluir_documento", return_value=True) as excluir:
                    resposta = produtos.excluir_produto("produto_001")
        self.assertEqual(resposta["mensagem"], "Produto excluído com sucesso")
        excluir.assert_called_once_with("produto_001", "1-abc")


if __name__ == "__main__":
    unittest.main()
