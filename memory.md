# Memory

## Completed Work
- Completed T1.7: Orquestração: Celery + Redis, modelo de tarefa, GET /analysis/{id} com estado/progresso
  - Implemented OrchestrationService with Celery + Redis integration
  - Added comprehensive mock tests for the orchestration service
  - Updated dependencies (celery, redis) in pyproject.toml
  - Updated main.py to include the orchestration router
- Completed T1.8: Frontend base: `app.py`, multipage, login, sidebar, `DisclaimerBanner`
  - Created frontend/app.py with multi-page navigation
  - Created login page with Supabase authentication
  - Created home page with user info and logout
  - Created sidebar and disclaimer banner components
  - Created placeholder pages for geo, ecology, forest, structural, orchestration, reports, and signup

## Current Work
- In progress T1.9: `MapSelector` (desenho de polígono, validação, envio)
  - Added streamlit-folium dependency to pyproject.toml
  - Created MapSelector component with folium map, drawing tools, validation, and mock sending
  - Updated geo.py page to use the MapSelector component for polygon drawing, validation, and sending

## Next Step
- Complete T1.9 and move to T1.10: Dashboards ecológico/florestal e `ProgressTracker`