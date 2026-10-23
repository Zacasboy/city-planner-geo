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
supabase/   Migrações SQL, testes de BD e instruções (ver supabase/README.md)
models/     Checkpoints ML (gitignored)
data/       Cache local (gitignored)
docs/       Documentação
tests/      Testes e fixtures
scripts/    Setup e migrações
```

## Ambiente de desenvolvimento
Requisitos: Python 3.11 ou 3.12 e [Poetry](https://python-poetry.org/docs/#installation).

```bash
poetry install                                   # dependências (inclui ferramentas de dev)
cp .env.example .env                             # preencher valores localmente
poetry run pre-commit install -t pre-commit -t commit-msg
```

Verificações (corra localmente antes de abrir um PR; o CI repete-as em cada PR):

```bash
poetry run ruff check .      # lint (inclui proibição de print/except genérico/eval)
poetry run black --check .   # formatação
poetry run mypy              # tipos (strict)
poetry run pytest            # testes + cobertura mínima de 70%
```

O pre-commit corre ruff, black e mypy automaticamente em cada commit; o pytest tem de ser
corrido manualmente. O workflow `.github/workflows/ci.yml` (GitHub Actions) corre as quatro
verificações em cada Pull Request para `main` ou `develop`, no job `checks`.

O pre-commit bloqueia commits diretos em `main`/`develop` e mensagens fora do padrão
Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).

## Contribuir
Siga `docs/Rules.md`: Conventional Commits, PRs pequenos (< 400 linhas), uma tarefa de cada vez.

## Licença
MIT
