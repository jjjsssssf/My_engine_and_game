# pesca.py
import random

DEFINICAO_VARAS: dict = {
    "Vara de Pesca": {
        "bonus_prof":       0,
        "bonus_xp":         0,
        "menor_velocidade": 0,
        "chance_lixo":      50,
        # chance_peixe: None = usa o sistema de profundidade padrão
        "chance_peixe":     None,
        "qualidade": {
            "bronze":  10,
            "prata":   0,
            "ouro":    0,
            "platina": 0,
        },
    },
    "Vara de Pesca Profissional": {
        "bonus_prof":       25,
        "bonus_xp":         5,
        "menor_velocidade": 1.0,
        "chance_lixo":      0,
        # Favorece incomum e raro, ainda pesca lendário mas raramente
        "chance_peixe": {
            "comum":    50,
            "incomum":  30,
            "raro":     15,
            "lendario":  5,
        },
        "qualidade": {
            "bronze":  40,
            "prata":   100,
            "ouro":    20,
            "platina":  5,
        },
    },
    "Vara de Carbono": {
        "bonus_prof":       8,
        "bonus_xp":        15,
        "menor_velocidade": 0.12,
        "chance_lixo":      5,
        # Equilibrada — melhora chances de raro sem ignorar os outros
        "chance_peixe": {
            "comum":    60,
            "incomum":  20,
            "raro":     15,
            "lendario":  5,
        },
        "qualidade": {
            "bronze":  20,
            "prata":   40,
            "ouro":    30,
            "platina": 10,
        },
    },
    "Vara Lendária": {
        "bonus_prof":      12,
        "bonus_xp":        30,
        "menor_velocidade": 0.20,
        "chance_lixo":      2,
        # Focada em raros e lendários
        "chance_peixe": {
            "comum":    25,
            "incomum":  30,
            "raro":     30,
            "lendario": 15,
        },
        "qualidade": {
            "bronze":   5,
            "prata":   25,
            "ouro":    45,
            "platina": 25,
        },
    },
}

# Vara padrão usada quando o jogador não tem nenhuma equipada
_VARA_PADRAO = DEFINICAO_VARAS["Vara de Pesca"]

# Tabela de conversão: tier de qualidade → número de estrelas (usado por _obter_item_estrelado)
_TIER_PARA_ESTRELAS = {
    "bronze":  1,
    "prata":   2,
    "ouro":    3,
    "platina": 4,
}

VARAS_VALIDAS = set(DEFINICAO_VARAS.keys())


def _sortear_qualidade_pesca(definicao_vara: dict, nivel_pesca: int) -> int:
    """
    Sorteia o número de estrelas (0–4) combinando as chances da vara
    com as chances do nível de pesca do jogador.

    Chances base por nível N (1-indexado):
      bronze  = 10 + (N-1)*5 %
      prata   = 2.5 + (N-1)*2.5 %
      ouro    = (N-1)*1.5 %
      platina = max(0, (N-4)*0.9) %

    Os pesos da vara são somados às chances base (em pontos percentuais).
    """
    n = max(0, nivel_pesca - 1)
    qualidade = definicao_vara.get("qualidade", {})

    chance_bronze  = 10.0 + n * 5.0  + qualidade.get("bronze",  0)
    chance_prata   = 2.5  + n * 2.5  + qualidade.get("prata",   0)
    chance_ouro    = 0.0  + n * 1.5  + qualidade.get("ouro",    0)
    chance_platina = max(0.0, (n - 3) * 0.9) + qualidade.get("platina", 0)

    r = random.uniform(0, 100)
    if r < chance_platina:
        return 4
    if r < chance_ouro:
        return 3
    if r < chance_prata:
        return 2
    if r < chance_bronze:
        return 1
    return 0


def _sortear_qualidade_vara(definicao_vara: dict) -> int:
    """Legado — mantido por compatibilidade. Usa nível 1 como base."""
    return _sortear_qualidade_pesca(definicao_vara, 1)


def _sortear_raridade_vara(definicao_vara: dict, prof: int) -> str:
    """
    Sorteia a raridade do peixe combinando chance_peixe da vara (se definida)
    com o bônus de profundidade do jogador.

    Se a vara tem chance_peixe definido:
      - Os pesos do dict são o ponto de partida (em %).
      - A profundidade ainda aplica um bônus aditivo nas raridades mais altas,
        mas bem menor que no sistema padrão — a vara é quem manda.

    Se chance_peixe for None:
      - Usa exclusivamente o sistema de profundidade (_PROF_RARIDADE), igual
        ao comportamento original.

    Retorna: "comum" | "incomum" | "raro" | "lendario"
    """
    chance_peixe = definicao_vara.get("chance_peixe")

    if chance_peixe is None:
        # sistema original: profundidade determina tudo
        raridade = "comum"
        for prof_min, rar in _PROF_RARIDADE:
            if prof >= prof_min:
                raridade = rar
                break
        return raridade

    # Sistema baseado em chance_peixe da vara
    # Bônus de profundidade: cada linha além de 5 dá +0.5% a incomum/raro/lendario
    bonus_prof = max(0, prof - 5) * 0.5

    peso_comum    = float(chance_peixe.get("comum",    60))
    peso_incomum  = float(chance_peixe.get("incomum",  20)) + bonus_prof * 0.5
    peso_raro     = float(chance_peixe.get("raro",     15)) + bonus_prof * 0.3
    peso_lendario = float(chance_peixe.get("lendario",  5)) + bonus_prof * 0.2

    # Normaliza para somar 100
    total = peso_comum + peso_incomum + peso_raro + peso_lendario
    if total <= 0:
        return "comum"

    r = random.uniform(0, total)
    if r < peso_lendario:
        return "lendario"
    r -= peso_lendario
    if r < peso_raro:
        return "raro"
    r -= peso_raro
    if r < peso_incomum:
        return "incomum"
    return "comum"

# ──────────────────────────────────────────────────────────────────────────────
# Tabelas de dificuldade da barra de captura
# R = falha instantânea  |  Y = perde vida  |  G = sucesso
# ──────────────────────────────────────────────────────────────────────────────
TABELA_DIFICULDADE = {
    "lixo":    [("R", 3), ("Y", 4), ("G",  8), ("Y", 4), ("R", 3)],
    "comum":    [("R", 3), ("Y", 4), ("G",  8), ("Y", 4), ("R", 3)],
    "incomum":  [("R", 4), ("Y", 3), ("G",  6), ("Y", 3), ("R", 4)],
    "raro":     [("R", 5), ("Y", 3), ("G",  4), ("Y", 3), ("R", 5)],
    "lendario": [("R", 8), ("Y", 2), ("G",  2), ("Y", 2), ("R", 8)],
}

ATRIBUTOS_RARIDADE = {
    "lixo":     {"vel_cursor": 0.60, "xp_pescar":  0},
    "comum":    {"vel_cursor": 0.60, "xp_pescar": 5},
    "incomum":  {"vel_cursor": 0.90, "xp_pescar": 10},
    "raro":     {"vel_cursor": 1.00, "xp_pescar": 20},
    "lendario": {"vel_cursor": 1.20, "xp_pescar": 40},
}

# Profundidade mínima (linhas do grid) para cada raridade
_PROF_RARIDADE = [
    (14, "lendario"),
    (10, "raro"),
    (5,  "incomum"),
    (0,  "comum"),
    (0,  "lixo"),

]

PEIXES_POR_TIPO = {
    # ══════════════════════════════════════════════════════════════════════════
    # Formato de cada entrada:
    #   nome     : str            — nome do item
    #   horas    : (ini,fim)|None — intervalo horário com wrap-around; None = qualquer hora
    #   clima    : "sol"|"chuva"|None — None = qualquer clima
    #   estacoes : list[str]|None — None = todas as estações
    # ══════════════════════════════════════════════════════════════════════════

    "tile_mar": {
        "lixo": [
            {"nome": "Bota Velha",           "horas": None,      "clima": None,    "estacoes": None},
            {"nome": "Lixo",                 "horas": None,      "clima": None,    "estacoes": None},
            {"nome": "Lata de Refrigerante", "horas": None,      "clima": None,    "estacoes": None},
            {"nome": "Alga",                 "horas": None,      "clima": None,    "estacoes": None},
        ],
        "comum": [
            # Sardinha — todo o ano, durante o dia
            {"nome": "Sardinha", "horas": (5,  19), "clima": None,    "estacoes": None},
            # Corvina — todo o ano, madrugada/manhã, tarde/noite e na chuva
            {"nome": "Corvina",  "horas": (4,  10), "clima": None,    "estacoes": None},
            {"nome": "Corvina",  "horas": (18, 24), "clima": None,    "estacoes": None},
            {"nome": "Corvina",  "horas": None,     "clima": "chuva", "estacoes": None},
        ],
        "incomum": [
            # Robalo Flecha — todo o ano, períodos de baixa luminosidade
            {"nome": "Robalo Flecha", "horas": (5,   8), "clima": None,    "estacoes": None},
            {"nome": "Robalo Flecha", "horas": (18, 24), "clima": None,    "estacoes": None},
            {"nome": "Robalo Flecha", "horas": (0,   5), "clima": None,    "estacoes": None},
            {"nome": "Robalo Flecha", "horas": None,     "clima": "chuva", "estacoes": None},
            # Olhete — Primavera e Verão (prefere água quente)
            {"nome": "Olhete", "horas": (7,  11), "clima": "sol", "estacoes": ["Primavera", "Verao"]},
            {"nome": "Olhete", "horas": (14, 18), "clima": "sol", "estacoes": ["Primavera", "Verao"]},
            # Outono: só pela manhã cedo
            {"nome": "Olhete", "horas": (6,  10), "clima": "sol", "estacoes": ["Outono"]},
        ],
        "raro": [
            # Beijupirá — Verão: muito ativo; Primavera/Outono: só manhã
            {"nome": "Beijupirá", "horas": (5,  12), "clima": "sol",   "estacoes": ["Verao"]},
            {"nome": "Beijupirá", "horas": (5,  18), "clima": "chuva", "estacoes": ["Verao"]},
            {"nome": "Beijupirá", "horas": (6,  10), "clima": "sol",   "estacoes": ["Primavera", "Outono"]},
            # Garoupa — todo o ano, períodos noturnos e na chuva
            {"nome": "Garoupa",   "horas": (19, 24), "clima": None,    "estacoes": None},
            {"nome": "Garoupa",   "horas": (0,   6), "clima": None,    "estacoes": None},
            {"nome": "Garoupa",   "horas": None,     "clima": "chuva", "estacoes": None},
        ],
        "lendario": [
            # Marlin Azul — só no Verão (temperatura máxima do oceano)
            {"nome": "Marlin Azul", "horas": (10, 16), "clima": "sol", "estacoes": ["Verao"]},
            # Primavera: raro mas aparece no pico do dia
            {"nome": "Marlin Azul", "horas": (11, 15), "clima": "sol", "estacoes": ["Primavera"]},
            # Mero — todo o ano, madrugada profunda e na chuva
            {"nome": "Mero", "horas": (22,  5), "clima": None,    "estacoes": None},
            {"nome": "Mero", "horas": None,     "clima": "chuva", "estacoes": None},
        ],
    },

    "tile_lago": {
        "lixo": [
            {"nome": "Bota Velha",           "horas": None, "clima": None, "estacoes": None},
            {"nome": "Lixo",                 "horas": None, "clima": None, "estacoes": None},
            {"nome": "Alga",                 "horas": None, "clima": None, "estacoes": None},
            {"nome": "Lata de Refrigerante", "horas": None, "clima": None, "estacoes": None},
        ],
        "comum": [
            # Lambari — todo o ano; mais fácil de dia com sol
            {"nome": "Lambari", "horas": (5,  17), "clima": "sol",   "estacoes": None},
            {"nome": "Lambari", "horas": (20, 22), "clima": "chuva", "estacoes": None},
            # Piava — Primavera e Verão (prefere água morna)
            {"nome": "Piava", "horas": (5,  10), "clima": "sol",   "estacoes": ["Primavera", "Verao"]},
            {"nome": "Piava", "horas": None,     "clima": "chuva", "estacoes": ["Primavera", "Verao"]},
            # Outono/Inverno: Piava some, Lambari permanece como único comum
        ],
        "incomum": [
            # Tilápia — todo o ano (espécie altamente adaptável)
            {"nome": "Tilápia", "horas": (6, 22), "clima": None,    "estacoes": None},
            # Traíra — Primavera, Verão e Outono (fica letárgica no Inverno)
            {"nome": "Traíra",  "horas": (5,  9), "clima": None,    "estacoes": ["Primavera", "Verao", "Outono"]},
            {"nome": "Traíra",  "horas": None,    "clima": "chuva", "estacoes": ["Primavera", "Verao", "Outono"]},
        ],
        "raro": [
            # Tucunaré — Primavera e Verão (temperatura alta)
            {"nome": "Tucunaré", "horas": (16, 20), "clima": None,    "estacoes": ["Primavera", "Verao"]},
            {"nome": "Tucunaré", "horas": (6,  10), "clima": None,    "estacoes": ["Primavera", "Verao"]},
            {"nome": "Tucunaré", "horas": None,     "clima": "chuva", "estacoes": ["Primavera", "Verao"]},
            # Outono: aparece só no entardecer
            {"nome": "Tucunaré", "horas": (16, 19), "clima": None,    "estacoes": ["Outono"]},
            # Pacu — Primavera e Verão (época de frutos caindo na água)
            {"nome": "Pacu", "horas": (5,  10), "clima": "sol",  "estacoes": ["Primavera", "Verao"]},
            {"nome": "Pacu", "horas": (22,  2), "clima": None,   "estacoes": ["Primavera", "Verao"]},
            # Outono: aparece pouco, só de manhã cedo
            {"nome": "Pacu", "horas": (6,   9), "clima": "sol",  "estacoes": ["Outono"]},
        ],
        "lendario": [
            # Surubim — todo o ano, noite e madrugada
            {"nome": "Surubim", "horas": (20,  5), "clima": None,    "estacoes": None},
            {"nome": "Surubim", "horas": None,     "clima": "chuva", "estacoes": None},
            # Dourado — Primavera e Verão (migração rio acima)
            {"nome": "Dourado", "horas": (10, 16), "clima": "sol",  "estacoes": ["Primavera", "Verao"]},
            # Outono: surge de manhã cedo durante a desova
            {"nome": "Dourado", "horas": (5,   9), "clima": None,   "estacoes": ["Outono"]},
        ],
    },

    "tile_mangi": {
        "lixo": [
            {"nome": "Alga",       "horas": None, "clima": None, "estacoes": None},
            {"nome": "Bota Velha", "horas": None, "clima": None, "estacoes": None},
            {"nome": "Lixo",       "horas": None, "clima": None, "estacoes": None},
        ],
        "comum": [
            # Caranguejo-uçá — todo o ano; reprodução intensa na Primavera
            {"nome": "Caranguejo-uçá", "horas": (5,  10), "clima": None,  "estacoes": None},
            {"nome": "Caranguejo-uçá", "horas": (17, 22), "clima": None,  "estacoes": None},
            # Siri — Primavera e Verão (mares mais quentes)
            {"nome": "Siri",    "horas": (6, 18), "clima": "sol",  "estacoes": ["Primavera", "Verao"]},
            # Outono: janela menor
            {"nome": "Siri",    "horas": (6, 14), "clima": "sol",  "estacoes": ["Outono"]},
            # Camarão — todo o ano, qualquer hora
            {"nome": "Camarão", "horas": None,    "clima": None,   "estacoes": None},
            # Bagre — todo o ano, noturno
            {"nome": "Bagre",   "horas": (18,  6), "clima": None,  "estacoes": None},
            # Tainha — Outono e Inverno (migração costeira clássica)
            {"nome": "Tainha",  "horas": (5,  12), "clima": "sol", "estacoes": ["Outono", "Inverno"]},
            # Primavera: cardumes jovens entrando no mangue
            {"nome": "Tainha",  "horas": (5,  10), "clima": None,  "estacoes": ["Primavera"]},
        ],
        "incomum": [
            # Tainha — Inverno é a melhor época (cardumes densos)
            {"nome": "Tainha",      "horas": (5,  12), "clima": None,    "estacoes": ["Inverno"]},
            {"nome": "Tainha",      "horas": None,     "clima": "chuva", "estacoes": ["Outono", "Inverno"]},
            # Bagre na chuva — noite chuvosa, todo o ano
            {"nome": "Bagre",       "horas": (18,  6), "clima": "chuva", "estacoes": None},
            # Robalo Peva — Primavera e Verão
            {"nome": "Robalo Peva", "horas": (5,   9), "clima": "sol",   "estacoes": ["Primavera", "Verao"]},
            {"nome": "Robalo Peva", "horas": (18, 22), "clima": None,    "estacoes": ["Primavera", "Verao"]},
            # Outono: horário bem reduzido
            {"nome": "Robalo Peva", "horas": (6,   9), "clima": "sol",   "estacoes": ["Outono"]},
        ],
        "raro": [
            # Corvina Malhada — Outono e Inverno (entra no estuário com a friagem)
            {"nome": "Corvina Malhada", "horas": (5,  12), "clima": None,    "estacoes": ["Outono", "Inverno"]},
            {"nome": "Corvina Malhada", "horas": None,     "clima": "chuva", "estacoes": ["Outono", "Inverno"]},
            # Primavera: aparece pouco, só de manhã com sol
            {"nome": "Corvina Malhada", "horas": (6,  10), "clima": "sol",   "estacoes": ["Primavera"]},
            # Curvina — todo o ano, noturna (emite sons para se comunicar)
            {"nome": "Curvina",         "horas": (20,  4), "clima": None,    "estacoes": None},
            # Robalo Flecha — Primavera e Verão
            {"nome": "Robalo Flecha",   "horas": (5,   9), "clima": "sol",   "estacoes": ["Primavera", "Verao"]},
            {"nome": "Robalo Flecha",   "horas": (18, 22), "clima": None,    "estacoes": ["Primavera", "Verao"]},
        ],
        "lendario": [
            # Snook Gigante — Verão (águas quentes do estuário)
            {"nome": "Snook Gigante", "horas": (20,  5), "clima": None,    "estacoes": ["Verao"]},
            {"nome": "Snook Gigante", "horas": None,     "clima": "chuva", "estacoes": ["Primavera", "Verao"]},
            # Inverno: madrugada com chuva forte — raridade máxima
            {"nome": "Snook Gigante", "horas": (1,   5), "clima": "chuva", "estacoes": ["Inverno"]},
            # Guaivira — Verão, sol forte da tarde
            {"nome": "Guaivira", "horas": (10, 16), "clima": "sol", "estacoes": ["Verao"]},
            # Primavera: surge no fim da tarde
            {"nome": "Guaivira", "horas": (12, 16), "clima": "sol", "estacoes": ["Primavera"]},
        ],
    },
}

# Nome de exibição de cada tipo de água (usado no título do mini-game)
NOMES_DISPLAY = {
    "tile_mar":   "MAR",
    "tile_lago":  "LAGO",
    "tile_mangi": "MANGUEZAL",
}

# ──────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────────────────────────────────────

def _hora_valida(horas_range, hora_atual: int) -> bool:
    """Verifica se hora_atual está dentro do intervalo (com wrap-around às 00h)."""
    if horas_range is None:
        return True
    ini, fim = horas_range
    if ini <= fim:
        return ini <= hora_atual < fim
    else:                                    # ex: (20, 6) = 20h→00h→06h
        return hora_atual >= ini or hora_atual < fim


def _estacao_valida(estacoes_entrada, estacao_atual: str) -> bool:
    """Retorna True se a estação atual está permitida na entrada.
    None significa 'qualquer estação'."""
    if estacoes_entrada is None:
        return True
    return estacao_atual in estacoes_entrada


# Ordem de fallback quando uma raridade não tem candidatos disponíveis
_ORDEM_RARIDADE = ["lendario", "raro", "incomum", "comum"]


def _filtrar_strict(tipo_agua: str, raridade: str,
                    hora: int, clima: str, estacao: str) -> list:
    """
    Filtra candidatos para uma raridade específica sem nenhum fallback.
    Retorna lista vazia se nenhum peixe estiver disponível nesse momento.

    Regras (em ordem de prioridade):
      1. hora + clima + estação batem  → retorna esses
      2. hora + estação batem, ignora clima → retorna esses
         (APENAS entradas com horas definido — entradas horas=None dependem
          do clima para fazer sentido e NÃO entram aqui)
      Sem candidatos → retorna []
    """
    tabela   = PEIXES_POR_TIPO.get(tipo_agua, PEIXES_POR_TIPO["tile_mar"])
    entradas = tabela.get(raridade, [])

    # 1. Estrito: hora + clima + estação
    cands = [
        e["nome"] for e in entradas
        if _hora_valida(e["horas"], hora)
        and (e["clima"] is None or e["clima"] == clima)
        and _estacao_valida(e.get("estacoes"), estacao)
    ]
    if cands:
        return cands

    # 2. Hora definida + estação bate + ignora clima
    cands = [
        e["nome"] for e in entradas
        if e["horas"] is not None
        and _hora_valida(e["horas"], hora)
        and _estacao_valida(e.get("estacoes"), estacao)
    ]
    return cands


def _filtrar_candidatos(tipo_agua: str, raridade: str,
                        hora: int, clima: str, estacao: str = "Primavera") -> tuple:
    """
    Retorna (raridade_final, candidatos) para a raridade pedida.
    Se não houver nenhum candidato válido (hora+clima+estação incompatíveis),
    cai para a próxima raridade na hierarquia até encontrar algum.
    Lixo é tratado separadamente: sempre tem candidatos (entradas sem
    restrição de hora/clima/estação), então nunca cai para fallback de peixe.
    """
    # Lixo tem sua própria hierarquia — nunca cai para raridades de peixe
    if raridade == "lixo":
        tabela   = PEIXES_POR_TIPO.get(tipo_agua, PEIXES_POR_TIPO["tile_mar"])
        entradas = tabela.get("lixo", [])
        cands = [
            e["nome"] for e in entradas
            if _hora_valida(e["horas"], hora)
            and (e["clima"] is None or e["clima"] == clima)
            and _estacao_valida(e.get("estacoes"), estacao)
        ]
        if not cands:
            # fallback: qualquer lixo sem restrição de hora/clima
            cands = [e["nome"] for e in entradas if e["horas"] is None]
        if not cands:
            cands = ["Lixo"]   # segurança absoluta
        return "lixo", cands

    inicio = _ORDEM_RARIDADE.index(raridade) if raridade in _ORDEM_RARIDADE else len(_ORDEM_RARIDADE)
    for rar in _ORDEM_RARIDADE[inicio:]:
        cands = _filtrar_strict(tipo_agua, rar, hora, clima, estacao)
        if cands:
            return rar, cands

    # Último recurso absoluto: Lambari (sempre disponível, sem restrições)
    return "comum", ["Lambari"]


def _sortear_peixe(candidatos: list) -> str:
    """Sorteia um peixe da lista com igual probabilidade."""
    return random.choice(candidatos) if candidatos else "Lixo"


def _calcular_estrelas(nivel_pesca: int) -> int:
    """Legado — mantido por compatibilidade. O sorteio agora é feito por _sortear_qualidade_vara."""
    return min(4, nivel_pesca // 3)


def _obter_item_estrelado(nome_base: str, estrelas: int) -> str:
    """Delega para itens.py para garantir registro em todos_itens."""
    if estrelas <= 0:
        return nome_base
    from itens import obter_item_estrelado as _oes
    return _oes(nome_base, estrelas)


# ══════════════════════════════════════════════════════════════════════════════
# PescaMiniGame
# ══════════════════════════════════════════════════════════════════════════════
class PescaMiniGame:
    """
    Fase 0 — Navegação da boia:
      WASD movem a boia dentro do aquário (arte_mar.png 128×128).
      A boia começa em y=0 do PNG (topo da imagem).
      Profundidade máxima = (nivel_pesca + 1) * 10% de 128px.
        nivel 0 →  10% = 12px   nivel 5 →  60% = 76px
        nivel 1 →  20% = 25px   nivel 6 →  70% = 89px
        nivel 2 →  30% = 38px   nivel 7 →  80% = 102px
        nivel 3 →  40% = 51px   nivel 8 →  90% = 115px
        nivel 4 →  50% = 64px   nivel 9 → 100% = 128px
                                 nivel 10→ 100% = 128px (cap)
      Peixes nadam da esquerda/direita; bolhas sobem do fundo.
      Quando a boia toca um peixe → Fase 1.
      Sem corais.

    Fase 1 — Barra de captura (timing):
      Cursor oscila sobre barra R/Y/G.
      Z / Espaço → puxar.
      Verde = captura | Amarelo = -1 vida + acelera | Vermelho = falha.
    """

    # Dimensões do fundo (arte_mar.png) — PNG 128×128
    MAR_W = 128
    MAR_H = 128
    CEL   = 4    # px por célula do grid interno; 128/4 = 32 cols, 128/4 = 32 rows

    def __init__(self, v, jogador, font_sid, box_sid,
                 itens_sprite_ids, arte_mar_sid,
                 tipo_agua: str = "tile_mar",
                 estado_chuva: dict = None):
        """
        tipo_agua:    "tile_mar" | "tile_lago" | "tile_mangi"
        estado_chuva: dict com chave 'chovendo' (bool) — fonte de verdade do clima.
                      Se None, usa jogador.clima como fallback (legado).
        """
        self.v          = v
        self.jogador    = jogador
        self.font_sid   = font_sid
        self.box_sid    = box_sid
        self.itens_sids = itens_sprite_ids
        self.mar_sid    = arte_mar_sid
        self.tipo_agua  = tipo_agua
        self.estado_chuva = estado_chuva   # fonte de verdade do clima

        vara             = jogador.itens_equipados.get("Primeira Mão", "")
        self.def_vara    = DEFINICAO_VARAS.get(vara, _VARA_PADRAO)
        # Suporta hab_pesca (atributo direto) e hab_niveis["pesca"] (dict)
        if hasattr(jogador, "hab_pesca"):
            self.nivel_pesca = jogador.hab_pesca
        else:
            self.nivel_pesca = getattr(jogador, "hab_niveis", {}).get("pesca", 1)

        # Estação atual — lida direto do jogador; fallback "Primavera" por segurança
        self.estacao = getattr(jogador, "estacao_atual", "Primavera")

        # Posição do sprite no centro da tela (364×244)
        scr_w      = v.render_w
        scr_h      = v.render_h
        self.mar_x = (scr_w - self.MAR_W) // 2
        self.mar_y = (scr_h - self.MAR_H) // 2 - 8

        # Grid interno: cobre TODO o PNG (boia começa no y=0 do PNG)
        C            = self.CEL
        self.aq_x0   = self.mar_x           # pixel esquerdo do aquário na tela
        self.aq_y0   = self.mar_y           # pixel do TOPO do PNG na tela (y=0)
        self.AQ_COLS = self.MAR_W // C      # 32 colunas
        self.AQ_ROWS = self.MAR_H // C      # 32 linhas (cobre 128px inteiros)

        # Profundidade máxima em LINHAS de célula:
        #   nivel 0 → 10% de 128 = 12.8px → int/CEL = 3 linhas
        #   nivel N → (N+1)*10% de 128px, mín 1 linha, máx AQ_ROWS-1
        nivel_base = min(10, max(0, self.nivel_pesca))
        prof_px    = int(self.MAR_H * (nivel_base + 1) * 0.10)
        prof_px   += self.def_vara["bonus_prof"] * self.CEL   # vara soma células extras
        self.prof_max = max(1, min(self.AQ_ROWS - 1, prof_px // C))

        # Estado geral
        self.fase           = 0
        self.vitoria        = False
        self.encerrado      = False
        self.mensagem_final = ""
        self.peixe_nome     = ""
        self.peixe_raridade = "comum"
        self.xp_ganho       = 0
        self.estrelas       = 0
        self.frame          = 0

        # Fase 0 — boia (começa na linha 0 = topo do PNG)
        self.anzol_col   = self.AQ_COLS // 2
        self.anzol_row   = 0               # linha 0 = y=0 do PNG
        self.peixes      = []
        self.spawn_timer = 0
        self.bolhas      = []
        self.bolha_timer = 0

        # Movimento fluido: delay inicial e intervalo de repetição (em frames)
        self._MOV_DELAY  = 18   # frames até começar a repetir ao segurar
        self._MOV_REPEAT = 6    # frames entre cada passo repetido
        # Timers por direção: "up", "down", "left", "right"
        self._mov_timer  = {"up": 0, "down": 0, "left": 0, "right": 0}

        # Fase 1 — barra
        # vidas começa em 0: o jogador precisa GANHAR os 3 corações
        # acertando na zona verde antes de poder capturar o peixe.
        self.barra_mapa = []
        self.barra_w    = 0
        self.cursor_pos = 0.0
        self.cursor_dir = 1
        self.cursor_vel = 0.8
        self.vidas      = 0   # 0 = nenhum coração; máx = 3

        # Cores da barra
        self._CR = (200,  55,  55)
        self._CY = (215, 195,  40)
        self._CG = ( 55, 175,  55)
        self._CW = (0, 0, 0)

    # ── Inicializa a barra de captura ─────────────────────────────────────────
    def _iniciar_disputa(self):
        self.fase = 1

        prof       = self.anzol_row
        hora       = getattr(self.jogador, "horas", 12)

        # Fonte de verdade do clima: estado_chuva['chovendo'] (passado pelo game.py).
        # Fallback para jogador.clima para compatibilidade com código legado.
        if self.estado_chuva is not None:
            chovendo = self.estado_chuva.get("chovendo", False)
        else:
            chovendo = getattr(self.jogador, "clima", "sol") == "chuva"
        clima = "chuva" if chovendo else "sol"

        # ── Raridade do peixe ─────────────────────────────────────────────────
        # 1. Decide se cai lixo (chance_lixo da vara ou cálculo por profundidade)
        chance_lixo = self.def_vara.get("chance_lixo")
        if chance_lixo is None:
            chance_lixo = max(5, 55 - prof * 2.8)   # cálculo padrão por profundidade

        if random.uniform(0, 100) < chance_lixo:
            raridade = "lixo"
        else:
            # 2. Sorteia a raridade usando chance_peixe da vara (ou profundidade pura)
            raridade = _sortear_raridade_vara(self.def_vara, prof)

        self.peixe_raridade, cands = _filtrar_candidatos(
            self.tipo_agua, raridade, hora, clima, self.estacao
        )
        self.peixe_nome            = _sortear_peixe(cands)

        atrib = ATRIBUTOS_RARIDADE[self.peixe_raridade]

        # Velocidade do cursor: nível reduz 3% por nível + redução extra da vara
        reducao_vel  = 1.0 - (self.nivel_pesca * 0.03) - self.def_vara["menor_velocidade"]
        reducao_vel  = max(0.20, reducao_vel)             # piso de 20% da vel original
        self.cursor_vel = atrib["vel_cursor"] * reducao_vel

        # XP: base da raridade + bônus da vara
        self.xp_ganho = atrib["xp_pescar"] + self.def_vara["bonus_xp"]

        # Qualidade (estrelas): lixo nunca ganha — demais usam sorteio ponderado vara+nível
        if self.peixe_raridade == "lixo":
            self.estrelas = 0
        else:
            self.estrelas = _sortear_qualidade_pesca(self.def_vara, self.nivel_pesca)

        layout = TABELA_DIFICULDADE.get(self.peixe_raridade, TABELA_DIFICULDADE["comum"])
        self.barra_mapa = []
        for tipo, tam in layout:
            self.barra_mapa.extend([tipo] * tam)
        self.barra_w    = len(self.barra_mapa)
        self.cursor_pos = 0.0
        self.cursor_dir = 1
        self.vidas      = 0   # começa sem corações — precisa ganhar os 3

    # ── Atualizar (1× por frame) ──────────────────────────────────────────────
    def atualizar(self, v):
        self.frame += 1
        if self.fase == 0:
            self._upd_fase0(v)
        else:
            self._upd_fase1(v)

    def _mov_fluido(self, v, direcao: str, teclas: list) -> bool:
        """
        Retorna True no frame em que a boia deve se mover na direção dada.
        - Primeiro toque (key_down, t==0): move imediatamente.
        - Segurar: aguarda _MOV_DELAY frames, depois repete a cada
          _MOV_REPEAT frames — movimento contínuo e fluido.
        - Ao soltar: zera o timer daquela direção.
        """
        pressionada = any(v.key_down(t) for t in teclas)
        if not pressionada:
            self._mov_timer[direcao] = 0
            return False

        t = self._mov_timer[direcao]
        self._mov_timer[direcao] += 1

        if t == 0:
            return True   # primeiro toque: move imediatamente
        if t >= self._MOV_DELAY and (t - self._MOV_DELAY) % self._MOV_REPEAT == 0:
            return True   # repetição ao segurar
        return False

    def _upd_fase0(self, v):
        if v.key_pressed(b"x") or v.key_pressed(b"escape"):
            self.encerrado      = True
            self.mensagem_final = "Voce recolheu a vara."
            return

        if self._mov_fluido(v, "up",    [b"w", b"up"]):
            if self.anzol_row > 0:                self.anzol_row -= 1
        if self._mov_fluido(v, "down",  [b"s", b"down"]):
            if self.anzol_row < self.prof_max:    self.anzol_row += 1
        if self._mov_fluido(v, "left",  [b"a", b"left"]):
            if self.anzol_col > 0:                self.anzol_col -= 1
        if self._mov_fluido(v, "right", [b"d", b"right"]):
            if self.anzol_col < self.AQ_COLS - 1: self.anzol_col += 1

        # Spawn peixes — nadam em qualquer linha dentro do prof_max
        self.spawn_timer += 1
        if self.spawn_timer >= 38 and len(self.peixes) < 7:
            self.spawn_timer = 0
            dire = random.choice([-1, 1])
            cores = [
                (240, 215,  50), (240, 130,  40), (195,  55,  50),
                (170, 120, 235), ( 70, 170, 235), ( 60, 200, 110),
            ]
            cr, cg, cb = random.choice(cores)
            self.peixes.append({
                "col":  0.0 if dire == 1 else float(self.AQ_COLS - 1),
                "row":  random.randint(1, max(1, self.prof_max - 1)),
                "vel":  random.uniform(0.12, 0.38),
                "dir":  dire,
                "tam":  random.choice([1, 1, 2, 2, 3]),
                "cr": cr, "cg": cg, "cb": cb,
                "frac": 0.0,
            })

        # Move peixes
        novos = []
        for p in self.peixes:
            p["frac"] += p["vel"]
            while p["frac"] >= 1.0:
                p["frac"] -= 1.0
                p["col"]  += p["dir"]
            icol = int(p["col"])
            if not (0 <= icol < self.AQ_COLS):
                continue
            if icol <= self.anzol_col < icol + p["tam"] and p["row"] == self.anzol_row:
                self._iniciar_disputa()
                return
            novos.append(p)
        self.peixes = novos

        # Bolhas — nascem na linha mais funda acessível e sobem
        self.bolha_timer += 1
        if self.bolha_timer >= 22:
            self.bolha_timer = 0
            self.bolhas.append({
                "col":  random.randint(0, self.AQ_COLS - 1),
                "row":  float(self.prof_max),
                "vel":  random.uniform(0.06, 0.16),
                "frac": 0.0,
                "size": random.choice([1, 1, 2]),
            })
        nb = []
        for b in self.bolhas:
            b["frac"] += b["vel"]
            while b["frac"] >= 1.0:
                b["frac"] -= 1.0
                b["row"]  -= 1
            if b["row"] > 0:
                nb.append(b)
        self.bolhas = nb

    def _upd_fase1(self, v):
        self.cursor_pos += self.cursor_vel * self.cursor_dir
        if self.cursor_pos >= self.barra_w - 1:
            self.cursor_pos = float(self.barra_w - 1)
            self.cursor_dir = -1
        elif self.cursor_pos <= 0:
            self.cursor_pos = 0.0
            self.cursor_dir = 1

        if v.key_pressed(b"z") or v.key_pressed(b" ") or v.key_pressed(b"return"):
            idx  = int(self.cursor_pos)
            zona = self.barra_mapa[idx] if 0 <= idx < self.barra_w else "R"

            if zona == "G":
                # Acertou a zona verde → ganha um coração e desacelera 15%
                self.vidas     += 1
                self.cursor_vel = max(0.20, self.cursor_vel * 0.85)
                if self.vidas >= 3:
                    # 3 corações cheios → captura realizada!
                    self.vidas     = 3
                    self.vitoria   = True
                    self.encerrado = True
                # Ainda não capturou: reinicia cursor
                self.cursor_pos = 0.0
                self.cursor_dir = 1

            elif zona == "Y":
                # Zona de perigo → perde um coração e cursor acelera
                self.vidas      -= 1
                self.cursor_vel *= 1.25
                if self.vidas < 0:
                    self.vidas = 0
                self.cursor_pos = 0.0
                self.cursor_dir = 1

            elif zona == "R":
                # Zona vermelha → falha instantânea
                self.encerrado      = True
                self.mensagem_final = "O peixe fugiu!"

        if v.key_pressed(b"x") or v.key_pressed(b"escape"):
            self.encerrado      = True
            self.mensagem_final = "Voce desistiu."

    # ═══════════════════════════════════════════════════════════════════════════
    # DESENHO
    # ═══════════════════════════════════════════════════════════════════════════
    def desenhar(self, v):
        v.draw_overlay(0, 0, v.render_w, v.render_h, 0, 0, 0, 0.62)

        # Fundo: arte_mar.png 128×128 completo, centralizado
        v.draw_sprite_part(self.mar_sid,
                           self.mar_x, self.mar_y,
                           0, 0, self.MAR_W, self.MAR_H)

        # Linha tracejada de profundidade máxima (fase 0)
        if self.fase == 0:
            self._draw_limite_prof(v)

        self._draw_bolhas(v)
        self._draw_peixes(v)
        self._draw_boia_e_linha(v)
        self._draw_titulo(v)

        if self.fase == 0:
            # Fase de navegação: mostra UI de profundidade + dicas
            self._draw_ui(v)
        else:
            # Fase de captura: substitui a UI por caixa com barra + corações
            self._draw_barra_e_coracoes(v)

        v.flush()

    # ── Helpers de posição ────────────────────────────────────────────────────
    def _px(self, col: int) -> int:
        """Coluna de célula → pixel X absoluto na tela."""
        return self.aq_x0 + col * self.CEL

    def _py(self, row) -> int:
        """Linha de célula → pixel Y absoluto na tela (y=0 do PNG = topo)."""
        return self.aq_y0 + int(row) * self.CEL

    # ── Bolhas ────────────────────────────────────────────────────────────────
    def _draw_bolhas(self, v):
        for b in self.bolhas:
            cx = self._px(b["col"]) + self.CEL // 2
            cy = self._py(b["row"]) + self.CEL // 2
            s  = b["size"]
            # Anel da bolha (4 lados)
            v.draw_rect(cx - s,     cy - s,     s*2+1, 1,     140, 210, 255)
            v.draw_rect(cx - s,     cy + s,     s*2+1, 1,     140, 210, 255)
            v.draw_rect(cx - s,     cy - s + 1, 1,     s*2-1, 140, 210, 255)
            v.draw_rect(cx + s,     cy - s + 1, 1,     s*2-1, 140, 210, 255)
            # Reflexo
            v.draw_rect(cx - s + 1, cy - s + 1, 1, 1, 220, 240, 255)

    # ── Peixes ────────────────────────────────────────────────────────────────
    def _draw_peixes(self, v):
        C = self.CEL
        for p in self.peixes:
            px  = self._px(int(p["col"]))
            py  = self._py(p["row"])
            tam = p["tam"]
            cr, cg, cb = p["cr"], p["cg"], p["cb"]
            cw, ch = tam * C, C

            # Corpo
            v.draw_rect(px, py, cw, ch, cr, cg, cb)
            # Rabo
            rw = max(2, C // 2)
            rh = max(2, C // 2)
            if p["dir"] == 1:
                v.draw_rect(px - rw + 1, py + ch//4, rw, rh, cr, cg, cb)
            else:
                v.draw_rect(px + cw - 1, py + ch//4, rw, rh, cr, cg, cb)
            # Barbatana dorsal (1px mais escura)
            dr, dg, db = max(0, cr-45), max(0, cg-45), max(0, cb-45)
            v.draw_rect(px + cw//4, py - 1, max(1, cw//2), 1, dr, dg, db)
            # Olho branco + pupila preta
            ox = (px + cw - 3) if p["dir"] == 1 else (px + 1)
            v.draw_rect(ox, py + 1, 2, 2, 240, 240, 240)
            v.draw_rect(ox + (0 if p["dir"] == 1 else 1), py + 1, 1, 1, 20, 20, 20)

    # ── Boia e linha ─────────────────────────────────────────────────────────
    def _draw_boia_e_linha(self, v):
        C  = self.CEL
        # Centro horizontal da coluna da boia
        lx = self._px(self.anzol_col) + C // 2

        # Linha de pesca: do topo do PNG (y=0 da tela do aquário) até a boia
        for row in range(self.anzol_row):
            v.draw_rect(lx, self._py(row), 1, C, 210, 205, 170)

        # Boia: círculo flutuante na posição atual
        # Pisca vermelho na fase 1 (peixe fisgado)
        pisca = (self.frame // 5) % 2 == 0
        by    = self._py(self.anzol_row)

        if self.fase == 1 and pisca:
            # Piscando — vermelho vivo
            cr, cg, cb = 255, 60, 40
        else:
            # Estado normal — boia laranja/vermelha clássica
            cr, cg, cb = 220, 90, 30

        # Corpo da boia: retângulo arredondado simulado
        # Parte superior (branca — flutua acima d'água)
        v.draw_rect(lx - 1, by,         3, C // 2, 230, 230, 230)
        # Parte inferior (colorida — fica submersa)
        v.draw_rect(lx - 1, by + C//2,  3, C // 2, cr, cg, cb)
        # Linha central (divisor branco/colorido)
        v.draw_rect(lx - 2, by + C//2 - 1, 5, 1, 255, 255, 255)
        # Ponta inferior afunilada
        v.draw_rect(lx,     by + C - 1,    1, 2, cr, cg, cb)

    # ── Linha tracejada de profundidade máxima ────────────────────────────────
    def _draw_limite_prof(self, v):
        """Linha tracejada horizontal no limite de profundidade do jogador."""
        if self.prof_max >= self.AQ_ROWS - 1:
            return
        ly = self._py(self.prof_max)
        # Tracejado: 3px preenchido, 3px vazio
        for col in range(0, self.AQ_COLS, 2):
            v.draw_rect(self._px(col), ly, self.CEL, 1, 90, 90, 90)

    # ── Barra de captura interna (chamada por _draw_barra_e_coracoes) ──────────
    def _draw_barra(self, v, bx, by):
        """
        Desenha a barra de captura na posição (bx, by).
        SEG_W=3, SEG_H=6 → máximo 24 segs × 3 = 72px, cabe em 128px.
        """
        SEG_W, SEG_H = 4, 7
        total_w = self.barra_w * SEG_W

        # Moldura branca (1px de borda)
        v.draw_rect(bx - 1, by - 1, total_w + 2, SEG_H + 2,
                    self._CW[0], self._CW[1], self._CW[2])
        # Segmentos coloridos
        cor_map = {"R": self._CR, "Y": self._CY, "G": self._CG}
        for i, tipo in enumerate(self.barra_mapa):
            cor = cor_map.get(tipo, self._CW)
            v.draw_rect(bx + i * SEG_W, by, SEG_W - 1, SEG_H,
                        cor[0], cor[1], cor[2])
        # Cursor ▼ (triângulo compacto — 3 linhas)
        idx = int(self.cursor_pos)
        cx  = bx + idx * SEG_W + SEG_W // 2 - 1
        cy  = by - 4
        v.draw_rect(cx,     cy,     3, 1, self._CW[0], self._CW[1], self._CW[2])
        v.draw_rect(cx + 1, cy + 1, 1, 1, self._CW[0], self._CW[1], self._CW[2])
        # Linha vertical do cursor sobre a barra
        v.draw_rect(cx + 1, by, 1, SEG_H, self._CW[0], self._CW[1], self._CW[2])

    # ── Caixa de captura: barra + corações (substitui _draw_ui na fase 1) ─────
    def _draw_barra_e_coracoes(self, v):
        """
        Fase 1 — substitui a _draw_ui.
        SEG_W=4, SEG_H=7  (deve bater com _draw_barra)
        Layout dentro da caixa (de cima para baixo):
          BT(8)   ← padding topo da box
          6px     ← corações 7×6px
          2px     ← gap
          4px     ← cursor ▼ acima da barra
          7px     ← barra (SEG_H=7)
          2px     ← gap
          8px     ← dica "Z: puxar!"
          BT(8)   ← padding base da box
        Total box_h = 8+6+2+4+7+2+8+8 = 45px
        """
        BT    = 8
        FW    = 8
        FH    = 8
        SEG_W = 4   # deve bater com _draw_barra
        SEG_H = 7   # deve bater com _draw_barra

        box_x = self.mar_x
        box_y = self.mar_y + self.MAR_H + 2
        box_w = self.MAR_W   # 128px
        box_h = BT + 6 + 2 + 4 + SEG_H + 2 + FH + BT   # = 45px

        # ── Moldura ───────────────────────────────────────────────────────────
        v.draw_text_box(
            x=box_x, y=box_y,
            box_w=box_w, box_h=box_h,
            title="", content="",
            box_sid=self.box_sid, box_tw=BT, box_th=BT,
            font_sid=self.font_sid, font_w=FW, font_h=FH,
        )

        # ── Corações 7×6px ────────────────────────────────────────────────────
        # 3 corações × 7px + 2 gaps × 3px = 27px → centralizado em 128px
        COR_W   = 7
        COR_GAP = 3
        total_c = 3 * COR_W + 2 * COR_GAP   # 27px
        cx_ini  = box_x + (box_w - total_c) // 2
        cy_cor  = box_y + BT

        for i in range(3):
            hx    = cx_ini + i * (COR_W + COR_GAP)
            hy    = cy_cor
            cheio = (i < self.vidas)

            if cheio:
                r, g, b    = 220,  50,  80
                hr, hg, hb = 255, 120, 140
            else:
                r, g, b    = 60, 60, 60
                hr, hg, hb = r, g, b

            v.draw_rect(hx + 1, hy,     2, 1, hr, hg, hb)
            v.draw_rect(hx + 4, hy,     2, 1, hr, hg, hb)
            v.draw_rect(hx,     hy + 1, 7, 3, r, g, b)
            v.draw_rect(hx + 1, hy + 4, 5, 1, r, g, b)
            v.draw_rect(hx + 2, hy + 5, 3, 1, r, g, b)

        # ── Barra de captura — centralizada com SEG_W=4 ───────────────────────
        total_bar = self.barra_w * SEG_W
        barra_x   = box_x + (box_w - total_bar) // 2
        barra_y   = cy_cor + 6 + 2 + 4   # corações + gap + cursor

        self._draw_barra(v, barra_x, barra_y)

        # ── Dica de controle ──────────────────────────────────────────────────
        dica   = "Z: puxar!"
        dica_x = box_x + (box_w - len(dica) * FW) // 2
        dica_y = barra_y + SEG_H + 2
        v.draw_text(dica_x, dica_y, dica,
                    font_sid=self.font_sid, font_w=FW, font_h=FH)

    # ── Título — draw_text_box 8×8 ────────────────────────────────────────────
    def _draw_titulo(self, v):
        FW, FH = 8, 8
        BT     = 8   # tile da box (8×8)

        if self.fase == 0:
            local  = NOMES_DISPLAY.get(self.tipo_agua, "AGUA")
            titulo = f"{local} | {self.estacao}"
            box_w   = 128
            box_h   = FH + BT * 2
            bx      = self.mar_x
            by      = self.mar_y - box_h - 2
            v.draw_text_box(
                x=bx, y=by, box_w=box_w, box_h=box_h,
                title="", content=titulo,
                box_sid=self.box_sid, box_tw=BT, box_th=BT,
                font_sid=self.font_sid, font_w=FW, font_h=FH,
            )
        else:
            # Nome do peixe no título durante a fase de captura
            label   = f"> Em Pesca <"
            box_w   = 128
            box_h   = FH + BT * 2
            bx      = self.mar_x
            by      = self.mar_y - box_h - 2
            v.draw_text_box(
                x=bx, y=by, box_w=box_w, box_h=box_h,
                title="", content=label,
                box_sid=self.box_sid, box_tw=BT, box_th=BT,
                font_sid=self.font_sid, font_w=FW, font_h=FH,
            )

    # ── UI abaixo do aquário — draw_text_box 8×8 ──────────────────────────────
    def _draw_ui(self, v):
        """UI de navegação — exibida apenas na fase 0."""
        FW, FH = 8, 8
        BT     = 8
        uy     = self.mar_y + self.MAR_H + 2
        box_w  = 128
        box_h  = FH * 2 + BT * 2 + 5   # 2 linhas de texto

        hora    = getattr(self.jogador, "horas", 0)
        content = (
            f"Prof:{self.anzol_row}/{self.prof_max} {hora:02d}h\n"
            f"WASD:mover  X:sair"
        )
        v.draw_text_box(
            x=self.mar_x, y=uy,
            box_w=box_w, box_h=box_h,
            title="", content=content,
            box_sid=self.box_sid, box_tw=BT, box_th=BT,
            font_sid=self.font_sid, font_w=FW, font_h=FH,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Processar resultado (chame UMA VEZ quando encerrado == True)
# ══════════════════════════════════════════════════════════════════════════════
def processar_resultado_pesca(estado_pesca: PescaMiniGame, jogador) -> str:
    if not estado_pesca.vitoria:
        return estado_pesca.mensagem_final or "O peixe escapou..."

    nome_base = estado_pesca.peixe_nome
    raridade  = estado_pesca.peixe_raridade
    xp        = estado_pesca.xp_ganho

    # Lixo nunca ganha qualidade
    if raridade == "lixo":
        nome_item = nome_base
        estrelas  = 0
    else:
        estrelas  = estado_pesca.estrelas
        nome_item = _obter_item_estrelado(nome_base, estrelas)

    jogador.adicionar_item(nome_item, 1)

    if hasattr(jogador, "ganhar_xp_hab"):
        jogador.ganhar_xp_hab("pescar", xp)
    elif hasattr(jogador, "ganhar_xp"):
        jogador.ganhar_xp(xp)

    return f"Pescou: {nome_base}  (+{xp} XP)"