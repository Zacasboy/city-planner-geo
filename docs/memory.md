# memory

**Propósito:** armazenamento e gestão do estado do projeto. Atualizar **no fim de cada dia de trabalho**; manter um único processo `[~]` ativo.

## 6.1 Estado atual

| Campo | Valor |
|-------|-------|
| Última alteração | 2026-10-06 (fim do dia) |
| Fase | Fase 0 — Setup |
| Versão | 0.1.0 (documentação) |
| Processo ativo | T0.5 (decisões aprovadas e aplicadas; faltam os testes ao vivo) |
| Bloqueios | Nenhum |
| Risco principal | Fontes externas por verificar (licenças, limites, cobertura) |

## 6.2 Registo diário

### 2026-10-06 (terça-feira)
- [x] Documentação inicial criada (PRD, Architecture, Design, Rules, Tasks, memory)
- [x] Stack definida; fontes priorizadas por fase

**Decisões**
- **D1** Frontend Streamlit (integração Python/ML)
- **D2** Backend FastAPI + Celery/Redis
- **D3** Supabase (PostgreSQL + PostGIS + Auth + Storage)
- **D4** Deploy: Streamlit Cloud/HF Spaces + Render/Fly.io (Vercel só se frontend for Next.js)
- **D5** MVP usa GBIF, regime florestal da DGT e TimoDS; The Well fora do MVP (D20); restantes datasets em v1.0+
- **D6** *Fine-tuning* regional adiado para v1.1
- **D7** ML é camada de estimativa; cálculo estrutural usa motores de engenharia validados

- [x] T0.1 Repositório local criado: estrutura, `.gitignore`, MIT, README, docs/ separados, branches `main` e `develop`

**Pendente (ação do utilizador):** criar o repositório remoto no GitHub, fazer push de `main` e `develop`, ativar branch protection.

### 2026-10-06 (terça-feira), continuação
- [x] T0.2 Ambiente de desenvolvimento: Poetry (`poetry.lock`), ruff, black, mypy (strict), pytest (cobertura mínima 70%), pre-commit, `.env.example`, smoke test
- Branch: `feature/dev-environment` (aguarda PR para `develop`)

**Decisões**
- **D8** Sem dependências de runtime no `pyproject.toml` até serem necessárias (cada uma entra com a sua tarefa, conforme Rules 3.3)
- **D9** Linha de 100 caracteres em ruff e black; docstrings Google Style via regras `D` do ruff
- **D10** Hook mypy limitado a `backend|frontend|shared` (alinhado com `pyproject.toml`)

### 2026-10-06 (terça-feira), T0.3
- [x] T0.3 CI: `.github/workflows/ci.yml` (job `checks`: ruff, black, mypy, pytest em PR para `main`/`develop`)
- Branch: `feature/ci`

**Decisões**
- **D11** Job único em Python 3.12 (nome estável `checks` para a branch protection); sem matriz 3.11/3.12
- **D12** Workflow só em `pull_request`; CD/deploy fica para a T0.6

**Pendente (ação do utilizador):** depois da primeira execução do workflow, em Settings → Branches exigir o status check `checks` em `main` e `develop`.

### 2026-10-06 (terça-feira), T0.4
- [x] T0.4 Supabase: migrações PostGIS, `projects`, `analysis_areas` (RLS, GIST) e 5 buckets privados; testes pgTAP (22 verificações, todas a passar numa base PostgreSQL 16 + PostGIS local que imita o Supabase)
- Branch: `feature/supabase-setup`

**Decisões**
- **D13** `users` = `auth.users`; só `projects` e `analysis_areas` no esquema inicial, as outras tabelas entram com as suas tarefas
- **D14** Soft delete: utilizadores não têm `DELETE` (sem grant nem policy); apagam com `deleted_at`
- **D15** `analysis_areas.geom` é `Polygon` 4326 com `ST_IsValid` obrigatório (Rules R1)
- **D16** Storage: buckets privados, acesso por pasta `<user_id>/…`
- **D18** Chaves Supabase: `publishable`/`secret` (as `anon`/`service_role` estão em descontinuação); variáveis `SUPABASE_PUBLISHABLE_KEY` e `SUPABASE_SECRET_KEY`
- **D17** Testes de BD em pgTAP (`supabase test db`); a segurança foi validada por mutação (5 quebras deliberadas, todas apanhadas)

**Verificado pelo utilizador:** `db push` aplicado; query de verificação devolveu `1 | 2 | 1 | 5 | 6 | 4` (PostGIS, 2 tabelas com RLS, índice GIST, 5 buckets privados, 6 policies em `public`, 4 em `storage`); `curl` com a publishable key recusado (HTTP 401, `42501`) e com a secret key `[]` (HTTP 200); `.env` preenchido. **Advisors → Security** não foi reportado.

**Por testar:** as migrações foram testadas num PostgreSQL local com um mock de `auth`/`storage`, não no Supabase real. Policies de UPDATE/DELETE do Storage sem teste dedicado.

### 2026-10-06 (terça-feira), T0.5
- [~] T0.5 Auditoria de fontes do MVP: `docs/data_sources.md` (GBIF, regime florestal, TimoDS, The Well)
- Branch: `docs/data-sources-audit`

**Achados**
- GBIF: sem limite de taxa fixo (HTTP 429 possível); `limit` máx. 300 e `offset` máx. 100 000; licença por registo. O "100 pedidos/min" do rascunho inicial era do iNaturalist
- O serviço OGC API da DGT encontrado tem uma só coleção de conteúdo desconhecido; o regime florestal está num **ArcGIS REST FeatureServer** (2000 registos por pedido, SRS 3857)
- TimoDS (CC BY 4.0, 60 000 vigas) é sintético e só tem cargas unitárias: valida contra outro software FEM, não contra ensaios
- The Well (16 datasets de PDE genéricas) **não tem dados de edifícios, microclima ou geografia**; F4 e F6 do PRD ficam sem base de dados

**Decisões (aprovadas pelo utilizador em 2026-10-06)**
- **D19** (P1) Serviço florestal usa o ArcGIS REST FeatureServer da DGT, não "OGC API InterGeoPT"
- **D20** (P2) The Well fora do MVP; estrutural usa PyNite/anastruct validado com TimoDS
- **D21** (P3) F6 sem fonte pública; depende de dados regionais reais do utilizador
- **D22** (P4) GBIF filtrado por licença (sem CC BY-NC); licença de cada registo no relatório
- **D23** (P5) O3 mede concordância com *benchmark* sintético; os relatórios di-lo

**Pendente:** testes ao vivo (secção 6 de `data_sources.md`); licença da camada florestal; PROF e corredores ecológicos não localizados

**Próximo passo:** fechar T0.5, depois T0.6

## 6.3 Processo atual (um por vez)

| Campo | Valor |
|-------|-------|
| ID | T0.5 |
| Nome | Auditoria de fontes de dados |
| Estado | `[~]` documento escrito e decisões aplicadas; faltam os testes ao vivo |
| Dependências | T0.4 |
| Checklist | [x] `docs/data_sources.md` · [ ] testes ao vivo (secção 6) · [x] aprovar P1–P5 · [x] aplicar aos docs · [ ] licença da camada florestal |

## 6.4 Fila de processos

| Ordem | ID | Nome | Estado |
|-------|----|------|--------|
| 1 | T0.1 | Repositório e estrutura | `[x]` |
| 2 | T0.2 | Ambiente de desenvolvimento | `[x]` |
| 3 | T0.3 | CI | `[x]` |
| 4 | T0.4 | Supabase | `[x]` |
| 5 | T0.5 | Auditoria de fontes de dados | `[~]` |
| 6 | T0.6 | Sentry + CD staging | `[ ]` |
| 7 | T1.1 | Backend base | `[ ]` |

## 6.5 Métricas

| Métrica | Atual | Meta MVP |
|---------|-------|----------|
| Tarefas de setup concluídas | 4 | 6 |
| Cobertura de testes | 0% | 70% |
| Fontes integradas | 0 | 4 |
| Staging | não | sim |

## 6.6 Riscos

| ID | Risco | Prob. | Impacto | Mitigação |
|----|-------|-------|---------|-----------|
| R1 | Limites de taxa/indisponibilidade de APIs (GBIF, DGT) | Média | Alto | Cache, backoff, fallback estático |
| R2 | ~~Custo/tamanho do The Well~~ | n/a | n/a | Encerrado: The Well fora do MVP (D20) |
| R3 | Cobertura do serviço florestal da DGT incompleta | Média | Médio | Verificar em T0.5; dados estáticos de reserva |
| R4 | Datasets sem cobertura em Portugal (CITYLID, Glasgow) | Alta | Médio | Usar para validar métodos, não como fonte local |
| R5 | Responsabilidade por resultados de engenharia | Média | Alto | Aviso obrigatório, validação contra referências, rótulo de estimativa |
| R6 | Licenças de datasets incompatíveis com uso comercial | Média | Alto | Auditoria em T0.5 |
| R7 | Vendor lock-in Supabase | Baixa | Médio | PostgreSQL padrão |
| R8 | Limite de tamanho de ficheiro do plano Supabase vs. LiDAR de até 5 GB | Média | Médio | Confirmar plano; upload resumível ou Cloudflare R2 |
| R9 | The Well não tem dados de edifícios/microclima/geografia; F4 e F6 sem base de dados | Alta | Alto | Decisões D20 e D21 (P2 e P3) |
| R10 | Licença da camada "Regime florestal" por confirmar | Média | Médio | Consultar metadados DGT/SNIG antes de redistribuir |

## 6.7 Modelo de entrada diária (copiar)

```
### AAAA-MM-DD (dia da semana)
- Tarefa(s): ID — estado
- Decisões:
- Bloqueios:
- Próximo passo:
- Última alteração: AAAA-MM-DD (fim do dia)
```

## 6.8 Histórico de versões

| Versão | Data | Alterações |
|--------|------|------------|
| 0.1.0 | 2026-10-06 | Documentação inicial |
| 0.2.0 | 2026-10-06 | Decisões P1–P5 da auditoria de fontes aplicadas a PRD, arquitetura, Rules e Tasks |
