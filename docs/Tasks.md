# Tasks

**Regras de execução:** sequencial, uma tarefa `[~]` de cada vez; não iniciar N+1 sem concluir N. Legenda: `[ ]` pendente · `[~]` em curso · `[x]` concluída · `[!]` bloqueada · `[-]` cancelada. Cada tarefa termina com testes verdes e `memory.md` atualizado.

## Fase 0 — Setup
- [x] **T0.1** Criar repositório `city-planner-geo`, `.gitignore`, licença, README, estrutura de pastas (local concluído; remoto GitHub e branch protection pendentes, requerem a conta do utilizador)
- [x] **T0.2** `pyproject.toml` (Poetry), ruff, black, mypy, pytest, pre-commit, `.env.example`
- [x] **T0.3** CI GitHub Actions (lint + testes em PR) (workflow concluído; falta o utilizador exigir o check `checks` na branch protection depois da primeira execução)
- [x] **T0.4** Projeto Supabase: PostGIS, esquema inicial, RLS, buckets (migrações aplicadas e verificadas no projeto remoto; ver `supabase/README.md`)
- [x] **T0.5** Auditoria de fontes: confirmar URL, licença, esquema e limites de cada dataset/API do MVP (GBIF, InterGeoPT, TimoDS, The Well); registar em `docs/data_sources.md` (concluída em 2026-10-06; a licença da camada florestal e o PROF passam a ser verificações da T1.5)
- [~] **T0.6** Configurar Sentry e CD para staging (código pronto: Sentry opcional por `SENTRY_DSN`, `Dockerfile`, `render.yaml` com deploy após CI verde; falta criar as contas e seguir `docs/deploy.md`)

## Fase 1 — MVP
- [x] **T1.1** Backend base: FastAPI, config Pydantic, logging, CORS, `/health` (CORS restrito por defeito a `http://localhost:8501`, `*` rejeitado; `HOST` 127.0.0.1)
- [x] **T1.2** Autenticação: validação JWT Supabase (JWKS ES256/RS256 e HS256; `exp`, `sub`, `aud`, `iss` obrigatórios), dependency `get_current_user`; exigida em `/geo`, `/ecology`, `/forest`, `/structural`, `/morphology`, `/reports`, `/orchestration` (falta verificar o login com o Supabase real; limite de pedidos por fazer)
- [x] **T1.3** Serviço Geo: `POST /geo/validate`, conversões 4326↔3763, testes
- [x] **T1.4** Serviço Ecológico (GBIF) com cache e testes mock; filtro de licenças (só CC0 e CC BY), lista de espécies por facetas (`speciesKey`; nomes via `/species/{key}` por verificar), `User-Agent`, backoff em HTTP 429, polígono anti-horário — `POST /ecology/area-species` (cache 24 h, retry)
- [x] **T1.5** Serviço Florestal (DGT, camada 1562 com 209 polígonos: avaliar sincronizar para o PostGIS em vez de consultar ao vivo; **confirmar a licença antes de redistribuir**) — `POST /forest/overlap`
- [x] **T1.6** Serviço Estrutural: viga de aço, `POST /structural/beam` (FEM de Timoshenko com apoios `pin`/`roller`/`fixed`, cargas pontuais, carga uniforme e peso próprio; secção retangular ou propriedades explícitas de um perfil; validado contra soluções analíticas e contra o TimoDS: flexão e axial com erro < 0,011 % em 2000 instâncias, ver `docs/memory.md` D30). **Torção não validada e não suportada** (T1.6b); catálogo IPE/HEA/HEB com alturas por criar (T1.6c)
- [ ] **T1.6b** Torção: a mola `c_x_B` do TimoDS não é compatível com o equilíbrio dos seus próprios resultados; analisar as 314 instâncias do caso 4
- [ ] **T1.6c** Catálogo de perfis IPE/HEA/HEB (o CSV do TimoDS dá S, I, J e áreas de corte mas não a altura da secção)
- [x] **T1.7** Orquestração: Celery + Redis, modelo de tarefa, estado/progresso em `/orchestration` (tarefas com dono; 404 para quem não é dono)
- [x] **T1.8** Frontend base: `app.py`, multipage, login, sidebar, `DisclaimerBanner`
- [x] **T1.9** `MapSelector` (desenho de polígono, validação, envio) (usado pelo painel ecológico; `send_polygon_to_backend` da página Geo ainda é simulado)
- [~] **T1.10** Dashboards ecológico/florestal e `ProgressTracker` (ecológico com dados reais do GBIF via `/ecology/area-species`; florestal ainda com dados de exemplo)
- [x] **T1.11** Vista estrutural (formulário + resultados)
- [x] **T1.12** Relatório PDF (Jinja2 + WeasyPrint, com fontes, licenças e o aviso do PRD 1.7; upload a Storage, `GET /reports/{id}`; ficheiros em `<user_id>/<report_id>.pdf`, só o dono acede; ainda sem contexto ecológico)
- [ ] **T1.13** Teste end-to-end e deploy em staging

## Fase 2 — v1.0
- [~] **T2.1** Morfologia: OpenBuildingMap/DBSM + métricas (densidade, altura, ocupação) (`POST /morphology/analyze` com edifícios simulados; área em m² via EPSG:3763, só Portugal continental; falta OpenBuildingMap/DBSM)
- [ ] **T2.2** Classificação morfológica (UMCC)
- [ ] **T2.3** Catálogo de materiais + `GET /materials/suggest`
- [ ] **T2.4** Quantidades IFC (IfcOpenShell; LivingBIM/IFC-Bench)
- [ ] **T2.5** Fonte para simulações físicas/térmicas: avaliar alternativas (The Well está fora do âmbito, ver `docs/data_sources.md`); só implementar `POST /physics/simulate` se houver dados relevantes
- [ ] **T2.6** Visualização 3D / LiDAR (PyDeck, PyVista; CITYLID/Glasgow para validação)
- [ ] **T2.7** Dashboards de morfologia e materiais; exportação CSV/GeoJSON
- [ ] **T2.8** Teste de carga (50 utilizadores), documentação OpenAPI, release v1.0.0

## Fase 3 — v1.1
- [ ] **T3.1** Pipeline de *geographic fine-tuning* (região piloto: Lisboa) com dados regionais reais do utilizador (sem fonte pública) + gestão de checkpoints; condicionada à disponibilidade desses dados
- [ ] **T3.2** Upload de dados do utilizador para *fine-tuning*
- [ ] **T3.3** API REST pública: chaves, rate limiting, SDK Python
- [ ] **T3.4** Exportação para QGIS/ArcGIS (GeoJSON, Shapefile)
- [ ] **T3.5** Internacionalização EN

## Fase 4 — v2.0
- [ ] **T4.1** Expansão UE (DBSM) e adaptação por país
- [ ] **T4.2** Fontes opcionais: STEEL-3dPointClouds, Bridge Datasets, EarthworkSat-7K, LUPAN, BuildingWorld, SUM4Re

**Estado (2026-11-01):** CI (`checks`) verde, 199 testes, cobertura ≥ 85%. Pendentes: T0.6, T1.6 (FEM/TimoDS), T1.13, painel florestal real, licença DGT.

**Cadeia de dependências:** T0.1→T0.2→T0.3→T0.4→T0.5→T0.6 → T1.1→…→T1.13 → T2.1→…→T2.8 → T3.1→…→T3.5 → T4.1→T4.2
