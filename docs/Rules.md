# Rules

## 4.1 Princípios gerais
1. **Seguir** `System_Architecture.md`, `PRD.md` e `Design.md`. Desvios exigem issue e aprovação em PR.
2. **Código limpo, legível e bem estruturado:** funções < 50 linhas (ideal < 30), ficheiros < 500, nomes descritivos, sem números mágicos, sem código comentado, docstrings Google Style em funções públicas, *type hints* obrigatórios.
3. **Simplicidade e sustentabilidade:** preferir stdlib e bibliotecas maduras; cada dependência nova justificada no PR; síncrono por defeito, async só quando necessário.
4. **Reutilização (DRY):** lógica em `services/`, `utils/`, `components/`, `shared/`.
5. **Mudanças mínimas e focadas:** um PR = uma funcionalidade/correção; diff < 400 linhas; sem misturar refactor com feature.
6. **Evitar alterar ficheiros não relacionados:** sem reformatações globais nem renomeações fora de escopo; bugs fora de escopo viram issues.
7. **Código autoexplicativo:** comentários só para o *porquê*.

```python
area_m2 = largura_m * altura_m   # nome claro dispensa comentário
```

## 4.2 Regras específicas

**Geoespacial** — API em WGS84 (EPSG:4326); cálculos locais em EPSG:3763 (PT-TM06); validar polígonos com `shapely.validation.make_valid()`; áreas em m² na API.

**Dados externos** — nunca hardcodar chaves (`os.getenv`); cache obrigatório para GBIF/InterGeoPT (TTL ≥ 24 h); timeout 30 s; retry com backoff exponencial (máx. 3); respeitar termos e licenças de cada dataset.

**Engenharia (crítico)** — todo cálculo físico tem teste contra caso de referência conhecido; unidades explícitas (sufixos `_m`, `_kn`, `_mpa`); ML nunca substitui verificação normativa — resultados ML são rotulados como estimativa.

**ML** — modelos versionados; checkpoints em `models/{dataset}/{region}/{version}/`; seeds fixos e dependências pinadas; inferência em `torch.no_grad()`; datasets grandes só em streaming.

**Base de dados** — migrações versionadas (Supabase CLI); soft delete em produção; índices GIST em colunas geoespaciais; `EXPLAIN ANALYZE` para queries > 1 s; RLS em todas as tabelas; sem `SELECT *`.

**Frontend** — estado em `st.session_state`; componentes em `frontend/components/`; páginas em `frontend/pages/`; sem JS customizado salvo justificação.

**Testes** — cobertura ≥ 70%; testes unitários para todos os `services/`; integração para endpoints críticos; APIs externas sempre mockadas nos testes.

**Git** — Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`); branches `feature/*`, `fix/*`; squash merge; PR com descrição e checklist.

**Performance** — tarefas > 30 s em Celery; paginação em listagens; lazy loading.

**Documentação** — README e CHANGELOG (Keep a Changelog) atualizados por feature.

## 4.3 Proibições
`print()` em produção (usar `logging`) · `except:` genérico · `eval()`/`exec()` · PII em logs · deploy manual · force push em `main`/`develop` · commits diretos em `main`.
