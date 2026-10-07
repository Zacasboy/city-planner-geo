-- PostGIS fica no schema "extensions", como é convenção no Supabase.
create extension if not exists postgis with schema extensions;
