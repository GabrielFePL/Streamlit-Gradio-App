"""Painel TechFix: consulta, cadastro, edição, exclusão e indicadores de OS."""

import re

import pandas as pd
import streamlit as st

st.set_option("client.showErrorDetails", "none")

from db import (
    STATUS_OS,
    ErroValidacaoTechFix,
    atualizar_cliente,
    atualizar_ordem,
    buscar_cliente_por_id,
    buscar_ordem_por_id,
    cadastrar_ordem,
    configuracao_disponivel,
    consultar_ordens,
    consultar_totais_por_status,
    excluir_cliente,
    excluir_ordem,
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


def invalidar_registro_edicao():
    """Uma nova busca nunca herda a confirmação do registro anterior."""
    st.session_state.pop("_registro_edicao", None)
    st.session_state.pop("_mensagem_edicao", None)
    st.session_state["_edicao_versao"] = (
        st.session_state.get("_edicao_versao", 0) + 1
    )


def interpretar_id(texto):
    texto = texto.strip()
    if not re.fullmatch(r"[0-9]{1,19}", texto):
        raise ErroValidacaoTechFix("Informe um ID inteiro e positivo.")
    identificador = int(texto)
    if not 1 <= identificador <= 9223372036854775807:
        raise ErroValidacaoTechFix("Informe um ID inteiro e positivo válido.")
    return identificador


def concluir_edicao(dados, mensagem):
    """Recarregar os campos salvos e a consulta sem repetir a operação."""
    selecao = st.session_state["_registro_edicao"]
    selecao["dados"] = {**selecao["dados"], **dados}
    st.session_state["_edicao_versao"] += 1
    st.session_state["_mensagem_edicao"] = mensagem
    st.session_state["pagina_os"] = 0
    st.rerun()


def mostrar_editor():
    st.caption(
        "Escolha o tipo de registro, informe seu ID e clique em Buscar por ID. "
        "Os IDs estão na aba Consultar; os filtros da consulta não limitam esta busca."
    )
    tipo = st.radio(
        "Tipo de registro", ["OS", "Cliente"], horizontal=True,
        key="edicao_tipo", on_change=invalidar_registro_edicao,
    )
    id_texto = st.text_input(
        "ID do registro", placeholder="Ex.: 12", key="edicao_id",
        on_change=invalidar_registro_edicao,
    )
    if st.button("Buscar por ID", key="edicao_buscar"):
        invalidar_registro_edicao()
        try:
            identificador = interpretar_id(id_texto)
            buscar = buscar_ordem_por_id if tipo == "OS" else buscar_cliente_por_id
            dados = buscar(identificador)
            if dados is None:
                st.warning("OS não encontrada." if tipo == "OS" else "Cliente não encontrado.")
            else:
                st.session_state["_registro_edicao"] = {
                    "tipo": tipo, "busca": id_texto.strip(), "dados": dados,
                }
        except Exception as exc:
            st.error(mensagem_erro_usuario(exc))

    mensagem = st.session_state.pop("_mensagem_edicao", None)
    if mensagem:
        st.success(mensagem)
        st.caption("A aba Consultar foi atualizada e mantém os filtros selecionados.")

    selecao = st.session_state.get("_registro_edicao")
    # Vincular todas as ações ao registro carregado, inclusive se a busca mudar.
    if not selecao or (selecao["tipo"], selecao["busca"]) != (tipo, id_texto.strip()):
        return

    dados = selecao["dados"]
    identificador = dados["id"]
    chave = f"{tipo}_{identificador}_{st.session_state['_edicao_versao']}"

    if tipo == "OS":
        st.subheader(f"OS nº {identificador}")
        cliente = dados["cliente"]
        st.write("ID do cliente:", dados["cliente_id"])
        st.write("Cliente:", cliente["nome"])
        st.write("E-mail:", cliente["email"])
        st.write("Modelo do computador:", dados["modelo_computador"])
        st.write("Problema relatado:", dados["problema_relatado"])
        with st.form(f"form_status_{chave}"):
            status = st.selectbox(
                "Novo status", STATUS_OS,
                index=STATUS_OS.index(dados["status"]), key=f"status_{chave}",
            )
            salvar = st.form_submit_button("Salvar status", type="primary")
        if salvar:
            try:
                atualizado = atualizar_ordem(identificador, status=status)
            except Exception as exc:
                st.error(mensagem_erro_usuario(exc))
            else:
                concluir_edicao(atualizado, f"Status da OS nº {identificador} atualizado com sucesso.")
        st.caption("Para alterar endereço, e-mail ou celular, busque o ID do cliente.")
    else:
        st.subheader(f"Cliente ID {identificador}")
        st.write("Nome:", dados["nome"])
        st.caption("As alterações cadastrais serão exibidas em todas as OS deste cliente.")
        with st.form(f"form_cliente_{chave}"):
            endereco = st.text_input(
                "Endereço do cliente", value=dados["endereco"],
                placeholder="Rua, número, bairro e cidade", key=f"endereco_{chave}",
            )
            email = st.text_input(
                "E-mail do cliente", value=dados["email"],
                placeholder="cliente@example.com", key=f"email_{chave}",
            )
            celular = st.text_input(
                "Celular/WhatsApp do cliente", value=dados["celular_whatsapp"],
                placeholder="11999998888", help="Use somente números, de 10 a 13 dígitos.",
                key=f"celular_{chave}",
            )
            salvar = st.form_submit_button("Salvar dados do cliente", type="primary")
        if salvar:
            try:
                atualizado = atualizar_cliente(
                    identificador, endereco=endereco, email=email,
                    celular_whatsapp=celular,
                )
            except Exception as exc:
                st.error(mensagem_erro_usuario(exc))
            else:
                concluir_edicao(atualizado, f"Cliente ID {identificador} atualizado com sucesso.")

    st.divider()
    st.subheader("Excluir registro")
    if tipo == "OS":
        alvo = f"OS nº {identificador}"
        st.warning("A exclusão da OS é permanente. O cadastro do cliente será preservado.")
    else:
        alvo = f"cliente ID {identificador}"
        st.warning(
            "A exclusão do cliente é permanente e fica bloqueada enquanto houver OS "
            "vinculadas, inclusive concluídas ou entregues. O banco preserva esse "
            "vínculo; mudar o status não libera a exclusão."
        )
        st.caption(
            "Se a remoção de todo o cadastro for necessária, exclua cada OS vinculada "
            "e depois o cliente. Não há exclusão automática das ordens."
        )
    confirmado = st.checkbox(
        f"Confirmo a exclusão de {alvo}.", key=f"confirmar_{chave}",
    )
    if st.button(
        "Excluir OS" if tipo == "OS" else "Excluir cliente",
        disabled=not confirmado, key=f"excluir_{chave}",
    ):
        if not confirmado:
            st.warning("Marque a confirmação antes de excluir o registro.")
        else:
            try:
                excluir = excluir_ordem if tipo == "OS" else excluir_cliente
                excluir(identificador)
            except Exception as exc:
                st.error(mensagem_erro_usuario(exc))
            else:
                invalidar_registro_edicao()
                st.session_state["_mensagem_edicao"] = f"Exclusão de {alvo} realizada com sucesso."
                st.session_state["pagina_os"] = 0
                st.rerun()


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
    if not configurada:
        st.info("A edição estará disponível quando o serviço for configurado.")
    else:
        mostrar_editor()

with indicadores:
    st.subheader("Indicadores das ordens de serviço")
    st.caption("Totais gerais das OS. Os filtros da aba Consultar não alteram estes indicadores.")
    if not configurada:
        st.info("Os indicadores estarão disponíveis quando o serviço for configurado.")
    else:
        st.button("Atualizar indicadores", key="indicadores_atualizar")
        try:
            # Sem cache de dados: cada execucao consulta novamente o banco.
            # Cadastro, edicao e exclusao bem-sucedidos ja provocam st.rerun().
            totais = consultar_totais_por_status()
        except Exception as exc:
            st.error(mensagem_erro_usuario(exc))
        else:
            colunas = st.columns(len(STATUS_OS))
            for coluna, status in zip(colunas, STATUS_OS):
                coluna.metric(label=status, value=totais[status], border=True)

            dados_grafico = pd.DataFrame({
                "Status": list(STATUS_OS),
                "Total de OS": [totais[status] for status in STATUS_OS],
            })
            st.bar_chart(
                dados_grafico, x="Status", y="Total de OS", sort=False,
                x_label="Status", y_label="Quantidade de OS",
                height=360, width="stretch",
            )
            st.caption(f"Total de OS: {sum(totais.values())}")
            st.caption(
                "Os indicadores são reconsultados após salvar ou excluir no painel. "
                "Para consultar alterações feitas em outro aplicativo, clique em Atualizar indicadores."
            )
