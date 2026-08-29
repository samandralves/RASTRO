"""
RASTRO — dados e regras do TALK/1%/WORLD.

Constantes e funções puras usadas para interpretar as respostas do TALK,
montar as metas do 1% e calcular o progresso do WORLD. Sem estado de usuário
aqui — isso agora vive no banco (models.py).
"""

WORLD_ELEMENTS = [
    (0, "🏡", "Um espaço que já é seu"),
    (15, "🌱", "Seu primeiro passo"),
    (30, "🌊", "Um lago calmo pra respirar"),
    (50, "🪑", "Um banco pra descansar"),
    (75, "🌳", "Uma barreira atravessada"),
    (95, "🪴", "Uma pequena constância"),
    (120, "🐦", "Mais movimento no seu mundo"),
    (145, "🌸", "Seu rastro está florescendo"),
]

WORLD_ELEMENT_MESSAGES = {
    0: "Você não precisa ter tudo planejado para começar. O importante é dar o primeiro passo e confiar que cada avanço te levará mais perto do seu objetivo.",
    15: "Todo caminho começa em algum lugar. Essa pequena semente é a prova de que você já começou.",
    30: "Nem tudo precisa ser feito com pressa. Às vezes, o avanço também é parar, respirar e continuar depois.",
    50: "Olhar pra trás e ver o quanto você já andou também é progresso.",
    75: "Você enfrentou aquilo que um dia parecia difícil demais. Essa conquista prova que seus limites podem ser apenas o começo de algo maior.",
    95: "Nem todo dia será fácil, mas cada pequeno esforço conta. Continue avançando, porque é a constância de hoje que constrói os resultados de amanhã.",
    120: "Cada conquista é um passo na direção do seu melhor.",
    145: "Cada conquista é um passo na direção do seu melhor.",
}

# ---------------- TROCA DE PONTOS: recompensas disponíveis ----------------
BENEFITS = [
    {"id": "gympass", "emoji": "🏋️", "label": "Wellhub (Gympass)", "cost": 500, "description": "Benefício de atividade física por parceiro."},
    {"id": "terapia", "emoji": "🧠", "label": "Sessão de terapia", "cost": 800, "description": "Crédito para uma sessão com profissional parceiro."},
    {"id": "nutricionista", "emoji": "🥗", "label": "Consulta com nutricionista", "cost": 700, "description": "Crédito para atendimento nutricional parceiro."},
    {"id": "meditacao", "emoji": "🧘", "label": "App de meditação", "cost": 300, "description": "Acesso promocional a um aplicativo de meditação."},
    {"id": "farmacia", "emoji": "💊", "label": "Vale-farmácia", "cost": 600, "description": "Crédito promocional para compras em farmácia parceira."},
]

# Mantido para compatibilidade com versões anteriores do protótipo.
REWARDS = [
    {"id": "sementes", "emoji": "🌱", "label": "Sementes", "cost": 50},
    {"id": "decoracoes", "emoji": "🏡", "label": "Decorações", "cost": 80},
    {"id": "movimentos", "emoji": "🐦", "label": "Movimentos", "cost": 100},
    {"id": "flores", "emoji": "🌸", "label": "Flores", "cost": 60},
    {"id": "itens-especiais", "emoji": "🎁", "label": "Itens especiais", "cost": 150},
]

MOOD_OPTIONS = ["muito mal", "mal", "mais ou menos", "bem", "muito bem"]

OBJECTIVE_RULES = {
    "estudos": ["estud", "enem", "prova", "faculdade", "matéria", "lição", "escola", "vestibular", "nota"],
    "trabalho": ["emprego", "trabalh", "vaga", "currículo", "entrevista", "estágio", "carreira", "chefe"],
    "dinheiro": ["dinheiro", "gasto", "gastar", "econom", "guardar", "dívida", "financeir", "salário", "orçamento"],
    "rotina": ["rotina", "organizar", "organiza", "horário", "tempo", "casa", "quarto", "tarefas", "procrastin"],
    "projeto pessoal": ["projeto", "ideia", "criar", "aprender", "curso", "hobby", "portfólio", "empreender"],
    "relações": ["amigo", "amizade", "família", "famili", "namoro", "relacion", "sozinh", "conversar com alguém"],
    "bem-estar": ["cansad", "sono", "dormir", "exerc", "aliment", "energia", "descans", "ansios", "estress", "estresse"],
}

BARRIER_RULES = {
    "não sei por onde começar": ["não sei por onde", "perdid", "não sei como", "não sei o que fazer", "sem direção", "por onde", "não sei começar"],
    "falta de tempo": ["sem tempo", "não tenho tempo", "tempo", "correria", "horário", "ocupad"],
    "distração": ["celular", "distra", "instagram", "tiktok", "procrastin", "não consigo focar", "foco"],
    "tarefa parece grande demais": ["muita coisa", "grande demais", "sobrecarreg", "não dou conta", "coisa demais", "tudo ao mesmo tempo", "complicado"],
    "falta de energia": ["cansad", "sem energia", "exaust", "esgot", "sem força", "sono", "desanim"],
    "medo de não conseguir": ["medo", "fracass", "não vou conseguir", "não sou capaz", "insegur", "vergonha"],
    "preciso de companhia": ["sozinh", "solidão", "ninguém", "isolad", "não tenho com quem", "companhia"],
}

BARRIER_OPTIONS = [
    "não sei por onde começar",
    "falta de tempo",
    "distração",
    "tarefa parece grande demais",
    "falta de energia",
    "medo de não conseguir",
    "preciso de companhia",
]

GOAL_TEMPLATES = {
    "estudos": {
        "não sei por onde começar": [
            ("Abrir o material e escolher apenas uma questão", "começo"),
            ("Ler o enunciado da primeira questão", "foco"),
            ("Estudar por 10 minutos sem exigir terminar", "progresso"),
        ],
        "falta de tempo": [
            ("Reservar 10 minutos para uma única matéria", "tempo"),
            ("Escolher a tarefa mais importante do dia", "prioridade"),
            ("Encerrar os 10 minutos registrando o que avançou", "progresso"),
        ],
        "distração": [
            ("Deixar o celular longe por 10 minutos", "foco"),
            ("Abrir somente o material que você vai usar", "ambiente"),
            ("Fazer uma questão antes de olhar outra tela", "começo"),
        ],
        "tarefa parece grande demais": [
            ("Dividir o conteúdo em uma única questão", "começo"),
            ("Estudar só a primeira parte, sem tentar terminar tudo", "ação"),
            ("Marcar o que você conseguiu entender", "progresso"),
        ],
        "falta de energia": [
            ("Beber água e fazer uma pausa curta", "corpo"),
            ("Escolher uma tarefa de estudo que leve 5 minutos", "energia"),
            ("Parar depois do primeiro pequeno avanço se precisar", "cuidado"),
        ],
        "medo de não conseguir": [
            ("Escolher uma questão fácil para começar", "coragem"),
            ("Tentar por 5 minutos sem buscar perfeição", "tentativa"),
            ("Anotar uma coisa que você descobriu tentando", "reflexão"),
        ],
        "preciso de companhia": [
            ("Mandar mensagem para alguém para estudar junto", "conexão"),
            ("Combinar 15 minutos de estudo acompanhado", "companhia"),
            ("Contar depois o que você conseguiu fazer", "progresso"),
        ],
    },
    "trabalho": {
        "não sei por onde começar": [
            ("Abrir uma única vaga compatível com você", "começo"),
            ("Anotar uma habilidade que você já possui", "clareza"),
            ("Dar um pequeno passo no currículo", "ação"),
        ],
        "falta de tempo": [
            ("Separar 10 minutos para procurar uma vaga", "tempo"),
            ("Escolher apenas uma plataforma para olhar hoje", "prioridade"),
            ("Salvar uma oportunidade interessante", "progresso"),
        ],
        "distração": [
            ("Abrir somente a página de vagas que você escolheu", "foco"),
            ("Pesquisar por 10 minutos sem alternar de aplicativo", "foco"),
            ("Salvar uma vaga antes de sair", "ação"),
        ],
        "tarefa parece grande demais": [
            ("Escrever apenas o título do seu currículo", "começo"),
            ("Escolher três habilidades para destacar", "ação"),
            ("Revisar uma única parte do currículo", "progresso"),
        ],
        "falta de energia": [
            ("Fazer uma pausa e beber água antes de começar", "cuidado"),
            ("Escolher uma tarefa profissional de 5 minutos", "energia"),
            ("Encerrar quando o pequeno passo estiver concluído", "limite"),
        ],
        "medo de não conseguir": [
            ("Encontrar uma vaga em que você cumpra parte dos requisitos", "coragem"),
            ("Escrever uma frase sobre o que você sabe fazer", "confiança"),
            ("Salvar a vaga sem se obrigar a enviar hoje", "tentativa"),
        ],
        "preciso de companhia": [
            ("Pedir para alguém revisar uma parte do seu currículo", "conexão"),
            ("Conversar com alguém sobre uma área que interessa", "companhia"),
            ("Registrar uma dica que recebeu", "progresso"),
        ],
    },
    "dinheiro": {
        "não sei por onde começar": [
            ("Registrar um único gasto de hoje", "começo"),
            ("Anotar quanto entrou e quanto saiu este mês", "clareza"),
            ("Escolher uma pequena despesa para observar", "consciência"),
        ],
        "falta de tempo": [
            ("Separar 5 minutos para registrar seus gastos", "tempo"),
            ("Anotar apenas as três últimas compras", "prioridade"),
            ("Escolher um gasto para acompanhar esta semana", "progresso"),
        ],
        "distração": [
            ("Abrir sua lista de gastos antes de qualquer rede social", "foco"),
            ("Registrar uma compra assim que ela acontecer", "atenção"),
            ("Fechar o aplicativo depois de completar o registro", "limite"),
        ],
        "tarefa parece grande demais": [
            ("Anotar somente os gastos de hoje", "começo"),
            ("Separar gastos em duas categorias", "clareza"),
            ("Escolher uma categoria para observar", "progresso"),
        ],
        "falta de energia": [
            ("Fazer uma pausa e depois registrar apenas um gasto", "cuidado"),
            ("Escolher a parte mais simples do orçamento", "energia"),
            ("Parar depois de organizar uma única informação", "limite"),
        ],
        "medo de não conseguir": [
            ("Escolher uma pequena economia possível esta semana", "coragem"),
            ("Registrar sem julgamento um gasto que aconteceu", "consciência"),
            ("Anotar uma mudança que seria realista", "progresso"),
        ],
        "preciso de companhia": [
            ("Conversar com alguém de confiança sobre uma meta financeira", "conexão"),
            ("Pedir ajuda para organizar uma categoria", "companhia"),
            ("Anotar uma dica que recebeu", "progresso"),
        ],
    },
    "rotina": {
        "não sei por onde começar": [
            ("Escolher uma única tarefa para hoje", "começo"),
            ("Colocar essa tarefa em um horário específico", "clareza"),
            ("Fazer só os primeiros 5 minutos", "ação"),
        ],
        "falta de tempo": [
            ("Escolher uma tarefa que caiba em 10 minutos", "tempo"),
            ("Bloquear 10 minutos no seu horário", "prioridade"),
            ("Deixar o próximo passo preparado", "progresso"),
        ],
        "distração": [
            ("Deixar o celular fora do alcance por 10 minutos", "foco"),
            ("Começar uma tarefa antes de abrir outra tela", "começo"),
            ("Usar um cronômetro de 10 minutos", "atenção"),
        ],
        "tarefa parece grande demais": [
            ("Escolher apenas uma parte da tarefa", "começo"),
            ("Fazer a menor ação possível", "ação"),
            ("Parar para reconhecer o que já mudou", "progresso"),
        ],
        "falta de energia": [
            ("Escolher uma tarefa que leve 5 minutos", "energia"),
            ("Beber água e fazer uma pausa curta", "cuidado"),
            ("Deixar uma tarefa pronta para amanhã", "continuidade"),
        ],
        "medo de não conseguir": [
            ("Criar uma versão pequena da rotina", "coragem"),
            ("Testar a nova rotina por apenas um dia", "tentativa"),
            ("Anotar o que funcionou", "reflexão"),
        ],
        "preciso de companhia": [
            ("Convidar alguém para fazer a tarefa junto", "conexão"),
            ("Contar a alguém qual pequena tarefa você quer concluir", "companhia"),
            ("Compartilhar depois que terminou", "progresso"),
        ],
    },
    "projeto pessoal": {
        "não sei por onde começar": [
            ("Escrever em uma frase o que você quer criar", "clareza"),
            ("Escolher a primeira ação do projeto", "começo"),
            ("Trabalhar nele por 10 minutos", "ação"),
        ],
        "falta de tempo": [
            ("Separar 10 minutos para o projeto", "tempo"),
            ("Escolher uma única entrega pequena", "prioridade"),
            ("Salvar o próximo passo para continuar depois", "progresso"),
        ],
        "distração": [
            ("Abrir somente a ferramenta do projeto", "foco"),
            ("Trabalhar por 10 minutos sem alternar de aplicativo", "atenção"),
            ("Salvar o que foi feito", "progresso"),
        ],
        "tarefa parece grande demais": [
            ("Transformar o projeto em uma tarefa de 5 minutos", "começo"),
            ("Fazer apenas a primeira parte", "ação"),
            ("Registrar o que já existe", "progresso"),
        ],
        "falta de energia": [
            ("Escolher uma parte leve do projeto", "energia"),
            ("Fazer uma pausa curta antes de começar", "cuidado"),
            ("Encerrar após um pequeno avanço", "limite"),
        ],
        "medo de não conseguir": [
            ("Criar uma versão simples do projeto", "coragem"),
            ("Testar uma ideia sem exigir que fique perfeita", "tentativa"),
            ("Anotar o que aprendeu", "reflexão"),
        ],
        "preciso de companhia": [
            ("Mostrar a ideia para alguém de confiança", "conexão"),
            ("Pedir uma opinião sobre o primeiro passo", "companhia"),
            ("Registrar uma sugestão útil", "progresso"),
        ],
    },
    "relações": {
        "não sei por onde começar": [
            ("Escrever o que você gostaria de conseguir dizer", "clareza"),
            ("Escolher uma pessoa segura para conversar", "conexão"),
            ("Enviar uma mensagem curta e honesta", "ação"),
        ],
        "falta de tempo": [
            ("Separar 5 minutos para responder alguém importante", "tempo"),
            ("Mandar uma mensagem simples", "conexão"),
            ("Marcar um momento para conversar depois", "progresso"),
        ],
        "distração": [
            ("Guardar o celular e ouvir alguém por 10 minutos", "presença"),
            ("Responder uma pessoa sem alternar aplicativos", "foco"),
            ("Fazer uma pergunta e realmente escutar", "conexão"),
        ],
        "tarefa parece grande demais": [
            ("Escolher apenas uma coisa que você quer dizer", "começo"),
            ("Escrever uma frase sem enviar ainda", "clareza"),
            ("Decidir se vale continuar a conversa", "limite"),
        ],
        "falta de energia": [
            ("Dar um pequeno espaço para descansar antes de conversar", "cuidado"),
            ("Enviar uma mensagem simples em vez de explicar tudo", "energia"),
            ("Escolher o momento em que você se sente mais disponível", "limite"),
        ],
        "medo de não conseguir": [
            ("Escrever primeiro o que você gostaria que a pessoa entendesse", "coragem"),
            ("Usar uma frase começando por 'eu sinto...'", "clareza"),
            ("Escolher se quer conversar agora ou depois", "limite"),
        ],
        "preciso de companhia": [
            ("Enviar mensagem para alguém de confiança", "conexão"),
            ("Pedir companhia para uma atividade simples", "companhia"),
            ("Agradecer a pessoa que esteve presente", "progresso"),
        ],
    },
    "bem-estar": {
        "não sei por onde começar": [
            ("Escolher uma coisa simples que faria seu dia um pouco melhor", "começo"),
            ("Fazer essa ação por 5 minutos", "ação"),
            ("Anotar como você se sentiu depois", "reflexão"),
        ],
        "falta de tempo": [
            ("Separar 5 minutos para você hoje", "tempo"),
            ("Escolher uma pausa curta que realmente ajude", "cuidado"),
            ("Deixar a próxima pausa marcada", "progresso"),
        ],
        "distração": [
            ("Ficar 10 minutos sem alternar entre aplicativos", "foco"),
            ("Deixar o celular longe durante uma pausa", "presença"),
            ("Perceber o que você estava procurando ao abrir o celular", "consciência"),
        ],
        "tarefa parece grande demais": [
            ("Escolher uma mudança pequena em vez de mudar tudo", "começo"),
            ("Fazer só 5 minutos hoje", "ação"),
            ("Reconhecer o que já foi possível", "progresso"),
        ],
        "falta de energia": [
            ("Beber água e fazer uma pausa curta", "corpo"),
            ("Escolher uma ação que exija pouca energia", "energia"),
            ("Permitir que o pequeno passo seja suficiente hoje", "cuidado"),
        ],
        "medo de não conseguir": [
            ("Escolher uma mudança tão pequena que pareça possível", "coragem"),
            ("Testar por um dia, sem promessa de perfeição", "tentativa"),
            ("Anotar o que funcionou", "reflexão"),
        ],
        "preciso de companhia": [
            ("Pensar em alguém com quem você se sente seguro", "conexão"),
            ("Enviar uma mensagem simples pedindo companhia", "companhia"),
            ("Registrar como foi receber apoio", "reflexão"),
        ],
    },
}

PATTERNS = {
    "não sei por onde começar": "Você parece avançar melhor quando transforma algo grande em um primeiro passo pequeno.",
    "falta de tempo": "Você pode se beneficiar de ações curtas e específicas, em vez de esperar por um bloco perfeito de tempo.",
    "distração": "Seu desafio parece estar menos na vontade e mais em proteger sua atenção no momento de começar.",
    "tarefa parece grande demais": "Quando algo parece enorme, dividir em partes pequenas pode tornar o começo mais possível.",
    "falta de energia": "Você parece se beneficiar de passos curtos que respeitam sua energia, em vez de tentar fazer tudo de uma vez.",
    "medo de não conseguir": "Você pode avançar melhor quando troca a cobrança de acertar pela liberdade de apenas tentar.",
    "preciso de companhia": "Ter alguém por perto pode tornar alguns próximos passos mais possíveis para você.",
}


def detect_objective(text):
    normalized = (text or "").lower()
    for objective, keywords in OBJECTIVE_RULES.items():
        if any(keyword in normalized for keyword in keywords):
            return objective
    return "projeto pessoal"


def detect_barrier(text):
    normalized = (text or "").lower()
    for barrier, keywords in BARRIER_RULES.items():
        if any(keyword in normalized for keyword in keywords):
            return barrier
    return "não sei por onde começar"


def build_goals(objective, barrier):
    templates = GOAL_TEMPLATES.get(objective, GOAL_TEMPLATES["projeto pessoal"])
    return [
        {"id": index + 1, "text": text, "tag": tag, "done": False}
        for index, (text, tag) in enumerate(
            templates.get(barrier, templates["não sei por onde começar"])
        )
    ]


# ==================== CICLO MENSAL (mensal/semanal/diário) — fallback sem IA ====================
# Usado quando não há ANTHROPIC_API_KEY configurada ou a chamada à API falha.
# Gera um bloco completo (1 mensal + 4 semanais + 140 diárias) a partir dos
# mesmos templates do objetivo/barreira detectados no TALK, só que expandido.

MONTHLY_GOAL_TEMPLATES = {
    "estudos": "Chegar ao fim do mês com uma rotina de estudo que você consiga manter, mesmo nos dias difíceis.",
    "trabalho": "Dar passos consistentes rumo a uma nova oportunidade de trabalho ou uma melhora real na atual.",
    "dinheiro": "Construir uma relação mais organizada e menos ansiosa com o seu dinheiro ao longo do mês.",
    "rotina": "Montar uma rotina que funcione pra você, não uma rotina perfeita.",
    "projeto pessoal": "Avançar de forma constante no seu projeto, saindo da ideia para algo concreto.",
    "relações": "Fortalecer uma relação importante, com pequenas ações de presença e honestidade.",
    "bem-estar": "Cuidar do seu bem-estar com ações pequenas e sustentáveis, não com mudanças radicais.",
}

WEEKLY_GOAL_TEMPLATES = {
    "não sei por onde começar": [
        "Descobrir, na prática, qual é o seu primeiro passo real.",
        "Repetir o primeiro passo até ele parar de dar tanto medo.",
        "Dar um passo um pouco maior que o da semana passada.",
        "Olhar pra trás e organizar o que já foi possível até aqui.",
    ],
    "falta de tempo": [
        "Encontrar os 10 minutos que realmente cabem na sua rotina.",
        "Proteger esses 10 minutos mesmo numa semana corrida.",
        "Aumentar um pouco o tempo dedicado, sem se cobrar demais.",
        "Ver quanto essa rotina pequena já rendeu no mês.",
    ],
    "distração": [
        "Criar um ambiente com menos chances de distração.",
        "Perceber os gatilhos que tiram sua atenção e testar 1 ajuste.",
        "Manter o foco por mais tempo seguido do que na semana passada.",
        "Reconhecer o quanto sua atenção já está mais protegida.",
    ],
    "tarefa parece grande demais": [
        "Quebrar o objetivo em pedaços realmente pequenos.",
        "Concluir o primeiro pedaço inteiro, sem pular etapas.",
        "Encarar um pedaço um pouco mais desafiador.",
        "Juntar os pedaços e ver o quanto já formam um todo.",
    ],
    "falta de energia": [
        "Descobrir o horário do dia em que você tem mais energia.",
        "Aproveitar esse horário para o passo mais importante da semana.",
        "Testar um ajuste pequeno pra sustentar essa energia por mais tempo.",
        "Perceber o que mudou na sua disposição ao longo do mês.",
    ],
    "medo de não conseguir": [
        "Tentar sem exigir que dê certo de primeira.",
        "Repetir a tentativa, mesmo com o medo ainda presente.",
        "Encarar uma tentativa um pouco mais exposta que a anterior.",
        "Olhar pra trás e ver quantas vezes você tentou mesmo com medo.",
    ],
    "preciso de companhia": [
        "Encontrar 1 pessoa com quem dividir esse processo.",
        "Manter essa troca viva ao longo da semana.",
        "Pedir apoio em algo um pouco mais difícil.",
        "Agradecer e reconhecer quem esteve com você nesse mês.",
    ],
}


WEEKLY_GOALS_PER_CYCLE_FALLBACK = 4


def _daily_pool(objective, barrier):
    """Junta os textos de metas diárias disponíveis pros templates existentes
    e, se faltar variedade, completa repetindo com pequenas variações — sem
    nunca deixar a lista vazia."""
    templates = GOAL_TEMPLATES.get(objective, GOAL_TEMPLATES["projeto pessoal"])
    base = templates.get(barrier, templates["não sei por onde começar"])
    pool = [text for text, _tag in base]
    if not pool:
        pool = ["Dar um pequeno passo em direção ao seu objetivo hoje."]
    return pool


def build_full_cycle(objective, barrier):
    """Monta o payload de um ciclo completo (mensal + 4 semanais + 140 diárias,
    35 por semana / 5 por dia), no mesmo formato usado pelos rascunhos gerados
    por IA — pra admin_dashboard poder aprovar os dois do mesmo jeito."""
    monthly = MONTHLY_GOAL_TEMPLATES.get(objective, MONTHLY_GOAL_TEMPLATES["projeto pessoal"])
    weekly = WEEKLY_GOAL_TEMPLATES.get(barrier, WEEKLY_GOAL_TEMPLATES["não sei por onde começar"])
    pool = _daily_pool(objective, barrier)

    daily_weeks = []
    for week_index in range(WEEKLY_GOALS_PER_CYCLE_FALLBACK):
        week_texts = []
        for day in range(7):
            for slot in range(5):
                i = (week_index * 35) + (day * 5) + slot
                base_text = pool[i % len(pool)]
                # pequena variação pra não repetir o texto idêntico dentro da semana
                cycle_pass = i // len(pool)
                text = base_text if cycle_pass == 0 else f"{base_text} (dia {day + 1})"
                week_texts.append(text)
        daily_weeks.append(week_texts)

    return {"monthly": monthly, "weekly": list(weekly), "daily": daily_weeks}


def unlocked_elements(owned_costs):
    """owned_costs: coleção com os custos (thresholds) dos itens do WORLD que
    o usuário já obteve (ver models.WorldItem)."""
    owned_costs = set(owned_costs)
    return [(emoji, label) for cost, emoji, label in WORLD_ELEMENTS if cost in owned_costs]


# ==================== VOLUNTARIADO: triagem por urgência ====================
# ATENÇÃO: isto é uma triagem por palavras-chave, não um diagnóstico. Qualquer
# sinal de risco iminente deve cair em "critica" e ser encaminhado ao CVV —
# na dúvida, o sistema deve preferir classificar como mais urgente, nunca menos.

CVV_MESSAGE = (
    "Pelo que você escreveu, acho que nossos voluntários não têm o preparo "
    "necessário para te ajudar com isso agora — e isso merece um cuidado "
    "imediato. Por favor, ligue para o CVV: 188 (Centro de Valorização da "
    "Vida), disponível 24h, gratuito e sigiloso. Se estiver em perigo agora, "
    "ligue também para o 192 (SAMU) ou vá até o pronto-socorro mais próximo."
)

# áreas que o usuário pode marcar como relacionadas ao que está vivendo —
# usado só para dar contexto ao voluntário/admin, não é diagnóstico.
VOLUNTEER_TICKET_AREAS = {
    "ansiedade": "Ansiedade",
    "tristeza_depressao": "Tristeza / depressão",
    "relacionamentos": "Relacionamentos",
    "familia": "Família",
    "escola_trabalho": "Escola / trabalho",
    "autoestima": "Autoestima",
    "luto": "Luto",
    "saude_fisica": "Saúde física",
    "alimentacao": "Alimentação",
    "outro": "Outro",
}

VOLUNTEER_INTRO_MESSAGE = (
    "Desabafe. Aqui é um local seguro e tudo o que disser será anonimizado. "
    "Evite informar dados pessoais, a menos que seja de extrema necessidade "
    "para o seu relato."
)

VOLUNTEER_WAIT_MESSAGE = (
    "Em alguns instantes, um voluntário supervisionado irá analisar o seu "
    "caso e te ajudar da maneira mais assertiva."
)

CRITICAL_KEYWORDS = [
    "quero morrer", "quero me matar", "vou me matar", "não aguento mais viver",
    "não quero mais viver", "acabar com tudo", "acabar com a minha vida",
    "me machucar", "me cortar", "tirar minha vida", "sem motivo pra viver",
    "melhor eu não existir", "pensando em suicídio", "suicídio", "suicidio",
]

HIGH_URGENCY_KEYWORDS = [
    "crise", "desesperad", "pânico", "panico", "não consigo mais", "surto",
    "em pânico", "muito mal", "não paro de chorar", "medo de mim mesmo",
]

MEDIUM_URGENCY_KEYWORDS = [
    "ansios", "triste", "sozinh", "cansad", "sobrecarreg", "estress",
    "não sei o que fazer", "confus",
]


VOLUNTEER_TICKET_AREAS = {
    "ansiedade": "Ansiedade",
    "tristeza_depressao": "Tristeza / depressão",
    "relacionamentos": "Relacionamentos",
    "familia": "Família",
    "escola_trabalho": "Escola / trabalho",
    "autoestima": "Autoestima",
    "luto": "Luto",
    "outro": "Outro",
}

VOLUNTEER_INTRO_MESSAGE = (
    "Desabafe. Aqui é um local seguro e tudo o que disser será anonimizado. "
    "Evite informar dados pessoais, a menos que seja de extrema necessidade "
    "para o seu relato."
)

VOLUNTEER_WAIT_MESSAGE = (
    "Em alguns instantes, um voluntário supervisionado irá analisar o seu "
    "caso e te ajudar da maneira mais assertiva."
)


def classify_ticket_urgency(text):
    """Retorna (urgency, is_crisis). is_crisis=True significa: não enfileirar
    pra voluntário, encaminhar direto pro CVV."""
    normalized = (text or "").lower()

    if any(keyword in normalized for keyword in CRITICAL_KEYWORDS):
        return "critica", True
    if any(keyword in normalized for keyword in HIGH_URGENCY_KEYWORDS):
        return "alta", False
    if any(keyword in normalized for keyword in MEDIUM_URGENCY_KEYWORDS):
        return "media", False
    return "baixa", False


# ==================== ESTATÍSTICAS DE INSATISFAÇÃO ====================

SATISFACTION_CONTEXTS = ["escola", "empresa", "cidade", "outro"]

SATISFACTION_REASON_TAGS = {
    "escola": ["metodologia de ensino", "infraestrutura", "relação com colegas", "carga de provas/tarefas", "outro"],
    "empresa": ["ambiente de trabalho", "carga horária", "salário/benefícios", "relação com liderança", "outro"],
    "cidade": ["segurança", "transporte", "acesso a lazer/cultura", "custo de vida", "outro"],
    "outro": ["outro"],
}


def world_progress(owned_costs, points):
    owned_costs = set(owned_costs)
    owned = len(owned_costs)
    total = len(WORLD_ELEMENTS)
    if owned >= total:
        return 100, 0
    locked_costs = sorted(cost for cost, *_ in WORLD_ELEMENTS if cost not in owned_costs)
    next_cost = locked_costs[0]
    return (owned / total) * 100, max(0, next_cost - points)




# ---------------- MUNDO REAL ----------------
WORLD_REAL_INTERESTS = {
    "cinema": "Cinema",
    "museus": "Museus",
    "teatro": "Teatro",
    "shows": "Shows e música",
    "parques": "Parques e natureza",
    "gastronomia": "Gastronomia",
    "arte_urbana": "Arte urbana",
    "esportes": "Esportes",
    "livrarias": "Livrarias e literatura",
    "cultura": "Centros culturais",
}

WORLD_REAL_PLACES = [
    {
        "id": "praca-liberdade",
        "name": "Praça da Liberdade",
        "category": "cultura",
        "interests": ["museus", "parques", "arte_urbana", "cultura"],
        "lat": -19.9321, "lng": -43.9378,
        "description": "Conjunto cultural e espaço aberto no coração da região da Savassi.",
    },
    {
        "id": "ccbb-bh",
        "name": "CCBB Belo Horizonte",
        "category": "museus",
        "interests": ["museus", "teatro", "shows", "cultura"],
        "lat": -19.9326, "lng": -43.9369,
        "description": "Centro cultural com exposições, teatro e programação artística.",
    },
    {
        "id": "palacio-das-artes",
        "name": "Palácio das Artes",
        "category": "teatro",
        "interests": ["teatro", "shows", "cultura"],
        "lat": -19.9247, "lng": -43.9362,
        "description": "Complexo cultural com teatro, música, dança, cinema e artes visuais.",
    },
    {
        "id": "parque-municipal",
        "name": "Parque Municipal Américo Renné Giannetti",
        "category": "parques",
        "interests": ["parques", "esportes"],
        "lat": -19.9245, "lng": -43.9334,
        "description": "Área verde tradicional para caminhada, lazer e atividades ao ar livre.",
    },
    {
        "id": "mercado-central",
        "name": "Mercado Central de Belo Horizonte",
        "category": "gastronomia",
        "interests": ["gastronomia", "cultura"],
        "lat": -19.9228, "lng": -43.9409,
        "description": "Um dos principais pontos de gastronomia e cultura popular de BH.",
    },
    {
        "id": "museu-pampulha",
        "name": "Museu de Arte da Pampulha",
        "category": "museus",
        "interests": ["museus", "arte_urbana", "cultura", "parques"],
        "lat": -19.8519, "lng": -43.9763,
        "description": "Espaço de arte e arquitetura no conjunto da Pampulha.",
    },
    {
        "id": "mineirao",
        "name": "Mineirão",
        "category": "esportes",
        "interests": ["esportes", "shows"],
        "lat": -19.8659, "lng": -43.9710,
        "description": "Estádio e espaço de grandes eventos esportivos e musicais.",
    },
    {
        "id": "mercado-novo",
        "name": "Mercado Novo",
        "category": "gastronomia",
        "interests": ["gastronomia", "shows", "arte_urbana"],
        "lat": -19.9227, "lng": -43.9442,
        "description": "Espaço urbano com gastronomia, bares, criatividade e eventos.",
    },
    {
        "id": "livraria-quixote",
        "name": "Quixote Livraria e Café",
        "category": "livrarias",
        "interests": ["livrarias", "gastronomia", "cultura"],
        "lat": -19.9360, "lng": -43.9364,
        "description": "Livraria e café para quem gosta de literatura e encontros culturais.",
    },
]
