"""Conexao, validacoes e CRUD compartilhados pelos aplicativos TechFix.

As funcoes de consulta devolvem dicionarios/listas, sem dependencia de pandas.
As consultas paginadas usam limite=100 e deslocamento=0 por padrao.
O cadastro de cliente e a abertura da OS sao requisicoes separadas: se a OS
falhar, o cliente criado permanece disponivel para uma nova tentativa.
"""

import logging
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client


load_dotenv(Path(__file__).resolve().parent / ".env")
LOGGER = logging.getLogger(__name__)

VARIAVEIS_SUPABASE = (
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_AUTH_EMAIL",
    "SUPABASE_AUTH_PASSWORD",
)

STATUS_OS = ("Aberto", "Em análise", "Aguardando peça", "Concluído", "Entregue")
COLUNAS_CLIENTE = "id,nome,endereco,email,celular_whatsapp,data_cadastro"
COLUNAS_ORDEM = (
    "id,cliente_id,modelo_computador,problema_relatado,status,"
    "data_abertura,data_atualizacao"
)
# !inner faz os filtros do cliente tambem restringirem as OS retornadas.
COLUNAS_ORDEM_COM_CLIENTE = (
    f"{COLUNAS_ORDEM},cliente:clientes!inner({COLUNAS_CLIENTE})"
)


class ErroTechFix(Exception):
    """Erro de acesso ou persistencia adequado para apresentar na interface."""


class ErroValidacaoTechFix(ValueError):
    """Validacao conhecida; continua compativel com except ValueError existente."""


MENSAGEM_ERRO_GENERICO = (
    "Não foi possível concluir a operação. "
    "Tente novamente mais tarde ou contate a equipe responsável."
)


def mensagem_erro_usuario(erro: Exception) -> str:
    """Exibe somente mensagens conhecidas; nunca converte erro inesperado em texto."""
    if isinstance(erro, (ErroValidacaoTechFix, ErroTechFix)):
        return str(erro)
    # Registrar somente o tipo: str(erro), repr(erro) e traceback podem ter segredos.
    LOGGER.error("Falha inesperada na operação (%s).", type(erro).__name__)
    return MENSAGEM_ERRO_GENERICO


def configuracao_disponivel() -> bool:
    """Verifica preenchimento, sem autenticar nem consultar o banco."""
    return all(os.getenv(nome, "").strip() for nome in VARIAVEIS_SUPABASE)


@lru_cache(maxsize=1)
def obter_conexao() -> Client:
    """Autentica a conta tecnica e reutiliza o cliente no processo Python."""
    if not configuracao_disponivel():
        raise ErroTechFix(
            "O serviço está temporariamente indisponível. "
            "Contate a equipe responsável."
        )
    try:
        cliente = create_client(
            os.environ["SUPABASE_URL"].strip(),
            os.environ["SUPABASE_KEY"].strip(),
        )
        resposta = cliente.auth.sign_in_with_password({
            "email": os.environ["SUPABASE_AUTH_EMAIL"].strip().lower(),
            "password": os.environ["SUPABASE_AUTH_PASSWORD"],
        })
        if resposta.user is None or resposta.session is None:
            LOGGER.error("Autenticação sem usuário ou sessão.")
            raise ErroTechFix("Não foi possível acessar o serviço. Tente novamente mais tarde.")
        return cliente
    except ErroTechFix:
        raise
    except Exception as exc:
        LOGGER.error("Falha na autenticação (%s).", type(exc).__name__)
        raise ErroTechFix(
            "Não foi possível acessar o serviço. Tente novamente mais tarde."
        ) from exc


def _texto_obrigatorio(valor: str, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ErroValidacaoTechFix(f"Preencha o campo {campo}.")
    return valor.strip()


def normalizar_email(email: str) -> str:
    """Remove espacos nas extremidades, converte para minusculas e valida."""
    email = _texto_obrigatorio(email, "e-mail").lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ErroValidacaoTechFix("Informe um e-mail válido, como cliente@example.com.")
    return email


def _validar_celular(celular: str) -> str:
    celular = _texto_obrigatorio(celular, "celular/WhatsApp")
    if not re.fullmatch(r"[0-9]{10,13}", celular):
        raise ErroValidacaoTechFix("O celular deve conter somente números, de 10 a 13 dígitos.")
    return celular


def _validar_id(valor: int, campo: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < 1:
        raise ErroValidacaoTechFix(f"Informe {campo} como um número inteiro e positivo.")
    return valor


def _validar_status(status: str) -> str:
    status = _texto_obrigatorio(status, "status")
    if status not in STATUS_OS:
        raise ErroValidacaoTechFix("Selecione um dos cinco status permitidos para a OS.")
    return status


def _filtro_texto(valor: str | None, campo: str) -> str | None:
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise ErroValidacaoTechFix(f"O filtro {campo} deve ser um texto.")
    return valor.strip() or None


def _validar_paginacao(limite: int, deslocamento: int) -> None:
    if isinstance(limite, bool) or not isinstance(limite, int) or not 1 <= limite <= 1000:
        raise ErroValidacaoTechFix("O limite deve ser um inteiro entre 1 e 1000.")
    if isinstance(deslocamento, bool) or not isinstance(deslocamento, int) or deslocamento < 0:
        raise ErroValidacaoTechFix("O deslocamento deve ser um inteiro maior ou igual a zero.")


def validar_cliente(
    nome: str, endereco: str, email: str, celular_whatsapp: str
) -> dict[str, str]:
    """Valida todos os campos cadastrais antes de qualquer chamada ao banco."""
    return {
        "nome": _texto_obrigatorio(nome, "nome"),
        "endereco": _texto_obrigatorio(endereco, "endereço"),
        "email": normalizar_email(email),
        "celular_whatsapp": _validar_celular(celular_whatsapp),
    }


def _validar_dados_ordem(
    modelo_computador: str, problema_relatado: str, status: str = "Aberto"
) -> dict[str, str]:
    return {
        "modelo_computador": _texto_obrigatorio(modelo_computador, "modelo do computador"),
        "problema_relatado": _texto_obrigatorio(problema_relatado, "problema relatado"),
        "status": _validar_status(status),
    }


def validar_cadastro(
    nome: str, endereco: str, email: str, celular_whatsapp: str,
    modelo_computador: str, problema_relatado: str,
) -> dict[str, str]:
    """Mantem a assinatura usada pelos formularios e devolve seis campos."""
    dados = validar_cliente(nome, endereco, email, celular_whatsapp)
    ordem = _validar_dados_ordem(modelo_computador, problema_relatado)
    dados.update({campo: ordem[campo] for campo in ("modelo_computador", "problema_relatado")})
    return dados


def _executar(consulta, mensagem: str, *, duplicidade: str | None = None,
              vinculo: str | None = None) -> list[dict]:
    """Centraliza falhas de API sem exibir credenciais ou a resposta completa."""
    try:
        return consulta.execute().data or []
    except Exception as exc:
        codigo = str(getattr(exc, "code", ""))
        if codigo == "23505" and duplicidade:
            mensagem = duplicidade
        elif codigo in ("23503", "23001") and vinculo:
            mensagem = vinculo
        registrar = LOGGER.warning if codigo in ("23505", "23503", "23001") else LOGGER.error
        registrar("Falha em operação de dados (%s; código %s).",
                  type(exc).__name__, codigo or "não informado")
        raise ErroTechFix(mensagem) from exc


def _primeiro(registros: list[dict], mensagem: str) -> dict:
    if not registros:
        raise ErroTechFix(mensagem)
    return registros[0]


def buscar_cliente_por_email(email: str) -> dict | None:
    """Busca exata pelo e-mail normalizado; devolve None se nao houver linha visivel."""
    email = normalizar_email(email)
    dados = _executar(
        obter_conexao().table("clientes").select(COLUNAS_CLIENTE).eq("email", email).limit(1),
        "Não foi possível buscar o cliente por e-mail.",
    )
    return dados[0] if dados else None


def buscar_cliente_por_id(cliente_id: int) -> dict | None:
    """Devolve o cliente visivel ou None."""
    cliente_id = _validar_id(cliente_id, "o ID do cliente")
    dados = _executar(
        obter_conexao().table("clientes").select(COLUNAS_CLIENTE).eq("id", cliente_id).limit(1),
        "Não foi possível buscar o cliente pelo ID.",
    )
    return dados[0] if dados else None


def criar_cliente(
    nome: str, endereco: str, email: str, celular_whatsapp: str
) -> dict:
    """Cria um cliente; um e-mail ja cadastrado gera ErroTechFix."""
    dados = validar_cliente(nome, endereco, email, celular_whatsapp)
    resposta = _executar(
        obter_conexao().table("clientes").insert(dados).select(COLUNAS_CLIENTE),
        "Não foi possível cadastrar o cliente. Tente novamente mais tarde.",
        duplicidade="Já existe um cliente com esse e-mail.",
    )
    return _primeiro(resposta, "Não foi possível confirmar o cadastro do cliente.")


def obter_ou_criar_cliente(
    nome: str, endereco: str, email: str, celular_whatsapp: str
) -> dict:
    """Reutiliza o cliente sem sobrescrever seus dados; evita duplicidade concorrente."""
    dados = validar_cliente(nome, endereco, email, celular_whatsapp)
    existente = buscar_cliente_por_email(dados["email"])
    if existente is not None:
        return existente
    # ON CONFLICT DO NOTHING protege inclusive duas requisicoes simultaneas.
    _executar(
        obter_conexao().table("clientes").upsert(
            dados, on_conflict="email", ignore_duplicates=True
        ),
        "Não foi possível cadastrar ou reutilizar o cliente.",
    )
    cliente = buscar_cliente_por_email(dados["email"])
    if cliente is None:
        raise ErroTechFix("Não foi possível confirmar o cadastro do cliente.")
    return cliente


def criar_ordem(
    cliente_id: int, modelo_computador: str, problema_relatado: str,
    *, status: str = "Aberto",
) -> dict:
    """Cria uma OS para um cliente existente e devolve o registro."""
    cliente_id = _validar_id(cliente_id, "o ID do cliente")
    dados = _validar_dados_ordem(modelo_computador, problema_relatado, status)
    dados["cliente_id"] = cliente_id
    resposta = _executar(
        obter_conexao().table("ordens_servico").insert(dados).select(COLUNAS_ORDEM),
        "Não foi possível cadastrar a ordem de serviço. Tente novamente mais tarde.",
        vinculo="O cliente informado não existe. Selecione um cliente válido.",
    )
    return _primeiro(resposta, "Não foi possível confirmar o cadastro da ordem de serviço.")


def cadastrar_ordem(
    nome: str, endereco: str, email: str, celular_whatsapp: str,
    modelo_computador: str, problema_relatado: str,
) -> int:
    """Fluxo dos formularios: validar tudo, reutilizar/criar cliente e abrir OS."""
    dados = validar_cadastro(
        nome, endereco, email, celular_whatsapp, modelo_computador, problema_relatado
    )
    cliente = obter_ou_criar_cliente(
        dados["nome"], dados["endereco"], dados["email"], dados["celular_whatsapp"]
    )
    ordem = criar_ordem(
        int(cliente["id"]), dados["modelo_computador"], dados["problema_relatado"]
    )
    numero_os = ordem.get("id")
    if isinstance(numero_os, bool) or not isinstance(numero_os, int) or numero_os < 1:
        LOGGER.error("Cadastro da OS sem identificador válido na resposta.")
        raise ErroTechFix("Não foi possível confirmar o cadastro da ordem de serviço.")
    return numero_os


def consultar_clientes(
    *, nome: str | None = None, email: str | None = None,
    limite: int = 100, deslocamento: int = 0,
) -> list[dict]:
    """Consulta uma pagina ordenada por ID; nome parcial e e-mail exato."""
    _validar_paginacao(limite, deslocamento)
    nome = _filtro_texto(nome, "nome")
    email = _filtro_texto(email, "e-mail")
    if email is not None:
        email = normalizar_email(email)
    consulta = obter_conexao().table("clientes").select(COLUNAS_CLIENTE)
    if nome is not None:
        consulta = consulta.ilike("nome", f"%{nome}%")
    if email is not None:
        consulta = consulta.eq("email", email)
    return _executar(
        consulta.order("id").range(deslocamento, deslocamento + limite - 1),
        "Não foi possível consultar os clientes.",
    )


def consultar_ordens(
    *, nome: str | None = None, email: str | None = None, status: str | None = None,
    cliente_id: int | None = None, numero_os: int | None = None,
    limite: int = 100, deslocamento: int = 0,
) -> list[dict]:
    """Consulta uma pagina de OS; cada resultado inclui os dados em 'cliente'."""
    _validar_paginacao(limite, deslocamento)
    nome = _filtro_texto(nome, "nome")
    email = _filtro_texto(email, "e-mail")
    status = _filtro_texto(status, "status")
    if email is not None:
        email = normalizar_email(email)
    if status is not None:
        status = _validar_status(status)
    if cliente_id is not None:
        cliente_id = _validar_id(cliente_id, "o ID do cliente")
    if numero_os is not None:
        numero_os = _validar_id(numero_os, "o número da OS")
    consulta = obter_conexao().table("ordens_servico").select(COLUNAS_ORDEM_COM_CLIENTE)
    if nome is not None:
        consulta = consulta.ilike("cliente.nome", f"%{nome}%")
    if email is not None:
        consulta = consulta.eq("cliente.email", email)
    if status is not None:
        consulta = consulta.eq("status", status)
    if cliente_id is not None:
        consulta = consulta.eq("cliente_id", cliente_id)
    if numero_os is not None:
        consulta = consulta.eq("id", numero_os)
    return _executar(
        consulta.order("id", desc=True).range(deslocamento, deslocamento + limite - 1),
        "Não foi possível consultar as ordens de serviço.",
    )


def buscar_ordem_por_id(numero_os: int) -> dict | None:
    """Devolve a OS com o cliente associado ou None."""
    numero_os = _validar_id(numero_os, "o número da OS")
    ordens = consultar_ordens(numero_os=numero_os, limite=1)
    return ordens[0] if ordens else None


def consultar_totais_por_status() -> dict[str, int]:
    """Conta todas as OS visiveis a conta autenticada, sem limitar a uma pagina.

    HEAD com count=exact devolve o total sem transferir os registros. Uma
    contagem ausente ou uma falha invalida todo o resultado, nunca vira zero.
    """
    try:
        conexao = obter_conexao()
        totais = {}
        for status in STATUS_OS:
            resposta = (
                conexao.table("ordens_servico")
                .select("id", count="exact", head=True)
                .eq("status", status)
                .execute()
            )
            total = resposta.count
            if isinstance(total, bool) or not isinstance(total, int) or total < 0:
                raise RuntimeError("Resposta sem contagem válida.")
            totais[status] = total
        return totais
    except ErroTechFix:
        raise
    except Exception as exc:
        LOGGER.error("Falha na consulta de indicadores (%s).", type(exc).__name__)
        raise ErroTechFix(
            "Não foi possível atualizar os indicadores. Tente novamente mais tarde."
        ) from exc


def atualizar_cliente(
    cliente_id: int, *, nome: str | None = None, endereco: str | None = None,
    email: str | None = None, celular_whatsapp: str | None = None,
) -> dict:
    """Edita somente campos informados; None preserva o valor e texto vazio e rejeitado."""
    cliente_id = _validar_id(cliente_id, "o ID do cliente")
    dados = {}
    if nome is not None:
        dados["nome"] = _texto_obrigatorio(nome, "nome")
    if endereco is not None:
        dados["endereco"] = _texto_obrigatorio(endereco, "endereço")
    if email is not None:
        dados["email"] = normalizar_email(email)
    if celular_whatsapp is not None:
        dados["celular_whatsapp"] = _validar_celular(celular_whatsapp)
    if not dados:
        raise ErroValidacaoTechFix("Informe pelo menos um campo do cliente para alterar.")
    resposta = _executar(
        obter_conexao().table("clientes").update(dados).eq("id", cliente_id)
        .select(COLUNAS_CLIENTE),
        "Não foi possível atualizar o cliente.",
        duplicidade="Esse e-mail já pertence a outro cliente.",
    )
    return _primeiro(resposta, "Cliente não encontrado ou sem permissão para edição.")


def atualizar_ordem(
    numero_os: int, *, status: str | None = None,
    modelo_computador: str | None = None, problema_relatado: str | None = None,
) -> dict:
    """Edita a OS e envia data_atualizacao em UTC no mesmo UPDATE."""
    numero_os = _validar_id(numero_os, "o número da OS")
    dados = {}
    if status is not None:
        dados["status"] = _validar_status(status)
    if modelo_computador is not None:
        dados["modelo_computador"] = _texto_obrigatorio(
            modelo_computador, "modelo do computador"
        )
    if problema_relatado is not None:
        dados["problema_relatado"] = _texto_obrigatorio(
            problema_relatado, "problema relatado"
        )
    if not dados:
        raise ErroValidacaoTechFix("Informe pelo menos um campo da OS para alterar.")
    dados["data_atualizacao"] = datetime.now(timezone.utc).isoformat()
    resposta = _executar(
        obter_conexao().table("ordens_servico").update(dados).eq("id", numero_os)
        .select(COLUNAS_ORDEM),
        "Não foi possível atualizar a OS.",
    )
    return _primeiro(resposta, "OS não encontrada ou sem permissão para edição.")


def excluir_ordem(numero_os: int) -> dict:
    """Exclui somente a OS indicada e devolve o registro removido."""
    numero_os = _validar_id(numero_os, "o número da OS")
    resposta = _executar(
        obter_conexao().table("ordens_servico").delete().eq("id", numero_os),
        "Não foi possível excluir a OS.",
    )
    return _primeiro(resposta, "OS não encontrada ou sem permissão para exclusão.")


def excluir_cliente(cliente_id: int) -> dict:
    """Exclui somente cliente sem OS; a FK RESTRICT e a garantia contra concorrencia."""
    cliente_id = _validar_id(cliente_id, "o ID do cliente")
    resposta = _executar(
        obter_conexao().table("clientes").delete().eq("id", cliente_id),
        "Não foi possível excluir o cliente.",
        vinculo="Este cliente possui OS vinculadas. Exclua essas ordens antes de excluir o cliente.",
    )
    return _primeiro(resposta, "Cliente não encontrado ou sem permissão para exclusão.")
