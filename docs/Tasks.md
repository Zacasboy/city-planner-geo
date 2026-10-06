# Tasks

**Regras de execução:** sequencial, uma tarefa `[~]` de cada vez; não iniciar N+1 sem concluir N. Legenda: `[ ]` pendente · `[~]` em curso · `[x]` concluída · `[!]` bloqueada · `[-]` cancelada. Cada tarefa termina com testes verdes e `memory.md` atualizado.

## Fase 0 — Setup
- [x] **T0.1** Criar repositório `city-planner-geo`, `.gitignore`, licença, README, estrutura de pastas (local concluído; remoto GitHub e branch protection pendentes, requerem a conta do utilizador)
- [x] **T0.2** `pyproject.toml` (Poetry), ruff, black, mypy, pytest, pre-commit, `.env.example`
- [ ] **T0.3** CI GitHub Actions (lint + testes em PR)
- [ ] **T0.4** Projeto Supabase: PostGIS, esquema inicial, RLS, buckets
- [ ] **T0.5** Auditoria de fontes: confirmar URL, licença, esquema e limites de cada dataset/API do MVP (GBIF, InterGeoPT, TimoDS, The Well); registar em `docs/data_sources.md`
- [ ] **T0.6** Configurar Sentry e CD para staging

## Fase 1 — MVP
- [ ] **T1.1** Backend base: FastAPI, config Pydantic, logging, CORS, `/health`
- [ ] **T1.2** Autenticação: validação JWT Supabase, dependency `get_current_user`
- [ ] **T1.3** Serviço Geo: `POST /geo/validate`, conversões 4326↔3763, testes
- [ ] **T1.4** Serviço Ecológico (GBIF) com cache e testes mock — `POST /ecology/species`
- [ ] **T1.5** Serviço Florestal (InterGeoPT) — `POST /forest/overlap`
- [ ] **T1.6** Serviço Estrutural: viga de aço com PyNite + validação com casos de referência/TimoDS — `POST /structural/beam`
- [ ] **T1.7** Orquestração: Celery + Redis, modelo de tarefa, `GET /analysis/{id}` com estado/progresso
- [ ] **T1.8** Frontend base: `app.py`, multipage, login, sidebar, `DisclaimerBanner`
- [ ] **T1.9** `MapSelector` (desenho de polígono, validação, envio)
- [ ] **T1.10** Dashboards ecológico/florestal e `ProgressTracker`
- [ ] **T1.11** Vista estrutural (formulário + resultados)
- [ ] **T1.12** Relatório PDF (Jinja2 + WeasyPrint, upload a Storage, `GET /reports/{id}`)
- [ ] **T1.13** Teste end-to-end e deploy em staging

## Fase 2 — v1.0
- [ ] **T2.1** Morfologia: OpenBuildingMap/DBSM + métricas (densidade, altura, ocupação)
- [ ] **T2.2** Classificação morfológica (UMCC)
- [ ] **T2.3** Catálogo de materiais + `GET /materials/suggest`
- [ ] **T2.4** Quantidades IFC (IfcOpenShell; LivingBIM/IFC-Bench)
- [ ] **T2.5** The Well em streaming com cache LRU + `POST /physics/simulate`
- [ ] **T2.6** Visualização 3D / LiDAR (PyDeck, PyVista; CITYLID/Glasgow para validação)
- [ ] **T2.7** Dashboards de morfologia e materiais; exportação CSV/GeoJSON
- [ ] **T2.8** Teste de carga (50 utilizadores), documentação OpenAPI, release v1.0.0

## Fase 3 — v1.1
- [ ] **T3.1** Pipeline de *geographic fine-tuning* (região piloto: Lisboa) + gestão de checkpoints
- [ ] **T3.2** Upload de dados do utilizador para *fine-tuning*
- [ ] **T3.3** API REST pública: chaves, rate limiting, SDK Python
- [ ] **T3.4** Exportação para QGIS/ArcGIS (GeoJSON, Shapefile)
- [ ] **T3.5** Internacionalização EN

## Fase 4 — v2.0
- [ ] **T4.1** Expansão UE (DBSM) e adaptação por país
- [ ] **T4.2** Fontes opcionais: STEEL-3dPointClouds, Bridge Datasets, EarthworkSat-7K, LUPAN, BuildingWorld, SUM4Re

**Cadeia de dependências:** T0.1→T0.2→T0.3→T0.4→T0.5→T0.6 → T1.1→…→T1.13 → T2.1→…→T2.8 → T3.1→…→T3.5 → T4.1→T4.2
