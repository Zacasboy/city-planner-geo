# System Architecture

## 2.1 High-Level Architecture

```
Utilizador (profissional: arquiteto/urbanista/engenheiro/planeador)
        │ HTTPS
        ▼
Frontend — Streamlit (mapa, formulários, dashboards, progresso em streaming)
        │ REST (+ polling/SSE de progresso)
        ▼
Backend — FastAPI
   ├─ Serviço Geo        (validação, projeções)
   ├─ Serviço Ecológico  (GBIF)
   ├─ Serviço Florestal  (OGC API InterGeoPT)
   ├─ Serviço Estrutural (PyNite/anastruct + TimoDS)
   ├─ Serviço Físico     (The Well, streaming)          [v1.0]
   ├─ Serviço Morfologia (OBM/DBSM/UMCC)                [v1.0]
   ├─ Serviço Materiais  (catálogo + IFC)               [v1.0]
   ├─ Motor ML           (PyTorch, checkpoints regionais)
   └─ Orquestração       (Celery + Redis) para tarefas longas
        │
        ├─ Supabase PostgreSQL + PostGIS (dados, RLS)
        ├─ Supabase Storage (PDF, IFC, LiDAR, checkpoints)
        └─ APIs/Datasets externos (GBIF, InterGeoPT, Hugging Face, Zenodo, Copernicus)
```

## 2.2 Technology Stack

| Camada | Escolha | Justificação |
|--------|---------|--------------|
| Frontend | **Streamlit** + Folium/streamlit-folium, PyDeck, Plotly (PyVista para 3D em v1.0) | Python nativo, rápido para dashboards ML/geo. Alternativa rejeitada: Next.js (mais manutenção, duas linguagens) |
| Backend | **FastAPI** + Pydantic | OpenAPI automático, validação forte |
| Geoespacial | GeoPandas, Shapely, PyProj, Rasterio | Stack padrão |
| Estrutural | PyNite, anastruct, sectionproperties | Motores abertos de análise de pórticos/secções |
| BIM/IFC | IfcOpenShell | Padrão open-source |
| ML | PyTorch, Hugging Face `datasets`/`huggingface_hub`; MLflow ou HF Hub para versionamento | Padrão da indústria |
| Tarefas longas | Celery + Redis | Simulações e *fine-tuning* fora do request |
| Relatórios | Jinja2 + WeasyPrint | HTML→PDF simples |
| **Base de dados** | **Supabase (PostgreSQL + PostGIS)** | PostGIS, Auth e RLS integrados. Alternativa: Neon (requer gerir extensões) |
| **Storage** | **Supabase Storage** | Integrado; considerar Cloudflare R2 se o custo de saída crescer |
| **Deployment** | Frontend: Streamlit Community Cloud ou HF Spaces; Backend + Workers: Render ou Fly.io (Docker) | Vercel não é adequado para este backend Python de longa duração/ML; só faria sentido se o frontend fosse Next.js |
| **Version control** | **Git + GitHub**, GitHub Actions (CI/CD) | Conventional Commits, branch protection |
| Observabilidade | Sentry, logging estruturado | Prometheus/Grafana em v2 |

## 2.3 Esquema de dados (principal)
`users` (Supabase Auth) · `projects` · `analysis_areas` (geometria PostGIS, índice GIST) · `reports` · `datasets_cache` · `materials` · `model_checkpoints`. RLS em todas as tabelas, por `user_id`.

## 2.4 Fluxo de análise
1. Utilizador desenha polígono → frontend envia `POST /analysis` (polígono + tipo de construção).
2. Backend valida geometria (`make_valid`, área máxima) e cria tarefa Celery.
3. Serviços correm em paralelo (ecológico, florestal, estrutural; depois morfologia/físico/materiais).
4. Motor ML aplica checkpoint regional (se existir) e devolve previsões com incerteza.
5. Agregação → JSON → PDF → Storage.
6. Frontend consulta o estado da tarefa e apresenta resultados à medida que ficam prontos.

## 2.5 Segurança
Supabase Auth (JWT) · RLS · segredos em variáveis de ambiente · rate limiting (`slowapi`) · validação Pydantic · CORS restrito · sanitização de GeoJSON · logs sem PII.

## 2.6 Estrutura de repositório
```
backend/ (app, services, api, tasks)   frontend/ (app.py, pages, components)
shared/ (schemas, constants)           models/   data/ (gitignored)
docs/   tests/ (fixtures)   scripts/   .github/workflows/
```
