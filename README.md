# TechFix Informática

Sistema acadêmico de ordens de serviço da Atividade Aula 2. O projeto utiliza Gradio para atendimento, Streamlit para administração e Supabase para persistência.

## Conteúdo desta entrega

Esta base corresponde ao segundo conjunto de atividades da etapa 1. Os formulários iniciais e as funções compartilhadas já estão preparados. As tabelas, as credenciais e as políticas de acesso serão configuradas nas próximas etapas.

| Arquivo | Responsabilidade |
|---|---|
| `app_gradio.py` | Formulário com os seis campos, botão Cadastrar, botão Limpar e retorno ao usuário. |
| `app_streamlit.py` | Quatro abas e formulário inicial de cadastro; as demais abas indicam funções ainda pendentes. |
| `db.py` | Configuração, autenticação, validações e abertura de OS compartilhadas. |
| `requirements.txt` | As cinco dependências diretas do projeto. |
| `README.md` | Instruções de execução e situação da implementação. |

As pastas `sql` e `evidencias` e o ambiente `.venv` foram criados na atividade anterior e permanecem no projeto.

## Instalação no PowerShell

Execute na pasta `techfix`. Se a `.venv` já existe, utilize-a:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

Para um ambiente novo, crie a `.venv` antes de instalar as dependências:

```powershell
py -3.11 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

## Execução

Em um terminal PowerShell:

```powershell
& ".\.venv\Scripts\python.exe" app_gradio.py
```

Em outro terminal, aberto na mesma pasta:

```powershell
& ".\.venv\Scripts\python.exe" -m streamlit run app_streamlit.py
```

Abra os endereços exibidos nos terminais. O Gradio solicita um link temporário público por meio de `share=True`; sua criação depende da conexão com os servidores do Gradio. O computador e o processo precisam permanecer ligados para utilizar esse link. Para encerrar cada aplicativo, pressione `Ctrl+C` em seu terminal.

## Comportamento nesta etapa

- Os aplicativos abrem sem credenciais e exibem um aviso de configuração pendente.
- Os campos obrigatórios, o formato do e-mail e o celular são validados antes de qualquer conexão.
- O celular aceita somente dígitos de 0 a 9, entre 10 e 13 caracteres, incluindo o DDD.
- O e-mail é convertido para minúsculas e tem os espaços externos removidos.
- Um envio válido ainda retorna aviso de configuração pendente enquanto o Supabase não estiver preparado.
- Nenhum cadastro é simulado e não há armazenamento local ou sucesso fictício.

## Configuração das próximas etapas

O módulo `db.py` lê as seguintes variáveis do ambiente ou de um arquivo `.env` na pasta do projeto:

```dotenv
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_AUTH_EMAIL=
SUPABASE_AUTH_PASSWORD=
```

A estratégia prevista utiliza uma chave `anon` ou `publishable`, uma conta técnica criada manualmente no Supabase Auth e políticas RLS que autorizam exclusivamente o ID dessa conta. Preencher variáveis não comprova que autenticação, tabelas e permissões estejam corretas. Reinicie os aplicativos após alterar a configuração.

O banco deverá conter `clientes` e `ordens_servico`, com os campos do enunciado. O e-mail precisa ter uma restrição `UNIQUE`. IDs e datas de cadastro, abertura e atualização devem ter valores padrão no banco. O cadastro consulta o ID do cliente e insere a OS com status `Aberto`.

O cadastro utiliza `upsert` com `on_conflict="email"` e `ignore_duplicates=True`: cria um cliente quando necessário e preserva os dados do cliente já existente. As operações de cliente e OS são chamadas separadas; se a criação da OS falhar, o cliente poderá permanecer cadastrado. A mensagem de sucesso só é apresentada quando o banco retorna o número da OS.

O `.env.example` e o `.gitignore` serão preparados no próximo conjunto da etapa 1. O arquivo `.env` real deve permanecer fora do pacote e do repositório. Use somente dados fictícios nos testes.

## Validação local

```powershell
& ".\.venv\Scripts\python.exe" -m py_compile db.py app_gradio.py app_streamlit.py
& ".\.venv\Scripts\python.exe" -m pip check
```

A compilação verifica sintaxe; não confirma operações no Supabase. Para verificar as telas, execute os dois aplicativos, teste os campos vazios, um e-mail inválido, um telefone com letras e o botão Limpar do Gradio.

O painel administrativo completo, incluindo consultas, filtros, edição, exclusão, indicadores e evidências, será implementado nas etapas seguintes do guia.

## Documentação de apoio

- [Gradio Blocks](https://www.gradio.app/docs/gradio/blocks)
- [Streamlit Forms](https://docs.streamlit.io/develop/api-reference/execution-flow/st.form)
- [Supabase Python](https://supabase.com/docs/reference/python/initializing)
- [Supabase Upsert](https://supabase.com/docs/reference/python/upsert)
