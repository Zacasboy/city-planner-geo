-- Esquema inicial (T0.4): projects e analysis_areas.
-- "users" é o auth.users do Supabase Auth, não há tabela própria.
-- Regras: RLS em todas as tabelas, índice GIST, soft delete (sem policy de DELETE).

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- projects -------------------------------------------------------------------

create table public.projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  name text not null check (char_length(name) between 1 and 120),
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index projects_user_id_idx on public.projects (user_id);

create trigger projects_set_updated_at
  before update on public.projects
  for each row execute function public.set_updated_at();

-- analysis_areas -------------------------------------------------------------
-- Geometria sempre em WGS84 (EPSG:4326) e válida (Rules R1).

create table public.analysis_areas (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects (id) on delete cascade,
  name text not null check (char_length(name) between 1 and 120),
  geom extensions.geometry(Polygon, 4326) not null check (extensions.st_isvalid(geom)),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index analysis_areas_project_id_idx on public.analysis_areas (project_id);
create index analysis_areas_geom_gist_idx on public.analysis_areas using gist (geom);

create trigger analysis_areas_set_updated_at
  before update on public.analysis_areas
  for each row execute function public.set_updated_at();

-- Propriedade do projeto, usada nas policies de analysis_areas.
-- security invoker: a RLS de projects aplica-se dentro da função.
create or replace function public.is_project_owner(p_project_id uuid)
returns boolean
language sql
stable
set search_path = ''
as $$
  select exists (
    select 1
    from public.projects p
    where p.id = p_project_id
      and p.user_id = (select auth.uid())
  );
$$;

revoke all on function public.is_project_owner(uuid) from public;
grant execute on function public.is_project_owner(uuid) to authenticated, service_role;

-- Privilégios: sem DELETE para utilizadores (soft delete via deleted_at) ------

revoke all on public.projects, public.analysis_areas from anon, authenticated;
grant select, insert, update on public.projects, public.analysis_areas to authenticated;
grant all on public.projects, public.analysis_areas to service_role;

-- RLS -------------------------------------------------------------------------

alter table public.projects enable row level security;

create policy projects_select_own on public.projects
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy projects_insert_own on public.projects
  for insert to authenticated
  with check (user_id = (select auth.uid()));

create policy projects_update_own on public.projects
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

alter table public.analysis_areas enable row level security;

create policy analysis_areas_select_own on public.analysis_areas
  for select to authenticated
  using (public.is_project_owner(project_id));

create policy analysis_areas_insert_own on public.analysis_areas
  for insert to authenticated
  with check (public.is_project_owner(project_id));

create policy analysis_areas_update_own on public.analysis_areas
  for update to authenticated
  using (public.is_project_owner(project_id))
  with check (public.is_project_owner(project_id));
