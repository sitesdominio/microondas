# Sistema de fila do micro-ondas

Aplicação web de matrícula, seleção de tempo e gerenciamento da fila do micro-ondas. Backend Flask/Python executado como função na Vercel; PostgreSQL no Supabase.

## Deploy na Vercel

1. Conecte este repositório GitHub ao projeto Vercel **microondas**.
2. Root Directory: `./` (os arquivos `api/`, `public/` e `vercel.json` estão na raiz).
3. Configure `DATABASE_URL` em **Settings → Environment Variables** para Preview e Production. Use a connection string PostgreSQL do Supabase com SSL (`sslmode=require`).
4. Faça redeploy após adicionar a variável.

Não coloque credenciais no repositório, em `.env` versionado ou em variáveis públicas `NEXT_PUBLIC_*`.

## Banco de dados

A aplicação espera as tabelas existentes:

- `public.usuarios(matricula, nome)`
- `public.fila(id, matricula, tempo_minutos, entrada_em, inicio_uso_em, finalizado_em)`

Usuários são cadastrados administrativamente no Supabase. A aplicação pública valida matrículas e adiciona entradas à fila.

A migration `supabase/migrations/20261126141600_queue_unique_active.sql` registra o índice parcial que impede mais de uma entrada ativa por matrícula. Ele pode ser aplicado com segurança usando `IF NOT EXISTS`.

## Rotas

- `/` — início e validação de matrícula
- `/validar` — POST para validar matrícula
- `/entrar` — POST para entrar na fila
- `/telao` — telão com atualização periódica
- `/health` — verificação de conexão com o banco

## Teste pós-deploy

Abra `/health`; o resultado esperado é `{"status":"ok","database":"connected"}`. Depois teste uma matrícula já cadastrada e confirme que ela aparece no telão.

A variável `DATABASE_URL` é necessária para as rotas de banco. Sem ela, o app retorna mensagem de configuração e não usa um banco local efêmero.
