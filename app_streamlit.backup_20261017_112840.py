"""Painel TechFix: consulta de OS e cadastro com cliente compartilhado."""

import pandas as pd
import streamlit as st

st.set_option("client.showErrorDetails", "none")

from db import (
    STATUS_OS,
    cadastrar_ordem,
    configuracao_disponivel,
    consultar_ordens,
    mensagem_erro_usuario,
)

TAMANHO_PAGINA = 50
COLUNAS_TABELA = {
    "id": "OS",
    "cliente_id": "ID do cliente",
    "cliente.nome": "Cliente",
    "cliente.endereco": "Endereço",
    "cliente.email": "E-mail",
    "cliente.celular_whatsapp": "Celular/WhatsApp",
    "modelo_computador": "Modelo do computador",
    "problema_relatado": "Problema relatado",
    "status": "Status",
    "data_abertura": "Abertura",
    "data_atualizacao": "Última atualização",
}


def preparar_tabela(ordens):
    """Transformar a resposta com cliente associado em uma tabela de leitura."""
    tabela = pd.json_normalize(ordens).reindex(columns=list(COLUNAS_TABELA))
    tabela = tabela.rename(columns=COLUNAS_TABELA)
    tabela["Celular/WhatsApp"] = tabela["Celular/WhatsApp"].astype("string")
    for coluna in ("Abertura", "Última atualização"):
        tabela[coluna] = (
            pd.to_datetime(tabela[coluna], utc=True, errors="coerce")
            .dt.tz_convert("America/Sao_Paulo")
            .dt.tz_localize(None)
        )
    return tabela


def processar_cadastro(nome, endereco, email, celular, modelo, problema):
    """Confirmar sucesso somente quando o cadastro devolver um ID valido."""
    try:
        numero_os = cadastrar_ordem(nome, endereco, email, celular, modelo, problema)
        if isinstance(numero_os, bool) or not isinstance(numero_os, int) or numero_os < 1:
            raise RuntimeError("Cadastro sem identificador de OS válido.")
    except Exception as exc:
        return False, mensagem_erro_usuario(exc)
    else:
        return True, f"Ordem de serviço nº {numero_os} cadastrada com sucesso. Status: Aberto."


def limpar_filtros():
    st.session_state["consulta_nome"] = ""
    st.session_state["consulta_email"] = ""
    st.session_state["consulta_status"] = "Todos"
    st.session_state["pagina_os"] = 0


def mudar_pagina(incremento):
    st.session_state["pagina_os"] = max(
        0, st.session_state.get("pagina_os", 0) + incremento
    )


st.set_page_config(page_title="TechFix Administrativo", layout="wide")
st.title("TechFix Informática")
st.caption("Painel administrativo de ordens de serviço")

st.session_state.setdefault("pagina_os", 0)
configurada = configuracao_disponivel()

with st.sidebar:
    st.header("Filtros da consulta")
    filtro_nome = st.text_input(
        "Nome do cliente",
        placeholder="Digite parte do nome",
        key="consulta_nome",
    )
    filtro_email = st.text_input(
        "E-mail do cliente",
        placeholder="cliente@example.com",
        help="Busca pelo e-mail completo.",
        key="consulta_email",
    )
    filtro_status = st.selectbox(
        "Status",
        ["Todos", *STATUS_OS],
        key="consulta_status",
    )
    st.button("Limpar filtros", on_click=limpar_filtros)
    st.button("Atualizar lista", help="Consultar novamente os atendimentos.")
    st.caption("Os filtros se aplicam à aba Consultar.")
    if not configurada:
        st.warning("Serviço temporariamente indisponível. Contate a equipe responsável.")

# Voltar para a primeira pagina quando o conjunto de filtros mudar.
assinatura_filtros = (
    filtro_nome.strip().lower(),
    filtro_email.strip().lower(),
    filtro_status,
)
if st.session_state.get("_filtros_anteriores") != assinatura_filtros:
    st.session_state["pagina_os"] = 0
    st.session_state["_filtros_anteriores"] = assinatura_filtros

consultar, cadastrar, editar, indicadores = st.tabs(
    ["Consultar", "Cadastrar", "Editar/Excluir", "Indicadores"]
)

with consultar:
    st.subheader("Consultar ordens de serviço")
    if not configurada:
        st.info("A consulta estará disponível quando o serviço for configurado.")
    else:
        try:
            pagina = st.session_state["pagina_os"]
            # Buscar uma linha extra permite saber se existe uma proxima pagina.
            registros = consultar_ordens(
                nome=filtro_nome or None,
                email=filtro_email or None,
                status=None if filtro_status == "Todos" else filtro_status,
                limite=TAMANHO_PAGINA + 1,
                deslocamento=pagina * TAMANHO_PAGINA,
            )
            if not registros and pagina > 0:
                st.session_state["pagina_os"] = 0
                st.rerun()

            tem_proxima = len(registros) > TAMANHO_PAGINA
            ordens_pagina = registros[:TAMANHO_PAGINA]

            if not ordens_pagina:
                st.info("Nenhuma ordem de serviço encontrada para os filtros selecionados.")
            else:
                tabela = preparar_tabela(ordens_pagina)
                st.dataframe(
                    tabela,
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "OS": st.column_config.NumberColumn(format="%d"),
                        "ID do cliente": st.column_config.NumberColumn(format="%d"),
                        "Celular/WhatsApp": st.column_config.TextColumn(),
                        "Problema relatado": st.column_config.TextColumn(width="large"),
                        "Abertura": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
                        "Última atualização": st.column_config.DatetimeColumn(
                            format="DD/MM/YYYY HH:mm"
                        ),
                    },
                    key="tabela_os",
                )
                inicio = pagina * TAMANHO_PAGINA + 1
                fim = inicio + len(ordens_pagina) - 1
                st.caption(f"Exibindo {inicio} a {fim} • Página {pagina + 1}")
                st.caption("Horários exibidos no fuso de Brasília.")

                anterior, proxima = st.columns(2)
                anterior.button(
                    "Anterior",
                    disabled=pagina == 0,
                    on_click=mudar_pagina,
                    args=(-1,),
                    key="consulta_anterior",
                )
                proxima.button(
                    "Próxima",
                    disabled=not tem_proxima,
                    on_click=mudar_pagina,
                    args=(1,),
                    key="consulta_proxima",
                )
        except Exception as exc:
            st.error(mensagem_erro_usuario(exc))

with cadastrar:
    st.subheader("Cadastrar ordem de serviço")
    st.caption(
        "Clientes existentes são identificados pelo e-mail; "
        "os dados cadastrais são preservados."
    )
    with st.form("cadastro_os"):
        col_cliente, col_equipamento = st.columns(2)
        with col_cliente:
            nome = st.text_input(
                "Nome do Cliente", placeholder="Nome completo", key="cadastro_nome"
            )
            endereco = st.text_input(
                "Endereço", placeholder="Rua, número, bairro e cidade", key="cadastro_endereco"
            )
            email = st.text_input(
                "E-mail", placeholder="cliente@example.com", key="cadastro_email"
            )
            celular = st.text_input(
                "Celular/WhatsApp", placeholder="11999998888", key="cadastro_celular"
            )
        with col_equipamento:
            modelo = st.text_input(
                "Modelo do Computador", placeholder="Marca e modelo", key="cadastro_modelo"
            )
            problema = st.text_area(
                "Problema Apresentado", placeholder="Descreva o defeito observado.",
                height=160, key="cadastro_problema",
            )
        enviado = st.form_submit_button("Cadastrar", type="primary")

    mensagem_sucesso = st.session_state.pop("_sucesso_cadastro", None)
    if mensagem_sucesso:
        st.success(mensagem_sucesso)
        if any((filtro_nome.strip(), filtro_email.strip(), filtro_status != "Todos")):
            st.caption("A consulta mantém os filtros selecionados. Ajuste-os para localizar a nova OS.")

    if enviado:
        sucesso, mensagem = processar_cadastro(nome, endereco, email, celular, modelo, problema)
        if sucesso:
            # Reconsultar apos a gravacao sem repetir a insercao no rerun.
            st.session_state["_sucesso_cadastro"] = mensagem
            st.session_state["pagina_os"] = 0
            st.rerun()
        else:
            st.error(mensagem)

with editar:
    st.subheader("Editar ou excluir registros")
    st.info("As operações de edição e exclusão serão implementadas na etapa do painel administrativo.")

with indicadores:
    st.subheader("Indicadores das ordens de serviço")
    st.info("As contagens por status e o gráfico serão implementados após a consulta ao banco.")
