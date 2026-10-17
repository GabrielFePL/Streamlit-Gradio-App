"""Interface inicial de atendimento da TechFix."""

import gradio as gr

from db import ErroTechFix, cadastrar_ordem, configuracao_disponivel


def cadastrar(nome, endereco, email, celular, modelo, problema):
    """Encaminha o cadastro ao módulo compartilhado e apresenta o resultado."""
    try:
        numero_os = cadastrar_ordem(nome, endereco, email, celular, modelo, problema)
        return f"Ordem de serviço nº {numero_os} cadastrada com sucesso. Status: Aberto."
    except (ValueError, ErroTechFix) as exc:
        return str(exc)


def criar_interface():
    with gr.Blocks(title="TechFix Informática") as app:
        gr.Markdown("# TechFix Informática\nPreencha os dados para abrir uma ordem de serviço.")
        if not configuracao_disponivel():
            gr.Markdown("**Configuração inicial:** a conexão com o banco será preparada na próxima etapa.")

        with gr.Row():
            with gr.Column():
                nome = gr.Textbox(label="Nome do Cliente", placeholder="Nome completo")
                endereco = gr.Textbox(label="Endereço", placeholder="Rua, número, bairro e cidade")
                email = gr.Textbox(label="E-mail", placeholder="cliente@example.com")
                celular = gr.Textbox(label="Celular/WhatsApp", placeholder="11999998888")
            with gr.Column():
                modelo = gr.Textbox(label="Modelo do Computador", placeholder="Marca e modelo")
                problema = gr.Textbox(
                    label="Problema Apresentado",
                    placeholder="Descreva o defeito observado.",
                    lines=6,
                )

        with gr.Row():
            botao_cadastrar = gr.Button("Cadastrar", variant="primary")
            botao_limpar = gr.Button("Limpar")
        retorno = gr.Textbox(label="Resultado", interactive=False, lines=3)
        campos = [nome, endereco, email, celular, modelo, problema]

        botao_cadastrar.click(fn=cadastrar, inputs=campos, outputs=retorno)
        botao_limpar.click(fn=lambda: [""] * 7, outputs=campos + [retorno])
    return app


if __name__ == "__main__":
    criar_interface().launch(share=True)
