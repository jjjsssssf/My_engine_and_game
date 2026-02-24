# funcoes.py
import time
from itens import todos_itens
from artes import *
from objeto import (obter_bloco_frente,verificar_chao,substituir_bloco,verificar_interacao,verificar_interacao_mensagem,colocar_bloco,quebrar_bloco,)

# --- Constantes Globais ---
FPS = 60
FRAME_TIME = 1.0 / FPS
TILE_SIZE = 16
SCREEN_W = 256
SCREEN_H = 240

HOTBAR_SLOTS    = 9
HOTBAR_SLOT_W   = 16
HOTBAR_SLOT_H   = 16
HOTBAR_PADDING  = 2
HOTBAR_ICON_W   = 16
HOTBAR_ICON_H   = 16
HUD_W           = 88
HUD_H           = 32
HUD_PAD         = 4

_HOTBAR_TOTAL_W = HOTBAR_SLOTS * HOTBAR_SLOT_W + (HOTBAR_SLOTS - 1) * HOTBAR_PADDING
HOTBAR_X_INICIO = HUD_W + 6
HOTBAR_Y_TOPO   = 3
HOTBAR_Y_BAIXO  = SCREEN_H - HOTBAR_SLOT_H - 4
_LIMIAR_TOPO_PX = 40

def calc_camera(player_px, player_py, map_cols, map_rows):
    cam_x = player_px - SCREEN_W // 2 + TILE_SIZE // 2
    cam_y = player_py - SCREEN_H // 2 + TILE_SIZE // 2
    map_pixel_w = map_cols * TILE_SIZE
    map_pixel_h = map_rows * TILE_SIZE
    cam_x = max(0, min(cam_x, map_pixel_w - SCREEN_W))
    cam_y = max(0, min(cam_y, map_pixel_h - SCREEN_H))
    return cam_x, cam_y

def _draw_bloco_simples(v, bloco_info, tileset_ids, x_px, y_px):
    """Desenha um bloco normal (1x1) na posição de pixel dada."""
    sid = tileset_ids.get(bloco_info["sprite"])
    if sid is None:
        return
    rx = bloco_info.get("start_x", 0) + bloco_info.get("col", 0) * bloco_info.get("w", 16)
    ry = bloco_info.get("start_y", 0) + bloco_info.get("l",   0) * bloco_info.get("h", 16)
    v.draw_sprite_part(sid, x_px, y_px, rx, ry, bloco_info.get("w", 16), bloco_info.get("h", 16))

def _mega_src_origem(bloco_info):
    tw = bloco_info.get("w", 16)
    th = bloco_info.get("h", 16)
    if "col" in bloco_info or "lin" in bloco_info:
        sx = bloco_info.get("start_x", 0) + bloco_info.get("col", 0) * tw
        sy = bloco_info.get("start_y", 0) + bloco_info.get("lin", 0) * th
    else:
        sx = bloco_info.get("src_x", 0)
        sy = bloco_info.get("src_y", 0)
    return sx, sy

def _calcular_mascara_autotile(mapa, blocos, col, row, tile_val):
    map_rows = len(mapa)
    map_cols = len(mapa[0]) if map_rows > 0 else 0

    def _grupos(info, tid):
        g = info.get("autotile_grupo", tid)
        return set(g) if isinstance(g, (list, tuple)) else {g}

    grupos_a = _grupos(blocos.get(tile_val, {}), tile_val)

    def mesmo(c, r):
        if 0 <= c < map_cols and 0 <= r < map_rows:
            vizinho = mapa[r][c]
            grupos_v = _grupos(blocos.get(vizinho, {}), vizinho)
            return bool(grupos_a & grupos_v)   # interseção não vazia
        return True   # borda do mapa fecha a parede

    mask = 0
    if mesmo(col,   row-1): mask |= 8   # cima
    if mesmo(col,   row+1): mask |= 4   # baixo
    if mesmo(col-1, row  ): mask |= 2   # esquerda
    if mesmo(col+1, row  ): mask |= 1   # direita
    return mask

def autotile_frames_da_grade(col_inicio, lin_inicio, colunas=4, linhas=4):
    frames = {}
    i = 0
    for r in range(linhas):
        for c in range(colunas):
            frames[i] = (col_inicio + c, lin_inicio + r)
            i += 1
            if i >= 16:
                return frames
    return frames

def draw_world(v, mapa_dict, cam_x, cam_y, tileset_ids):
    mapa   = mapa_dict["arte"]
    blocos = mapa_dict["blocos"]
    map_rows = len(mapa)
    map_cols = len(mapa[0]) if map_rows > 0 else 0
    mega_ocupadas = set()

    # ── Primeira passagem: detecta âncoras de mega-tiles ──────────────
    for row in range(map_rows):
        for col in range(map_cols):
            tile_val   = mapa[row][col]
            bloco_info = blocos.get(tile_val)
            if not bloco_info:
                continue
            mega = bloco_info.get("mega")
            if not mega:
                continue
            # Este tile é a âncora (canto sup-esq). Marca os vizinhos.
            for dr in range(mega["rows"]):
                for dc in range(mega["cols"]):
                    if dr == 0 and dc == 0:
                        continue
                    mega_ocupadas.add((col + dc, row + dr))

    # ── Passagem principal: renderiza tudo ────────────────────────────
    for row in range(map_rows):
        for col in range(map_cols):
            tile_val = mapa[row][col]
            x_px = col * TILE_SIZE - cam_x
            y_px = row * TILE_SIZE - cam_y

            # Culling básico (margem extra para mega-tiles)
            if x_px + TILE_SIZE * 4 < 0 or x_px > SCREEN_W + TILE_SIZE * 4:
                continue
            if y_px + TILE_SIZE * 4 < 0 or y_px > SCREEN_H + TILE_SIZE * 4:
                continue

            # Célula ocupada por mega-tile (já foi desenhada pela âncora)
            if (col, row) in mega_ocupadas:
                continue

            bloco_info = blocos.get(tile_val)
            if not bloco_info:
                continue

            # ── Fundo ───────────────────────────────────────────────
            if "fundo" in bloco_info:
                fi = blocos.get(bloco_info["fundo"])
                if fi:
                    _draw_bloco_simples(v, fi, tileset_ids, x_px, y_px)

            # ── Plantações ──────────────────────────────────────────
            if "plantacoes" in mapa_dict and (col, row) in mapa_dict["plantacoes"]:
                from itens import TODAS_PLANTAS
                dados  = mapa_dict["plantacoes"][(col, row)]
                planta = TODAS_PLANTAS.get(dados["semente"])
                if planta:
                    if dados["dias_idade"] >= planta.dias_total:
                        idx = len(planta.estagios_tiles) - 1
                    else:
                        proporcao = dados["dias_idade"] / planta.dias_total
                        idx = min(int(proporcao * len(planta.estagios_tiles)),
                                  len(planta.estagios_tiles) - 2)
                    planta_tile_id = planta.estagios_tiles[idx]
                    if planta_tile_id in blocos:
                        b_info = blocos[planta_tile_id]
                        sid = tileset_ids.get(b_info["sprite"])
                        if sid is not None:
                            v.draw_sprite_part(
                                sid, x_px, y_px,
                                b_info.get("col", 0) * b_info.get("w", TILE_SIZE),
                                b_info.get("l",   0) * b_info.get("h", TILE_SIZE),
                                b_info.get("w", TILE_SIZE), b_info.get("h", TILE_SIZE)
                            )

            # ── MEGA-TILE: âncora desenha toda a área ───────────────
            mega = bloco_info.get("mega")
            if mega:
                sid = tileset_ids.get(bloco_info["sprite"])
                if sid is None:
                    continue
                src_x0, src_y0 = _mega_src_origem(bloco_info)
                tw = bloco_info.get("w", TILE_SIZE)   # tamanho de cada sub-tile
                th = bloco_info.get("h", TILE_SIZE)
                for dr in range(mega["rows"]):
                    for dc in range(mega["cols"]):
                        sub_src_x = src_x0 + dc * tw
                        sub_src_y = src_y0 + dr * th
                        dst_x = x_px + dc * TILE_SIZE
                        dst_y = y_px + dr * TILE_SIZE
                        v.draw_sprite_part(sid, dst_x, dst_y,
                                           sub_src_x, sub_src_y, tw, th)
                continue   # não cai no bloco simples abaixo

            # ── AUTO-TILE de paredes ────────────────────────────────
            if bloco_info.get("autotile"):
                frames = bloco_info.get("frames", {})
                # frames é um dict: mascara_int -> (col, lin) no spritesheet
                mask = _calcular_mascara_autotile(mapa, blocos, col, row, tile_val)
                frame = frames.get(mask, frames.get("padrao", None))
                if frame:
                    sid = tileset_ids.get(bloco_info["sprite"])
                    if sid is not None:
                        tw = bloco_info.get("w", TILE_SIZE)
                        th = bloco_info.get("h", TILE_SIZE)
                        rx = frame[0] * tw
                        ry = frame[1] * th
                        v.draw_sprite_part(sid, x_px, y_px, rx, ry, tw, th)
                continue

            # ── Bloco simples normal ────────────────────────────────
            _draw_bloco_simples(v, bloco_info, tileset_ids, x_px, y_px)

def _hotbar_y(jogador, cam_y):
    player_y_na_tela = jogador.grid_y * TILE_SIZE - cam_y
    if player_y_na_tela < _LIMIAR_TOPO_PX:
        return HOTBAR_Y_BAIXO
    return HOTBAR_Y_TOPO

def desenhar_hotbar(v, jogador, itens_sprite_ids, cam_y=0):
    from itens import todos_itens

    sy_base = _hotbar_y(jogador, cam_y)
    x0 = HOTBAR_X_INICIO

    v.draw_overlay(x0 - 2, sy_base - 2,_HOTBAR_TOTAL_W + 4, HOTBAR_SLOT_H + 4, 24,8,24, 1)

    for slot in range(1, HOTBAR_SLOTS + 1):
        sx = x0 + (slot - 1) * (HOTBAR_SLOT_W + HOTBAR_PADDING)
        sy = sy_base
        ativo    = (slot == jogador.item_selecionado)
        nome_item = jogador.hotbar.get(slot)
        equipado  = nome_item and (nome_item in jogador.itens_equipados.values())

        # --- Fundo do slot ---
        if equipado:
            if ativo:
                v.draw_rect(sx - 1, sy - 1, HOTBAR_SLOT_W + 2, HOTBAR_SLOT_H + 2, 80,48,104)
            v.draw_rect(sx, sy, HOTBAR_SLOT_W, HOTBAR_SLOT_H,240, 216, 248)

        elif ativo:
            v.draw_rect(sx - 1, sy - 1, HOTBAR_SLOT_W + 2, HOTBAR_SLOT_H + 2, 240, 216, 248)
            v.draw_rect(sx, sy, HOTBAR_SLOT_W, HOTBAR_SLOT_H, 176, 112, 192)

        else:
            v.draw_rect(sx, sy, HOTBAR_SLOT_W, HOTBAR_SLOT_H, 240, 216, 248)
            v.draw_rect(sx + 1, sy + 1, HOTBAR_SLOT_W - 2, HOTBAR_SLOT_H - 2, 50, 50, 65)

        # Número do slot pequeno no canto
        v.draw_text(sx + 1, sy + 1, str(slot),-1, font_w=6, font_h=8, chars_per_row=16) if False else None

        # --- Ícone do item ---
        if nome_item and nome_item in todos_itens:
            item = todos_itens[nome_item]
            sid  = itens_sprite_ids.get(item.sprite)
            if sid is not None:
                rx, ry, iw, ih = item.get_sprite_rect()
                icon_x = sx + (HOTBAR_SLOT_W - HOTBAR_ICON_W) // 2
                icon_y = sy + (HOTBAR_SLOT_H - HOTBAR_ICON_H) // 2
                v.draw_sprite_part(sid, icon_x, icon_y, rx, ry, iw, ih)

def processar_input_hotbar(v, jogador, mapa_dict):
    from itens import todos_itens
    
    # --- 1 a 9: Apenas seleciona o Slot da Hotbar ---
    for num in range(1, 10):
        if v.key_pressed(str(num).encode()):
            jogador.item_selecionado = num
            nome_item = jogador.hotbar.get(num)
            if nome_item:
                return f"[{nome_item}] equipado no slot {num}."
            return f"Slot {num} selecionado."

    slot_atual = jogador.item_selecionado
    nome_item = jogador.hotbar.get(slot_atual)
    item = todos_itens.get(nome_item) if nome_item else None
    #  --- ENTER: Atalho para plantar rapidamente ---
    if v.key_pressed(b"z"):
        if nome_item and item and item.tipo == "Semente":
            from objeto import plantar_semente, obter_bloco_frente
            
            # Descobre para onde o jogador está a olhar
            resultado = obter_bloco_frente(jogador, mapa_dict)
            
            if resultado:
                nx, ny, tile_id = resultado
                # Chama a função nova passando o nome da semente e as coordenadas!
                return plantar_semente(jogador, mapa_dict, nx, ny, nome_item)
            else:
                return "Fora do mapa."

    # --- R: Colocar bloco no chão ou Usar item ---
    if v.key_pressed(b"return"):
        if not nome_item:
            return "Slot vazio."
        if not item:
            return "Item inválido."

        # Se for um Material -> delega sempre para o sistema de colocar bloco
        if item.tipo == "Material":
            return colocar_bloco(jogador, mapa_dict)

        # Se for um item consumível/equipável -> usa
        res = jogador.usar_hotbar(slot_atual, todos_itens)
        if isinstance(res, dict):
            return res.get("msg", "")
        return str(res)

    # --- F: Usar ferramenta (quebrar/arar/regar) ---
    if v.key_pressed(b"x"):
        return quebrar_bloco(jogador, mapa_dict)

    return ""

def processar_input_inventario(v, jogador, inv_pagina, inv_cursor, max_pag, item_sel):
    # Movimentação nas páginas do inventário
    if v.key_pressed(b"up"):    inv_cursor -= 1
    if v.key_pressed(b"down"):  inv_cursor += 1
    if v.key_pressed(b"d") or v.key_pressed(b"right"):
        inv_pagina += 1; inv_cursor = 0
    if v.key_pressed(b"a") or v.key_pressed(b"left"):
        inv_pagina -= 1; inv_cursor = 0

    if item_sel:
        for num in range(1, 10):
            if v.key_pressed(str(num).encode()):
                jogador.hotbar[num] = item_sel

    return inv_pagina, inv_cursor

def processar_input_loja(v, loja_modo, loja_cursor, loja_pagina, itens_pagina):
    if v.key_pressed(b"space"):
        loja_modo = "vender" if loja_modo == "comprar" else "comprar"
        return loja_modo, 0, 0

    if v.key_pressed(b"down"):  loja_cursor += 1
    elif v.key_pressed(b"up"): loja_cursor -= 1
    if v.key_pressed(b"right"):
        loja_pagina += 1; loja_cursor = 0
    elif v.key_pressed(b"left"):
        loja_pagina -= 1; loja_cursor = 0

    loja_pagina = max(0, loja_pagina)
    if itens_pagina:
        loja_cursor = max(0, min(loja_cursor, len(itens_pagina) - 1))
    else:
        loja_cursor = 0
    return loja_modo, loja_cursor, loja_pagina

def gerar_lista_loja(jogador, loja_modo, todos_itens):
    if loja_modo == "comprar":
        return [n for n, o in todos_itens.items() if o.compravel]
    return [n for n in jogador.invetario if n in todos_itens and todos_itens[n].vendivel]

def calcular_paginacao_loja(lista_atual, loja_pagina, itens_por_pagina=5):
    total = len(lista_atual)
    max_p = max(0, (total - 1) // itens_por_pagina) if total > 0 else 0
    loja_pagina = max(0, min(loja_pagina, max_p))
    inicio = loja_pagina * itens_por_pagina
    return lista_atual[inicio:inicio + itens_por_pagina], max_p, loja_pagina

def gerar_texto_loja(jogador, loja_modo, itens_pagina, loja_cursor, loja_pagina, max_paginas, mensagem_loja, todos_itens):
    texto = f"Ouro: {jogador.gold}g\n[Space] Modo | [X] Sair\n--- {loja_modo.upper()} ---\n\n"
    if not itens_pagina:
        texto += "Vazio...\n"
    else:
        for i, nome in enumerate(itens_pagina):
            marca = "> " if i == loja_cursor else "  "
            obj   = todos_itens.get(nome)
            if loja_modo == "comprar":
                texto += f"{marca}{nome} - {obj.compra if obj else 0}g\n"
            else:
                texto += f"{marca}{nome} (x{jogador.invetario.get(nome,0)}) - {obj.preco if obj else 0}g\n"

    texto += f"\n> {mensagem_loja}\n"
    item_sel = itens_pagina[loja_cursor] if itens_pagina else None
    if item_sel and item_sel in todos_itens:
        texto += f"\n- {todos_itens[item_sel].descrica}"
    texto += f"\nPag {loja_pagina+1}/{max_paginas+1} | [Enter] Confirmar"
    return texto, item_sel

def processar_transacao_loja(v, jogador, loja_modo, item_sel, todos_itens, mensagem_loja):
    if v.key_pressed(b"return") and item_sel:
        if loja_modo == "comprar":
            mensagem_loja = jogador.comprar_item(item_sel, todos_itens, 1)
        else:
            mensagem_loja = jogador.vender_item(item_sel, todos_itens, 1)
    return mensagem_loja

def atualizar_camera(v, jogador, map_cols, map_rows):
    px, py = jogador.get_pixel_pos()
    cam_x, cam_y = calc_camera(px, py, map_cols, map_rows)
    v.set_object_pos(jogador.oid, px - cam_x, py - cam_y)
    return cam_x, cam_y

def desenhar_ui_inventario(v, jogador, inv_pagina, inv_cursor, box_sid, font_sid):
    texto, max_pag, inv_cursor, item_sel = jogador.obter_pagina_inventario(
        pagina=inv_pagina, itens_por_pagina=4, cursor_idx=inv_cursor
    )
    v.draw_text_box(
        x=0, y=0, box_w=256, box_h=240,
        title="Inventario", content=texto,
        box_sid=box_sid, box_tw=8, box_th=8,
        font_sid=font_sid, font_w=8, font_h=8
    )
    return inv_cursor, item_sel

def desenhar_ui_loja(v, texto_loja, box_sid, font_sid):
    v.draw_text_box(
        0, 0, 256, 240,
        title="Lojinha", content=texto_loja,
        box_sid=box_sid, box_tw=8, box_th=8,
        font_sid=font_sid, font_w=8, font_h=8
    )

def inicializar_estado_caixa():
    """Chame uma vez junto com inicializar_estado_ui()."""
    return {
        'mostrar_caixa':       False,
        'caixa_cursor':        0,
        'caixa_pagina':        0,
        'caixa_modo_qtd':      False, 
        'caixa_qtd_cursor':    1,
        'caixa_item_sel':      None,  
        'mostrar_relatorio':   False,
        'relatorio_dados':     None,
        'relatorio_pagina':    0,
    }

def _itens_vendiveis(jogador):
    """Retorna lista de (nome, qtd, item_obj) vendíveis do inventário."""
    resultado = []
    for nome, qtd in jogador.invetario.items():
        if nome in todos_itens and qtd > 0:
            obj = todos_itens[nome]
            if obj.vendivel:
                resultado.append((nome, qtd, obj))
    return resultado

def _paginar(lista, pagina, por_pagina):
    total = len(lista)
    max_pag = max(0, (total - 1) // por_pagina) if total > 0 else 0
    pagina = max(0, min(pagina, max_pag))
    inicio = pagina * por_pagina
    return lista[inicio: inicio + por_pagina], max_pag, pagina

def processar_vendas_e_dormir(jogador, estado_chuva=None):
    from artes import mapas_mundo
    from objeto import atualizar_plantacoes_do_mundo
    dia_anterior = jogador.dia_atual
    lucro_total = 0
    por_tipo    = {}
    caixa = jogador.caixa_vendas
    if isinstance(caixa, dict):
        itens_iter = list(caixa.items())
    else:
        contagem = {}
        for nome in caixa:
            contagem[nome] = contagem.get(nome, 0) + 1
        itens_iter = list(contagem.items())

    for nome, qtd in itens_iter:
        if nome not in todos_itens:
            continue
        obj        = todos_itens[nome]
        valor_total = obj.preco * qtd
        lucro_total += valor_total

        categoria = obj.tipo_presente if obj.tipo_presente else obj.tipo
        por_tipo.setdefault(categoria, {}).setdefault(nome, {'qtd': 0, 'valor': 0})
        por_tipo[categoria][nome]['qtd']   += qtd
        por_tipo[categoria][nome]['valor'] += valor_total

    jogador.gold += lucro_total
    jogador.caixa_vendas = {} if isinstance(caixa, dict) else []

    # ── 3. Avança o dia e a estação ────────────────────────────────────
    ESTACOES = ["Primavera", "Verao", "Outono", "Inverno"]
    jogador.dia_atual += 1
    if jogador.dia_atual > 28:
        jogador.dia_atual = 1
        idx_atual = ESTACOES.index(jogador.estacao_atual)
        jogador.estacao_atual = ESTACOES[(idx_atual + 1) % 4]

    # ── 4. Cresce / mata as plantações de todos os mapas ───────────────
    atualizar_plantacoes_do_mundo(mapas_mundo, jogador.estacao_atual)

    # ── 5. Decide o clima do novo dia (chuva) ──────────────────────────
    if estado_chuva is not None:
        decidir_clima_novo_dia(jogador, estado_chuva, mapas_mundo)

    # ── 6. Restaura status do jogador ──────────────────────────────────
    jogador.hp      = jogador.hp_max
    jogador.mana    = jogador.mana_max
    jogador.horas   = 6
    jogador.minutos = 0

    return {
        'dia_anterior': dia_anterior,
        'lucro_total':  lucro_total,
        'por_tipo':     por_tipo,
        'chovendo':     estado_chuva['chovendo'] if estado_chuva else False,
    }

ITENS_POR_PAG_CAIXA = 6

def atualizar_caixa_vendas(v, jogador, estado_caixa):
    ec = estado_caixa

    # ── Sub-estado: escolhendo quantidade ──────────────────
    if ec['caixa_modo_qtd']:
        nome = ec['caixa_item_sel']
        max_qtd = jogador.invetario.get(nome, 0)

        if v.key_pressed(b"up"):
            ec['caixa_qtd_cursor'] = min(ec['caixa_qtd_cursor'] + 1, max_qtd)
        elif v.key_pressed(b"down"):
            ec['caixa_qtd_cursor'] = max(ec['caixa_qtd_cursor'] - 1, 1)

        elif v.key_pressed(b"z"):
            qtd = ec['caixa_qtd_cursor']
            # Move do inventário para caixa_vendas
            jogador.invetario[nome] -= qtd
            if jogador.invetario[nome] <= 0:
                del jogador.invetario[nome]

            caixa = jogador.caixa_vendas
            if isinstance(caixa, dict):
                caixa[nome] = caixa.get(nome, 0) + qtd
            else:
                for _ in range(qtd):
                    caixa.append(nome)

            ec['caixa_modo_qtd']  = False
            ec['caixa_item_sel']  = None
            ec['caixa_qtd_cursor'] = 1

        elif v.key_pressed(b"q"):
            ec['caixa_modo_qtd']  = False
            ec['caixa_item_sel']  = None
            ec['caixa_qtd_cursor'] = 1

        return True   # segue no menu

    # ── Navegação principal ────────────────────────────────
    vendiveis = _itens_vendiveis(jogador)
    itens_pag, max_pag, ec['caixa_pagina'] = _paginar(
        vendiveis, ec['caixa_pagina'], ITENS_POR_PAG_CAIXA
    )
    n = len(itens_pag)

    if v.key_pressed(b"up"):
        ec['caixa_cursor'] = (ec['caixa_cursor'] - 1) % max(n, 1)
    elif v.key_pressed(b"down"):
        ec['caixa_cursor'] = (ec['caixa_cursor'] + 1) % max(n, 1)
    elif v.key_pressed(b"left"):
        ec['caixa_pagina'] = max(0, ec['caixa_pagina'] - 1)
        ec['caixa_cursor'] = 0
    elif v.key_pressed(b"right"):
        ec['caixa_pagina'] = min(max_pag, ec['caixa_pagina'] + 1)
        ec['caixa_cursor'] = 0

    elif v.key_pressed(b"z") and itens_pag:
        cursor = min(ec['caixa_cursor'], n - 1)
        nome, qtd_inv, obj = itens_pag[cursor]
        ec['caixa_modo_qtd']   = True
        ec['caixa_item_sel']   = nome
        ec['caixa_qtd_cursor'] = 1

    elif v.key_pressed(b"x"):
        ec['mostrar_caixa'] = False
        return False

    return True

def desenhar_caixa_vendas(v, jogador, estado_caixa, box_sid, font_sid,SCREEN_W, SCREEN_H):
    ec = estado_caixa
    BOX_X  = 0
    BOX_Y  = 0
    BOX_W  = SCREEN_W
    BOX_H  = SCREEN_H
    vendiveis = _itens_vendiveis(jogador)
    itens_pag, max_pag, ec['caixa_pagina'] = _paginar(
        vendiveis, ec['caixa_pagina'], ITENS_POR_PAG_CAIXA
    )
    n = len(itens_pag)
    cursor = min(ec['caixa_cursor'], max(n - 1, 0))

    # ── Calcula resumo da caixa ────────────────────────────
    caixa = getattr(jogador, 'caixa_vendas', {})
    if isinstance(caixa, dict):
        itens_na_caixa = sum(caixa.values())
        valor_caixa    = sum(todos_itens[nm].preco * q
                            for nm, q in caixa.items() if nm in todos_itens)
    else:
        itens_na_caixa = len(caixa)
        valor_caixa    = sum(todos_itens[nm].preco
                            for nm in caixa if nm in todos_itens)

    # ── Monta texto principal ──────────────────────────────
    if not itens_pag:
        lista_txt = "Nenhum item vendivel\nno inventario.\n"
    else:
        lista_txt = ""
        for i, (nome, qtd_inv, obj) in enumerate(itens_pag):
            seta = "-> " if i == cursor else "   "
            lista_txt += f"{seta}{nome} x{qtd_inv}  ({obj.preco}G/un)\n"

    rodape = (
        f"\nPag {ec['caixa_pagina']+1}/{max_pag+1}"
        f"  |  Na caixa: {itens_na_caixa} item(s)  ~{valor_caixa}G\n"
        f"[Up/Down] Mover  [right/left] Pagina\n"
        f"[Z] Depositar   [X] Fechar"
    )

    titulo = "Caixa de Vendas"
    conteudo = lista_txt + rodape

    # ── Sub-estado: escolhendo quantidade ──────────────────
    if ec['caixa_modo_qtd']:
        nome = ec['caixa_item_sel']
        max_qtd = jogador.invetario.get(nome, 0)
        qtd = ec['caixa_qtd_cursor']
        valor_prev = todos_itens[nome].preco * qtd if nome in todos_itens else 0
        conteudo = (
            f"Depositando: {nome}\n"
            f"Disponivel: x{max_qtd}\n\n"
            f"Quantidade: {qtd}\n"
            f"Valor previsto: {valor_prev}G\n\n"
            f"[Up/Down] Ajustar\n"
            f"[Z] Confirmar  [X] Cancelar"
        )
        titulo = "Quanto depositar?"

    v.draw_text_box(
        x=BOX_X, y=BOX_Y,
        box_w=BOX_W, box_h=BOX_H,
        title=titulo,
        content=conteudo,
        box_sid=box_sid, box_tw=8, box_th=8,
        font_sid=font_sid, font_w=8, font_h=8
    )

LINHAS_POR_PAG_REL = 10

def _montar_linhas_relatorio(relatorio):
    linhas = []
    por_tipo = relatorio.get('por_tipo', {})

    for categoria, itens in por_tipo.items():
        total_cat = sum(d['valor'] for d in itens.values())
        linhas.append(f"== {categoria} ==  [{total_cat}G]")
        for nome, dados in itens.items():
            linhas.append(f"  {nome} x{dados['qtd']}  = {dados['valor']}G")
        linhas.append("")  # linha em branco entre categorias

    if not linhas:
        linhas.append("Nenhum item vendido hoje.")

    return linhas

def atualizar_tela_relatorio(v, estado_caixa):
    ec = estado_caixa
    rel = ec.get('relatorio_dados') or {}
    linhas = _montar_linhas_relatorio(rel)
    max_pag = max(0, (len(linhas) - 1) // LINHAS_POR_PAG_REL)

    if v.key_pressed(b"left"):
        ec['relatorio_pagina'] = max(0, ec['relatorio_pagina'] - 1)
    elif v.key_pressed(b"right"):
        ec['relatorio_pagina'] = min(max_pag, ec['relatorio_pagina'] + 1)
    elif v.key_pressed(b"return") or v.key_pressed(b"e"):
        ec['mostrar_relatorio'] = False
        ec['relatorio_dados']   = None
        ec['relatorio_pagina']  = 0
        return False

    return True

def desenhar_tela_relatorio(v, estado_caixa, box_sid, font_sid,SCREEN_W, SCREEN_H):
    ec = estado_caixa
    rel = ec.get('relatorio_dados') or {}
    linhas = _montar_linhas_relatorio(rel)
    max_pag = max(0, (len(linhas) - 1) // LINHAS_POR_PAG_REL)
    pag = ec['relatorio_pagina']

    inicio = pag * LINHAS_POR_PAG_REL
    fatia  = linhas[inicio: inicio + LINHAS_POR_PAG_REL]

    dia_ant   = rel.get('dia_anterior', 1)
    lucro     = rel.get('lucro_total', 0)

    titulo    = f"Dia {dia_ant} acabou!\nLucro diario: {lucro}G"
    conteudo  = "\n".join(fatia)
    conteudo += f"\n\nPag {pag+1}/{max_pag+1}\n[Esq/Dir] Pagina  [Enter] Acordar"

    v.draw_text_box(
        x=0, y=0,
        box_w=SCREEN_W, box_h=SCREEN_H,
        title=titulo,
        content=conteudo,
        box_sid=box_sid, box_tw=8, box_th=8,
        font_sid=font_sid, font_w=8, font_h=8
    )

def controlar_framerate(start_time):
    elapsed = time.time() - start_time
    if elapsed < FRAME_TIME:
        time.sleep(FRAME_TIME - elapsed)

import random as _random

_CHANCE_CHUVA_BASE    = 0.40
_CICLO_CHUVA_DIAS     = 4
_DURACAO_CHUVA_MINIMA = 1
_DURACAO_CHUVA_MAXIMA = 3

# Gotas
_NUM_GOTAS   = 55
_GOTA_W      = 1
_GOTA_H      = 4
_GOTA_VEL    = 3
_GOTA_SPREAD = 2

def inicializar_estado_chuva():
    return {
        'chovendo':       False,
        'dias_restantes': 0,
        'frame':          0,
        'gotas': [
            (
                _random.randint(0, SCREEN_W - 1),
                i * (SCREEN_H // _NUM_GOTAS)
            )
            for i in range(_NUM_GOTAS)
        ],
    }

def _regar_terra_arada(mapas_mundo):
    for nome, mapa_dict in mapas_mundo.items():
        mapa   = mapa_dict["arte"]
        map_rows = len(mapa)
        map_cols = len(mapa[0]) if map_rows > 0 else 0

        # Terra arada seca (1) → terra arada molhada (2)
        for y in range(map_rows):
            for x in range(map_cols):
                if mapa[y][x] == 1:
                    mapa[y][x] = 2

        # Plantações → marcadas como regadas
        if "plantacoes" in mapa_dict:
            from objeto import _atualizar_tile_planta
            for coords, dados in mapa_dict["plantacoes"].items():
                dados["regada"] = True
                _atualizar_tile_planta(mapa_dict, coords[0], coords[1])

def decidir_clima_novo_dia(jogador, estado_chuva, mapas_mundo):
    ec = estado_chuva

    if ec['chovendo']:
        # Chuva em andamento: decrementa contador
        ec['dias_restantes'] -= 1
        if ec['dias_restantes'] <= 0:
            ec['chovendo']       = False
            ec['dias_restantes'] = 0
            jogador.clima        = "sol"
        # Mesmo dia de chuva → rega tudo de novo
        else:
            _regar_terra_arada(mapas_mundo)
    else:
        # Sem chuva: só verifica a cada _CICLO_CHUVA_DIAS dias
        if jogador.dia_atual % _CICLO_CHUVA_DIAS == 0:
            if _random.random() < _CHANCE_CHUVA_BASE:
                duracao = _random.randint(_DURACAO_CHUVA_MINIMA, _DURACAO_CHUVA_MAXIMA)
                ec['chovendo']       = True
                ec['dias_restantes'] = duracao
                jogador.clima        = "chuva"
                _regar_terra_arada(mapas_mundo)

def atualizar_chuva(estado_chuva):
    if not estado_chuva['chovendo']:
        return

    ec = estado_chuva
    ec['frame'] += 1

    novas_gotas = []
    for gx, gy in ec['gotas']:
        # Move a gota para baixo + leve inclinação de vento
        gx = (gx + _GOTA_SPREAD) % SCREEN_W
        gy = gy + _GOTA_VEL
        if gy >= SCREEN_H:
            # Gota saiu da tela: reinicia no topo com X aleatório
            gy = _random.randint(-20, -1)
            gx = _random.randint(0, SCREEN_W - 1)
        novas_gotas.append((gx, gy))
    ec['gotas'] = novas_gotas

def desenhar_chuva(v, estado_chuva):
    if not estado_chuva['chovendo']:
        return
    offset = estado_chuva['frame'] % 2
    for y in range(0, SCREEN_H, 2):
        for x in range((y + offset) % 2, SCREEN_W, 2):
            v.draw_rect(x, y, 1, 1, 0, 20, 70)

    # ── Gotas ──────────────────────────────────────────────────────────
    for gx, gy in estado_chuva['gotas']:
        if 0 <= gy < SCREEN_H:
            v.draw_rect(gx, gy,            _GOTA_W, _GOTA_H, 160, 210, 255)
            v.draw_rect(gx, gy + _GOTA_H,  _GOTA_W, 2,        80, 130, 210)

_FRAMES_POR_5MIN = 25 * FPS

def atualizar_tempo(jogador, estado_ui):
    estado_ui['timer_tempo'] = estado_ui.get('timer_tempo', 0) + 1
    if estado_ui['timer_tempo'] >= _FRAMES_POR_5MIN:
        estado_ui['timer_tempo'] = 0
        jogador.minutos += 5
        if jogador.minutos >= 60:
            jogador.minutos = 0
            jogador.horas += 1
            if jogador.horas >= 24:
                jogador.horas = 0

def _intensidade_noite(horas, minutos):
    hora_total = horas + minutos / 60.0
    if hora_total < 18.0:
        return 0.0
    elif hora_total < 21.0:
        return ((hora_total - 18.0) / 3.0) * 0.45
    else:
        return 0.45

def desenhar_noite(v, jogador):
    intensidade = _intensidade_noite(jogador.horas, jogador.minutos)
    if intensidade > 0.0:
        v.draw_overlay(0, 0, SCREEN_W, SCREEN_H, 10, 10, 40, intensidade)

def desenhar_hud_tempo(v, jogador, estado_chuva, box_sid, font_sid, cam_y=0):
    W   = HUD_W
    H   = HUD_H    
    sy_base = _hotbar_y(jogador, cam_y)    
    if sy_base == HOTBAR_Y_BAIXO:
        hud_y = SCREEN_H - H - 4
    else:
        hud_y = HOTBAR_Y_TOPO
    ABREV = {"Primavera": "Pri", "Verao": "Ver", "Verao": "Ver","Outono": "Out", "Inverno": "Inv"}
    est = ABREV.get(jogador.estacao_atual, jogador.estacao_atual[:3])
    chuva = "~" if estado_chuva.get('chovendo') else " "
    linha = f"Dia:{jogador.dia_atual:02d}\n{est} {jogador.horas:02d}:{jogador.minutos:02d} {chuva}"
    
    v.draw_text_box(
        0, hud_y, box_w=W, box_h=H,
        title="", content=linha,
        box_sid=box_sid, box_tw=8, box_th=8,
        font_sid=font_sid, font_w=8, font_h=8
    )

def desenhar_chuva(v, estado_chuva):
    """Overlay azul com alpha blend real + gotas animadas. Sem pontilhado."""
    if not estado_chuva['chovendo']:
        return
    v.draw_overlay(0, 0, SCREEN_W, SCREEN_H, 0, 30, 90, 0.22)
    for gx, gy in estado_chuva['gotas']:
        if 0 <= gy < SCREEN_H:
            v.draw_rect(gx, gy,           _GOTA_W, _GOTA_H, 180, 220, 255)
            v.draw_rect(gx, gy + _GOTA_H, _GOTA_W, 2,        90, 140, 220)

def inicializar_estado_ui():
    return {
        'mostrar_status':      False,
        'inv_pagina':          0,
        'inv_cursor':          0,
        'mostrar_loja':        False,
        'loja_modo':           "comprar",
        'loja_cursor':         0,
        'loja_pagina':         0,
        'mensagem_loja':       "Bem-vindo a Loja!",
        'msg_interacao':       "",
        'msg_interacao_timer': 0,
    }