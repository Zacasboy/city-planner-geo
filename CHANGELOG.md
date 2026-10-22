# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-22

### Added

#### Fase 0 — Setup
- **T0.1**: Repository structure, .gitignore, MIT license, README
- **T0.2**: Poetry configuration with ruff, black, mypy, pytest, pre-commit
- **T0.3**: GitHub Actions CI pipeline (lint + tests)
- **T0.4**: Supabase project with PostGIS, initial schema, RLS, storage buckets
- **T0.6**: Sentry configuration and staging CD setup

#### Fase 1 — MVP
- **T1.1**: FastAPI backend base with Pydantic config, logging, CORS, `/health` endpoint
- **T1.2**: Supabase JWT authentication with `get_current_user` dependency
- **T1.3**: Geo service - `POST /geo/validate`, CRS conversions (EPSG:4326↔3763)
- **T1.4**: Ecology service - GBIF integration with caching, `POST /ecology/species`
- **T1.5**: Forest service - InterGeoPT API integration, `POST /forest/overlap`
- **T1.6**: Structural service - Steel beam analysis with PyNite, TimoDS validation, `POST /structural/beam`
- **T1.7**: Orchestration - Celery + Redis, task model, `GET /analysis/{id}` with progress tracking
- **T1.8**: Frontend base - Streamlit multipage app, login, sidebar, DisclaimerBanner
- **T1.9**: MapSelector component - polygon drawing, validation, submission (streamlit-folium)
- **T1.10**: Ecological & forest dashboards with ProgressTracker component
- **T1.11**: Structural analysis view - form + results display (demo + live modes)
- **T1.12**: PDF reports - Jinja2 + WeasyPrint, Supabase Storage upload, `GET /reports/{id}`
- **T1.13**: End-to-end tests and staging deployment preparation

#### Fase 2 — v1.0
- **T2.1**: Morphology service - OpenBuildingMap/DBSM metrics (density, height, occupancy, building types)
- **T2.2**: UMCC morphological classification (Height, PrimaryType, Orientation, Density, Vertical)
- **T2.3**: Materials catalog - 17 default materials, `GET /materials/suggest` with multi-filter
- **T2.4**: IFC quantities extraction - IfcOpenShell, element/material summaries, `POST /ifc/quantities`
- **T2.5**: The Well streaming - LRU cache with TTL, physics simulation endpoints (structural/thermal/acoustic/fluid)
- **T2.6**: 3D/LiDAR visualization - PyDeck/PyVista, morphology/IFC/point clouds, CITYLID/Glasgow validation
- **T2.7**: Morphology & materials dashboards - CSV/GeoJSON export
- **T2.8**: Load testing - 50 concurrent users, 60s, 24.8k requests, 100% success rate, avg 72ms, P95 159ms

### Technical Details

- **Python**: 3.12+
- **Framework**: FastAPI 0.115+
- **Frontend**: Streamlit 1.41+
- **Database**: Supabase (PostgreSQL + PostGIS)
- **Async Tasks**: Celery 5.6 + Redis
- **Key Libraries**: PyNite, IfcOpenShell, PyDeck, PyVista, WeasyPrint, PyProj, Shapely

### API Endpoints (v1.0)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/geo/validate` | POST | GeoJSON validation & CRS conversion |
| `/ecology/species` | POST | GBIF species lookup |
| `/forest/overlap` | POST | InterGeoPT forest overlap analysis |
| `/structural/beam` | POST | Steel beam analysis (PyNite) |
| `/analysis/{id}` | GET | Task status & progress |
| `/morphology/analyze` | POST | Urban morphology metrics |
| `/materials/` | GET | Materials catalog |
| `/materials/suggest` | POST | Filtered material suggestions |
| `/ifc/quantities` | POST | IFC element quantities extraction |
| `/physics/simulate` | POST | Physics simulation (structural/thermal/acoustic/fluid) |
| `/well/stream` | POST | The Well data streaming |
| `/visualization/visualize` | POST | 3D visualization (morphology/IFC/LiDAR) |
| `/dashboard/morphology` | POST | Morphology dashboard data |
| `/dashboard/materials` | POST | Materials dashboard data |
| `/reports/structural` | POST | Structural PDF report generation |
| `/reports/{id}` | GET | Report retrieval |

### Performance Benchmarks (T2.8 Load Test)

- **Concurrent Users**: 50
- **Duration**: 60 seconds
- **Total Requests**: 24,850
- **Success Rate**: 100%
- **Average Response Time**: 72 ms
- **P95 Response Time**: 159 ms
- **Throughput**: 414 req/s
- **Error Rate**: 0%

### Known Limitations

- PDF generation (WeasyPrint) requires system dependencies (cairo, pango, gobject) - works in containers
- Full GBIF/InterGeoPT integration requires API keys - mocked in development
- LiDAR validation against CITYLID/Glasgow requires dataset downloads

---

## [Unreleased]

### Planned (Fase 3 — v1.1)
- T3.1: Geographic fine-tuning pipeline (Lisbon pilot) + checkpoint management
- T3.2: User data upload for fine-tuning
- T3.3: Public REST API - API keys, rate limiting, Python SDK
- T3.4: QGIS/ArcGIS export (GeoJSON, Shapefile)
- T3.5: English internationalization (i18n)

### Planned (Fase 4 — v2.0)
- T4.1: EU expansion (DBSM) with per-country adaptation
- T4.2: Optional datasets: STEEL-3dPointClouds, Bridge Datasets, EarthworkSat-7K, LUPAN, BuildingWorld, SUM4Re