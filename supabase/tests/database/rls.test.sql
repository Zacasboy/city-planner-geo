-- Testes pgTAP de esquema e RLS. Correr com: supabase test db
begin;

create extension if not exists pgtap with schema extensions;

select plan(22);

-- Fixtures (como superutilizador) ---------------------------------------------

insert into auth.users (id, email) values
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a@example.com'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'b@example.com');

-- Esquema -----------------------------------------------------------------------

select ok(
  (select relrowsecurity from pg_class where oid = 'public.projects'::regclass),
  'RLS ativa em projects'
);
select ok(
  (select relrowsecurity from pg_class where oid = 'public.analysis_areas'::regclass),
  'RLS ativa em analysis_areas'
);
select ok(
  exists (
    select 1 from pg_indexes
    where schemaname = 'public' and tablename = 'analysis_areas'
      and indexdef ilike '%using gist (geom)%'
  ),
  'índice GIST em analysis_areas.geom'
);
select is(
  (select count(*)::int from storage.buckets
   where id in ('lidar', 'bim', 'reports', 'datasets', 'models') and not public),
  5,
  'os 5 buckets existem e são privados'
);

-- Utilizador A ------------------------------------------------------------------

set local role authenticated;
select set_config('request.jwt.claims', '{"sub": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}', true);

select lives_ok(
  $$insert into public.projects (id, name)
    values ('11111111-1111-1111-1111-111111111111', 'Projeto A')$$,
  'A cria projeto (user_id vem de auth.uid())'
);
select is(
  (select user_id from public.projects where id = '11111111-1111-1111-1111-111111111111'),
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid,
  'user_id preenchido automaticamente'
);
select throws_ok(
  $$insert into public.projects (name, user_id)
    values ('Intruso', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')$$,
  '42501',
  null,
  'A não pode criar projeto em nome de B'
);
select lives_ok(
  $$insert into public.analysis_areas (id, project_id, name, geom) values (
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    'Lote 1',
    extensions.st_geomfromtext('POLYGON((-9.15 38.70, -9.14 38.70, -9.14 38.71, -9.15 38.71, -9.15 38.70))', 4326)
  )$$,
  'A cria área válida no seu projeto'
);
select throws_ok(
  $$insert into public.analysis_areas (project_id, name, geom) values (
    '11111111-1111-1111-1111-111111111111',
    'Gravata',
    extensions.st_geomfromtext('POLYGON((0 0, 1 1, 1 0, 0 1, 0 0))', 4326)
  )$$,
  '23514',
  null,
  'polígono inválido (auto-interseção) é rejeitado'
);
select throws_ok(
  $$insert into public.analysis_areas (project_id, name, geom) values (
    '11111111-1111-1111-1111-111111111111',
    'Ponto',
    extensions.st_geomfromtext('POINT(-9.15 38.70)', 4326)
  )$$,
  null,
  null,
  'geometria que não é Polygon é rejeitada'
);
select lives_ok(
  $$update public.projects set deleted_at = now()
    where id = '11111111-1111-1111-1111-111111111111'$$,
  'A faz soft delete do projeto'
);
select throws_ok(
  $$delete from public.projects where id = '11111111-1111-1111-1111-111111111111'$$,
  '42501',
  null,
  'A não pode apagar fisicamente (sem DELETE)'
);
select lives_ok(
  $$insert into storage.objects (bucket_id, name)
    values ('reports', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/relatorio.pdf')$$,
  'A escreve na sua pasta do Storage'
);
select throws_ok(
  $$insert into storage.objects (bucket_id, name)
    values ('reports', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/roubo.pdf')$$,
  '42501',
  null,
  'A não escreve na pasta de B'
);

-- Utilizador B ------------------------------------------------------------------

select set_config('request.jwt.claims', '{"sub": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"}', true);

select is(
  (select count(*)::int from public.projects),
  0,
  'B não vê projetos de A'
);
select is(
  (select count(*)::int from public.analysis_areas),
  0,
  'B não vê áreas de A'
);
select is(
  (select count(*)::int from storage.objects),
  0,
  'B não vê ficheiros de A'
);
select lives_ok(
  $$update public.projects set name = 'Sequestrado'
    where id = '11111111-1111-1111-1111-111111111111'$$,
  'update de B sobre projeto de A não falha, mas não afeta nenhuma linha'
);
select throws_ok(
  $$insert into public.analysis_areas (project_id, name, geom) values (
    '11111111-1111-1111-1111-111111111111',
    'Intrusa',
    extensions.st_geomfromtext('POLYGON((-9.15 38.70, -9.14 38.70, -9.14 38.71, -9.15 38.71, -9.15 38.70))', 4326)
  )$$,
  '42501',
  null,
  'B não cria áreas no projeto de A'
);

-- Anónimo -----------------------------------------------------------------------

reset role;
set local role anon;

select throws_ok(
  $$select id from public.projects$$,
  '42501',
  null,
  'anon não tem acesso a projects'
);
select throws_ok(
  $$select id from public.analysis_areas$$,
  '42501',
  null,
  'anon não tem acesso a analysis_areas'
);

-- Confirmação final (superutilizador): nada foi alterado por B -----------------

reset role;

select is(
  (select name from public.projects where id = '11111111-1111-1111-1111-111111111111'),
  'Projeto A',
  'nome do projeto de A intacto'
);

select * from finish();
rollback;
