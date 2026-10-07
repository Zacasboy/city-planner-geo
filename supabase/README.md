# Supabase

Migrações SQL, testes de base de dados e instruções de ligação ao projeto Supabase.

## Estrutura

```
supabase/
  migrations/   SQL versionado (só avança; nunca DROP em produção)
  tests/database/rls.test.sql   testes pgTAP de esquema e RLS
```

| Migração | Conteúdo |
|----------|----------|
| `…120000_enable_postgis` | Extensão PostGIS no schema `extensions` |
| `…120100_create_projects_and_analysis_areas` | Tabelas `projects` e `analysis_areas`, índices (incl. GIST), triggers `updated_at`, RLS |
| `…120200_create_storage_buckets` | Buckets privados `lidar`, `bim`, `reports`, `datasets`, `models` e policies |

`users` é o `auth.users` do Supabase Auth, não existe tabela própria. As restantes tabelas
da arquitetura (`reports`, `materials`, …) entram com as tarefas que as usam.

## Modelo de segurança

- RLS ativa em todas as tabelas; cada utilizador só vê e altera o que é seu.
- `anon` não tem acesso a nenhuma tabela.
- Utilizadores **não têm `DELETE`**: apagar é fazer `update … set deleted_at = now()` (soft delete).
  A aplicação deve filtrar `deleted_at is null`.
- Ficheiros no Storage vivem em `<user_id>/<ficheiro>`; só o dono lê e escreve.
- A **secret key** (`sb_secret_…`, antiga `service_role`) ignora a RLS: usar **apenas** no backend, nunca no frontend nem no Git.
  A **publishable key** (`sb_publishable_…`, antiga `anon`) é a única que o frontend pode usar.

## Ligar a um projeto Supabase (uma vez)

1. Instalar a CLI: `brew install supabase/tap/supabase`
2. Criar o projeto em supabase.com/dashboard, de preferência numa região da UE (RGPD).
   Guardar a password da base de dados.
3. Na raiz do repositório:
   ```bash
   supabase init                       # cria supabase/config.toml (sem segredos; pode ir para o Git)
   supabase login
   supabase link --project-ref <ref>   # o ref está no URL do projeto
   supabase db push                    # aplica as migrações
   ```
4. Copiar `.env.example` para `.env` e preencher `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` e
   `SUPABASE_SECRET_KEY` (Dashboard → Project Settings → API Keys). Editar o ficheiro num editor,
   não com `echo` no terminal (ficaria no histórico). O `.env` nunca vai para o Git.

## Verificar no projeto remoto

No SQL Editor do dashboard:

```sql
select extname, extnamespace::regnamespace from pg_extension where extname = 'postgis';
select relname, relrowsecurity from pg_class
  where relnamespace = 'public'::regnamespace and relname in ('projects', 'analysis_areas');
select indexname from pg_indexes where tablename = 'analysis_areas';
select id, public from storage.buckets order by id;
select schemaname, tablename, policyname, cmd from pg_policies
  where schemaname in ('public', 'storage') order by 1, 2, 3;
```

Esperado: PostGIS em `extensions`; `relrowsecurity = true` nas duas tabelas; índice
`analysis_areas_geom_gist_idx`; 5 buckets com `public = false`; policies para projects,
analysis_areas e storage.objects. Em **Advisors → Security** não deve aparecer nenhum aviso
de "RLS disabled".

## Testes locais

Requer Docker.

```bash
supabase start
supabase test db
```

Os testes estão em `tests/database/rls.test.sql` (22 verificações: isolamento entre utilizadores,
ausência de `DELETE`, geometrias inválidas, acesso anónimo, pastas do Storage).

## Limites a confirmar [VERIFICAR]

Os limites de tamanho de ficheiro e de armazenamento dependem do plano. A arquitetura prevê
ficheiros LiDAR de 100 MB a 5 GB: confirmar em supabase.com/pricing se o plano escolhido o permite.
Se não, alternativas: subir de plano, upload resumível ou Cloudflare R2 (ver `System_Architecture.md`).
