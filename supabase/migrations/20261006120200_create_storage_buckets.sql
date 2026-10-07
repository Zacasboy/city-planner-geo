-- Buckets privados (T0.4). Cada utilizador só acede à sua pasta: "<user_id>/ficheiro".
-- Limites de tamanho por ficheiro dependem do plano Supabase: ver supabase/README.md.

insert into storage.buckets (id, name, public)
values
  ('lidar', 'lidar', false),
  ('bim', 'bim', false),
  ('reports', 'reports', false),
  ('datasets', 'datasets', false),
  ('models', 'models', false)
on conflict (id) do nothing;

-- Predicado comum às quatro policies:
--   bucket_id in ('lidar','bim','reports','datasets','models')
--   and (storage.foldername(name))[1] = (select auth.uid())::text

create policy storage_own_select on storage.objects
  for select to authenticated
  using (
    bucket_id in ('lidar', 'bim', 'reports', 'datasets', 'models')
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

create policy storage_own_insert on storage.objects
  for insert to authenticated
  with check (
    bucket_id in ('lidar', 'bim', 'reports', 'datasets', 'models')
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

create policy storage_own_update on storage.objects
  for update to authenticated
  using (
    bucket_id in ('lidar', 'bim', 'reports', 'datasets', 'models')
    and (storage.foldername(name))[1] = (select auth.uid())::text
  )
  with check (
    bucket_id in ('lidar', 'bim', 'reports', 'datasets', 'models')
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

create policy storage_own_delete on storage.objects
  for delete to authenticated
  using (
    bucket_id in ('lidar', 'bim', 'reports', 'datasets', 'models')
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );
