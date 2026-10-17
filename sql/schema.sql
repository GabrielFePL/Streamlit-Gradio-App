-- TechFix Informatica - Atividade Aula 2
-- Execute este arquivo completo no SQL Editor do projeto Supabase.
-- Substitua  pelo UID do usuario do Supabase Auth.
-- Nao remove tabelas nem registros. Substitui as policies somente destas duas tabelas.

-- Bloco 1 - Transacao: aplicar a criacao e as permissoes em conjunto.
begin;

-- Bloco 2 - Clientes: identificador automatico e dados obrigatorios.
-- O e-mail e armazenado em minusculas, como ja faz o modulo db.py.
-- UNIQUE(email) permite reaproveitar o cliente no upsert do Python.
create table if not exists public.clientes (
    id bigint generated always as identity primary key,
    nome text not null,
    endereco text not null,
    email text not null,
    celular_whatsapp text not null,
    data_cadastro timestamptz not null default now(),

    constraint clientes_nome_preenchido
        check (length(btrim(nome)) > 0),
    constraint clientes_endereco_preenchido
        check (length(btrim(endereco)) > 0),
    constraint clientes_email_unico
        unique (email),
    constraint clientes_email_formato
        check (email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'),
    constraint clientes_email_normalizado
        check (email = lower(btrim(email))),
    constraint clientes_celular_formato
        check (celular_whatsapp ~ '^[0-9]{10,13}$')
);

-- Bloco 3 - Ordens de servico: um cliente pode possuir varias OS.
-- RESTRICT impede excluir um cliente enquanto houver OS vinculadas.
-- As datas sao preenchidas na insercao. Ao editar uma OS, o Python
-- devera atualizar data_atualizacao; o valor DEFAULT nao faz isso sozinho.
create table if not exists public.ordens_servico (
    id bigint generated always as identity primary key,
    cliente_id bigint not null,
    modelo_computador text not null,
    problema_relatado text not null,
    status text not null default 'Aberto',
    data_abertura timestamptz not null default now(),
    data_atualizacao timestamptz not null default now(),

    constraint ordens_servico_cliente_fk
        foreign key (cliente_id)
        references public.clientes (id)
        on delete restrict,
    constraint ordens_servico_modelo_preenchido
        check (length(btrim(modelo_computador)) > 0),
    constraint ordens_servico_problema_preenchido
        check (length(btrim(problema_relatado)) > 0),
    constraint ordens_servico_status_valido
        check (status in (
            'Aberto', 'Em análise', 'Aguardando peça', 'Concluído', 'Entregue'
        ))
);

-- Bloco 4 - Indice da chave estrangeira para consultas por cliente.
-- As PKs e a restricao UNIQUE ja criam seus proprios indices.
create index if not exists idx_ordens_servico_cliente_id
    on public.ordens_servico (cliente_id);

-- INICIO BLOCO DE SEGURANCA TECHFIX
-- Bloco 5 - Ativar RLS. O SQL Editor administrativo pode ignorar a RLS;
-- os testes reais pela API devem usar a chave anon/publishable e o login tecnico.
alter table public.clientes enable row level security;
alter table public.ordens_servico enable row level security;

-- Bloco 6 - Liberar somente as quatro operacoes necessarias a authenticated.
-- PUBLIC representa todos os papeis do PostgreSQL. Sua revogacao evita
-- que anon receba privilegios de tabela por heranca desse grupo.
-- Os grants permitem tentar a operacao; as policies conferem o UID especifico.
revoke all on table public.clientes, public.ordens_servico
    from public, anon, authenticated;

grant usage on schema public to authenticated;
grant select, insert, update, delete
    on table public.clientes, public.ordens_servico
    to authenticated;

-- Bloco 7 - Permitir a geracao dos IDs para a conta autenticada.
-- As sequences abaixo sao criadas automaticamente pelas colunas identity.
revoke all on sequence public.clientes_id_seq, public.ordens_servico_id_seq
    from public, anon, authenticated;

grant usage on sequence public.clientes_id_seq, public.ordens_servico_id_seq
    to authenticated;

-- Bloco 8 - Policies exclusivas para o UID da conta tecnica.
-- Informe o UID UMA VEZ, na declaracao abaixo. A conta deve existir neste
-- projeto e possuir e-mail confirmado. Um erro desfaz toda a transacao.
-- O SQL dinamico grava o UUID como literal nas oito policies; a aplicacao
-- nao fornece esse UUID ao consultar dados: auth.uid() vem do token validado.
do $techfix_rls$
declare
    v_uid uuid := ''::uuid;
    v_tabela text;
    v_policy record;
begin
    if not exists (
        select 1
        from auth.users
        where id = v_uid
          and email_confirmed_at is not null
    ) then
        raise exception 'UID inexistente ou e-mail nao confirmado no Supabase Auth.';
    end if;

    -- Policies permissivas se combinam por OR. Remover as anteriores somente
    -- nestas duas tabelas evita uma regra antiga liberando outras identidades.
    -- Isso tambem permite reexecutar o arquivo sem duplicar policies.
    for v_policy in
        select schemaname, tablename, policyname
        from pg_policies
        where schemaname = 'public'
          and tablename in ('clientes', 'ordens_servico')
    loop
        execute format(
            'drop policy %I on %I.%I',
            v_policy.policyname, v_policy.schemaname, v_policy.tablename
        );
    end loop;

    foreach v_tabela in array array['clientes', 'ordens_servico']
    loop
        -- SELECT: permitir visualizar registros somente para a conta tecnica.
        execute format(
            'create policy %I on public.%I for select to authenticated '
            'using ((select auth.uid()) = %L::uuid)',
            v_tabela || '_tecnica_select', v_tabela, v_uid::text
        );

        -- INSERT: validar a identidade que esta inserindo o novo registro.
        execute format(
            'create policy %I on public.%I for insert to authenticated '
            'with check ((select auth.uid()) = %L::uuid)',
            v_tabela || '_tecnica_insert', v_tabela, v_uid::text
        );

        -- UPDATE: validar tanto o acesso ao registro quanto sua nova versao.
        -- A SELECT policy acima tambem e necessaria para localizar a linha.
        execute format(
            'create policy %I on public.%I for update to authenticated '
            'using ((select auth.uid()) = %L::uuid) '
            'with check ((select auth.uid()) = %L::uuid)',
            v_tabela || '_tecnica_update', v_tabela, v_uid::text, v_uid::text
        );

        -- DELETE: permitir a remocao somente para a conta tecnica.
        -- A FK continua impedindo excluir um cliente com OS vinculadas.
        execute format(
            'create policy %I on public.%I for delete to authenticated '
            'using ((select auth.uid()) = %L::uuid)',
            v_tabela || '_tecnica_delete', v_tabela, v_uid::text
        );
    end loop;
end;
$techfix_rls$;
-- FIM BLOCO DE SEGURANCA TECHFIX

-- Bloco 9 - Confirmar as alteracoes.
commit;

-- Bloco 10 - Conferencia final: oito policies, quatro por tabela, RLS true.
-- Os campos condicao_leitura e condicao_gravacao devem conter o UID informado.
select
    p.tablename as tabela,
    c.relrowsecurity as rls_ativo,
    p.policyname as politica,
    p.cmd as operacao,
    p.roles as papeis,
    p.qual as condicao_leitura,
    p.with_check as condicao_gravacao
from pg_policies as p
join pg_namespace as n on n.nspname = p.schemaname
join pg_class as c on c.relnamespace = n.oid and c.relname = p.tablename
where p.schemaname = 'public'
  and p.tablename in ('clientes', 'ordens_servico')
order by p.tablename, p.cmd;
