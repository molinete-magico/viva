import logging
from datetime import datetime, time, timedelta

from sqlmodel import Session, select

from app.models import (
    Character,
    CharacterJob,
    District,
    Job,
    Location,
    Schedule,
    SimulationLog,
    WorldState,
)
from app.models.base import utcnow

logger = logging.getLogger("viva.seed")

DISTRICTS = [
    {
        "name": "Centro Velho",
        "slug": "centro-velho",
        "description": "Ruas de pedra, fachadas antigas, restaurantes pequenos e o barulho bom de quem caminha.",
        "sort_order": 1,
    },
    {
        "name": "Beira-Rio",
        "slug": "beira-rio",
        "description": "O calçadão, a brisa da água e os encontros que acontecem sem hora marcada.",
        "sort_order": 2,
    },
    {
        "name": "Estação",
        "slug": "estacao",
        "description": "Mercado, oficinas e o movimento de quem começa o dia cedo.",
        "sort_order": 3,
    },
    {
        "name": "Morro Verde",
        "slug": "morro-verde",
        "description": "Ruas em ladeira, jardins cuidados e uma vista que compensa subir a pé.",
        "sort_order": 4,
    },
]

LOCATIONS = [
    {
        "name": "Ramen da Esquina",
        "slug": "ramen-da-esquina",
        "district": "centro-velho",
        "kind": "restaurant",
        "description": "Seis mesas, balcão de madeira e um cheiro que enche a rua. O ponto de encontro da Vila Serena.",
        "opening_hours": {"ranges": [["11:30", "23:30"]], "closed_days": []},
        "activities": ["comer ramen", "conversar", "encontrar amigos", "eventos"],
    },
    {
        "name": "Café Pé de Serra",
        "slug": "cafe-pe-de-serra",
        "district": "morro-verde",
        "kind": "cafe",
        "description": "Café forte, bolos da casa e uma mesa junto à janela perfeita para ler ou observar a ladeira.",
        "opening_hours": {"ranges": [["07:00", "19:00"]], "closed_days": []},
        "activities": ["tomar café", "ler", "estudar", "trabalhar"],
    },
    {
        "name": "Padaria Estrela",
        "slug": "padaria-estrela",
        "district": "estacao",
        "kind": "shop",
        "description": "Pão às 6h da manhã, brigadeiro na vitrine e fila que vira conversa.",
        "opening_hours": {"ranges": [["06:00", "14:00"]], "closed_days": [0]},
        "activities": ["comprar pão", "café rápido", "fofoca"],
    },
    {
        "name": "Mercado Municipal",
        "slug": "mercado-municipal",
        "district": "estacao",
        "kind": "shop",
        "description": "Bancas de fruta, legumes, tempero e gente que sabe o preço de tudo.",
        "opening_hours": {"ranges": [["07:00", "20:00"]], "closed_days": []},
        "activities": ["comprar mantimentos", "encontrar vizinhos"],
    },
    {
        "name": "Oficina Boa Rosca",
        "slug": "oficina-boa-rosca",
        "district": "estacao",
        "kind": "work",
        "description": "Macaco hidráulico, rádio ligado e conserto de tudo que tem roda.",
        "opening_hours": {"ranges": [["08:00", "18:00"]], "closed_days": [0, 6]},
        "activities": ["consertar carro", "puxar conversa"],
    },
    {
        "name": "Livraria Página Aberta",
        "slug": "livraria-pagina-aberta",
        "district": "centro-velho",
        "kind": "shop",
        "description": "Estantes até o teto, gato dormindo na sessão de poesia e cheiro de papel.",
        "opening_hours": {"ranges": [["10:00", "20:00"]], "closed_days": [1]},
        "activities": ["folhear livros", "silêncio", "encontros raros"],
    },
    {
        "name": "Parque da Beira-Rio",
        "slug": "parque-beira-rio",
        "district": "beira-rio",
        "kind": "park",
        "description": "Trilha de terra batida, bancos sob os ipês e a água passando devagar.",
        "opening_hours": {"ranges": [["05:00", "22:00"]], "closed_days": []},
        "activities": ["correr", "passear", "piquenique", "pensar na vida"],
    },
    {
        "name": "Praça do Relógio",
        "slug": "praca-do-relogio",
        "district": "estacao",
        "kind": "street",
        "description": "O relógio de torre marca as horas que ninguém olha. Bancos, pombos e quem espera ônibus.",
        "opening_hours": {"ranges": [["00:00", "23:59"]], "closed_days": []},
        "activities": ["esperar", "encontrar", "assistir o mundo"],
    },
    {
        "name": "Fliperama Cores",
        "slug": "fliperama-cores",
        "district": "centro-velho",
        "kind": "arcade",
        "description": "Máquinas coloridas, batidas altas e fichas que somem rápido. O barulhento da rua.",
        "opening_hours": {"ranges": [["14:00", "00:00"]], "closed_days": []},
        "activities": ["jogar", "competir", "assistir"],
    },
    {
        "name": "Bar do Canto",
        "slug": "bar-do-canto",
        "district": "beira-rio",
        "kind": "cafe",
        "description": "Mesa de plástico na calçada, copo gelado e conversa que atravessa a noite.",
        "opening_hours": {"ranges": [["18:00", "02:00"]], "closed_days": []},
        "activities": ["tomar uma", "conversar", "descontrair"],
    },
]

JOBS = [
    {
        "title": "Garçom de restaurante",
        "description": "Serviço de mesa, atendimento e fechamento do salão à noite.",
        "employer": "ramen-da-esquina",
        "salary_per_shift": 90,
        "schedule_template": {"shifts": [["18:00", "23:30"]], "days": [0, 1, 2, 3, 4, 5, 6]},
    },
    {
        "title": "Cozinheiro de restaurante",
        "description": "Preparo dos pratos e controle da cozinha.",
        "employer": "ramen-da-esquina",
        "salary_per_shift": 140,
        "schedule_template": {"shifts": [["10:00", "16:00"], ["18:00", "23:00"]], "days": [1, 2, 3, 4, 5, 6]},
    },
    {
        "title": "Proprietário de restaurante",
        "description": "Compra, cozinha, contas e conversa com todo mundo que entra.",
        "employer": "ramen-da-esquina",
        "salary_per_shift": 0,
        "schedule_template": {"shifts": [["09:00", "16:00"], ["18:00", "23:00"]], "days": [0, 1, 2, 3, 4, 5, 6]},
    },
    {
        "title": "Barista",
        "description": "Café, padaria de balcão e a mesa da janela.",
        "employer": "cafe-pe-de-serra",
        "salary_per_shift": 85,
        "schedule_template": {"shifts": [["07:00", "15:00"]], "days": [0, 1, 2, 3, 4, 5, 6]},
    },
    {
        "title": "Padeiro",
        "description": "Forno desde as quatro da manhã.",
        "employer": "padaria-estrela",
        "salary_per_shift": 110,
        "schedule_template": {"shifts": [["04:00", "14:00"]], "days": [1, 2, 3, 4, 5, 6]},
    },
    {
        "title": "Vendedora de mercado",
        "description": "Bancas, atendimento e organização das prateleiras.",
        "employer": "mercado-municipal",
        "salary_per_shift": 95,
        "schedule_template": {"shifts": [["07:00", "16:00"]], "days": [0, 1, 2, 3, 4, 5]},
    },
    {
        "title": "Mecânico",
        "description": "Revisão, conserto e palpite sobre tudo.",
        "employer": "oficina-boa-rosca",
        "salary_per_shift": 130,
        "schedule_template": {"shifts": [["08:00", "18:00"]], "days": [1, 2, 3, 4, 5]},
    },
    {
        "title": "Livraria",
        "description": "Atendimento, reposição e silêncio de qualidade.",
        "employer": "livraria-pagina-aberta",
        "salary_per_shift": 80,
        "schedule_template": {"shifts": [["10:00", "20:00"]], "days": [2, 3, 4, 5, 6, 0]},
    },
    {
        "title": "Operador de fliperama",
        "description": "Trocar fichas, consertar máquina e manter a ordem.",
        "employer": "fliperama-cores",
        "salary_per_shift": 70,
        "schedule_template": {"shifts": [["14:00", "22:00"]], "days": [0, 1, 2, 3, 4, 5, 6]},
    },
    {
        "title": "Motorista de aplicativo",
        "description": "Corridas pela cidade, dia e noite.",
        "employer": None,
        "salary_per_shift": 120,
        "schedule_template": {"shifts": [["07:00", "16:00"]], "days": [0, 1, 2, 3, 4, 5, 6]},
    },
    {
        "title": "Atendente de bar",
        "description": "Balca, copo e ouvindo a noite inteira.",
        "employer": "bar-do-canto",
        "salary_per_shift": 85,
        "schedule_template": {"shifts": [["18:00", "02:00"]], "days": [0, 1, 2, 3, 4, 5, 6]},
    },
]

NPCS = [
    {
        "name": "Taro",
        "age": 58,
        "pronouns": "ele/dele",
        "bio": "Abre o Ramen da Esquina todo dia há vinte anos. Acredita que caldo resolve quase tudo.",
        "profession_label": "Proprietário do Ramen da Esquina",
        "communication_style": "calmo, frases curtas, ouve mais do que fala",
        "personality": {"energy": 0.3, "formality": 0.6, "humor": 0.4, "emoji_usage": 0.1, "tone": "sereno"},
        "hobbies": ["cozinhar sozinho", "pesca", "rádio antigamente"],
        "likes": ["silêncio bom", "frescor da manhã", "clientes de sempre"],
        "dislikes": ["pressa na cozinha", "desperdício"],
        "goals": ["passar a receita adiante sem perder o gosto"],
        "flaws": ["orgulhoso", "demora para pedir ajuda"],
        "favorites": ["ramen-da-esquina"],
        "job": "Proprietário de restaurante",
        "schedule": [
            ["05:30", "07:00", "Acorda, chá e caldo de manhã", None],
            ["09:00", "16:00", "Na cozinha do Ramen", "ramen-da-esquina"],
            ["16:00", "18:00", "Descansa em casa", None],
            ["18:00", "23:30", "Ramen da Esquina, salão", "ramen-da-esquina"],
        ],
        "discovered_level": 2,
        "photo_color": "#8c5a3c",
        "money": 1400,
    },
    {
        "name": "Nina",
        "age": 29,
        "pronouns": "ela/dela",
        "bio": "Cozinheira do Ramen, tempero rápido e humor mais rápido ainda. Sonha com um lugar próprio um dia.",
        "profession_label": "Cozinheira do Ramen da Esquina",
        "communication_style": "extrovertida, gíria leve, responde com ironia doce",
        "personality": {"energy": 0.9, "formality": 0.3, "humor": 0.9, "emoji_usage": 0.7, "tone": "bem-humorada"},
        "hobbies": ["fotografia de rua", "manga", "corrida noturna"],
        "likes": ["aparador lotado", "playlist alta", "elogio sincero"],
        "dislikes": ["coisa sem sal", "gente que não agradece"],
        "goals": ["ter a cozinha dela em três anos"],
        "flaws": ["impulsiva", "promete demais"],
        "favorites": ["ramen-da-esquina", "bar-do-canto"],
        "job": "Cozinheiro de restaurante",
        "schedule": [
            ["08:00", "10:00", "Mercado comprando legume", "mercado-municipal"],
            ["10:00", "16:00", "Preparando a cozinha", "ramen-da-esquina"],
            ["18:00", "23:00", "Fogo alto no Ramen", "ramen-da-esquina"],
            ["23:00", "01:00", "Uma no Bar do Canto", "bar-do-canto"],
        ],
        "discovered_level": 2,
        "photo_color": "#d9534f",
        "money": 620,
    },
    {
        "name": "Bia",
        "age": 22,
        "pronouns": "ela/dela",
        "bio": "Garçom à noite e faculdade de enfermagem de dia. Anota tudo que escuta no balcão.",
        "profession_label": "Garçom do Ramen da Esquina",
        "communication_style": "ansiosa, fala rápido, se desculpa demais",
        "personality": {"energy": 0.7, "formality": 0.4, "humor": 0.5, "emoji_usage": 0.6, "tone": "nervosa-esperançosa"},
        "hobbies": ["desenhar nos intervalos", "séries policiais"],
        "likes": ["gelo no copo", "elogio de cliente"],
        "dislikes": ["coça de vergonha alheia", "fechar sozinha"],
        "goals": ["passar no semestre e não faltar turno"],
        "flaws": ["se compara com todo mundo", "evita conflito"],
        "favorites": ["ramen-da-esquina", "cafe-pe-de-serra"],
        "job": "Garçom de restaurante",
        "schedule": [
            ["08:00", "12:00", "Aula na faculdade", None],
            ["13:00", "17:00", "Estuda na Página Aberta", "livraria-pagina-aberta"],
            ["18:00", "23:30", "Turno no Ramen", "ramen-da-esquina"],
        ],
        "discovered_level": 2,
        "photo_color": "#e8a0bf",
        "money": 260,
    },
    {
        "name": "Caio",
        "age": 26,
        "pronouns": "ele/dele",
        "bio": "Barista do Café Pé de Serra. Troca discos no balcão e conhece o pedido de todo mundo.",
        "profession_label": "Barista do Café Pé de Serra",
        "communication_style": "reservado, respostas curtas, piada seca",
        "personality": {"energy": 0.35, "formality": 0.5, "humor": 0.6, "emoji_usage": 0.1, "tone": "quieto"},
        "hobbies": ["vinil", "cinema antigo", "andar de bike"],
        "likes": ["café coado devagar", "chapada de nuvem"],
        "dislikes": ["barulho de manhã", "redes sociais"],
        "goals": ["gravar um EP com a banda"],
        "flaws": ["evita gente", "não responde mensagem"],
        "favorites": ["cafe-pe-de-serra", "parque-beira-rio"],
        "job": "Barista",
        "schedule": [
            ["06:30", "07:00", "Bike até o café", "cafe-pe-de-serra"],
            ["07:00", "15:00", "Balcão do Café", "cafe-pe-de-serra"],
            ["16:00", "18:00", "Rolê de bike no parque", "parque-beira-rio"],
            ["19:00", "23:00", "Em casa, no vinil", None],
        ],
        "discovered_level": 1,
        "photo_color": "#5b7f8c",
        "money": 430,
    },
    {
        "name": "Dedé",
        "age": 41,
        "pronouns": "ele/dele",
        "bio": "Mecânico da Boa Rosca. Resolve motor e vizinhança com a mesma paciência.",
        "profession_label": "Mecânico da Oficina Boa Rosca",
        "communication_style": "falador, contado história, chama todo mundo de amigo",
        "personality": {"energy": 0.8, "formality": 0.3, "humor": 0.8, "emoji_usage": 0.5, "tone": "descontraído"},
        "hobbies": ["futebol de várzea", "churrasco", "mecânica de bike"],
        "likes": ["domingo sem alarme", "sábado de jogo"],
        "dislikes": ["peça cara", "gente que enrola"],
        "goals": ["comprar o boteco do bairro"],
        "flaws": ["gasta com o que não deve", "conta história longa"],
        "favorites": ["oficina-boa-rosca", "bar-do-canto", "praca-do-relogio"],
        "job": "Mecânico",
        "schedule": [
            ["07:00", "08:00", "Café na padaria", "padaria-estrela"],
            ["08:00", "18:00", "Oficina Boa Rosca", "oficina-boa-rosca"],
            ["19:00", "01:00", "No Bar do Canto", "bar-do-canto"],
        ],
        "discovered_level": 2,
        "photo_color": "#c9863a",
        "money": 780,
    },
    {
        "name": "Marina",
        "age": 34,
        "pronouns": "ela/dela",
        "bio": "Vendedora do Mercado Municipal e mãe da Sophia. Sabe quem saiu com quem na cidade inteira.",
        "profession_label": "Vendedora do Mercado Municipal",
        "communication_style": "direta, calorosa, fofoca como linguagem do amor",
        "personality": {"energy": 0.85, "formality": 0.4, "humor": 0.7, "emoji_usage": 0.8, "tone": "animada"},
        "hobbies": ["reality show", "plantar tempero", "grupo do bairro"],
        "likes": ["banca organizada", "café com as vizinhas"],
        "dislikes": ["cliente que apalpa tomate", "plano que dá errado"],
        "goals": ["pagar a faculdade da Sophia"],
        "flaws": ["metida onde não é chamada", "ansiosa"],
        "favorites": ["mercado-municipal", "praca-do-relogio", "ramen-da-esquina"],
        "job": "Vendedora de mercado",
        "schedule": [
            ["06:00", "07:00", "Leva a Sophia pra escola", "praca-do-relogio"],
            ["07:00", "16:00", "Banca no Mercado", "mercado-municipal"],
            ["16:30", "18:00", "Compras e vizinhança", None],
            ["20:00", "22:00", "Sofá e série", None],
        ],
        "discovered_level": 2,
        "photo_color": "#b3543f",
        "money": 540,
    },
    {
        "name": "Luna",
        "age": 24,
        "pronouns": "ela/dela",
        "bio": "Trabalha na Página Aberta e escreve de madrugada. Fala baixo, mas lembra de tudo.",
        "profession_label": "Livraria Página Aberta",
        "communication_style": "reserveda, precisa de tempo para aquecer",
        "personality": {"energy": 0.25, "formality": 0.7, "humor": 0.5, "emoji_usage": 0.2, "tone": "poética"},
        "hobbies": ["poesia", "fotografia analógica", "chá"],
        "likes": ["estante vazia à meia-luz", "madrugada quieta"],
        "dislikes": ["resumo de livro", "linguagem grossa"],
        "goals": ["publicar o primeiro caderno de poemas"],
        "flaws": ["distante", "julga rápido em silêncio"],
        "favorites": ["livraria-pagina-aberta", "parque-beira-rio"],
        "job": "Livraria",
        "schedule": [
            ["09:00", "10:00", "Chá e caderno", None],
            ["10:00", "20:00", "Turno na livraria", "livraria-pagina-aberta"],
            ["21:00", "01:00", "Escrevendo", None],
        ],
        "discovered_level": 1,
        "photo_color": "#7d6b9e",
        "money": 310,
    },
    {
        "name": "Vicente",
        "age": 63,
        "pronouns": "ele/dele",
        "bio": "Padeiro da Estrela há trinta anos. Chega antes do sol e some depois do almoço.",
        "profession_label": "Padeiro da Padaria Estrela",
        "communication_style": "sessentão, calmo, conselho curto",
        "personality": {"energy": 0.4, "formality": 0.6, "humor": 0.5, "emoji_usage": 0.1, "tone": "afável"},
        "hobbies": ["assar de madrugada", "tênis velho", "rádio amador"],
        "likes": ["fermento bom", "silêncio das quatro da manhã"],
        "dislikes": ["forno com defeito", "acordar tarde"],
        "goals": ["ensinar alguém antes de se aposentar"],
        "flaws": ["teimoso", "não aceita elogio"],
        "favorites": ["padaria-estrela", "praca-do-relogio"],
        "job": "Padeiro",
        "schedule": [
            ["03:30", "04:00", "A pé até a padaria", None],
            ["04:00", "14:00", "Forno da Estrela", "padaria-estrela"],
            ["14:00", "16:00", "Almoço e rádio", None],
            ["17:00", "19:00", "Banco da Praça do Relógio", "praca-do-relogio"],
        ],
        "discovered_level": 1,
        "photo_color": "#8e8e5c",
        "money": 900,
    },
    {
        "name": "Rafa",
        "age": 19,
        "pronouns": "ele/dele",
        "bio": "Operador do Fliperama Cores. Jogou tudo que existe lá dentro e ainda tem recorde no pinball.",
        "profession_label": "Operador do Fliperama Cores",
        "communication_style": "rápido, memes naturais, grita de alegria",
        "personality": {"energy": 0.95, "formality": 0.2, "humor": 0.85, "emoji_usage": 0.9, "tone": "elétrico"},
        "hobbies": ["arcade", "anime", "tênis colecionador"],
        "likes": ["combo perfeito", "noite cheia"],
        "dislikes": ["ficha barata", "jogador que reclama"],
        "goals": ["competir em torneio fora da cidade"],
        "flaws": ["impaciente", "largando estudo"],
        "favorites": ["fliperama-cores", "ramen-da-esquina"],
        "job": "Operador de fliperama",
        "schedule": [
            ["11:00", "13:00", "Lanche e feed", "ramen-da-esquina"],
            ["14:00", "22:00", "Turno no Fliperama", "fliperama-cores"],
            ["22:00", "02:00", "Rolê com a galera", "bar-do-canto"],
        ],
        "discovered_level": 2,
        "photo_color": "#4f9d69",
        "money": 190,
    },
    {
        "name": "Cleide",
        "age": 67,
        "pronouns": "ela/dela",
        "bio": "Aposentada, viúva, e a memória viva da Vila Serena. O banco da praça é o escritório dela.",
        "profession_label": "Aposentada",
        "communication_style": "acolhedora, provérbio pronto, olho para o detalhe",
        "personality": {"energy": 0.5, "formality": 0.6, "humor": 0.6, "emoji_usage": 0.4, "tone": "maternal"},
        "hobbies": ["crochê", "jardinar", "observar a praça"],
        "likes": ["menino que ajuda a vizinha", "café da tarde"],
        "dislikes": ["jovem com pressa", "gente que não cumprimenta"],
        "goals": ["ver o bairro mais unido"],
        "flaws": ["controladora", "fala do passado demais"],
        "favorites": ["praca-do-relogio", "parque-beira-rio", "cafe-pe-de-serra"],
        "job": None,
        "schedule": [
            ["07:00", "09:00", "Café e janela", None],
            ["09:00", "11:00", "Mercado e cumprimentos", "mercado-municipal"],
            ["16:00", "19:00", "Banco da Praça do Relógio", "praca-do-relogio"],
            ["19:00", "21:00", "Café da tarde no Pé de Serra", "cafe-pe-de-serra"],
        ],
        "discovered_level": 2,
        "photo_color": "#a67c52",
        "money": 1100,
    },
]


def ensure_districts(session: Session) -> dict[str, District]:
    result: dict[str, District] = {}
    for data in DISTRICTS:
        district = session.exec(select(District).where(District.slug == data["slug"])).first()
        if district is None:
            district = District(**data)
            session.add(district)
            session.commit()
            session.refresh(district)
        result[data["slug"]] = district
    return result


def ensure_locations(session: Session, districts: dict[str, District]) -> dict[str, Location]:
    result: dict[str, Location] = {}
    for data in LOCATIONS:
        location = session.exec(select(Location).where(Location.slug == data["slug"])).first()
        if location is None:
            location = Location(
                name=data["name"],
                slug=data["slug"],
                district_id=districts[data["district"]].id,
                kind=data["kind"],
                description=data["description"],
                opening_hours=data["opening_hours"],
                activities=data["activities"],
                is_public=True,
            )
            session.add(location)
            session.commit()
            session.refresh(location)
        result[data["slug"]] = location
    return result


def ensure_jobs(session: Session, locations: dict[str, Location]) -> dict[str, Job]:
    result: dict[str, Job] = {}
    for data in JOBS:
        job = session.exec(select(Job).where(Job.title == data["title"])).first()
        if job is None:
            employer_slug = data["employer"]
            job = Job(
                title=data["title"],
                description=data["description"],
                employer_location_id=locations[employer_slug].id if employer_slug else None,
                salary_per_shift=data["salary_per_shift"],
                schedule_template=data["schedule_template"],
            )
            session.add(job)
            session.commit()
            session.refresh(job)
        result[data["title"]] = job
    return result


def ensure_npcs(
    session: Session,
    locations: dict[str, Location],
    jobs: dict[str, Job],
) -> list[Character]:
    npcs: list[Character] = []
    for data in NPCS:
        existing = session.exec(select(Character).where(Character.name == data["name"], Character.is_npc == True)).first()  # noqa: E712
        if existing is None:
            existing = Character(
                user_id=None,
                name=data["name"],
                age=data["age"],
                pronouns=data["pronouns"],
                bio=data["bio"],
                profession_label=data["profession_label"],
                is_npc=True,
                personality=data["personality"],
                communication_style=data["communication_style"],
                hobbies=data["hobbies"],
                likes=data["likes"],
                dislikes=data["dislikes"],
                goals=data["goals"],
                flaws=data["flaws"],
                favorite_location_ids=[
                    locations[slug].id for slug in data["favorites"] if slug in locations
                ],
                money=data["money"],
                discovered_level=data["discovered_level"],
                current_location_id=None,
            )
            session.add(existing)
            session.commit()
            session.refresh(existing)

            job_title = data.get("job")
            if job_title and job_title in jobs:
                session.add(CharacterJob(character_id=existing.id, job_id=jobs[job_title].id))

            for start, end, activity, location_slug in data["schedule"]:
                session.add(
                    Schedule(
                        character_id=existing.id,
                        day_of_week=None,
                        start_time=start,
                        end_time=end,
                        activity=activity,
                        location_id=locations[location_slug].id if location_slug else None,
                    )
                )
            session.commit()
        npcs.append(existing)
    return npcs


def run_world_seed(session: Session) -> None:
    districts = ensure_districts(session)
    locations = ensure_locations(session, districts)
    jobs = ensure_jobs(session, locations)
    npcs = ensure_npcs(session, locations, jobs)
    logger.info(
        "world seed: %d districts, %d locations, %d jobs, %d npcs",
        len(districts),
        len(locations),
        len(jobs),
        len(npcs),
    )


def advance_world_time_session(session: Session, minutes: int) -> WorldState:
    if minutes <= 0:
        from app.domain.errors import ServiceError

        raise ServiceError("Informe quantos minutos devem passar.", 400)
    state = session.get(WorldState, 1)
    if state is None:
        from app.database.seed import ensure_world_state

        state = ensure_world_state(session)
    current = datetime.combine(state.current_date, time.fromisoformat(state.current_time))
    new_moment = current + timedelta(minutes=minutes)
    state.current_date = new_moment.date()
    state.current_time = new_moment.strftime("%H:%M")
    state.last_simulated_at = utcnow()
    session.add(state)
    session.add(
        SimulationLog(
            kind="manual",
            elapsed_minutes=minutes,
            summary=f"Relógio avançou {minutes} minutos para {state.current_date.isoformat()} {state.current_time}.",
        )
    )
    session.commit()
    session.refresh(state)
    return state
