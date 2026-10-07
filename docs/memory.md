# memory

**Propósito:** armazenamento e gestão do estado do projeto. Atualizar **no fim de cada dia de trabalho**; manter um único processo `[~]` ativo.

## 6.1 Estado atual

| Campo | Valor |
|-------|-------|
| Última alteração | 2026-10-06 (fim do dia) |
| Fase | Fase 0 — Setup |
| Versão | 0.1.0 (documentação) |
| Processo ativo | Nenhum (próximo: T0.4) |
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
- **D5** MVP usa GBIF, InterGeoPT, TimoDS, The Well (streaming); restantes datasets em v1.0+
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

**Próximo passo:** T0.4

## 6.3 Processo atual (um por vez)

| Campo | Valor |
|-------|-------|
| ID | T0.4 |
| Nome | Supabase |
| Estado | `[ ]` não iniciado |
| Dependências | T0.1 |
| Checklist | projeto Supabase · PostGIS · esquema inicial · RLS · buckets de Storage |

## 6.4 Fila de processos

| Ordem | ID | Nome | Estado |
|-------|----|------|--------|
| 1 | T0.1 | Repositório e estrutura | `[x]` |
| 2 | T0.2 | Ambiente de desenvolvimento | `[x]` |
| 3 | T0.3 | CI | `[x]` |
| 4 | T0.4 | Supabase | `[ ]` |
| 5 | T0.5 | Auditoria de fontes de dados | `[ ]` |
| 6 | T0.6 | Sentry + CD staging | `[ ]` |
| 7 | T1.1 | Backend base | `[ ]` |

## 6.5 Métricas

| Métrica | Atual | Meta MVP |
|---------|-------|----------|
| Tarefas de setup concluídas | 3 | 6 |
| Cobertura de testes | 0% | 70% |
| Fontes integradas | 0 | 4 |
| Staging | não | sim |

## 6.6 Riscos

| ID | Risco | Prob. | Impacto | Mitigação |
|----|-------|-------|---------|-----------|
| R1 | Limites de taxa/indisponibilidade de APIs (GBIF, InterGeoPT) | Média | Alto | Cache, backoff, fallback estático |
| R2 | Custo/tamanho do The Well | Alta | Médio | Streaming, subconjuntos, cache LRU |
| R3 | Cobertura InterGeoPT incompleta | Média | Médio | Verificar em T0.5; dados estáticos de reserva |
| R4 | Datasets sem cobertura em Portugal (CITYLID, Glasgow) | Alta | Médio | Usar para validar métodos, não como fonte local |
| R5 | Responsabilidade por resultados de engenharia | Média | Alto | Aviso obrigatório, validação contra referências, rótulo de estimativa |
| R6 | Licenças de datasets incompatíveis com uso comercial | Média | Alto | Auditoria em T0.5 |
| R7 | Vendor lock-in Supabase | Baixa | Médio | PostgreSQL padrão |

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
