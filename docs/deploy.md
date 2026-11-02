# Deploy de staging (T0.6)

Backend no Render, frontend no Streamlit Community Cloud, base de dados no Supabase. Nada disto
corre sozinho: precisa de contas e de segredos que só o utilizador pode criar.

## 1. Sentry
1. Criar um projeto Sentry de plataforma Python/FastAPI e copiar o DSN.
2. O DSN vai para o Render (passo 2). Sem `SENTRY_DSN` o Sentry fica desligado.
3. A aplicação não envia cabeçalhos, cookies, IP nem corpo dos pedidos (`send_default_pii=False`,
   `max_request_body_size="never"`).

## 2. Backend (Render)
1. No Render: New → Blueprint, escolher este repositório. Lê o `render.yaml` (branch `develop`).
2. Preencher quando pedir: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`,
   `SENTRY_DSN` e `BACKEND_CORS_ORIGINS` (JSON com o URL do frontend, por exemplo
   `["https://o-meu-app.streamlit.app"]`).
3. O Redis (`city-planner-geo-redis`) é criado e ligado a `REDIS_URL` automaticamente.
4. `autoDeployTrigger: checksPass`: cada merge no `develop` faz deploy depois de o check `checks`
   passar. O CI corre também em `push` para esse efeito.
5. Verificar `https://<serviço>.onrender.com/health`.

Limitações do plano gratuito: o serviço adormece sem tráfego (o primeiro pedido demora) e não
há worker Celery: as tarefas de orquestração ainda não têm um módulo de worker (`backend/app/tasks`
está vazio).

## 3. Frontend (Streamlit Community Cloud)
1. New app → este repositório, branch `develop`, ficheiro `frontend/app.py`.
2. As dependências vêm de `frontend/requirements.txt` (só as do frontend). Sem ele, o Streamlit instala as do `pyproject.toml` (backend incluído) e a instalação pode falhar. Em Advanced settings escolher Python 3.12.
3. Em Advanced settings → Secrets:

```
BACKEND_URL = "https://<serviço>.onrender.com"
SUPABASE_URL = "https://<projeto>.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_..."
```

Nunca pôr `SUPABASE_SECRET_KEY` no frontend.

## 4. Supabase
- Authentication → URL Configuration: acrescentar o URL do frontend em Site URL / Redirect URLs.
- Migrações: `supabase db push` à mão, a partir da máquina do programador (decisão D28).

## 5. Verificar o backend publicado
```
SMOKE_TOKEN=<JWT de um utilizador de teste> \
  poetry run python scripts/smoke_staging.py https://<serviço>.onrender.com
```
Confirma `/health`, que as rotas protegidas recusam pedidos anónimos e que uma viga conhecida dá
a flecha da solução fechada. Sem `SMOKE_TOKEN` só faz as duas primeiras verificações. O JWT obtém-se
iniciando sessão no frontend com um utilizador de teste; não o cole em conversas nem em commits.
O primeiro pedido pode demorar até um minuto (o plano gratuito adormece).

## 6. Pendente de verificar
- O `Dockerfile` não foi construído neste ambiente (sem daemon Docker). Verificar o primeiro build
  no Render; se faltar uma biblioteca de sistema do WeasyPrint, o erro aparece ao gerar um PDF.
