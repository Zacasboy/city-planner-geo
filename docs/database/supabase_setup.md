# Supabase Setup Guide

## T0.4: Projeto Supabase

Objetivo: Configurar o projeto Supabase com PostGIS, esquema inicial, RLS e buckets de storage.

### Etapas de Configuração

1. **Criar Projeto Supabase**
   - Acessar https://supabase.com/
   - Criar novo projeto
   - Anotar as credenciais (URL, chave anon, chave de serviço)

2. **Configurar Extensões Necessárias**
   - Habilitar PostGIS para suporte geoespacial
   - Considerar outras extensões conforme necessário

3. **Definir Esquema Inicial**
   - Tabela `projects` (projetos de planeamento)
   - Tabela `analysis_areas` (áreas de análise com geometria PostGIS)
   - Tabela `reports` (relatórios gerados)
   - Tabela `datasets_cache` (cache de datasets externos)
   - Tabela `materials` (catálogo de materiais)
   - Tabela `model_checkpoints` (checkpoints de modelos ML)

4. **Configurar RLS (Row Level Security)**
   - Habilitar RLS em todas as tabelas
   - Criar políticas baseadas em `user_id` (auth.uid())
   - Garantir isolamento de dados entre usuários

5. **Configurar Buckets de Storage**
   - Bucket para relatórios PDF
   - Bucket para arquivos IFC
   - Bucket para dados LiDAR/point clouds
   - Bucket para checkpoints de modelos ML
   - Configurar políticas de acesso adequadas

6. **Testar Conexão**
   - Verificar conexão com Supabase a partir do backend
   - Testar operações básicas de CRUD
   - Validar funcionamento do RLS
   - Testar upload/download de arquivos no storage

### Referências
- Decisão D3: Supabase (PostgreSQL + PostGIS + Auth + Storage)
- Seção 2.3 do System Architecture: Esquema de dados principal
- Seção 2.5: Segurança (Supabase Auth, RLS, etc.)

### Próximos Passos Após T0.4
- T0.5: Auditoria de fontes de dados
- T0.6: Configurar Sentry e CD para staging
- T1.1: Backend base