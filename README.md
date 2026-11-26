# Sistema de fila do micro-ondas

Aplicação web para validar matrícula, selecionar tempo de utilização e gerenciar a fila do micro-ondas, com PostgreSQL no Supabase e deploy na Vercel.

## Configuração

1. Configure `DATABASE_URL` nas Environment Variables da Vercel (Preview e Production).
2. Use a connection string PostgreSQL do Supabase com SSL.
3. Faça redeploy após salvar a variável.

A aplicação consulta `public.usuarios` e `public.fila`. O cadastro de usuários é administrativo, diretamente no banco.
