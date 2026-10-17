"""Estrutura inicial do painel administrativo da TechFix."""

import streamlit as st

from db import ErroTechFix, cadastrar_ordem, configuracao_disponivel


st.set_page_config(page_title="TechFix Administrativo", layout="wide")
st.title("TechFix Informática")
st.caption("Painel administrativo de ordens de serviço")

if configuracao_disponivel():
    st.sidebar.info("Variáveis de conexão preenchidas. A conexão será testada ao cadastrar.")
else:
    st.sidebar.warning("Conexão com o Supabase ainda não configurada.")

consultar, cadastrar, editar, indicadores = st.tabs(
    ["Consultar", "Cadastrar", "Editar/Excluir", "Indicadores"]
)

with consultar:
    st.subheader("Consultar ordens de serviço")
    st.info("A consulta e os filtros serão implementados na etapa do painel administrativo.")

with cadastrar:
    st.subheader("Cadastrar ordem de serviço")
    with st.form("cadastro_os"):
        col_cliente, col_equipamento = st.columns(2)
        with col_cliente:
            nome = st.text_input("Nome do Cliente", placeholder="Nome completo")
            endereco = st.text_input("Endereço", placeholder="Rua, número, bairro e cidade")
            email = st.text_input("E-mail", placeholder="cliente@example.com")
            celular = st.text_input("Celular/WhatsApp", placeholder="11999998888")
        with col_equipamento:
            modelo = st.text_input("Modelo do Computador", placeholder="Marca e modelo")
            problema = st.text_area("Problema Apresentado", placeholder="Descreva o defeito observado.")
        enviado = st.form_submit_button("Cadastrar")

    if enviado:
        try:
            numero_os = cadastrar_ordem(nome, endereco, email, celular, modelo, problema)
            st.success(f"Ordem de serviço nº {numero_os} cadastrada com sucesso. Status: Aberto.")
        except (ValueError, ErroTechFix) as exc:
            st.error(str(exc))

with editar:
    st.subheader("Editar ou excluir registros")
    st.info("As operações de edição e exclusão serão implementadas na etapa do painel administrativo.")

with indicadores:
    st.subheader("Indicadores das ordens de serviço")
    st.info("As contagens por status e o gráfico serão implementados após a consulta ao banco.")
