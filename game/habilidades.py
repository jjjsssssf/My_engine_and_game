HABILIDADES = {
    "coleta":  {"nome": "Coleta",  "nivel_max": 10, "tipo_item": "Colheita"},
    "cultivo": {"nome": "Cultivo", "nivel_max": 10, "tipo_item": "Cultivo"},
    "pesca":   {"nome": "Pesca",   "nivel_max": 10, "tipo_item": "Peixe"},
    "social":  {"nome": "Social",  "nivel_max": 10, "tipo_item": None},
}

# XP necessário para subir cada nível de habilidade
XP_POR_NIVEL = 100

# XP ganho por ação
XP_ACOES = {
    "colher":    15,
    "plantar":    1,
    "pescar":    20,
    "conversar":  5,
    "presente":  10,
}

# Estrelas: nome, cor RGB, ordem
ESTRELAS_INFO = {
    0: {"nome": "Sem estrela", "cor": (80,  80,  80),  "simbolo": " "},
    1: {"nome": "Bronze",      "cor": (180, 100, 40),  "simbolo": "*"},
    2: {"nome": "Preta",       "cor": (60,  60,  60),  "simbolo": "*"},
    3: {"nome": "Ouro",        "cor": (220, 185, 30),  "simbolo": "*"},
    4: {"nome": "Platina",     "cor": (200, 220, 240), "simbolo": "*"},
}

# ══════════════════════════════════════════════════════════════════════
#  INICIALIZAÇÃO NO PLAYER
# ══════════════════════════════════════════════════════════════════════

def inicializar_habilidades(jogador):
    """Adiciona os atributos de habilidade ao jogador se não existirem."""
    if not hasattr(jogador, 'hab_niveis'):
        jogador.hab_niveis = {k: 1 for k in HABILIDADES}
    if not hasattr(jogador, 'hab_xp'):
        jogador.hab_xp = {k: 0 for k in HABILIDADES}
    if not hasattr(jogador, 'xp_pendente'):
        jogador.xp_pendente = 0
    if not hasattr(jogador, 'nivel_disponivel'):
        jogador.nivel_disponivel = False
    if not hasattr(jogador, '_niveis_para_distribuir'):
        jogador._niveis_para_distribuir = 0
    # Limiar de XP por instância — dobra a cada level up adquirido
    if not hasattr(jogador, 'xp_por_ponto') or jogador.xp_por_ponto <= 0:
        jogador.xp_por_ponto = XP_POR_NIVEL

# ══════════════════════════════════════════════════════════════════════
#  GANHO DE XP
# ══════════════════════════════════════════════════════════════════════

def ganhar_xp(jogador, acao: str) -> dict:
    """
    Concede XP ao jogador pela ação realizada.
    Retorna dict com: xp_ganho, xp_atual, nivel_subiu (bool), mensagem.

    A cada ponto ganho o limiar de XP dobra:
      1º ponto → 100 XP  |  2º → 200  |  3º → 400  |  4º → 800 ...
    """
    inicializar_habilidades(jogador)

    ganho = XP_ACOES.get(acao, 0)
    if ganho <= 0:
        return {"xp_ganho": 0, "xp_atual": jogador.xp, "nivel_subiu": False, "mensagem": ""}

    # Garante que o limiar por instância existe (compatibilidade com saves antigos)
    if not hasattr(jogador, 'xp_por_ponto') or jogador.xp_por_ponto <= 0:
        jogador.xp_por_ponto = XP_POR_NIVEL

    jogador.xp += ganho
    jogador.xp_pendente += ganho

    nivel_subiu = False
    msg = f"+{ganho} XP ({acao})"

    while jogador.xp_pendente >= jogador.xp_por_ponto:
        jogador.xp_pendente -= jogador.xp_por_ponto
        jogador.xp_por_ponto *= 2          # ← dobra o limiar
        jogador._niveis_para_distribuir = getattr(jogador, '_niveis_para_distribuir', 0) + 1
        jogador.nivel_disponivel = True
        nivel_subiu = True
        msg += " — Nível disponível! Abra o menu de status."

    return {
        "xp_ganho": ganho,
        "xp_atual": jogador.xp,
        "nivel_subiu": nivel_subiu,
        "mensagem": msg,
    }

# ══════════════════════════════════════════════════════════════════════
#  DISTRIBUIÇÃO DE NÍVEL
# ══════════════════════════════════════════════════════════════════════

def pode_subir_habilidade(jogador, chave: str) -> bool:
    inicializar_habilidades(jogador)
    cfg = HABILIDADES.get(chave)
    if not cfg:
        return False
    return (
        jogador._niveis_para_distribuir > 0
        and jogador.hab_niveis[chave] < cfg["nivel_max"]
    )

def subir_habilidade(jogador, chave: str) -> str:
    """Aumenta 1 nível na habilidade escolhida. Retorna mensagem."""
    inicializar_habilidades(jogador)
    if not pode_subir_habilidade(jogador, chave):
        cfg = HABILIDADES.get(chave, {})
        if jogador.hab_niveis.get(chave, 1) >= cfg.get("nivel_max", 10):
            return f"{cfg.get('nome', chave)} já está no nível máximo!"
        return "Sem pontos de nível disponíveis."

    jogador.hab_niveis[chave] += 1
    jogador._niveis_para_distribuir -= 1
    if jogador._niveis_para_distribuir <= 0:
        jogador.nivel_disponivel = False

    novo = jogador.hab_niveis[chave]
    nome_hab = HABILIDADES[chave]["nome"]
    return f"{nome_hab} subiu para nível {novo}!"

# ══════════════════════════════════════════════════════════════════════
#  CÁLCULO DE ESTRELAS DOS ITENS
# ══════════════════════════════════════════════════════════════════════

def _tipo_para_habilidade(tipo_item: str) -> str | None:
    """Mapeia tipo_presente de um item para a habilidade correspondente."""
    mapa = {
        "Colheita": "coleta",
        "Cultivo":  "cultivo",
        "Peixe":    "pesca",
    }
    return mapa.get(tipo_item)

def calcular_estrelas_item(jogador, item) -> int:
    """
    Sorteia as estrelas do item com base no nível da habilidade.
    As chances por nível crescem linearmente:
      Nível N → bronze = 10 + (N-1)*5%  |  prata = 2.5 + (N-1)*2.5%
                 ouro   = 0  + (N-1)*1.5% |  platina = 0 + (N-1)*0.9% (a partir nível 4)

    Se o item já tem estrelas base > 0 (ex: fertilizante), retorna direto.
    """
    import random as _random
    inicializar_habilidades(jogador)

    chave = _tipo_para_habilidade(getattr(item, 'tipo_presente', ''))
    if chave is None:
        return getattr(item, 'estrelas', 0)

    # Itens com estrelas fixas (ex: itens de fertilizante já aplicado)
    base = getattr(item, 'estrelas', 0)
    if base > 0:
        return base

    nivel = jogador.hab_niveis.get(chave, 1)
    n = nivel - 1   # offset para calcular a progressão (nível 1 → n=0)

    # Chances em % para cada tier
    chance_bronze  = 10.0 + n * 5.0
    chance_prata   = 2.5  + n * 2.5
    chance_ouro    = 0.0  + n * 1.5
    chance_platina = max(0.0, (n - 3) * 0.9)   # só começa no nível 4

    # Sorteia do maior para o menor (platina tem prioridade sobre ouro, etc.)
    r = _random.uniform(0, 100)
    if r < chance_platina:
        return 4
    if r < chance_ouro:
        return 3
    if r < chance_prata:
        return 2
    if r < chance_bronze:
        return 1
    return 0

def preco_com_estrelas(item, estrelas: int) -> int:
    """Preço ajustado pelas estrelas: cada nível de estrela +25% sobre o base."""
    mult = 1.0 + (estrelas * 0.25)
    return int(getattr(item, 'preco', 0) * mult)

# ══════════════════════════════════════════════════════════════════════
#  BÔNUS DE AMIZADE (habilidade social)
# ══════════════════════════════════════════════════════════════════════

def bonus_amizade(jogador) -> float:
    """
    Retorna um multiplicador de pontos de amizade com base no nível social.
    Nível 1 → 1.0×  |  Nível 10 → 2.0×
    """
    inicializar_habilidades(jogador)
    nivel = jogador.hab_niveis.get("social", 1)
    return 1.0 + (nivel - 1) * 0.111   # +~11% por nível → +100% no nível 10

# ══════════════════════════════════════════════════════════════════════
#  DESENHO DO MENU DE STATUS  (chama funções da engine via v)
# ══════════════════════════════════════════════════════════════════════

# Cores de estrela para desenho
_COR_ESTRELA = {
    0: (80,  80,  80),
    1: (180, 100, 40),
    2: (60,  60,  60),
    3: (220, 185, 30),
    4: (200, 220, 240),
}

def _desenhar_estrela(v, x, y, estrelas: int, font_sid, font_w=8, font_h=8):
    """Desenha um símbolo de estrela colorido na posição dada."""
    cor = _COR_ESTRELA.get(estrelas, (80, 80, 80))
    simbolo = "*" if estrelas > 0 else "-"
    v.draw_text(x, y, simbolo,
                font_sid=font_sid, font_w=font_w, font_h=font_h,
                r=cor[0], g=cor[1], b=cor[2])

def _barra_xp(v, x, y, w, h, xp_atual, xp_max):
    """Desenha uma barra de XP pixel-art."""
    # Fundo escuro
    v.draw_rect(x, y, w, h, 20, 20, 20)
    # Borda
    v.draw_rect(x,         y,     w, 1,  80, 80, 80)
    v.draw_rect(x,         y+h-1, w, 1,  80, 80, 80)
    v.draw_rect(x,         y,     1, h,  80, 80, 80)
    v.draw_rect(x+w-1,     y,     1, h,  80, 80, 80)
    # Preenchimento
    fill = int((xp_atual / max(1, xp_max)) * (w - 2))
    if fill > 0:
        v.draw_rect(x+1, y+1, fill, h-2, 80, 180, 80)

def desenhar_menu_status(v, jogador, box_sid, font_sid,
                          font_w=8, font_h=8,
                          cursor_hab=0, modo_distribuir=False):
    """
    Desenha o menu de Status + Habilidades completo.
    cursor_hab: índice da habilidade selecionada (0-3).
    modo_distribuir: True quando o jogador está escolhendo onde gastar o nível.
    """
    inicializar_habilidades(jogador)

    from funcoes import SCREEN_W, SCREEN_H
    FW, FH = font_w, font_h
    MX, MY = 4, 4
    BTH = 8
    BW = SCREEN_W - MX * 2
    BH = SCREEN_H - MY * 2
    PAD = 8

    # ── Painel principal ────────────────────────────────────────────
    v.draw_text_box(x=MX, y=MY, box_w=BW, box_h=BH,
                    title="== STATUS ==", content="",
                    box_sid=box_sid, box_tw=8, box_th=BTH,
                    font_sid=font_sid, font_w=FW, font_h=FH)

    cx = MX + PAD
    cy = MY + BTH + FH + 6

    # ── Informações básicas ─────────────────────────────────────────
    v.draw_text(cx, cy, f"Nome: {jogador.nome}", font_sid=font_sid, font_w=FW, font_h=FH)
    cy += FH + 3

    v.draw_text(cx, cy, f"HP:  {jogador.hp}/{jogador.hp_max}", font_sid=font_sid, font_w=FW, font_h=FH)
    cy += FH + 2
    v.draw_text(cx, cy, f"MP:  {jogador.mana}/{jogador.mana_max}", font_sid=font_sid, font_w=FW, font_h=FH)
    cy += FH + 2
    v.draw_text(cx, cy, f"Gold: {jogador.gold}G", font_sid=font_sid, font_w=FW, font_h=FH)
    cy += FH + 4

    # ── Barra XP geral ──────────────────────────────────────────────
    xp_pen    = getattr(jogador, 'xp_pendente', 0)
    xp_limite = getattr(jogador, 'xp_por_ponto', XP_POR_NIVEL)
    pts_disp  = getattr(jogador, '_niveis_para_distribuir', 0)
    v.draw_text(cx, cy, f"XP: {xp_pen}/{xp_limite}", font_sid=font_sid, font_w=FW, font_h=FH)
    cy += FH + 2
    _barra_xp(v, cx, cy, BW - PAD * 2, 5, xp_pen, xp_limite)
    cy += 9

    if pts_disp > 0:
        # Destaque piscante (usa cor diferente) para avisar o jogador
        v.draw_text(cx, cy, f">> {pts_disp} ponto(s) para distribuir! <<",
                    font_sid=font_sid, font_w=FW, font_h=FH,
                    r=255, g=220, b=60)
    cy += FH + 6

    # ── Separador decorativo ────────────────────────────────────────
    sep_w = BW - PAD * 2
    for sx in range(0, sep_w, 4):
        v.draw_rect(cx + sx, cy, 2, 1, 160, 130, 50)
    cy += 5

    # ── Habilidades ─────────────────────────────────────────────────
    chaves = list(HABILIDADES.keys())
    for i, chave in enumerate(chaves):
        cfg   = HABILIDADES[chave]
        nivel = jogador.hab_niveis.get(chave, 1)
        sel   = (i == cursor_hab)

        # Fundo do item selecionado
        if sel and modo_distribuir:
            v.draw_rect(cx - 2, cy - 1, BW - PAD * 2 + 4, FH + 3, 40, 60, 40)
        elif sel:
            v.draw_rect(cx - 2, cy - 1, BW - PAD * 2 + 4, FH + 3, 40, 40, 60)

        # Nome + nível
        label = f"{cfg['nome']:8s} Nv {nivel:2d}/{cfg['nivel_max']}"
        v.draw_text(cx, cy, label, font_sid=font_sid, font_w=FW, font_h=FH)

        # Mini barra de nível
        BAR_X = cx + (FW * 18)
        BAR_W = 30
        BAR_H = 4
        _barra_xp(v, BAR_X, cy + 2, BAR_W, BAR_H, nivel, cfg["nivel_max"])

        # Seta "pode subir" se tiver ponto disponível
        if sel and pode_subir_habilidade(jogador, chave):
            v.draw_text(BAR_X + BAR_W + 3, cy, "+",
                        font_sid=font_sid, font_w=FW, font_h=FH,
                        r=100, g=255, b=100)

        cy += FH + 4

    # ── Rodapé de controles ─────────────────────────────────────────
    rod_y = MY + BH - BTH - FH * 2 - 4
    for sx2 in range(0, BW - PAD * 2, 4):
        v.draw_rect(cx + sx2, rod_y - 3, 2, 1, 120, 100, 50)

    if modo_distribuir:
        v.draw_text(cx, rod_y,         "Cima/Baixo: escolher",
                    font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(cx, rod_y + FH + 1, "Z: confirmar  X: cancelar",
                    font_sid=font_sid, font_w=FW, font_h=FH)
    else:
        v.draw_text(cx, rod_y,         "Cima/Baixo: navegar",
                    font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(cx, rod_y + FH + 1, "Space: fechar",
                    font_sid=font_sid, font_w=FW, font_h=FH)

# ══════════════════════════════════════════════════════════════════════
#  ESTADO DO MENU DE STATUS (para usar em game.py)
# ══════════════════════════════════════════════════════════════════════

def inicializar_estado_status():
    return {
        "aberto":          False,
        "cursor_hab":      0,
        "modo_distribuir": False,
    }

def processar_input_status(estado_status, jogador, v):
    """
    Processa teclas do menu de status.
    Retorna True enquanto o menu deve continuar aberto.
    """
    chaves = list(HABILIDADES.keys())
    n = len(chaves)
    cur = estado_status["cursor_hab"]
    modo = estado_status["modo_distribuir"]
    pts = getattr(jogador, '_niveis_para_distribuir', 0)

    if v.key_pressed(b"up"):
        estado_status["cursor_hab"] = (cur - 1) % n
    if v.key_pressed(b"down"):
        estado_status["cursor_hab"] = (cur + 1) % n

    if v.key_pressed(b"z") or v.key_pressed(b"return"):
        if pts > 0 and not modo:
            estado_status["modo_distribuir"] = True
        elif modo:
            chave_sel = chaves[estado_status["cursor_hab"]]
            msg = subir_habilidade(jogador, chave_sel)
            print(f"[STATUS] {msg}")
            if getattr(jogador, '_niveis_para_distribuir', 0) <= 0:
                estado_status["modo_distribuir"] = False

    if v.key_pressed(b"x"):
        estado_status["modo_distribuir"] = False

    if v.key_pressed(b" "):
        estado_status["aberto"] = False
        estado_status["modo_distribuir"] = False
        return False

    return True

# ══════════════════════════════════════════════════════════════════════
#  DESENHO DE ESTRELA AO LADO DO ITEM NO INVENTÁRIO
# ══════════════════════════════════════════════════════════════════════

def desenhar_estrela_item(v, x, y, item, jogador, font_sid, font_w=8, font_h=8):
    """
    Desenha a estrela do item na posição (x, y).
    Deve ser chamado logo após desenhar o ícone do item.
    """
    estrelas = calcular_estrelas_item(jogador, item)
    if estrelas == 0:
        return
    cor = _COR_ESTRELA[estrelas]
    nome_estrela = ESTRELAS_INFO[estrelas]["nome"][0]  # B / P / O / Pl
    v.draw_text(x, y, nome_estrela,
                font_sid=font_sid, font_w=font_w, font_h=font_h,
                r=cor[0], g=cor[1], b=cor[2])