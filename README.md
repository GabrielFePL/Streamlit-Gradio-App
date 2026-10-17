# TechFix Informática

Gestão de clientes e ordens de serviço com Python, Supabase, Gradio e Streamlit.

O Gradio recebe os cadastros de atendimento, o Streamlit oferece o painel administrativo e o Supabase mantém os dados. Os dois aplicativos reutilizam a conexão, a autenticação, as validações e as operações do módulo `db.py`.

## Arquivos do projeto

| Arquivo ou pasta | Finalidade |
| --- | --- |
| `app_gradio.py` | Formulário de abertura de OS, com link público temporário. |
| `app_streamlit.py` | Consulta, cadastro, edição, exclusão, indicadores e exportação dos indicadores em CSV. |
| `db.py` | Acesso compartilhado ao Supabase e regras de validação e persistência. |
| `sql/schema.sql` | Tabelas, restrições, índice, permissões e políticas RLS. |
| `requirements.txt` | Dependências Python do projeto. |
| `.env.example` | Nomes das quatro variáveis de configuração, com valores vazios. |
| `.env` | Configuração local, mantida fora do repositório. |
| `.gitignore` | Exclusão de credenciais, ambiente virtual e caches do versionamento. |
| `evidencias/` | Capturas de tela da validação com dados fictícios. |

## 1. Preparar o ambiente Python

Instale o Python 3.11 e obtenha o código do repositório por clone ou download do ZIP. Os comandos deste README usam o PowerShell no Windows e consideram a pasta `Downloads\techfix`; ajuste o caminho se necessário.

```powershell
Set-Location "$env:USERPROFILE\Downloads\techfix"
py -3.11 --version
py -3.11 -m venv .venv
```

Instale as dependências no ambiente criado:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

O `requirements.txt` inclui `gradio`, `streamlit`, `supabase`, `python-dotenv` e `pandas`. O uso do caminho completo do executável dispensa ativar a `.venv` e garante que instalação e execução utilizem o mesmo ambiente.

## 2. Criar o projeto e a conta técnica no Supabase

1. Crie um projeto no [Supabase](https://supabase.com/) e aguarde sua disponibilização.
2. Nas configurações de conexão/API do projeto, copie a **Project URL** e uma chave **publishable** ou **anon** legada.
3. Em **Authentication → Users**, crie manualmente uma conta técnica com e-mail e senha próprios do projeto. Confirme o e-mail dessa conta; quando disponível no cadastro manual, utilize a opção de confirmação automática.
4. Abra o registro do usuário e copie seu **User UID/ID**, no formato UUID. Esse é o ID usado nas políticas RLS; ele é diferente do ID numérico de um cliente.

A estratégia adotada é autenticar o cliente Python com essa conta técnica, por e-mail e senha, utilizando a chave pública do projeto. A chave identifica o projeto; o token do usuário autenticado identifica a conta técnica.

Use a chave **anon ou publishable** em `SUPABASE_KEY`. Chaves `service_role` ou secret possuem privilégios que podem ignorar a RLS e não fazem parte desta estratégia.

A autenticação acontece no backend dos aplicativos. A conta técnica concede ao processo Python acesso às duas tabelas; essa configuração não implementa login individual dos operadores nas telas. O painel administrativo deve ser acessado em ambiente controlado.

## 3. Informar o UID nas políticas e executar o schema

Abra `sql/schema.sql` e encontre esta declaração:

```sql
v_uid uuid := 'SUBSTITUA_PELO_UID_DA_CONTA_TECNICA'::uuid;
```

Substitua `SUBSTITUA_PELO_UID_DA_CONTA_TECNICA` pelo UID copiado de **Authentication → Users**, mantendo as aspas e o `::uuid`. No script do projeto, esse valor é informado uma vez e utilizado para gerar as políticas das duas tabelas.

Em seguida:

1. Abra o **SQL Editor** do mesmo projeto Supabase.
2. Crie uma consulta, cole o conteúdo completo de `sql/schema.sql` já configurado e execute.
3. Confira as tabelas `public.clientes` e `public.ordens_servico` no Table Editor.
4. Confira a saída final do script: devem existir **oito políticas**, quatro por tabela, com RLS ativa e o UID informado nas condições.

O script cria as tabelas ausentes, suas restrições e o índice de `cliente_id`. Ele também revoga o acesso das requisições sem autenticação e concede as quatro operações necessárias ao papel `authenticated`, sujeitas às políticas por UID.

As políticas permitem **SELECT, INSERT, UPDATE e DELETE somente para a conta técnica definida**. As condições usam `auth.uid()`, obtido do token validado pelo Supabase. Outra conta autenticada não corresponde ao UID autorizado.

Reexecutar esse schema preserva os registros, mas substitui as políticas das duas tabelas. A criação com `IF NOT EXISTS` não migra a estrutura de tabelas que já existam com colunas ou restrições diferentes. Para configurar outro projeto Supabase, crie a conta naquele projeto e atualize seu UID antes de executar.

O SQL Editor usa acesso administrativo. Validar uma consulta por ele não confirma as permissões do cliente Python; faça a validação final pelos aplicativos.

## 4. Preencher o arquivo .env local

O `.env.example` deve conter somente os nomes, com valores vazios:

```dotenv
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_AUTH_EMAIL=
SUPABASE_AUTH_PASSWORD=
```

Crie a configuração local a partir do exemplo, preservando um `.env` que já esteja preenchido:

```powershell
if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env"
}
notepad .\.env
```

Preencha os quatro valores reais do seu projeto. O exemplo abaixo contém marcadores que devem ser substituídos:

```dotenv
SUPABASE_URL=https://SEU-PROJETO.supabase.co
SUPABASE_KEY=SUA_CHAVE_ANON_OU_PUBLISHABLE
SUPABASE_AUTH_EMAIL=EMAIL_DA_CONTA_TECNICA
SUPABASE_AUTH_PASSWORD="SENHA_DA_CONTA_TECNICA"
```

| Variável | Valor esperado |
| --- | --- |
| `SUPABASE_URL` | Project URL do projeto em que o schema foi executado. |
| `SUPABASE_KEY` | Chave anon ou publishable desse mesmo projeto. |
| `SUPABASE_AUTH_EMAIL` | E-mail da conta técnica criada manualmente. |
| `SUPABASE_AUTH_PASSWORD` | Senha dessa conta técnica. Utilize aspas se houver espaços ou `#`. |

O `db.py` carrega o `.env` localizado na mesma pasta do módulo. O UID fica nas políticas do `schema.sql`; não é necessário criar outra variável de ambiente para ele.

Mantenha os valores reais somente no `.env` local. O `.gitignore` deve excluir, pelo menos:

```gitignore
.env
.streamlit/secrets.toml
.venv/
__pycache__/
*.pyc
```

Depois de alterar as credenciais, reinicie os dois processos Python para estabelecer a conexão com a configuração atualizada.

## 5. Executar os aplicativos

Confira a sintaxe dos arquivos:

```powershell
.\.venv\Scripts\python.exe -m py_compile .\db.py .\app_gradio.py .\app_streamlit.py
```

Abra dois terminais PowerShell. Em cada um, entre na pasta do projeto.

**Terminal 1 — Gradio:**

```powershell
Set-Location "$env:USERPROFILE\Downloads\techfix"
.\.venv\Scripts\python.exe .\app_gradio.py
```

**Terminal 2 — Streamlit:**

```powershell
Set-Location "$env:USERPROFILE\Downloads\techfix"
.\.venv\Scripts\python.exe -m streamlit run .\app_streamlit.py
```

Abra os endereços informados em cada terminal. Normalmente, o Gradio usa [http://127.0.0.1:7860](http://127.0.0.1:7860) e o Streamlit usa [http://localhost:8501](http://localhost:8501); utilize a porta efetivamente exibida na execução.

Para encerrar um aplicativo, pressione `Ctrl+C` no terminal correspondente.

## 6. Usar o Gradio e o link temporário

Preencha nome, endereço, e-mail, celular/WhatsApp, modelo do computador e problema relatado. Utilize somente números no celular, com 10 a 13 dígitos, e descreva o problema no campo de várias linhas.

Clique em **Cadastrar**. A confirmação apresenta o número da OS somente depois de sua criação, com status inicial **Aberto**. O botão **Limpar** esvazia os seis campos e a mensagem de resultado.

O aplicativo inicia com `share=True` e apresenta no terminal uma URL pública temporária. Copie essa URL e abra no navegador do celular para testar o formulário.

**Mantenha o computador ligado, conectado à internet e com o processo Gradio em execução durante todo o acesso pelo link.** Fechar o terminal, pressionar `Ctrl+C` ou suspender o computador interrompe o acesso. O link tem validade limitada; quando necessário, inicie novamente o aplicativo e copie o novo endereço exibido.

## 7. Usar o painel Streamlit

| Aba | Operação |
| --- | --- |
| **Consultar** | Exibe OS e dados do cliente. Filtre pelo nome parcial, e-mail completo e status na barra lateral. A listagem possui páginas de até 50 registros; use Anterior/Próxima, Limpar filtros e Atualizar lista. |
| **Cadastrar** | Abre uma nova OS com os mesmos campos e validações do Gradio. |
| **Editar/Excluir** | Escolha OS ou Cliente, informe seu ID e clique em Buscar por ID. Para OS, altere o status e clique em Salvar status. Para Cliente, edite endereço, e-mail e celular e clique em Salvar dados do cliente. |
| **Indicadores** | Exibe os cinco totais por status e o gráfico, incluindo valores zero. Atualizar indicadores busca novamente os dados. Exportar indicadores em CSV baixa `techfix_indicadores.csv`. |

Os status permitidos são **Aberto**, **Em análise**, **Aguardando peça**, **Concluído** e **Entregue**.

Os filtros da barra lateral se aplicam à consulta. A busca por ID e os indicadores consideram os registros disponíveis para a conta técnica, independentemente desses filtros. O CSV contém as colunas `Status` e `Total de OS`, com cinco linhas, separador ponto e vírgula e UTF-8 com BOM para preservar os acentos.

Depois de cadastrar, editar ou excluir com sucesso no painel, a consulta e os indicadores são reconsultados. Para refletir mudanças feitas pelo Gradio ou por outra sessão, utilize **Atualizar lista** ou **Atualizar indicadores**.

## 8. Regras de cadastro e exclusão

O e-mail é normalizado com remoção de espaços nas extremidades e conversão para minúsculas. Campos obrigatórios vazios e celular inválido são rejeitados antes do envio.

Se o e-mail já existir, o cadastro reutiliza o ID do cliente e cria outra OS. Os dados cadastrais existentes são preservados; suas alterações devem ser feitas em **Editar/Excluir**. Se a criação do cliente ocorrer e a abertura da OS falhar, esse cliente permanece disponível para uma nova tentativa com o mesmo e-mail.

Cada edição de OS também atualiza `data_atualizacao` pelo Python. As datas são armazenadas com fuso horário, e a consulta do painel as apresenta no fuso de Brasília.

| Exclusão | Comportamento |
| --- | --- |
| OS | Remove somente a OS selecionada e preserva o cliente. |
| Cliente sem OS | Remove o cliente após a confirmação. |
| Cliente com OS | É bloqueada pela chave estrangeira com `ON DELETE RESTRICT`, inclusive se as ordens estiverem concluídas ou entregues. |

Para excluir, carregue o registro pelo ID, confira seus dados e marque a confirmação. O botão de exclusão é habilitado para aquele registro. Trocar o ID/tipo, buscar novamente ou salvar uma edição com sucesso exige nova confirmação.

As exclusões são permanentes. Para remover todo o cadastro, exclua cada OS vinculada, confirmando individualmente, e depois o cliente. O banco impede a exclusão do cliente enquanto existir qualquer OS vinculada; mudar o status não remove esse vínculo.

As operações apresentam mensagens amigáveis. Credenciais e detalhes internos de exceções ficam fora das telas e do CSV.

## 9. Validação e problemas comuns

Utilize dados fictícios. Cadastre uma OS pelo Gradio, confira-a no Streamlit, abra outra com o mesmo e-mail e confirme que há um cliente com duas OS. Altere um status, confira os indicadores e exporte o CSV. Teste o bloqueio de exclusão do cliente antes de remover suas OS de teste.

| Situação | Como verificar |
| --- | --- |
| `No module named streamlit` ou outro pacote | Execute pelo Python da `.venv` e instale `requirements.txt` nesse mesmo ambiente. |
| Serviço indisponível ou falha de autenticação | Confira as quatro variáveis, o projeto, o e-mail confirmado e a senha da conta técnica. Reinicie os aplicativos após alterar o `.env`. |
| Falha no schema por UID inválido/inexistente | Substitua o marcador pelo UUID da conta criada no mesmo projeto e confirme seu e-mail. |
| Permissão negada ou registros não aparecem | Confira a autenticação, o UID gravado nas políticas, a RLS e os filtros ativos. |
| Cliente com OS não pode ser excluído | O bloqueio preserva os vínculos. Remova suas OS primeiro se a exclusão completa for necessária. |
| Link do Gradio não abre no celular | Confira se o processo local continua ativo, o computador está conectado e a URL temporária ainda é válida. |

## Referências

- [Ambientes virtuais do Python 3.11](https://docs.python.org/3.11/library/venv.html)
- [Chaves de API do Supabase](https://supabase.com/docs/guides/getting-started/api-keys)
- [Row Level Security do Supabase](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Autenticação Python com e-mail e senha](https://supabase.com/docs/reference/python/auth-signinwithpassword)
- [Compartilhamento de aplicativos Gradio](https://www.gradio.app/guides/sharing-your-app)
- [Execução do Streamlit](https://docs.streamlit.io/develop/api-reference/cli/run)
