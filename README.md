# City Planner Geo

Sistema de Planeamento de Cidades Geolocalizadas: plataforma web em Python que apoia
arquitetos urbanistas e planeadores na análise de construções por região, combinando
contexto ecológico, morfologia urbana, cálculo estrutural e análise de materiais.

> Os resultados são pré-dimensionamento e apoio à decisão. Não substituem projeto de
> especialidade nem verificação normativa.

## Estado
Fase 0 (setup). Ver [`docs/memory.md`](docs/memory.md) e [`docs/Tasks.md`](docs/Tasks.md).

## Documentação
| Documento | Conteúdo |
|-----------|----------|
| [PRD](docs/PRD.md) | Requisitos do produto |
| [System Architecture](docs/System_Architecture.md) | Arquitetura e stack |
| [Design](docs/Design.md) | Fluxos e componentes de UI |
| [Rules](docs/Rules.md) | Regras de contribuição (obrigatórias) |
| [Tasks](docs/Tasks.md) | Tarefas sequenciais |
| [Memory](docs/memory.md) | Estado e decisões do projeto |

## Estrutura
```
backend/    FastAPI (app/api, app/services, app/tasks)
frontend/   Streamlit (pages, components)
shared/     Schemas e constantes partilhados
models/     Checkpoints ML (gitignored)
data/       Cache local (gitignored)
docs/       Documentação
tests/      Testes e fixtures
scripts/    Setup e migrações
```

## Contribuir
Siga `docs/Rules.md`: Conventional Commits, PRs pequenos (< 400 linhas), uma tarefa de cada vez.

## Licença
MIT
