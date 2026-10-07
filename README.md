# Viva — rede social de uma cidade fictícia

Aplicação web (PWA) de rede social ficcional com simulação de mundo persistente:
posts, DMs com NPCs, eventos interativos, relacionamentos multidimensionais,
memórias e um mundo que continua vivendo com o app fechado.

Documentação de arquitetura: [`ARCHITECTURE.md`](./ARCHITECTURE.md)

## Requisitos

- Python 3.14+
- Node.js 22+
- (opcional) Chave de API do **Groq** para respostas de IA dos NPCs
  — sem chave, tudo funciona com o fallback determinístico (`MockLLMProvider`)

## Estrutura

```text
status/
├── frontend/    React + TypeScript + Vite + Tailwind + PWA
├── backend/     FastAPI + SQLModel + Alembic
├── data/app.db  banco SQLite (criado automaticamente)
├── docs/
├── ARCHITECTURE.md
└── README.md
```

## Execução local

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # edite se quiser: GROQ_API_KEY, JWT_SECRET
python -m app.database.migrate   # cria o banco data/app.db + migrations
python -m app.database.seed      # seed idempotente (cidade, NPCs, jobs)

uvicorn app.main:app --reload --port 8000
```

- API: `http://localhost:8000/docs` (Swagger)
- Banco: `data/app.db`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

- App: `http://localhost:5173`

### 3. Usar o Groq (opcional)

Em `backend/.env`:

```env
GROQ_API_KEY=sua_chave_aqui
```

Reinicie o backend. Enquanto a chave não existir (ou a taxa de requisições for
atingida), DMs e eventos usam o fallback determinístico — ideal para testes e
desenvolvimento offline. Com a chave ativa os NPCs respondem via Groq Cloud:

| Uso | Modelo |
|---|---|
| DM, cenas de eventos, resumos | `openai/gpt-oss-20b` |
| Posts automáticos de NPCs | `openai/gpt-oss-120b` |

Se a cota da Groq estourar (HTTP 429), a conversa continua guardada e a
resposta do NPC vem com um aviso de "mensagem guardada, responde depois".

## Acessar pelo celular (mesma rede)

1. Suba o backend normalmente.
2. No frontend: `npm run dev -- --host` e acesse `http://<IP-da-máquina>:5173`
   pelo celular.
3. O backend deve ter `CORS_ORIGINS` incluindo `http://<IP-da-máquina>:5173`.

## PWA

O build de produção (`npm run build` + `npm run preview`) registra o service worker
e permite **"Adicionar à tela inicial"**. Em desenvolvimento o service worker fica
desativado para evitar cache confuso.

## Testes

```bash
# backend
cd backend && source .venv/bin/activate && pytest

# cobertura
pytest --cov=app
```

Os testes rodam com `GROQ_API_KEY` vazia — nenhuma chamada externa, sem custo de IA.

```bash
# frontend E2E (Playwright) — precisa do backend na porta 8000
npm run test:e2e
```

O E2E (Fase 13) cobre o fluxo completo: conta → onboarding → post no feed →
explorar e seguir um NPC → conversar com o NPC → criar evento → avançar o
relógio do mundo.

## Variáveis de ambiente (`backend/.env`)

| Variável | Obrigatória | Descrição |
|---|---|---|
| `GROQ_API_KEY` | não | chave da Groq Cloud; ausente → fallback determinístico |
| `JWT_SECRET` | sim (gerado no `.env.example`) | segredo do token |
| `DATABASE_URL` | não | default `sqlite:///../data/app.db` |
| `CORS_ORIGINS` | não | default `http://localhost:5173` |

## Migrations

```bash
cd backend
alembic upgrade head          # aplicar
alembic revision --autogenerate -m "msg"  # gerar nova migration
```

O schema nunca é alterado manualmente.

## Estratégia futura (fora do MVP)

```text
SQLite → PostgreSQL          (troca de DATABASE_URL, sem mudar domínio)
Frontend → Vercel            (HTTPS habilita PWA instalável)
Backend FastAPI → hospedagem adequada
Imagens → storage persistente
```

Nada disso é necessário para desenvolver e validar o produto.
