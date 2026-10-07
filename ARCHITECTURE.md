# ARCHITECTURE — Rede Social da Cidade (Viva)

> Documento de arquitetura da aplicação. Fonte de verdade sobre entidades, estados,
> contratos e decisões. Atualizar este documento a cada mudança estrutural.

---

## 1. Visão

Rede social ficcional persistente de uma cidade fictícia ("Vila Serena"), com uma
simulação de mundo rodando por trás. O jogador é um morador entre vários — os NPCs
vivem, trabalham, postam, conversam e criam eventos mesmo com o app fechado.

Loop central do produto:

```text
FEED → POST → DM → EVENTO → INTERAÇÃO → RELACIONAMENTO → MEMÓRIA
   → FUTURO EVENTO/DM → POST → FEED
```

## 2. Stack e infraestrutura (MVP local)

| Camada | Tecnologia |
|---|---|
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS v4 + vite-plugin-pwa + react-router |
| Backend | Python 3.14 + FastAPI + Pydantic v2 + SQLModel |
| Banco | SQLite em `data/app.db` (Alembic para migrations) |
| LLM | Abstração `LLMProvider` → `GroqProvider` (gpt-oss) / `MockLLMProvider` |
| Auth | JWT (PyJWT) + hash bcrypt |

Regras de infraestrutura:

- **100% local** durante o MVP. Sem Vercel/Supabase/Neon/PostgreSQL para começar.
- Nenhum segredo no frontend. LLM é chamado somente pelo backend.
- SQLite escolhido para desenvolvimento; a persistência é feita apenas via
  SQLModel/SQLAlchemy para permitir migração futura para PostgreSQL sem reescrever
  domínio, serviços ou regras de negócio.

## 3. Estrutura do projeto

```text
status/
├── frontend/
│   └── src/
│       ├── app/            # router, providers, layout
│       ├── components/     # componentes genéricos (UI kit)
│       ├── features/
│       │   ├── feed/
│       │   ├── messages/
│       │   ├── events/
│       │   ├── profiles/
│       │   ├── notifications/
│       │   ├── milestones/
│       │   ├── characters/
│       │   ├── world/
│       │   └── admin/
│       ├── hooks/
│       ├── services/       # cliente HTTP (fetch), tipos de API
│       ├── styles/
│       └── types/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── public/     # rotas autenticadas/domínio
│   │   │   └── admin/      # rotas de administração do mundo
│   │   ├── domain/         # regras de negócio (characters, events, relationships…)
│   │   ├── models/         # modelos SQLModel (tabelas)
│   │   ├── schemas/        # schemas Pydantic de request/response/LLM
│   │   ├── services/       # casos de uso (orchestram domain + repository)
│   │   ├── llm/            # providers, context builders, prompts, validation
│   │   ├── database/       # engine, session, repositories, alembic
│   │   └── main.py
│   ├── alembic/
│   └── tests/
├── data/app.db             # criado automaticamente, fora do git
├── docs/
├── ARCHITECTURE.md
└── README.md
```

Fluxo de dependência: `api → services → domain → repositories → database`.
Endpoints não contêm regra de negócio.

## 4. Conceito User ≠ Character

- **User**: conta de acesso (email, senha). Autenticação/autorização.
- **Character**: pessoa dentro da cidade (jogador ou NPC). Vida social, rotina, dinheiro.

Um `User` possui até um `Character` ativo no MVP (`active_character_id`), mas o campo
permite múltiplos personagens no futuro. NPCs não têm `User`.

## 5. Entidades

Campos principais listados por domínio. Todos os modelos têm `id` (UUID ou int),
`created_at` e, quando aplicável, `updated_at`.

### 5.1 Conta

| Entidade | Campos principais |
|---|---|
| `User` | email, password_hash, active_character_id?, is_admin, is_active |

### 5.2 Mundo

| Entidade | Campos principais |
|---|---|
| `District` | name, slug, description, sort_order |
| `Location` | name, slug, district_id, kind (cafe/restaurante/loja/rua/park/trabalho/casa/arcade), description, opening_hours (JSON: dia→{open,close}), activities (JSON), is_public |
| `Job` | title, description, employer_location_id?, salary_per_shift, schedule_template (JSON) |
| `Schedule` | character_id, day_of_week (0–6 ou null=todos), start_time, end_time, activity, location_id? |
| `WorldState` | singleton: current_date, current_time, last_simulated_at, last_catchup_at, day_of_week (derivado) |
| `SimulationLog` | ran_at, kind (bootstrap/catchup/manual/routine), elapsed_minutes, summary, payload (JSON) |

### 5.3 Personagens

| Entidade | Campos principais |
|---|---|
| `Character` | user_id? (null = NPC), name, age, pronouns, bio, profession_label, is_npc, personality (JSON), communication_style, hobbies/likes/dislikes/goals/flaws (JSON arrays), favorite_location_ids (JSON), money, discovered_level (descoberta gradual), photo_id?, seed_photo_key?, created_at |
| `CharacterPhoto` | character_id, source (seed/manual/upload), path, label, is_primary |
| `CharacterJob` | character_id, job_id, is_primary, started_at, ended_at? |

`personality` JSON: `{ big_five_ish: {...}, tone, energy, formality, humor, emoji_usage }`
usado pelo context builder do LLM.

### 5.4 Social (feed)

| Entidade | Campos principais |
|---|---|
| `Post` | author_character_id, content, kind (post/event/news/system), location_id?, event_id?, created_at |
| `Comment` | post_id, author_character_id, content, parent_comment_id?, created_at |
| `Like` | target_type (post/comment), target_id, character_id, created_at — único por par |
| `Follow` | follower_character_id, followed_character_id, created_at — único por par |
| `Notification` | character_id (destinatário), type (enum abaixo), payload (JSON: rota + ids), created_at, read_at? |

Tipos de notificação (sempre com ação navegável):

```text
NEW_MESSAGE        → /messages/{conversationId}
EVENT_INVITE       → /events/{eventId}
EVENT_STARTING     → /events/{eventId}
EVENT_CANCELLED    → /events/{eventId}
POST_LIKE          → /posts/{postId}
POST_COMMENT       → /posts/{postId}
NEW_FOLLOWER       → /profile/{characterId}
RELATIONSHIP_CHANGE→ /profile/{characterId}
MILESTONE          → /settings/world/relationships
NPC_DM_INITIATIVE  → /messages/{conversationId}
EVENT_RESULT       → /events/{eventId}
```

### 5.5 Mensagens diretas

| Entidade | Campos principais |
|---|---|
| `Conversation` | character_a_id, character_b_id (par ordenado e único), last_message_at, created_at |
| `ConversationSession` | conversation_id, status (ACTIVE/IDLE/ENDED), started_at, ended_at?, ended_reason? |
| `Message` | conversation_id, session_id, sender_character_id, content, created_at |

- A conversa (par) é **permanente**; sessões terminam e novas podem começar.
- Mensagem só existe após confirmação do backend (sem "mensagem fantasma" no cliente).
- O NPC pode iniciar conversa: cria `Conversation` + `ConversationSession` + primeira
  `Message`, e uma notificação.

### 5.6 Eventos

| Entidade | Campos principais |
|---|---|
| `Event` | title, description, location_id, host_character_id?, created_by (user/npc/system), scheduled_at, status, kind (social/dinner/arcade/festival/work), max_participants?, cancel_reason? |
| `EventParticipant` | event_id, character_id, status (INVITED/ACCEPTED/DECLINED/JOINED/WITHDREW), responded_at?, joined_at? |
| `EventSession` | event_id, player_character_id, status, turn_count, last_activity_at, started_at, ended_at?, resume_count, outcome_id? |
| `EventTurn` | session_id, turn_index, narrative, dialogue (JSON [{character,text}]), available_actions (JSON [{id,label}]), player_action_id?, player_action_label?, created_at |
| `EventOutcome` | session_id (único), summary, relationship_changes (JSON), memories (JSON), social_effects (JSON), future_hooks (JSON), applied_at |
| `FutureHook` | source_type (event/dm), source_id, target_character_id, kind (dm_message/event_invite), payload, due_at, status (PENDING/CONSUMED/EXPIRED) |

### 5.7 Relacionamentos e memória

| Entidade | Campos principais |
|---|---|
| `Relationship` | character_a_id, character_b_id (par ordenado e único), familiarity, friendship, trust, romance, respect, tension (0–100 cada), last_interaction_at, updated_at |
| `Memory` | owner_character_id, other_character_id?, category (IMPORTANT/NORMAL/TEMPORARY), kind (first_meeting/promise/favor/argument/date/discovered_preference/shared_experience/secret), content, context (JSON), occurred_at, importance (0–100), source_event_id?, dedupe_key? |

Dimensões com invariantes aplicadas pelo domínio:
`0 <= cada dimensão <= 100`. Mudanças são **sugeridas** pelo LLM e **aplicadas**
apenas pelo `RelationshipService`, com clamp e log.

### 5.8 Milestones

| Entidade | Campos principais |
|---|---|
| `StoryMilestone` | key, name, description, threshold (default 5) |
| `MilestoneProgress` | key (único), qualifying_count, pending_opportunity (bool), last_opportunity_at? |

Regra: a cada `threshold` de progresso (default 5) o milestone libera
`pending_opportunity`; o usuário resgata via `POST /api/milestones/{key}/claim`
(+80 Vivas). Eventos cancelados não contam; abandonados não contam.

## 6. State machines

### 6.1 Event (status)

```text
SCHEDULED ──open──→ OPEN ──start──→ ACTIVE ──complete──→ COMPLETED (terminal)
   │  │             │   │            │
   │  └─start──→ ACTIVE    └─cancel──→ CANCELLED (terminal)
   └─cancel──→ CANCELLED (terminal)
```

- `SCHEDULED` pode ir direto a `ACTIVE` ("start", ex.: jogador entra cedo).
- Recovery: `check_open_events()` abre `SCHEDULED → OPEN` quando `scheduled_at <= now`.
- Transições válidas declaradas num dict `_EVENT_TRANSITIONS` em `app/domain/events.py`;
  qualquer outra transição é erro de domínio. `COMPLETED`/`CANCELLED` são terminais.

### 6.2 EventSession

```text
ACTIVE ──complete──→ COMPLETED (terminal)
ACTIVE ──abandon──→ ABANDONED (terminal)
```

Cada tentativa de entrar gera uma sessão ativa; só há uma sessão por evento por vez.
`POST /api/events/{id}/sessions` cria a primeira ou devolve a ativa (idempotente).

### 6.3 ConversationSession

```text
ACTIVE ⇄ IDLE (inatividade)
ACTIVE|IDLE → ENDED (despedida, conclusão, sessão nova iniciada)
```

### 6.4 EventParticipant

```text
INVITED → ACCEPTED | DECLINED
ACCEPTED → JOINED | WITHDREW
JOINED → WITHDREW
DECLINED → ACCEPTED
```

### 6.5 Regras críticas

- **Nenhum evento/sessão fica preso**: todo caminho termina em estado final.
- **Idempotência**: `finish_event(session_id)` — se `COMPLETED`, retorna o
  outcome existente sem reaplicar nada. Chave: `EventOutcome.session_id` único.
- **Resolução atômica**: `BEGIN → aplicar relationship/memory/notification/social
  effects/future hooks → salvar outcome → marcar COMPLETED → COMMIT`; falha = ROLLBACK.
- **Recovery**: sessões `ACTIVE` com `last_activity_at` antigo são resolvidas no
  boot/catch-up → resume | abandon | complete | cancel.

## 7. Contratos da API

Prefixo `/api`. Auth: header `Authorization: Bearer <jwt>`. Todas as respostas de
erro: `{ "detail": "mensagem humana" }` (HTTP 4xx/5xx) — nunca vazar stacktrace.

### 7.1 Auth (`/api/auth`)

```text
POST   /api/auth/register      {email, password} → {token, user}
POST   /api/auth/login         {email, password} → {token, user}
GET    /api/auth/me            → {user, active_character}
```

### 7.2 World (`/api/world`)

```text
GET    /api/world              → WorldState (date, time, day_of_week, last_simulated_at)
GET    /api/world/districts    → District[]
GET    /api/world/locations    → Location[]  (filtro ?district=)
GET    /api/world/catchup-report → {elapsed_minutes, summary[]}  (o que aconteceu fora)
```

### 7.3 Characters (`/api/characters`)

```text
GET    /api/characters                 → lista (descoberta gradual aplicada)
GET    /api/characters/{id}            → perfil público + relationship? (do viewer)
GET    /api/characters/{id}/posts      → posts do personagem
GET    /api/characters/{id}/memories   → memórias visíveis ao viewer
GET    /api/characters/{id}/relationship → Relationship (viewer × alvo)
POST   /api/characters/{id}/follow     / DELETE
POST   /api/characters/{id}/dm         → cria/recupera Conversation (inicia sessão)
```

### 7.4 Feed (`/api/feed`, `/api/posts`, `/api/comments`)

```text
GET    /api/feed?cursor=&limit=        → {items: [...], next_cursor}  (persistente)
POST   /api/posts                      {content, location_id?} → Post
GET    /api/posts/{id}                 → Post + comments
DELETE /api/posts/{id}                 (autor)
POST   /api/posts/{id}/like            / DELETE
GET    /api/posts/{id}/comments        → Comment[]
POST   /api/posts/{id}/comments        {content} → Comment
POST   /api/comments/{id}/like         / DELETE
```

### 7.5 Messages (`/api/conversations`)

```text
GET    /api/conversations                       → lista ordenada por last_message_at
GET    /api/conversations/{id}                  → conversa + sessão atual
GET    /api/conversations/{id}/messages?cursor= → Message[] (histórico persistido)
GET    /api/conversations/{id}/sessions         → ConversationSession[]
POST   /api/conversations/{id}/messages         {content} → {message, npc_reply?}
                                                 (ACK do backend antes de exibir)
POST   /api/conversations/{id}/end-session      → encerra sessão atual
```

Resposta do NPC: chamada LLM síncrona com timeout; em falha, HTTP 503 com mensagem
humana e a sessão permanece intacta (frontend mostra "Tentar novamente").

### 7.6 Events (`/api/events`)

```text
GET    /api/events?mine=                    → Event[] (mine filtra participação)
POST   /api/events       {title, description, location_id, scheduled_at, invitees[]} → Event
GET    /api/events/{id}           → Event + participants + am_host
POST   /api/events/{id}/rsvp      {accept: bool} → EventDetail
POST   /api/events/{id}/cancel    {reason?} → Event
POST   /api/events/{id}/sessions  → SessionState (cria/recupera sessão ativa)
GET    /api/events/{id}/sessions  → SessionSummary[]
GET    /api/events/sessions/{id}  → SessionState (última cena + turnos)
POST   /api/events/sessions/{id}/actions  {action_id} → TurnOut (próxima cena)
POST   /api/events/sessions/{id}/end      → OutcomeOut (resolução completa)
POST   /api/events/sessions/{id}/abandon  → SessionSummary (volta ao evento)
GET    /api/events/sessions/{id}/outcome  → OutcomeOut
```

- Host entra `JOINED` automaticamente; convidados entram `INVITED` (notificação
  `EVENT_INVITE` para jogadores).
- O frontend envia **apenas `action_id`**; o backend resolve efeitos (dinheiro,
  memória com `dedupe_key`, relacionamento via clamp) e gera a próxima cena.
- `end` é idempotente: sessão `COMPLETED` retorna o outcome existente.
- Abandonar marca sessão `ABANDONED` e participante `WITHDREW`; o evento volta a
  `OPEN` se não houver outra sessão ativa.

### 7.7 Relationships / Memories / Notifications / Milestones

```text
GET    /api/relationships                  → Relationship[] do viewer
GET    /api/notifications?unread=          → Notification[]
POST   /api/notifications/{id}/read        / POST /api/notifications/read-all
GET    /api/milestones                     → StoryMilestone[] + progress
POST   /api/milestones/{key}/claim         → libera oportunidade de criar personagem
```

### 7.8 Simulation (`/api/simulation`)

```text
POST   /api/simulation/catchup  ?minutes=&with_social= → CatchUpReport (manual; também roda no boot)
GET    /api/simulation/logs     → SimulationLog[]
```

Catch-up: calcula `elapsed = now_real − agora_simulado` (cap 15–1440 min), avança
o relógio, paga turnos de trabalho, abre eventos vencidos e, se mudou o dia,
gera posts de NPCs (quando `with_social=true`). Resultado vira `SimulationLog`
exibido em `GET /api/world/catchup-report`.

### 7.9 Admin (`/api/admin`, requer `is_admin`)

```text
GET/POST        /api/admin/characters      lista/cria (NPC)
GET/PATCH       /api/admin/characters/{id} edição (nível descoberta, bio, dinheiro, humor…)
GET/PATCH/DELETE /api/admin/relationships  consulta/edite/apague dimensões
GET/POST/DELETE /api/admin/memories        CRUD de memórias
GET/POST/PATCH/DELETE /api/admin/jobs
GET/POST/DELETE /api/admin/locations
GET/POST        /api/admin/districts
POST            /api/admin/simulation/routines  ?minutes=&with_social= (economia + schedule)
```

Edições manuais têm prioridade sobre conteúdo gerado por IA e refletem
imediatamente em perfil, feed, DMs, eventos e simulação.

## 8. Camada LLM

### 8.1 Provider

```python
class LLMProvider(Protocol):
    async def generate(self, *, prompt: str, schema_name: str,
                       system: str, temperature: float = 0.8) -> str: ...
```

- `GroqProvider`: API do Groq Cloud (`api.groq.com/openai/v1`), chave em `GROQ_API_KEY` (`.env` do backend).
  Dois modelos: `quick` (`openai/gpt-oss-20b`) para DM/respostas rápidas e `standard` (`openai/gpt-oss-120b`)
  para conteúdo importante (posts públicos dos NPCs).
- Limite da API atingido (HTTP 429) → `RateLimitError`: a mensagem enviada é mantida e a resposta
  `POST /api/conversations/{id}/messages` volta com `npc_reply=null` e `warning`, exibido em tela
  pelo frontend (`WarningBanner`).
- `MockLLMProvider`: respostas determinísticas para testes e desenvolvimento sem chave.
- Seleção em `backend/app/llm/__init__.py`: sem chave → mock (log avisando).

### 8.2 Context builders

Cada builder monta **só o necessário** — nunca o banco inteiro:

| Builder | Contexto |
|---|---|
| `DMContextBuilder` | personalidade, estilo de fala, relationship_state, memórias relevantes (top-N por importância/recência), últimas ~12 mensagens, hora/dia/local atual, world blurb |
| `EventContextBuilder` | local, hora, participantes + personalidade, relationships, memórias relevantes, últimos turnos (últimos 4), estado do mundo |
| `PostContextBuilder` | personalidade, rotina do dia, relationship com o jogador, eventos recentes |

Recuperação de memórias: `relevance = importance + recência + tipo` → top 5–8.
Memórias `TEMPORARY` têm TTL e saem do contexto.

### 8.3 Validação de saída

```text
resposta bruta → parse JSON → Pydantic schema → domain validation → persistência
```

Schemas Pydantic: `DMReply`, `EventScene`, `PostSuggestion`.
- JSON inválido/schema inválido → **retry 1x** → falha controlada (503 / UI de retry).
- `suggested_consequences` do LLM são **sugestões**: o serviço de domínio valida
  limites (clamp 0–100, delta máximo por turno, tipos permitidos) e decide.

### 8.4 O que usa LLM vs. código determinístico

| LLM (pagar por quê) | Determinístico (nunca LLM) |
|---|---|
| Resposta de DM | Tempo, rotina, horário |
| Cena narrativa de evento | Salário, economia |
| Posts significativos de NPC | Agendamento de eventos |
| Decisões sociais pontuais | Open/close de locais |
| | Curtidas, follows triviais |
| | Notificações, milestones, recovery |
| | Catch-up de rotina |

Anti-spam: NPCs não postam/mensageiam toda hora; limites por dia por NPC;
períodos de silêncio respeitados.

## 9. Simulação e tempo

- `WorldState` guarda data/hora canônicas. Relógio avança por:
  `POST /api/simulation/advance` (dev) ou **catch-up automático** quando o usuário
  abre o app.
- **Catch-up**: calcula `elapsed = now_real − last_simulated_at` (limitado, ex. máx.
  24h por passo), converte em passos de simulação (30–60 min), para cada passo:
  atualiza rotina/local dos NPCs (blocos de tempo), processa expediente/salário,
  atualiza status de eventos, gera no máximo **poucos** acontecimentos sociais
  relevantes (posts, DMs de NPC, convites) — qualidade > quantidade.
- Cada catch-up gera `SimulationLog` + `catchup-report` para o usuário ver
  "o que aconteceu enquanto você estava fora".
- NPCs rodam sem LLM na rotina; LLM só quando há conteúdo social a gerar.

## 10. Persistência, transações e migrações

- Engine SQLAlchemy via SQLModel; session por request (`FastAPI Depends`).
- Transações obrigatórias em: `finish_event/apply_outcome`, `send_message`,
  `relationship_update`, `memory_creation`, `character_edit`, catch-up.
- Migrations: **Alembic** desde o início (`alembic upgrade head` no setup).
  Seed inicial (distritos, locais, NPCs, jobs, milestones) como migration/seed script
  idempotente (`python -m app.database.seed`).
- Caminho para PostgreSQL: nada de SQL bruto específico de SQLite; tipos JSON
  usam `JSON` do SQLAlchemy (compatível com os dois); UUIDs/texto padronizados;
  `DATABASE_URL` em `.env` troca o dialect sem tocar no domínio.

## 11. Segurança

- `.env` no backend apenas (`GROQ_API_KEY`, `JWT_SECRET`, `DATABASE_URL?`,
  `CORS_ORIGINS`). `.env.example` versionado. `.env` no `.gitignore`.
- JWT com expiração; senha com bcrypt; validação Pydantic em toda request.
- Frontend nunca confiado para: consequências, dinheiro, relacionamentos, memórias,
  estados de evento.
- CORS restrito a `http://localhost:5173` (+ IP da LAN em dev mobile).
- Estrutura pronta para publicação: auth separada de autorização, `is_admin`
  para `/api/admin`.

## 12. Frontend

Rotas:

```text
/login  /register
/feed
/explore
/messages  /messages/:conversationId
/events  /events/:eventId  /events/session/:sessionId
/profile/:characterId
/posts/:postId
/notifications
/world
/settings
/settings/world  /settings/world/characters  /settings/world/characters/:characterId
/settings/world/relationships  /settings/world/memories  /settings/world/jobs
/settings/world/locations  /settings/world/simulation
```

- **Mobile-first**: bottom nav (Home, Explorar, Mensagens, Eventos, Perfil),
  safe areas, sem hover obrigatório, alvos de toque ≥44px, suporte a teclado virtual.
- **Desktop**: sidebar esquerda + feed central + painel contextual direito.
- Estados de carregamento/erro/vazio em toda tela que depende de backend
  (§85–87 do master prompt).
- PWA: manifest + ícones + service worker (cache de app shell, rede-first para API),
  instalável.
- Cliente HTTP único com tratamento de 401 → login; erros exibem mensagem humana.

## 13. Testes

`backend/tests/` com pytest + `GROQ_API_KEY` vazio (fallback determinístico, sem
chamada externa — 60 testes verdes):

- unit: domínio (relacionamentos/invariantes, memórias, state machines, economia),
  validação de saída LLM, context builders.
- API: auth, feed, DMs, eventos, admin, notificações.
- integração: catch-up/simulação, **fluxo social completo** (feed→post→DM→evento→
  memória→future hook→consequência), **5 cenários de evento** (natural, manual,
  abandono+recovery, cancelamento, idempotência ×3), **ciclo de DM** completo,
  **recuperação** (sessão de evento presa → ABANDONED/WITHDREW/OPEN; DM ociosa →
  IDLE; novo DM após IDLE → sessão nova ativa).
- E2E (Playwright, `frontend/e2e/happy-path.spec.ts`): conta → onboarding →
  feed (post) → explorar/seguir NPC → DM com NPC → criar evento → avançar o
  relógio do mundo. Roda com `npm run test:e2e` (backend na porta 8000, Vite
  com proxy `/api` na 5173).

## 14. Fases de implementação

Seguem-se as fases do master prompt (0 a 13). Regra: implementar → testar →
executar → validar → corrigir → documentar → avançar. Deploy/PostgreSQL só na
Fase 14, fora do MVP.

Status atual: **Fases 0–13 implementadas e testadas** (auth/conta, mundo+rotina,
feed, DMs+ciclo NPC, relacionamentos/memórias/milestones, eventos+sessões,
economia, simulação catch-up, admin, polimento, recovery/timeouts, perfis e E2E).

- **Recovery/timeouts (Fase 11)**: sessões de evento `ACTIVE` paradas há +24h →
  `ABANDONED` (participante `WITHDREW`; evento volta a `OPEN` sem outra sessão);
  conversas de DM `ACTIVE` ociosas há +60 min → `IDLE`; nova mensagem abre
  sessão nova ativa. Executado no catch-up (`run_catchup`) e no boot.
- **Perfis (Fase 12)**: página de perfil exibe posts do personagem e o nível de
  descoberta (`discovered_level`, 1–3) para NPCs; `PostCard`/`CommentForm`
  compartilhados entre Feed e Perfil.
- **E2E (Fase 13)**: Playwright com fluxo completo feliz em `frontend/e2e/`.
- **Polimento (Fase 10)**: notificações de `POST_LIKE`/`POST_COMMENT` levam ao
  Feed; `ChatPage` trata erro/429 com aviso visível e recarregamento.
- **Reações sociais no feed**: seguir um NPC é recíproco (o morador devolve o
  follow e avisa com `NEW_FOLLOWER`); a cada avanço de simulação acionado pelo
  usuário, NPCs que seguem um humano curtem (até 3) e comentam os posts dele,
  sem depender do relógio (idempotente). O botão "Pular para o próximo dia"
  roda com `with_social=true`.

Frontend PWA com Feed, Explorar, Mensagens, Perfil, Notificações, Eventos
(lista + detalhe + sessão), Mundo (relógio + catch-up + relatório) e
Configurações (relações/memórias/marcos, painel admin).

## 15. Decisões registradas

| Decisão | Justificativa |
|---|---|
| SQLite + Alembic desde o dia 1 | migração futura sem retrabalho |
| UUID/int auto no banco? → **int autoincremental** | simplicidade SQLite/PG, IDs menores |
| JWT stateless (sem refresh token) | projeto pessoal; estrutura aceita refresh depois |
| DM síncrona (request/response) | simplicidade; streaming fica para futuro |
| Evento = 1 sessão do jogador por vez | simplifica idempotência e recovery |
| Mock LLM como default sem chave | desenvolvimento sem custo/dependência |
| Feed por cursor (created_at, id) | estável com inserções frequentes |

## 16. VIVA V2 — Autonomia e agência

A implementação agora deve tratar o prompt como comportamento de produto, não como checklist de endpoints.

### Ação livre em eventos

ActionRequest aceita action_id ou free_text. Ações sugeridas continuam sendo atalhos, mas não limitam o jogador. A intenção livre é enviada ao contexto narrativo; efeitos de domínio continuam sendo aplicados somente por serviços.

Fluxo:

    ação sugerida OU texto livre
    ↓
    backend valida
    ↓
    LLM interpreta intenção
    ↓
    nova cena
    ↓
    efeitos autorizados pelo domínio

### Consequências assíncronas

Eventos concluídos podem criar FutureHook(kind=dm_message) para um NPC participante. O hook amadurece posteriormente e o catch-up pode entregá-lo como uma DM iniciada pelo NPC. O processamento é idempotente e possui limite de hooks pendentes para evitar spam.

### Iniciativa de NPC

messaging_service.send_npc_initiative() permite que um NPC crie/recupere uma conversa, abra uma sessão e envie uma mensagem sem o jogador iniciar a conversa. A notificação leva diretamente para o DM.

### Regra de produto

O botão de avanço de tempo continua sendo uma ferramenta de desenvolvimento/UX. O mundo deve também produzir consequências por tempo decorrido, future hooks e iniciativas sociais durante catch-up.

### Master Prompt

MASTER_PROMPT_V2.md é a especificação operacional atual para futuras sessões de agente. Ele adiciona agência livre, autonomia NPC↔NPC, iniciativa social, future hooks, descoberta gradual, rumores/segredos e uma Definition of Done baseada em comportamento ponta a ponta.

### Próximos blocos obrigatórios

Ainda devem ser auditados/implementados como evolução do V2:

- grafo social NPC↔NPC persistente e simulado;
- atividades/locais como espaços realmente interativos;
- rumores e segredos persistentes;
- iniciativa social com cooldown/prioridade;
- resolução de evento natural baseada em estado narrativo, sem depender apenas de limite de turnos;
- memória bilateral para experiências relevantes;
- relatório de retorno priorizado por relevância ao jogador.


## 17. VIVA V3 — Motor de mundo vivo

O catch-up social agora é temporal e incremental, através de autonomy_service.

O motor percorre o período simulado em janelas de 90 minutos e pode:

- atualizar posições de NPCs conforme Schedule;
- formar encontros NPC↔NPC em Location;
- alterar dimensões de Relationship;
- criar Memory bilateral;
- gerar tensão/romance emergentes;
- publicar posts espontâneos;
- gerar curtidas/comentários entre NPCs;
- criar rumores públicos ocasionais;
- criar uma atividade Event espontânea por dia;
- convidar o jogador por DM;
- permitir iniciativa proativa de NPCs;
- estabelecer uma primeira conexão social para novos personagens.

### Regra de arquitetura

O motor decide quando, quem e qual tipo de ação deve ocorrer. O LLM só escreve a camada narrativa/textual. Estado de domínio continua sendo materializado por serviços existentes.

A simulação não deve ser reduzida a feed request -> generate content. O feed é uma janela para uma sociedade que já estava funcionando.

### Limites

O V3 usa:
- janelas de 90 minutos;
- limites de posts por NPC/dia;
- cooldown por relacionamento;
- no máximo duas interações por local/janela;
- uma atividade espontânea por dia;
- iniciativa proativa limitada por memória/dia.

Esses limites existem para evitar spam e custo excessivo de LLM, não para tornar o mundo passivo.


## 18. Dinâmica social contínua V4

`autonomous_world_service.py` complementa `autonomy_service.py` com manutenção do grafo social, arrefecimento de tensão, resolução de eventos ambientais, reações NPC, propagação de rumores, reputação e o resumo `city_pulse`. `social_arc_service.py` transforma arcos em DMs e encontros concretos. `feed_service.py` oferece o escopo `for_you`/`popular`, ponderando recência, engajamento, follows e relação com o leitor.

A camada continua sem nova tabela: memórias são usadas como marcadores de deduplicação e histórico. O backend determina consequências; o LLM não recebe autoridade sobre estado.
