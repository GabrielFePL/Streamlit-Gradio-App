"""Validacao local das mensagens. Nao faz login nem grava dados no Supabase."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import db
import app_gradio


class TestarMensagens(unittest.TestCase):
    def setUp(self):
        self.campos = ("Teste", "Endereco", "teste@example.com", "11999999999", "PC", "Defeito")
        self.bloqueio = patch.object(
            db, "obter_conexao",
            side_effect=AssertionError("O teste local nao pode acessar o Supabase."),
        )
        self.bloqueio.start()
        self.addCleanup(self.bloqueio.stop)
        self.log_patch = patch.object(db.LOGGER, "error")
        self.log = self.log_patch.start()
        self.addCleanup(self.log_patch.stop)

    def test_campos_vazios(self):
        retorno = app_gradio.cadastrar("", "", "", "", "", "")
        self.assertIn("Preencha", retorno)
        self.assertNotIn("sucesso", retorno)

    def test_celular_invalido(self):
        campos = list(self.campos)
        campos[3] = "(11) 99999-9999"
        self.assertIn("somente números", app_gradio.cadastrar(*campos))

    def test_sucesso_com_numero_os(self):
        with patch.object(app_gradio, "cadastrar_ordem", return_value=27):
            retorno = app_gradio.cadastrar(*self.campos)
        self.assertIn("27", retorno)
        self.assertIn("cadastrada com sucesso", retorno)

    def test_mensagem_conhecida(self):
        mensagem = "Este cliente possui OS vinculadas."
        with patch.object(app_gradio, "cadastrar_ordem", side_effect=db.ErroTechFix(mensagem)):
            self.assertEqual(app_gradio.cadastrar(*self.campos), mensagem)

    def test_erro_inesperado_sem_detalhes(self):
        detalhe = "SUPABASE_KEY=SEGREDO; password=SENHA; SQL=select auth.users"
        with patch.object(app_gradio, "cadastrar_ordem", side_effect=RuntimeError(detalhe)):
            retorno = app_gradio.cadastrar(*self.campos)
        self.assertEqual(retorno, db.MENSAGEM_ERRO_GENERICO)
        for texto in ("SEGREDO", "SENHA", "SQL=", "auth.users"):
            self.assertNotIn(texto, retorno)
            self.assertNotIn(texto, str(self.log.call_args_list))

    def test_valueerror_inesperado_tambem_e_ocultado(self):
        with patch.object(app_gradio, "cadastrar_ordem", side_effect=ValueError("SEGREDO_INTERNO")):
            retorno = app_gradio.cadastrar(*self.campos)
        self.assertEqual(retorno, db.MENSAGEM_ERRO_GENERICO)

    def test_identificador_invalido_nao_confirma(self):
        for valor in (None, False, 0, -1, "27"):
            with self.subTest(valor=valor):
                with patch.object(app_gradio, "cadastrar_ordem", return_value=valor):
                    retorno = app_gradio.cadastrar(*self.campos)
                self.assertNotIn("cadastrada com sucesso", retorno)

    def test_falha_na_os_nao_confirma_cliente_como_atendimento(self):
        with patch.object(db, "obter_ou_criar_cliente", return_value={"id": 1}):
            with patch.object(db, "criar_ordem", side_effect=db.ErroTechFix(
                "Não foi possível cadastrar a ordem de serviço."
            )):
                retorno = app_gradio.cadastrar(*self.campos)
        self.assertNotIn("cadastrada com sucesso", retorno)
        self.assertIn("Não foi possível", retorno)

    def test_db_exige_id_da_os(self):
        for resposta in ({}, {"id": None}, {"id": False}, {"id": 0}):
            with self.subTest(resposta=resposta):
                with patch.object(db, "obter_ou_criar_cliente", return_value={"id": 1}):
                    with patch.object(db, "criar_ordem", return_value=resposta):
                        with self.assertRaises(db.ErroTechFix):
                            db.cadastrar_ordem(*self.campos)

    def test_compatibilidade_com_valueerror(self):
        with self.assertRaises(ValueError) as resultado:
            db.normalizar_email("email-invalido")
        self.assertIsInstance(resultado.exception, db.ErroValidacaoTechFix)


if __name__ == "__main__":
    unittest.main(verbosity=2)
