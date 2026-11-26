-- Supabase schema expected by the Microondas queue app.
-- The tables were created in the connected Supabase project; this migration
-- documents the active-entry uniqueness rule for fresh installations.
CREATE UNIQUE INDEX IF NOT EXISTS fila_matricula_ativa_unica
ON public.fila (matricula)
WHERE finalizado_em IS NULL;
