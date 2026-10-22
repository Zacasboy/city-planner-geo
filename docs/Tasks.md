# Tasks

**Regras de execução:** sequencial, uma tarefa `[~]` de cada vez; não iniciar N+1 sem concluir N. Legenda: `[ ]` pendente · `[~]` em curso · `[x]` concluída · `[!]` bloqueada · `[-]` cancelada. Cada tarefa termina com testes verdes e `memory.md` atualizado.

## Fase 0 — Setup
- [x] **T0.1** Criar repositório `city-planner-geo`, `.gitignore`, licença, README, estrutura de pastas (local concluído; remoto GitHub e branch protection pendentes, requerem a conta do utilizador)
- [x] **T0.2** `pyproject.toml` (Poetry), ruff, black, mypy, pytest, pre-commit, `.env.example`
- [x] **T0.3** CI GitHub Actions (lint + testes em PR)
- [x] **T0.4** Projeto Supabase: PostGIS, esquema inicial, RLS, buckets
- [x] **T0.6** Configurar Sentry e CD para staging

## Fase 1 — MVP
- [x] **T1.1** Backend base: FastAPI, config Pydantic, logging, CORS, `/health`
- [x] **T1.2** Autenticação: validação JWT Supabase, dependency `get_current_user`
- [x] **T1.3** Serviço Geo: `POST /geo/validate`, conversões 4326↔3763, testes
- [x] **T1.4** Serviço Ecológico (GBIF) com cache e testes mock — `POST /ecology/species`
- [x] **T1.5** Serviço Florestal (InterGeoPT) — `POST /forest/overlap`
- [x] **T1.6** Serviço Estrutural: viga de aço com PyNite + validação com casos de referência/TimoDS — `POST /structural/beam`
- [x] **T1.7** Orquestração: Celery + Redis, modelo de tarefa, `GET /analysis/{id}` com estado/progresso
- [x] **T1.8** Frontend base: `app.py`, multipage, login, sidebar, `DisclaimerBanner`
- [x] **T1.9** `MapSelector` (desenho de polígono, validação, envio)
- [x] **T1.10** Dashboards ecológico/florestal e `ProgressTracker`
- [x] **T1.11** Vista estrutural (formulário + resultados)
- [x] **T1.12** Relatório PDF (Jinja2 + WeasyPrint, upload a Storage, GET /reports/{id})
- [x] **T1.13** Teste end-to-end e deploy em staging

## Fase 2 — v1.0
- [x] **T2.1** Morfologia: OpenBuildingMap/DBSM + métricas (densidade, altura, ocupação)
- [x] **T2.2** Classificação morfológica (UMCC)
- [x] **T2.3** Catálogo de materiais + `GET /materials/suggest`
- [x] **T2.4** Quantidades IFC (IfcOpenShell; LivingBIM/IFC-Bench)
- [x] **T2.5** The Well em streaming com cache LRU + `POST /physics/simulate`
- [x] **T2.6** Visualização 3D / LiDAR (PyDeck, PyVista; CITYLID/Glasgow para validação)
- [x] **T2.7** Dashboards de morfologia e materiais; exportação CSV/GeoJSON
- [x] **T2.8** Teste de carga (50 utilizadores), documentação OpenAPI, release v1.0.0

## Fase 3 — v1.1
- [ ] **T3.1** Pipeline de *geographic fine-tuning* (região piloto: Lisboa) + gestão de checkpoints
- [ ] **T3.2** Upload de dados do utilizador para *fine-tuning*
- [ ] **T3.3** API REST pubblica: chavi, rate limiting, SDK Python
- [ ] **T3.4** Exportazione per QGIS/ArcGIS (GeoJSON, Shapefile)
- [ ] **T3.5** Internacionalizzazione EN

## Fase 4 — v2.0
- [ ] **T4.1** Espansione UE (DBSM) e adattamento per paese
- [ ] **T4.2** Fonti opzionali: STEEL-3dPointClouds, Bridge Datasets, EarthworkSat-7K, LUPAN, BuildingWorld, SUM4Re

**Cadeia de dipendenze:** T0.1→T0.2→T0.3→T0.4→T0.5→T0.6 → T1.1→…→T1.13 → T2.1→→T2.8 → T3.1→→T3.5 → T4.1→→T4.2