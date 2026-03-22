import time
import random as _random
import json as _json
import os as _os
from itens import todos_itens, todos_npcs
from artes import *
from objeto import *

FPS = 60
FRAME_TIME = 1.0 / FPS
TILE_SIZE = 16
SCREEN_W = 364
SCREEN_H = 244

HOTBAR_SLOTS   = 9
HOTBAR_SLOT_W  = 16
HOTBAR_SLOT_H  = 16
HOTBAR_PADDING = 2
HOTBAR_ICON_W  = 16
HOTBAR_ICON_H  = 16

_HOTBAR_TOTAL_W = HOTBAR_SLOTS * HOTBAR_SLOT_W + (HOTBAR_SLOTS - 1) * HOTBAR_PADDING
HOTBAR_X_INICIO = (SCREEN_W - _HOTBAR_TOTAL_W) // 2
HOTBAR_Y_FIXO   = SCREEN_H - HOTBAR_SLOT_H - 4
_LIMIAR_TOPO_PX = 40
HOTBAR_Y_TOPO   = 3
HOTBAR_Y_BAIXO  = HOTBAR_Y_FIXO

HUD_BAR_W   = 5
HUD_BAR_H   = 34
HUD_BAR_GAP = 3
HUD_BAR_X   = SCREEN_W - HUD_BAR_W * 2 - HUD_BAR_GAP - 4
HUD_BAR_Y   = SCREEN_H - HUD_BAR_H - 4

HUD_INFO_W = 88
HUD_INFO_H = 34
HUD_INFO_Y = 2
HUD_INFO_X = SCREEN_W - HUD_INFO_W - 2
HUD_GOLD_W = HUD_INFO_W
HUD_GOLD_H = 24
HUD_GOLD_Y = HUD_INFO_Y + HUD_INFO_H + 2

HUD_W   = HUD_INFO_W
HUD_H   = HUD_INFO_H
HUD_PAD = 4

def invalidar_cache_mega(mapa_dict):
    for key in list(mapa_dict.keys()):
        if key.startswith("_mega_cache_"):
            del mapa_dict[key]

def calc_camera(player_px, player_py, map_cols, map_rows, scr_w=None, scr_h=None):
    sw = scr_w if scr_w is not None else SCREEN_W
    sh = scr_h if scr_h is not None else SCREEN_H
    cam_x = player_px - sw // 2 + TILE_SIZE // 2
    cam_y = player_py - sh // 2 + TILE_SIZE // 2
    cam_x = max(0, min(cam_x, map_cols * TILE_SIZE - sw))
    cam_y = max(0, min(cam_y, map_rows * TILE_SIZE - sh))
    return cam_x, cam_y

def _draw_bloco_simples(v, bloco_info, tileset_ids, x_px, y_px):
    sid = tileset_ids.get(bloco_info["sprite"])
    if sid is None:
        return
    rx = bloco_info.get("start_x", 0) + bloco_info.get("col", 0) * bloco_info.get("w", 16)
    ry = bloco_info.get("start_y", 0) + bloco_info.get("l", 0) * bloco_info.get("h", 16)
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
            return bool(grupos_a & _grupos(blocos.get(mapa[r][c], {}), mapa[r][c]))
        return True

    mask = 0
    if mesmo(col, row - 1): mask |= 8
    if mesmo(col, row + 1): mask |= 4
    if mesmo(col - 1, row): mask |= 2
    if mesmo(col + 1, row): mask |= 1
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

def _draw_camada(v, mapa, blocos, mapa_dict, cam_x, cam_y, tileset_ids, skip_zero=False):
    map_rows = len(mapa)
    map_cols = len(mapa[0]) if map_rows > 0 else 0

    cache_key = f"_mega_cache_{id(mapa)}"
    mega_ocupadas = mapa_dict.get(cache_key)
    if mega_ocupadas is None:
        mega_ocupadas = set()
        for row in range(map_rows):
            for col in range(map_cols):
                bloco_info = blocos.get(mapa[row][col])
                if not bloco_info:
                    continue
                mega = bloco_info.get("mega")
                if mega:
                    for dr in range(mega["rows"]):
                        for dc in range(mega["cols"]):
                            if dr == 0 and dc == 0:
                                continue
                            mega_ocupadas.add((col + dc, row + dr))
        mapa_dict[cache_key] = mega_ocupadas

    for row in range(map_rows):
        for col in range(map_cols):
            tile_val = mapa[row][col]
            if skip_zero and tile_val == 0:
                continue
            x_px = col * TILE_SIZE - cam_x
            y_px = row * TILE_SIZE - cam_y

            if x_px + TILE_SIZE * 4 < 0 or x_px > SCREEN_W + TILE_SIZE * 4:
                continue
            if y_px + TILE_SIZE * 4 < 0 or y_px > SCREEN_H + TILE_SIZE * 4:
                continue
            if (col, row) in mega_ocupadas:
                continue

            bloco_info = blocos.get(tile_val)
            if not bloco_info:
                continue

            if "plantacoes" in mapa_dict and (col, row) in mapa_dict["plantacoes"]:
                dados = mapa_dict["plantacoes"][(col, row)]
                _draw_bloco_simples(v, bloco_info, tileset_ids, x_px, y_px)

                nome_est = dados.get("_estagio_nome", "")
                if not nome_est:
                    from itens import TODAS_PLANTAS as _TP
                    pl = _TP.get(dados.get("semente", ""))
                    if pl:
                        dias_nec = pl.dias_total + dados.get("dias_penalidade", 0)
                        if dados["dias_idade"] >= dias_nec:
                            ie = len(pl.estagios_tiles) - 1
                        else:
                            prop = dados["dias_idade"] / max(1, dias_nec)
                            ie = min(int(prop * len(pl.estagios_tiles)), len(pl.estagios_tiles) - 2)
                        nome_est = pl.estagios_tiles[ie]
                        dados["_estagio_nome"] = nome_est

                b_est = None
                if nome_est:
                    for tid_e, bi_e in blocos.items():
                        if bi_e.get("nome") == nome_est:
                            b_est = bi_e
                            break

                if b_est is not None:
                    sid = tileset_ids.get(b_est.get("sprite", b""))
                    if sid is not None:
                        bw = b_est.get("w", TILE_SIZE)
                        bh = b_est.get("h", TILE_SIZE)
                        v.draw_sprite_part(sid, x_px, y_px,
                                           b_est.get("col", 0) * bw, b_est.get("l", 0) * bh, bw, bh)
                continue

            if "fundo" in bloco_info:
                fundo_val = bloco_info["fundo"]
                if isinstance(fundo_val, str):
                    fi = None
                    for tid, bi in blocos.items():
                        if bi.get("nome") == fundo_val or (isinstance(bi.get("nomes"), list) and fundo_val in bi["nomes"]):
                            fi = bi
                            break
                else:
                    fi = blocos.get(fundo_val)
                if fi:
                    _draw_bloco_simples(v, fi, tileset_ids, x_px, y_px)

            mega = bloco_info.get("mega")
            if mega:
                sid = tileset_ids.get(bloco_info["sprite"])
                if sid is None:
                    continue
                src_x0, src_y0 = _mega_src_origem(bloco_info)
                tw = bloco_info.get("w", TILE_SIZE)
                th = bloco_info.get("h", TILE_SIZE)
                for dr in range(mega["rows"]):
                    for dc in range(mega["cols"]):
                        v.draw_sprite_part(sid, x_px + dc * TILE_SIZE, y_px + dr * TILE_SIZE,
                                           src_x0 + dc * tw, src_y0 + dr * th, tw, th)
                continue

            if bloco_info.get("autotile"):
                frames = bloco_info.get("frames", {})
                mask = _calcular_mascara_autotile(mapa, blocos, col, row, tile_val)
                frame = frames.get(mask, frames.get("padrao"))
                if frame:
                    sid = tileset_ids.get(bloco_info["sprite"])
                    if sid is not None:
                        tw = bloco_info.get("w", TILE_SIZE)
                        th = bloco_info.get("h", TILE_SIZE)
                        v.draw_sprite_part(sid, x_px, y_px, frame[0] * tw, frame[1] * th, tw, th)
                continue

            _draw_bloco_simples(v, bloco_info, tileset_ids, x_px, y_px)

def draw_world(v, mapa_dict, cam_x, cam_y, tileset_ids):
    blocos = mapa_dict["blocos"]
    chao = mapa_dict.get("chao")
    if chao:
        _draw_camada(v, chao, blocos, mapa_dict, cam_x, cam_y, tileset_ids, skip_zero=False)
    arte = mapa_dict.get("arte")
    if arte:
        _draw_camada(v, arte, blocos, mapa_dict, cam_x, cam_y, tileset_ids, skip_zero=True)

def draw_world_topo(v, mapa_dict, cam_x, cam_y, tileset_ids):
    topo = mapa_dict.get("topo")
    if not topo:
        return
    _draw_camada(v, topo, mapa_dict["blocos"], mapa_dict, cam_x, cam_y, tileset_ids, skip_zero=True)

def _hotbar_y(jogador, cam_y):
    return HOTBAR_Y_FIXO

def desenhar_hotbar(v, jogador, itens_sprite_ids, cam_y=0, estado=None, font_sid=-1):
    from itens import todos_itens
    sy    = HOTBAR_Y_FIXO
    x0    = HOTBAR_X_INICIO
    ativa = estado and estado.get('hotbar_ativa')

    v.draw_rect(x0 - 3, sy - 3, _HOTBAR_TOTAL_W + 6, HOTBAR_SLOT_H + 6, 0, 0, 0)
    v.draw_rect(x0 - 4, sy - 4, _HOTBAR_TOTAL_W + 8, 1, 255, 255, 255)
    v.draw_rect(x0 - 4, sy + HOTBAR_SLOT_H + 3, _HOTBAR_TOTAL_W + 8, 1, 255, 255, 255)
    v.draw_rect(x0 - 4, sy - 4, 1, HOTBAR_SLOT_H + 8, 255, 255, 255)
    v.draw_rect(x0 + _HOTBAR_TOTAL_W + 3, sy - 4, 1, HOTBAR_SLOT_H + 8, 255, 255, 255)

    for slot in range(1, HOTBAR_SLOTS + 1):
        sx = x0 + (slot - 1) * (HOTBAR_SLOT_W + HOTBAR_PADDING)
        ativo    = (slot == jogador.item_selecionado)
        nome_item = jogador.hotbar.get(slot)
        equipado = nome_item and (nome_item in jogador.itens_equipados.values())

        if ativo and ativa:
            v.draw_rect(sx, sy, HOTBAR_SLOT_W, HOTBAR_SLOT_H, 255, 255, 255)
        elif ativo:
            v.draw_rect(sx - 1, sy - 1, HOTBAR_SLOT_W + 2, HOTBAR_SLOT_H + 2, 255, 255, 255)
            v.draw_rect(sx, sy, HOTBAR_SLOT_W, HOTBAR_SLOT_H, 20, 20, 20)
        elif equipado:
            v.draw_rect(sx, sy, HOTBAR_SLOT_W, HOTBAR_SLOT_H, 80, 80, 80)
        else:
            v.draw_rect(sx, sy, HOTBAR_SLOT_W, HOTBAR_SLOT_H, 0, 0, 0)

        if nome_item and nome_item in todos_itens:
            item = todos_itens[nome_item]
            sid  = itens_sprite_ids.get(item.sprite)
            if sid is not None:
                rx, ry, iw, ih = item.get_sprite_rect()
                v.draw_sprite_part(sid, sx + (HOTBAR_SLOT_W - iw) // 2,
                                   sy + (HOTBAR_SLOT_H - ih) // 2, rx, ry, iw, ih)

        v.draw_text(sx + HOTBAR_SLOT_W - 8, sy + HOTBAR_SLOT_H - 8,
                    str(slot), font_sid=font_sid, font_w=8, font_h=8)

def processar_input_hotbar(v, jogador, mapa_dict, estado=None):
    from itens import todos_itens
    if estado is None:
        estado = {}
    if 'hotbar_ativa' not in estado:
        estado['hotbar_ativa'] = False

    slot_atual = jogador.item_selecionado
    nome_item  = jogador.hotbar.get(slot_atual)
    item       = todos_itens.get(nome_item) if nome_item else None

    if v.key_pressed(b"return"):
        if not estado['hotbar_ativa']:
            estado['hotbar_ativa'] = True
            return "Hotbar ativada! Use as setas (Esq/Dir) para escolher."
        else:
            if item and item.tipo == "Equipavel":
                res = jogador.usar_hotbar(slot_atual, todos_itens)
                estado['hotbar_ativa'] = False
                return res.get("msg", "") if isinstance(res, dict) else str(res)
            else:
                estado['hotbar_ativa'] = False
                return "Hotbar desativada. Item selecionado."

    if estado['hotbar_ativa']:
        if v.key_pressed(b"right"):
            jogador.item_selecionado = jogador.item_selecionado % 9 + 1
        elif v.key_pressed(b"left"):
            jogador.item_selecionado = (jogador.item_selecionado - 2) % 9 + 1
        return ""

    if v.key_pressed(b"z"):
        if not nome_item or not item:
            return ""
        if item.tipo == "Semente":
            from objeto import plantar_semente, obter_bloco_frente
            resultado = obter_bloco_frente(jogador, mapa_dict)
            if resultado:
                nx, ny, tile_id = resultado
                return plantar_semente(jogador, mapa_dict, nx, ny, nome_item)
            return "Fora do mapa."
        elif item.tipo == "Material":
            return colocar_bloco(jogador, mapa_dict)
        elif item.tipo != "Equipavel":
            res = jogador.usar_hotbar(slot_atual, todos_itens)
            return res.get("msg", "") if isinstance(res, dict) else str(res)

    if v.key_pressed(b"x"):
        return quebrar_bloco(jogador, mapa_dict)

    return ""

INV_COLS      = 8
INV_ROWS      = 3
INV_ITENS_PAG = INV_COLS * INV_ROWS
INV_FONT_W    = 8
INV_FONT_H    = 8

def processar_input_inventario(v, jogador, estado, todos_itens_ref=None):
    from itens import todos_itens as _todos_itens
    if todos_itens_ref is None:
        todos_itens_ref = _todos_itens

    inv_pagina  = estado['inv_pagina']
    inv_cursor  = estado['inv_cursor']
    esp_tot     = getattr(jogador, 'espacos_inventario', INV_ITENS_PAG)
    COLS_NAV    = INV_COLS

    itens_lista  = list(jogador.invetario.items())
    total_itens  = len(itens_lista)
    max_pag      = max(0, (total_itens - 1) // esp_tot) if total_itens > 0 else 0
    inv_pagina   = max(0, min(inv_pagina, max_pag))
    inicio       = inv_pagina * esp_tot
    pagina_itens = itens_lista[inicio: inicio + esp_tot]
    inv_cursor   = max(0, min(inv_cursor, max(0, len(pagina_itens) - 1)))
    item_sel     = pagina_itens[inv_cursor][0] if pagina_itens else None

    if estado.get('inv_hotbar_ativo'):
        hc = estado['inv_hotbar_cursor']
        if v.key_pressed(b"right"):
            hc = hc % 9 + 1
        elif v.key_pressed(b"left"):
            hc = (hc - 2) % 9 + 1
        elif v.key_pressed(b"z") and item_sel:
            for s in range(1, 10):
                if jogador.hotbar[s] == item_sel:
                    jogador.hotbar[s] = None
            jogador.hotbar[hc] = item_sel
            estado['inv_hotbar_ativo'] = False
        elif v.key_pressed(b"x"):
            estado['inv_hotbar_ativo'] = False
        estado['inv_hotbar_cursor'] = hc
        estado['inv_pagina']  = inv_pagina
        estado['inv_cursor']  = inv_cursor
        return inv_pagina, inv_cursor

    if v.key_pressed(b"space"):
        estado['mostrar_status']   = False
        estado['inv_hotbar_ativo'] = False
        estado['inv_pagina']  = inv_pagina
        estado['inv_cursor']  = inv_cursor
        return inv_pagina, inv_cursor

    if v.key_pressed(b"return") and item_sel:
        estado['inv_hotbar_ativo']  = True
        estado['inv_hotbar_cursor'] = 1
        estado['inv_pagina']  = inv_pagina
        estado['inv_cursor']  = inv_cursor
        return inv_pagina, inv_cursor

    if v.key_pressed(b"z") and item_sel:
        jogador.usar_item(item_sel, todos_itens_ref)

    if v.key_pressed(b"x") and item_sel:
        jogador.remover_item(item_sel, 1)
        pagina2    = itens_lista[inicio: inicio + esp_tot]
        inv_cursor = max(0, min(inv_cursor, max(0, len(pagina2) - 1)))

    if v.key_pressed(b"up"):
        novo = inv_cursor - COLS_NAV
        if novo >= 0:
            inv_cursor = novo
    if v.key_pressed(b"down"):
        novo = inv_cursor + COLS_NAV
        if novo < esp_tot:
            inv_cursor = novo
    if v.key_pressed(b"right"):
        if inv_cursor % COLS_NAV < COLS_NAV - 1 and inv_cursor + 1 < esp_tot:
            inv_cursor += 1
    if v.key_pressed(b"left"):
        if inv_cursor % COLS_NAV > 0:
            inv_cursor -= 1

    inv_cursor = max(0, min(inv_cursor, esp_tot - 1))
    estado['inv_pagina'] = inv_pagina
    estado['inv_cursor'] = inv_cursor
    return inv_pagina, inv_cursor

def desenhar_ui_inventario(v, jogador, inv_pagina, inv_cursor, box_sid, font_sid,
                           itens_sprite_ids=None, estado=None):
    from itens import todos_itens as _todos_itens

    SCR_W = getattr(v, 'render_w', SCREEN_W)
    SCR_H = getattr(v, 'render_h', SCREEN_H)

    FW, FH = 8, 8
    MX, MY = 4, 4
    GAP    = 2
    _PAD   = 9
    BTH    = 8
    BH     = SCR_H - MY * 2
    INNER_BOT = MY + BH - BTH

    INV_S   = 16
    INV_P   = 2
    COLS    = INV_COLS
    esp_tot = getattr(jogador, 'espacos_inventario', INV_ITENS_PAG)
    ROWS    = (esp_tot + COLS - 1) // COLS
    GRID_W  = COLS * (INV_S + INV_P) - INV_P
    LISTA_W = 165
    DET_X   = MX + LISTA_W + GAP
    DET_W   = SCR_W - MX - DET_X

    itens_lista  = list(jogador.invetario.items())
    total_itens  = len(itens_lista)
    max_pag      = max(0, (total_itens - 1) // esp_tot) if total_itens > 0 else 0
    inv_pagina   = max(0, min(inv_pagina, max_pag))
    inicio       = inv_pagina * esp_tot
    pagina_itens = itens_lista[inicio: inicio + esp_tot]
    inv_cursor   = max(0, min(inv_cursor, max(0, len(pagina_itens) - 1)))
    item_sel     = pagina_itens[inv_cursor][0] if pagina_itens else None

    hotbar_ativo = estado.get('inv_hotbar_ativo', False) if estado else False
    hotbar_cur   = estado.get('inv_hotbar_cursor', 1) if estado else 1

    # ── estado para descrição expandida e jogar-fora ──────────────────────────
    desc_expandida   = estado.get('inv_desc_expandida', False) if estado else False
    jogar_fora_ativo = estado.get('inv_jogar_fora_ativo', False) if estado else False
    jogar_fora_qtd   = estado.get('inv_jogar_fora_qtd', 1) if estado else 1

    pag_txt = f"{inv_pagina + 1}/{max_pag + 1}"
    v.draw_text_box(x=MX, y=MY, box_w=LISTA_W, box_h=BH,
                    title=f"Mochila {pag_txt}", content="",
                    box_sid=box_sid, box_tw=8, box_th=BTH,
                    font_sid=font_sid, font_w=FW, font_h=FH)

    GRID_X = MX + _PAD
    GRID_Y = MY + BTH + FH + 8 + 3

    for idx in range(esp_tot):
        row = idx // COLS
        col = idx % COLS
        sx  = GRID_X + col * (INV_S + INV_P)
        sy  = GRID_Y + row * (INV_S + INV_P)
        sel = (idx == inv_cursor)

        if sel:
            v.draw_rect(sx - 1, sy - 1, INV_S + 2, INV_S + 2, 255, 220, 80)
            v.draw_rect(sx, sy, INV_S, INV_S, 30, 30, 30)
        else:
            v.draw_rect(sx, sy, INV_S, INV_S, 20, 20, 20)
            v.draw_rect(sx, sy, INV_S, 1, 80, 80, 80)
            v.draw_rect(sx, sy, 1, INV_S, 80, 80, 80)
            v.draw_rect(sx + INV_S - 1, sy, 1, INV_S, 80, 80, 80)
            v.draw_rect(sx, sy + INV_S - 1, INV_S, 1, 80, 80, 80)

        if idx < len(pagina_itens):
            nome_i, _ = pagina_itens[idx]
            obj_i = _todos_itens.get(nome_i)
            if obj_i and itens_sprite_ids is not None:
                sid = itens_sprite_ids.get(obj_i.sprite)
                if sid is not None:
                    rx, ry, iw, ih = obj_i.get_sprite_rect()
                    v.draw_sprite_part(sid, sx + (INV_S - iw) // 2, sy + (INV_S - ih) // 2, rx, ry, iw, ih)
            desenhar_estrelas_slot(v, sx, sy, INV_S, nome_i, jogador, font_sid, FW, FH)

    esp_y = GRID_Y + ROWS * (INV_S + INV_P) + 3
    v.draw_text(GRID_X, esp_y, f"{len(jogador.invetario)}/{esp_tot} espaços",
                font_sid=font_sid, font_w=FW, font_h=FH)

    rod_esq = INNER_BOT - FH * 2 - 4
    v.draw_text(GRID_X, rod_esq, "setas: mover", font_sid=font_sid, font_w=FW, font_h=FH)
    v.draw_text(GRID_X, rod_esq + FH + 1, "Space: sair", font_sid=font_sid, font_w=FW, font_h=FH)

    # ═════════════════════════════════════════════════════════════════════════
    # PAINEL DE DETALHES (direita)
    # ═════════════════════════════════════════════════════════════════════════
    v.draw_text_box(x=DET_X, y=MY, box_w=DET_W, box_h=BH,
                    title="Detalhes", content="",
                    box_sid=box_sid, box_tw=8, box_th=BTH,
                    font_sid=font_sid, font_w=FW, font_h=FH)

    PX    = DET_X + _PAD
    PY    = MY + BTH + FH + 8 + 3
    PW    = DET_W - _PAD * 2
    rod_y = INNER_BOT - FH * 2 - 4

    for sx in range(0, PW, 4):
        v.draw_rect(PX + sx, rod_y - 3, 2, 1, 180, 155, 60)

    # ── Rodapé — depende do modo ativo ───────────────────────────────────────
    if jogar_fora_ativo:
        # modo jogar fora: mostra quantidade e instruções
        v.draw_text(PX, rod_y, "^v qtd  Z:ok X:cancela", font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(PX, rod_y + FH + 1, f"Jogar fora: x{jogar_fora_qtd}", font_sid=font_sid, font_w=FW, font_h=FH)

    elif hotbar_ativo:
        v.draw_text(PX, rod_y, "<-> mudar slot", font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(PX, rod_y + FH + 1, "Z:ok X:cancela", font_sid=font_sid, font_w=FW, font_h=FH)

        # ── Hotbar visual com slots 1..9 + slot 10 = JOGAR FORA (vermelho) ──
        SLOT_W    = 16
        SLOT_P    = 2
        SLOT_COLS = max(1, PW // (SLOT_W + SLOT_P))
        hb_y      = 170
        # slots 1–9 normais
        for s in range(1, 10):
            row2 = (s - 1) // SLOT_COLS
            col2 = (s - 1) % SLOT_COLS
            sx2  = PX + col2 * (SLOT_W + SLOT_P)
            sy2  = hb_y + row2 * (SLOT_W + SLOT_P)
            sel2 = (s == hotbar_cur)

            if sel2:
                v.draw_rect(sx2 - 1, sy2 - 1, SLOT_W + 2, SLOT_W + 2, 255, 220, 80)
                v.draw_rect(sx2, sy2, SLOT_W, SLOT_W, 35, 35, 35)
            else:
                v.draw_rect(sx2, sy2, SLOT_W, SLOT_W, 20, 20, 20)
                v.draw_rect(sx2, sy2, SLOT_W, 1, 80, 80, 80)
                v.draw_rect(sx2, sy2, 1, SLOT_W, 80, 80, 80)
                v.draw_rect(sx2 + SLOT_W - 1, sy2, 1, SLOT_W, 80, 80, 80)
                v.draw_rect(sx2, sy2 + SLOT_W - 1, SLOT_W, 1, 80, 80, 80)

            nome_slot = jogador.hotbar.get(s)
            if nome_slot and itens_sprite_ids is not None:
                obj_s = _todos_itens.get(nome_slot)
                if obj_s:
                    sid_s = itens_sprite_ids.get(obj_s.sprite)
                    if sid_s is not None:
                        rx, ry2, iw, ih = obj_s.get_sprite_rect()
                        v.draw_sprite_part(sid_s, sx2 + (SLOT_W - iw) // 2,
                                           sy2 + (SLOT_W - ih) // 2, rx, ry2, iw, ih)

        # ── Slot 10 = Jogar Fora (quadrado vermelho com X) ───────────────────
        s10_col = 9 % SLOT_COLS   # décima posição (índice 9)
        s10_row = 9 // SLOT_COLS
        sx10    = PX + s10_col * (SLOT_W + SLOT_P)
        sy10    = hb_y + s10_row * (SLOT_W + SLOT_P)
        sel10   = (hotbar_cur == 10)

        if sel10:
            v.draw_rect(sx10 - 1, sy10 - 1, SLOT_W + 2, SLOT_W + 2, 255, 80, 80)

    elif desc_expandida:
        v.draw_text(PX, rod_y, "Z:Usar Enter:Hotbar", font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(PX, rod_y + FH + 1, "X:excluir Space: sair", font_sid=font_sid, font_w=FW, font_h=FH)

    else:
        v.draw_text(PX, rod_y, "Z:Usar Enter:Hotbar", font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(PX, rod_y + FH + 1, "X:excluir Space: sair", font_sid=font_sid, font_w=FW, font_h=FH)

    # ═════════════════════════════════════════════════════════════════════════
    # CONTEÚDO DO ITEM SELECIONADO
    # ═════════════════════════════════════════════════════════════════════════
    if item_sel and item_sel in _todos_itens:
        obj = _todos_itens[item_sel]
        qtd = jogador.invetario.get(item_sel, 0)
        eq  = item_sel in jogador.itens_equipados.values()

        ICON  = 24
        max_c = max(1, (PW - ICON - 5) // FW)
        _desenhar_slot_item(v, PX, PY, item_sel, _todos_itens, itens_sprite_ids, destaque=True, tamanho=ICON)
        TX = PX + ICON + 5

        # nome base (sem sufixo de estrela)
        _sufixos_est = (" (B)", " (N)", " (O)", " (P)")
        _nome_base = item_sel
        for _sf in _sufixos_est:
            if _nome_base.endswith(_sf):
                _nome_base = _nome_base[:-len(_sf)]
                break
        v.draw_text(TX, PY, _nome_base[:max_c], font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(TX, PY + FH + 2, f"[{obj.tipo}]{' (E)' if eq else ''}"[:max_c],
                    font_sid=font_sid, font_w=FW, font_h=FH)

        # ── Estrelas do item ─────────────────────────────────────────────────
        _est = _estrelas_do_nome(item_sel)
        _nomes_est = {0: "", 1: "Bronze", 2: "Prata", 3: "Ouro", 4: "Platina"}
        if _est > 0:
            _cor_e = _COR_ESTRELA.get(_est, (80, 80, 80))
            _txt_e = _nomes_est[_est]
            v.draw_rect(TX, PY + FH * 2 + 5, 6, 6, _cor_e[0], _cor_e[1], _cor_e[2])
            v.draw_text(TX + 9, PY + FH * 2 + 5,
                        _txt_e[:max_c - 2],
                        font_sid=font_sid, font_w=FW, font_h=FH)

        CY = PY + ICON + 6
        for sx in range(0, PW, 4):
            v.draw_rect(PX + sx, CY, 2, 1, 120, 100, 50)
        CY += 5

        # ── ícone de mochila + quantidade ────────────────────────────────────
        v.draw_rect(PX + 2, CY, 4, 1, 200, 170, 90)
        v.draw_rect(PX + 1, CY, 1, 2, 200, 170, 90)
        v.draw_rect(PX + 6, CY, 1, 2, 200, 170, 90)
        v.draw_rect(PX, CY + 2, 8, 5, 160, 130, 60)
        v.draw_rect(PX + 1, CY + 6, 6, 1, 140, 110, 50)
        v.draw_text(PX + 11, CY + 1, f"x{qtd}", font_sid=font_sid, font_w=FW, font_h=FH)
        CY += FH + 5

        for sx in range(0, PW, 4):
            v.draw_rect(PX + sx, CY, 2, 1, 120, 100, 50)
        CY += 5

        # ── Calcular altura dos stats para ancorar na parte de baixo ─────────
        stats_hp  = obj.recupar_hp or 0
        stats_st  = obj.recupar_mn or 0
        stats_hpm = obj.bonus_hp   or 0
        stats_g   = obj.preco      or 0

        # Conta quantas linhas de stats existem (separador + cada stat)
        n_stats = sum(bool(s) for s in (stats_hp, stats_st, stats_hpm, stats_g))
        STATS_BLOCO_H = (5 + 3) if n_stats > 0 else 0   # separador + gap
        STATS_BLOCO_H += n_stats * (FH + 3)

        # Área disponível para descrição (entre CY e o rodapé menos stats)
        desc_limite = rod_y - 8 - STATS_BLOCO_H - (5 if n_stats > 0 else 0)
        MAX_DESC_LINHAS = 5
        max_c_d = max(1, PW // FW)

        # ── Descrição — word-wrap, máximo 5 linhas ───────────────────────────
        desc = obj.descrica or "Sem descricao."

        def _wrap_desc(texto, largura):
            linhas, linha = [], ""
            for palavra in texto.split():
                teste = (linha + " " + palavra).strip() if linha else palavra
                if len(teste) <= largura:
                    linha = teste
                else:
                    if linha:
                        linhas.append(linha)
                    linha = palavra
            if linha:
                linhas.append(linha)
            return linhas or [""]

        linhas_desc = _wrap_desc(desc, max_c_d)[:MAX_DESC_LINHAS]

        for linha in linhas_desc:
            if CY + FH > desc_limite:
                break
            v.draw_text(PX, CY, linha, font_sid=font_sid, font_w=FW, font_h=FH)
            CY += FH + 1

        # ── Stats: HP, STM, Gold — sempre logo abaixo da descrição ──────────
        if n_stats > 0:
            # Posiciona os stats logo após a última linha da descrição
            # mas nunca abaixo do rodapé
            stats_y = CY + 3
            # garante que não vai vazar pro rodapé
            if stats_y + STATS_BLOCO_H > rod_y - 4:
                stats_y = rod_y - 4 - STATS_BLOCO_H

            for sx in range(0, PW, 4):
                v.draw_rect(PX + sx, stats_y, 2, 1, 120, 100, 50)
            stats_y += 5

            if stats_hp:
                _draw_icone_coracao(v, PX, stats_y)
                v.draw_text(PX + 11, stats_y, f"HP  +{stats_hp}",
                            font_sid=font_sid, font_w=FW, font_h=FH)
                stats_y += FH + 3

            if stats_hpm:
                _draw_icone_coracao(v, PX, stats_y, r=180, g=80, b=200)
                v.draw_text(PX + 11, stats_y, f"HPmax +{stats_hpm}",
                            font_sid=font_sid, font_w=FW, font_h=FH)
                stats_y += FH + 3

            if stats_st:
                _draw_icone_coxa_frango(v, PX, stats_y)
                v.draw_text(PX + 11, stats_y, f"STM +{stats_st}",
                            font_sid=font_sid, font_w=FW, font_h=FH)
                stats_y += FH + 3

            if stats_g:
                _draw_icone_moeda(v, PX, stats_y)
                v.draw_text(PX + 11, stats_y, f"{stats_g}G",
                            font_sid=font_sid, font_w=FW, font_h=FH)

    else:
        v.draw_text(PX, PY, "Mochila vazia.", font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(PX, PY + FH + 3, "Colete itens", font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(PX, PY + FH * 2 + 6, "no mundo!", font_sid=font_sid, font_w=FW, font_h=FH)

    return inv_cursor, item_sel

_LOJA_VISIVEIS = 5

def gerar_lista_loja(jogador, loja_modo, todos_itens, itens_vendidos=None):
    """
    Gera a lista de itens disponíveis na loja.

    itens_vendidos (opcional): dict com filtros aplicados em AMBOS os modos.
        Chaves aceitas:
          "nome" : tuple/list de prefixos — inclui itens cujo nome comece com qualquer um deles.
          "tipo" : tuple/list de tipos   — compara com tipo_presente do item (ex: "Cultivo", "Peixe").
        Itens que satisfaçam qualquer critério são incluídos (lógica OR).
        Se None ou vazio, sem filtro (mostra tudo permitido).

    Exemplos:
        itens_vendidos={"nome": ("Semente", "Fertilizante"), "tipo": ("Cultivo",)}
        → comprar: sementes/fertilizantes comprável
        → vender:  itens cujo nome comece com Semente/Fertilizante OU tipo_presente == Cultivo
    """
    prefixos = itens_vendidos.get("nome", ()) if itens_vendidos else ()
    tipos    = itens_vendidos.get("tipo", ()) if itens_vendidos else ()
    filtrado = bool(prefixos or tipos)

    def _tipo_bate(o):
        """Compara com tipo_presente (ex: 'Cultivo') e tipo (ex: 'Semente')."""
        return getattr(o, 'tipo_presente', '') in tipos or getattr(o, 'tipo', '') in tipos

    if loja_modo == "comprar":
        def _match_comprar(n, o):
            if not o.compravel:
                return False
            if not filtrado:
                return True
            if any(n.startswith(p) for p in prefixos):
                return True
            return _tipo_bate(o)

        return [n for n, o in todos_itens.items() if _match_comprar(n, o)]

    # ── modo vender ──────────────────────────────────────────────────────────
    # Itens com estrelas nunca podem ser vendidos na loja.
    def _match_vender(n, o):
        if not o.vendivel:
            return False
        if getattr(o, 'estrelas', 0) != 0:
            return False
        if not filtrado:
            return True
        if any(n.startswith(p) for p in prefixos):
            return True
        return _tipo_bate(o)

    return [
        n for n in jogador.invetario
        if n in todos_itens and _match_vender(n, todos_itens[n])
    ]

def calcular_paginacao_loja(lista_atual, loja_pagina, itens_por_pagina=5):
    return lista_atual, 0, 0

def processar_input_loja(v, loja_modo, loja_cursor, loja_pagina, itens_pagina):
    return loja_modo, loja_cursor, loja_pagina

def atualizar_loja(v, jogador, estado, todos_itens, itens_vendidos=None):
    ec    = estado
    lista = gerar_lista_loja(jogador, ec['loja_modo'], todos_itens, itens_vendidos)
    total = len(lista)

    if ec['loja_modo_qtd']:
        nome = ec['loja_item_sel']
        obj  = todos_itens.get(nome)

        if ec['loja_modo'] == "comprar":
            max_qtd = max(1, min((jogador.gold // obj.compra) if obj and obj.compra > 0 else 0, 99))
        else:
            max_qtd = jogador.invetario.get(nome, 0)

        if v.key_pressed(b"up"):
            ec['loja_qtd_cursor'] = min(ec['loja_qtd_cursor'] + 1, max_qtd)
        elif v.key_pressed(b"down"):
            ec['loja_qtd_cursor'] = max(ec['loja_qtd_cursor'] - 1, 1)
        elif v.key_pressed(b"right"):
            ec['loja_qtd_cursor'] = min(ec['loja_qtd_cursor'] + 10, max_qtd)
        elif v.key_pressed(b"left"):
            ec['loja_qtd_cursor'] = max(ec['loja_qtd_cursor'] - 10, 1)
        elif v.key_pressed(b"z"):
            qtd = ec['loja_qtd_cursor']
            jogador.comprar_item(nome, todos_itens, qtd) if ec['loja_modo'] == "comprar" else jogador.vender_item(nome, todos_itens, qtd)
            ec['loja_modo_qtd']   = False
            ec['loja_item_sel']   = None
            ec['loja_qtd_cursor'] = 1
        elif v.key_pressed(b"x") or v.key_pressed(b"q"):
            ec['loja_modo_qtd']   = False
            ec['loja_item_sel']   = None
            ec['loja_qtd_cursor'] = 1
        return

    if v.key_pressed(b"return"):
        ec['loja_modo']     = "vender" if ec['loja_modo'] == "comprar" else "comprar"
        ec['loja_cursor']   = 0
        ec['loja_scroll']   = 0
        return

    if v.key_pressed(b"down") and total > 0:
        ec['loja_cursor'] = (ec['loja_cursor'] + 1) % total
        if ec['loja_cursor'] >= ec['loja_scroll'] + _LOJA_VISIVEIS:
            ec['loja_scroll'] = ec['loja_cursor'] - _LOJA_VISIVEIS + 1
        if ec['loja_cursor'] == 0:
            ec['loja_scroll'] = 0
    elif v.key_pressed(b"up") and total > 0:
        ec['loja_cursor'] = (ec['loja_cursor'] - 1) % total
        if ec['loja_cursor'] < ec['loja_scroll']:
            ec['loja_scroll'] = ec['loja_cursor']
        if ec['loja_cursor'] == total - 1:
            ec['loja_scroll'] = max(0, total - _LOJA_VISIVEIS)
    elif v.key_pressed(b"z") and total > 0:
        nome = lista[ec['loja_cursor']]
        obj  = todos_itens.get(nome)
        if ec['loja_modo'] == "comprar" and obj and obj.compra > 0 and jogador.gold >= obj.compra:
            ec['loja_modo_qtd']   = True
            ec['loja_item_sel']   = nome
            ec['loja_qtd_cursor'] = 1
        elif ec['loja_modo'] == "vender" and jogador.invetario.get(nome, 0) > 0:
            ec['loja_modo_qtd']   = True
            ec['loja_item_sel']   = nome
            ec['loja_qtd_cursor'] = 1
        else:
            pass
    elif v.key_pressed(b"x"):
        ec['mostrar_loja']        = False
        ec['loja_itens_vendidos'] = None

def gerar_texto_loja(jogador, loja_modo, itens_pagina, loja_cursor, loja_pagina, max_paginas, mensagem_loja, todos_itens):
    return "", itens_pagina[loja_cursor] if itens_pagina else None

def processar_transacao_loja(v, jogador, loja_modo, item_sel, todos_itens, mensagem_loja):
    return mensagem_loja

def atualizar_camera(v, jogador, map_cols, map_rows):
    px, py = jogador.get_pixel_pos()
    cam_x, cam_y = calc_camera(px, py, map_cols, map_rows,
                                getattr(v, 'render_w', SCREEN_W),
                                getattr(v, 'render_h', SCREEN_H))
    v.set_object_pos(jogador.oid, px - cam_x, py - cam_y)
    return cam_x, cam_y

def desenhar_ui_loja(v, texto_loja, box_sid, font_sid, estado=None, jogador=None,
                     itens_sprite_ids=None, itens_vendidos=None):
    from itens import todos_itens as _todos_itens

    SCR_W = getattr(v, 'render_w', SCREEN_W)
    SCR_H = getattr(v, 'render_h', SCREEN_H)

    if estado is None:
        v.draw_text_box(0, 0, SCR_W, SCR_H, title="Lojinha", content=texto_loja,
                        box_sid=box_sid, box_tw=8, box_th=8,
                        font_sid=font_sid, font_w=8, font_h=8, line_spacing=2)
        return

    ec           = estado
    lista        = gerar_lista_loja(jogador, ec['loja_modo'], _todos_itens, itens_vendidos)
    total        = len(lista)
    modo_comprar = (ec['loja_modo'] == "comprar")

    FW, FH = 8, 8
    MX, MY = 0, 0
    GAP    = 0
    _PAD   = 9
    BH     = SCR_H - MY * 2

    # Esquerda 65% / Direita 35%
    LISTA_W = (SCR_W - MX * 2 - GAP) * 59 // 100
    DET_X   = MX + LISTA_W + GAP
    DET_W   = SCR_W - MX - DET_X

    nome_sel = lista[ec['loja_cursor']] if total > 0 else None
    obj_sel  = _todos_itens.get(nome_sel) if nome_sel else None

    # =========================================================================
    # POPUP DE QUANTIDADE — mais alto para caber nome longo
    # =========================================================================
    if ec['loja_modo_qtd']:
        nome = ec['loja_item_sel']
        obj  = _todos_itens.get(nome)
        qtd  = ec['loja_qtd_cursor']

        if modo_comprar:
            max_qtd = max(1, min((jogador.gold // obj.compra) if obj and obj.compra > 0 else 0, 99))
            val_str = f"Custo: {(obj.compra if obj else 0) * qtd}G"
            saldo   = f"Ouro: {jogador.gold}G"
        else:
            max_qtd = jogador.invetario.get(nome, 0)
            val_str = f"Ganho: {(obj.preco if obj else 0) * qtd}G"
            saldo   = f"Inv: x{max_qtd}"

        # Calcula altura do popup dinamicamente conforme nome precisa de 1 ou 2 linhas
        QW     = 148
        IX_tmp = MX + _PAD   # só para calcular IW
        IW     = QW - _PAD * 2
        n_linhas_nome = 1 + (1 if len(nome) > IW // FW else 0)
        QH = 8 + FH + 4 + n_linhas_nome*(FH+2) + FH+3 + 5 + FH+6 + FH+4 + 4 + FH + FH+1 + 8
        QX = (SCR_W - QW) // 2
        QY = max(MY, (SCR_H - QH) // 2)

        v.draw_text_box(QX, QY, box_w=160, box_h=112,
                        title="Quantidade" if modo_comprar else "Vender",
                        content="", box_sid=box_sid, box_tw=8, box_th=8,
                        font_sid=font_sid, font_w=FW, font_h=FH)

        IX = QX + _PAD
        IY = QY + 8 + FH + 4

        # nome em até 2 linhas
        chars_l = IW // FW
        _nome_p = _nome_sem_estrela(nome)
        v.draw_text(IX, IY, _nome_p[:chars_l], font_sid=font_sid, font_w=FW, font_h=FH)
        IY += FH + 2
        if len(_nome_p) > chars_l:
            v.draw_text(IX, IY, _nome_p[chars_l:chars_l*2],
                        font_sid=font_sid, font_w=FW, font_h=FH)
            IY += FH + 2

        # saldo
        v.draw_text(IX, IY, saldo[:chars_l], font_sid=font_sid, font_w=FW, font_h=FH)
        IY += FH + 3

        # separador
        for sx in range(0, IW, 4):
            v.draw_rect(IX + sx, IY, 2, 1, 110, 90, 45)
        IY += 5

        # seletor  <  qtd  >
        qs = str(qtd)
        qx = IX + (IW - len(qs) * FW) // 2
        v.draw_text(IX + 2,           IY + 1, "<", font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(IX + IW - FW - 2, IY + 1, ">", font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(qx,               IY + 1, qs,  font_sid=font_sid, font_w=FW, font_h=FH)
        IY += FH + 6

        # valor total com ícone moeda
        v.draw_rect(IX + 1, IY,     5, 1, 255, 215, 0)
        v.draw_rect(IX,     IY + 1, 7, 4, 220, 170, 0)
        v.draw_rect(IX + 1, IY + 2, 5, 2, 255, 200, 30)
        v.draw_rect(IX + 1, IY + 5, 5, 1, 255, 215, 0)
        v.draw_text(IX + 9, IY, val_str[:chars_l], font_sid=font_sid, font_w=FW, font_h=FH)
        IY += FH + 4

        # separador + controles
        for sx in range(0, IW, 4):
            v.draw_rect(IX + sx, IY, 2, 1, 110, 90, 45)
        IY += 4
        v.draw_text(IX, IY,          "^v:+1  <>:+10"[:chars_l],
                    font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(IX, IY + FH + 1, "Z:OK   X:Cancela"[:chars_l],
                    font_sid=font_sid, font_w=FW, font_h=FH)
        return

    # =========================================================================
    # BORDAS
    # =========================================================================
    _tit_max = max(1, (LISTA_W - 16) // FW)
    titulo_lista = ("Comprar" if modo_comprar else "Vender")[:_tit_max]
    # Direita: título vazio — nome aparece dentro em 2 linhas se necessário
    v.draw_text_box(x=MX, y=MY, box_w=LISTA_W, box_h=BH,
                    title=titulo_lista, content="",
                    box_sid=box_sid, box_tw=8, box_th=8,
                    font_sid=font_sid, font_w=FW, font_h=FH)

    v.draw_text_box(x=DET_X, y=MY, box_w=DET_W, box_h=BH,
                    title="Detalhe", content="",
                    box_sid=box_sid, box_tw=8, box_th=8,
                    font_sid=font_sid, font_w=FW, font_h=FH)

    # =========================================================================
    # COLUNA ESQUERDA
    # =========================================================================
    LX = MX + _PAD 
    LY = MY + 8 + FH + 3
    LW = LISTA_W - _PAD * 2

    # abas modo
    pfx_c = "> " if     modo_comprar else "  "
    pfx_v = "> " if not modo_comprar else "  "
    meio  = LX + LW // 2
    v.draw_text(LX,   LY + 1, f"{pfx_c}Comprar", font_sid=font_sid, font_w=FW, font_h=FH)
    v.draw_text(meio, LY + 1, f"{pfx_v}Vender",  font_sid=font_sid, font_w=FW, font_h=FH)
    LY += FH + 6

    # ouro
    v.draw_rect(LX + 1, LY,     5, 1, 255, 215, 0)
    v.draw_rect(LX,     LY + 1, 7, 4, 220, 170, 0)
    v.draw_rect(LX + 1, LY + 2, 5, 2, 255, 200, 30)
    v.draw_rect(LX + 1, LY + 5, 5, 1, 255, 215, 0)
    v.draw_text(LX + 9, LY, f"{jogador.gold}G", font_sid=font_sid, font_w=FW, font_h=FH)
    LY += FH + 4

    # separador
    for sx in range(0, LW, 4):
        v.draw_rect(LX + sx, LY, 2, 1, 110, 90, 45)
    LY += 5

    # lista de itens: cursor > + ícone 16px + nome completo
    SLOT_L   = 16
    ITEM_H   = SLOT_L + 4
    ROD_H    = FH * 2 + 10
    AREA_H   = BH - (LY - MY) - ROD_H
    VISIVEIS = max(1, AREA_H // ITEM_H)

    cursor = ec['loja_cursor']
    scroll = max(0, min(ec['loja_scroll'], max(0, total - VISIVEIS)))
    ec['loja_scroll'] = scroll

    if scroll > 0:
        cx = LX + LW // 2
        v.draw_rect(cx,     LY - 6, 1, 1, 200, 200, 200)
        v.draw_rect(cx - 1, LY - 5, 3, 1, 200, 200, 200)
        v.draw_rect(cx - 2, LY - 4, 5, 1, 200, 200, 200)

    NOME_X_OFF = FW * 2 + SLOT_L + 3
    NOME_MAX_C = max(1, (LW - NOME_X_OFF) // FW)

    for i in range(scroll, min(scroll + VISIVEIS, total)):
        nome = lista[i]
        iy   = LY + (i - scroll) * ITEM_H
        sel  = (i == cursor)
        ty   = iy + (ITEM_H - FH) // 2

        if sel:
            v.draw_text(LX, ty, ">", font_sid=font_sid, font_w=FW, font_h=FH)

        _desenhar_slot_item(v, LX + FW * 2, iy + (ITEM_H - SLOT_L) // 2,
                            nome, _todos_itens, itens_sprite_ids,
                            destaque=False, tamanho=SLOT_L)

        v.draw_text(LX + NOME_X_OFF, ty, _nome_sem_estrela(nome)[:NOME_MAX_C],
                    font_sid=font_sid, font_w=FW, font_h=FH)

    if scroll + VISIVEIS < total:
        by = LY + VISIVEIS * ITEM_H + 1
        cx = LX + LW // 2
        v.draw_rect(cx - 2, by,     5, 1, 200, 200, 200)
        v.draw_rect(cx - 1, by + 1, 3, 1, 200, 200, 200)
        v.draw_rect(cx,     by + 2, 1, 1, 200, 200, 200)

    # rodapé lista
    rod_lista = MY + BH - FH * 2 - 7
    for sx in range(0, LW, 4):
        v.draw_rect(LX + sx, rod_lista - 3, 2, 1, 110, 90, 45)
    cont_str = f"{cursor + 1}/{total}" if total > 0 else "0/0"
    v.draw_text(LX, rod_lista,          cont_str[:LW // FW],
                font_sid=font_sid, font_w=FW, font_h=FH)
    v.draw_text(LX, rod_lista + FH + 1, "Enter:trocar  X:sair"[:LW // FW],
                font_sid=font_sid, font_w=FW, font_h=FH)

    # =========================================================================
    # COLUNA DIREITA — nome em 2 linhas + tipo + preço + descrição
    # =========================================================================
    PX    = DET_X + _PAD
    PY    = MY + 8 + FH + 3
    PW    = DET_W - _PAD * 2
    rod_y = MY + BH - FH * 2 - 7

    if obj_sel is None:
        v.draw_text(PX, PY, "Nenhum item.", font_sid=font_sid, font_w=FW, font_h=FH)
    else:
        CY    = PY
        max_c = max(1, PW // FW)

        # nome completo — até 2 linhas, word-wrap por palavra
        def _wrap(texto, largura):
            linhas, linha = [], ""
            for p in texto.split():
                teste = (linha + " " + p).strip() if linha else p
                if len(teste) <= largura: linha = teste
                else:
                    if linha: linhas.append(linha)
                    linha = p
            if linha: linhas.append(linha)
            return linhas or [""]

        nome_linhas = _wrap(nome_sel, max_c)[:2]   # máximo 2 linhas
        for nl in nome_linhas:
            v.draw_text(PX, CY, nl, font_sid=font_sid, font_w=FW, font_h=FH)
            CY += FH + 1
        CY += 2

        # tipo
        tipo_str = f"[{obj_sel.tipo}]"[:max_c]
        v.draw_text(PX, CY, tipo_str, font_sid=font_sid, font_w=FW, font_h=FH)
        CY += FH + 4

        # separador duplo
        for sx in range(0, PW, 4):
            v.draw_rect(PX + sx, CY,     2, 1, 140, 110, 40)
        for sx in range(0, PW, 4):
            v.draw_rect(PX + sx, CY + 2, 2, 1, 80,  60,  20)
        CY += 7

        # preço + ouro jogador na mesma linha
        if modo_comprar:
            preco_val = obj_sel.compra
            pode      = jogador.gold >= preco_val and preco_val > 0
        else:
            preco_val = obj_sel.preco
            pode      = jogador.invetario.get(nome_sel, 0) > 0

        # ícone moeda + preço
        v.draw_rect(PX + 1, CY,     5, 1, 255, 215, 0)
        v.draw_rect(PX,     CY + 1, 7, 4, 220, 170, 0)
        v.draw_rect(PX + 1, CY + 2, 5, 2, 255, 200, 30)
        v.draw_rect(PX + 1, CY + 5, 5, 1, 255, 215, 0)
        v.draw_text(PX + 9, CY, f"{preco_val}G", font_sid=font_sid, font_w=FW, font_h=FH)

        # ouro do jogador à direita (se couber)
        saldo_str = f"{jogador.gold}G"
        saldo_x   = PX + PW - len(saldo_str) * FW
        if saldo_x >= PX + 9 + (len(str(preco_val)) + 2) * FW:
            v.draw_rect(saldo_x - 8, CY,     5, 1, 255, 215, 0)
            v.draw_rect(saldo_x - 9, CY + 1, 7, 4, 220, 170, 0)
            v.draw_rect(saldo_x - 8, CY + 2, 5, 2, 255, 200, 30)
            v.draw_rect(saldo_x - 8, CY + 5, 5, 1, 255, 215, 0)
            v.draw_text(saldo_x, CY, saldo_str, font_sid=font_sid, font_w=FW, font_h=FH)
        CY += FH + 5

        # separador
        for sx in range(0, PW, 4):
            v.draw_rect(PX + sx, CY, 2, 1, 110, 90, 45)
        CY += 5

        # descrição word-wrap até o rodapé
        desc        = obj_sel.descrica or "Sem descricao."
        limite_desc = rod_y - FH - 8
        for linha in _wrap(desc, max_c):
            if CY + FH > limite_desc:
                break
            v.draw_text(PX, CY, linha, font_sid=font_sid, font_w=FW, font_h=FH)
            CY += FH + 1

        # stats antes do rodapé
        stats = []
        if hasattr(obj_sel, 'recupar_hp') and obj_sel.recupar_hp: stats.append(f"HP+{obj_sel.recupar_hp}")
        if hasattr(obj_sel, 'recupar_mn') and obj_sel.recupar_mn: stats.append(f"ST+{obj_sel.recupar_mn}")
        if hasattr(obj_sel, 'bonus_hp')   and obj_sel.bonus_hp:   stats.append(f"HPmax+{obj_sel.bonus_hp}")
        if stats:
            for st in stats:
                if CY + FH <= limite_desc:
                    v.draw_text(PX, CY, st[:max_c], font_sid=font_sid, font_w=FW, font_h=FH)
                    CY += FH + 1

    # rodapé direito
    for sx in range(0, PW, 4):
        v.draw_rect(PX + sx, rod_y - 3, 2, 1, 110, 90, 45)

    if obj_sel:
        if modo_comprar:
            pode = obj_sel.compra and jogador.gold >= obj_sel.compra
            acao = "Z: Comprar" if pode else "G insuficiente"
        else:
            pode = jogador.invetario.get(nome_sel, 0) > 0
            acao = "Z: Vender" if pode else "Sem estoque"
        v.draw_text(PX, rod_y,      acao[:PW // FW], font_sid=font_sid, font_w=FW, font_h=FH)

    v.draw_text(PX, rod_y + FH + 1, "^v Mover"[:PW // FW],
                font_sid=font_sid, font_w=FW, font_h=FH)

def inicializar_estado_caixa():
    return {
        'mostrar_caixa':     False,
        'caixa_cursor':      0,
        'caixa_pagina':      0,
        'caixa_modo_qtd':    False,
        'caixa_qtd_cursor':  1,
        'caixa_item_sel':    None,
        'mostrar_relatorio': False,
        'relatorio_dados':   None,
        'relatorio_pagina':  0,
    }

def _itens_vendiveis(jogador):
    return [
        (nome, qtd, todos_itens[nome])
        for nome, qtd in jogador.invetario.items()
        if nome in todos_itens and qtd > 0 and todos_itens[nome].vendivel
    ]

def _paginar(lista, pagina, por_pagina):
    total   = len(lista)
    max_pag = max(0, (total - 1) // por_pagina) if total > 0 else 0
    pagina  = max(0, min(pagina, max_pag))
    inicio  = pagina * por_pagina
    return lista[inicio: inicio + por_pagina], max_pag, pagina

def processar_vendas_e_dormir(jogador, estado_chuva=None):
    from artes import mapas_mundo
    from objeto import atualizar_plantacoes_do_mundo

    dia_anterior = jogador.dia_atual
    lucro_total  = 0
    por_tipo     = {}
    caixa        = jogador.caixa_vendas

    itens_iter = list(caixa.items()) if isinstance(caixa, dict) else list({n: caixa.count(n) for n in caixa}.items())

    for nome, qtd in itens_iter:
        if nome not in todos_itens:
            continue
        obj   = todos_itens[nome]
        valor = obj.preco * qtd
        lucro_total += valor
        cat = obj.tipo_presente if obj.tipo_presente else obj.tipo
        por_tipo.setdefault(cat, {}).setdefault(nome, {'qtd': 0, 'valor': 0})
        por_tipo[cat][nome]['qtd']   += qtd
        por_tipo[cat][nome]['valor'] += valor

    jogador.gold        += lucro_total
    jogador.caixa_vendas = {} if isinstance(caixa, dict) else []

    ESTACOES = ["Primavera", "Verao", "Outono", "Inverno"]
    jogador.dia_atual += 1
    if jogador.dia_atual > 28:
        jogador.dia_atual = 1
        jogador.estacao_atual = ESTACOES[(ESTACOES.index(jogador.estacao_atual) + 1) % 4]

    atualizar_plantacoes_do_mundo(mapas_mundo, jogador.estacao_atual)

    if estado_chuva is not None:
        decidir_clima_novo_dia(jogador, estado_chuva, mapas_mundo)

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

    if ec['caixa_modo_qtd']:
        nome    = ec['caixa_item_sel']
        max_qtd = jogador.invetario.get(nome, 0)

        if v.key_pressed(b"up"):
            ec['caixa_qtd_cursor'] = min(ec['caixa_qtd_cursor'] + 1, max_qtd)
        elif v.key_pressed(b"down"):
            ec['caixa_qtd_cursor'] = max(ec['caixa_qtd_cursor'] - 1, 1)
        elif v.key_pressed(b"z"):
            qtd = ec['caixa_qtd_cursor']
            jogador.invetario[nome] -= qtd
            if jogador.invetario[nome] <= 0:
                del jogador.invetario[nome]
            caixa = jogador.caixa_vendas
            if isinstance(caixa, dict):
                caixa[nome] = caixa.get(nome, 0) + qtd
            else:
                for _ in range(qtd):
                    caixa.append(nome)
            ec['caixa_modo_qtd']   = False
            ec['caixa_item_sel']   = None
            ec['caixa_qtd_cursor'] = 1
        elif v.key_pressed(b"q"):
            ec['caixa_modo_qtd']   = False
            ec['caixa_item_sel']   = None
            ec['caixa_qtd_cursor'] = 1
        return True

    vendiveis = _itens_vendiveis(jogador)
    itens_pag, max_pag, ec['caixa_pagina'] = _paginar(vendiveis, ec['caixa_pagina'], ITENS_POR_PAG_CAIXA)
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

def desenhar_caixa_vendas(v, jogador, estado_caixa, box_sid, font_sid, SCREEN_W, SCREEN_H):
    ec        = estado_caixa
    vendiveis = _itens_vendiveis(jogador)
    itens_pag, max_pag, ec['caixa_pagina'] = _paginar(vendiveis, ec['caixa_pagina'], ITENS_POR_PAG_CAIXA)
    n      = len(itens_pag)
    cursor = min(ec['caixa_cursor'], max(n - 1, 0))

    caixa = getattr(jogador, 'caixa_vendas', {})
    if isinstance(caixa, dict):
        itens_na_caixa = sum(caixa.values())
        valor_caixa    = sum(todos_itens[nm].preco * q for nm, q in caixa.items() if nm in todos_itens)
    else:
        itens_na_caixa = len(caixa)
        valor_caixa    = sum(todos_itens[nm].preco for nm in caixa if nm in todos_itens)

    if not itens_pag:
        lista_txt = "Nenhum item vendivel\nno inventario.\n"
    else:
        lista_txt = ""
        for i, (nome, qtd_inv, obj) in enumerate(itens_pag):
            seta = "->" if i == cursor else "  "
            lista_txt += f"{seta} {nome}\n    x{qtd_inv} no inv.  {obj.preco}G/un\n\n"

    titulo   = "Caixa de Vendas"
    conteudo = lista_txt + (
        f"------------------------\nNa caixa: {itens_na_caixa} item(s)\n"
        f"Valor estimado: {valor_caixa}G\n------------------------\n"
        f"Pag {ec['caixa_pagina']+1}/{max_pag+1}\n[Cima/Baixo] Mover\n[Z] Depositar   [X] Fechar"
    )

    if ec['caixa_modo_qtd']:
        nome      = ec['caixa_item_sel']
        max_qtd   = jogador.invetario.get(nome, 0)
        qtd       = ec['caixa_qtd_cursor']
        valor_prev = todos_itens[nome].preco * qtd if nome in todos_itens else 0
        conteudo = (
            f"Item: {nome}\nDisponivel: x{max_qtd}\n------------------------\n\n"
            f"Quantidade: {qtd}\n\nValor recebido:\n  {valor_prev}G\n\n"
            f"------------------------\n[Cima/Baixo] Ajustar\n[Z] Confirmar  [X] Cancelar"
        )
        titulo = "Depositar na caixa"

    v.draw_text_box(x=0, y=0, box_w=364, box_h=244,
                    title="titulo", content=conteudo,
                    box_sid=box_sid, box_tw=8, box_th=8,
                    font_sid=font_sid, font_w=8, font_h=8)

LINHAS_POR_PAG_REL = 10

def _montar_linhas_relatorio(relatorio):
    linhas = []
    for categoria, itens in relatorio.get('por_tipo', {}).items():
        total_cat = sum(d['valor'] for d in itens.values())
        linhas.append(f"[ {categoria} ]  {total_cat}G")
        for nome, dados in itens.items():
            linhas.append(f"  {nome}")
            linhas.append(f"    x{dados['qtd']}  ->  {dados['valor']}G")
        linhas.append("")
    return linhas or ["Nenhum item vendido hoje."]

def atualizar_tela_relatorio(v, estado_caixa):
    ec     = estado_caixa
    linhas = _montar_linhas_relatorio(ec.get('relatorio_dados') or {})
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

def desenhar_tela_relatorio(v, estado_caixa, box_sid, font_sid, SCREEN_W, SCREEN_H):
    ec      = estado_caixa
    rel     = ec.get('relatorio_dados') or {}
    linhas  = _montar_linhas_relatorio(rel)
    max_pag = max(0, (len(linhas) - 1) // LINHAS_POR_PAG_REL)
    pag     = ec['relatorio_pagina']
    fatia   = linhas[pag * LINHAS_POR_PAG_REL: pag * LINHAS_POR_PAG_REL + LINHAS_POR_PAG_REL]

    lucro       = rel.get('lucro_total', 0)
    lucro_label = f"Lucro total: {lucro}G" if lucro > 0 else "Nenhuma venda hoje."
    conteudo    = (
        f"{lucro_label}\n------------------------\n\n"
        + "\n".join(fatia)
        + f"\n\n------------------------\nPag {pag+1}/{max_pag+1}\n[Esq/Dir] Pagina  [Enter] Acordar"
    )

    v.draw_text_box(x=0, y=0, box_w=SCREEN_W, box_h=SCREEN_H,
                    title=f"Fim do dia {rel.get('dia_anterior', 1)}!",
                    content=conteudo, box_sid=box_sid, box_tw=8, box_th=8,
                    font_sid=font_sid, font_w=8, font_h=8)

def mostrar_xp_ganho(estado, texto, duracao=90):
    """Registra uma notificação de XP ganho para exibir na tela."""
    estado['xp_notif_texto'] = texto
    estado['xp_notif_timer'] = duracao

def desenhar_xp_notif(v, estado, font_sid):
    """
    Exibe notificação de XP/nível no canto superior da tela.
    Fade-out nos últimos 30 frames.
    """
    timer = estado.get('xp_notif_timer', 0)
    if timer <= 0:
        return
    estado['xp_notif_timer'] = timer - 1
    texto = estado.get('xp_notif_texto', '')
    if not texto:
        return

    SCR_W = getattr(v, 'render_w', SCREEN_W)
    FW, FH = 8, 8
    W = len(texto) * FW + 10
    X = (SCR_W - W) // 2
    Y = 6

    # fundo semi-opaco
    v.draw_rect(X - 1, Y - 1, W + 2, FH + 4, 0, 0, 0)
    v.draw_rect(X,     Y,     W,     FH + 2, 15, 15, 30)

    # destaque via draw_rect antes do texto (engine não aceita cor no draw_text)
    if "ponto" in texto.lower() or "nivel" in texto.lower():
        v.draw_rect(X, Y, W, FH + 2, 60, 45, 0)       # fundo ambar escuro
    else:
        v.draw_rect(X, Y, W, FH + 2, 0, 45, 0)        # fundo verde escuro
    v.draw_text(X + 5, Y + 1, texto, font_sid=font_sid, font_w=FW, font_h=FH)

def ganhar_xp_e_notificar(jogador, estado, acao, bonus_xp=0):
    """
    Atalho: chama jogador.ganhar_xp_hab() e registra a notificação visual.
    Use este em game.py em vez de chamar ganhar_xp_hab direto.
    """
    if not hasattr(jogador, 'ganhar_xp_hab'):
        return
    res = jogador.ganhar_xp_hab(acao, bonus_xp)
    if res['xp_ganho'] > 0:
        mostrar_xp_ganho(estado, res['mensagem'][:36])

def controlar_framerate(start_time):
    elapsed = time.time() - start_time
    if elapsed < FRAME_TIME:
        time.sleep(FRAME_TIME - elapsed)

_CHANCE_CHUVA_BASE    = 0.40
_CICLO_CHUVA_DIAS     = 4
_DURACAO_CHUVA_MINIMA = 1
_DURACAO_CHUVA_MAXIMA = 3

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
            (_random.randint(0, SCREEN_W - 1), i * (SCREEN_H // _NUM_GOTAS))
            for i in range(_NUM_GOTAS)
        ],
    }

def _regar_terra_arada(mapas_mundo):
    for mapa_dict in mapas_mundo.values():
        mapa     = mapa_dict["arte"]
        map_rows = len(mapa)
        map_cols = len(mapa[0]) if map_rows > 0 else 0
        for y in range(map_rows):
            for x in range(map_cols):
                if mapa[y][x] == 1:
                    mapa[y][x] = 2
        if "plantacoes" in mapa_dict:
            from objeto import _atualizar_tile_planta
            for coords, dados in mapa_dict["plantacoes"].items():
                dados["regada"] = True
                _atualizar_tile_planta(mapa_dict, coords[0], coords[1])

def decidir_clima_novo_dia(jogador, estado_chuva, mapas_mundo):
    ec = estado_chuva
    if ec['chovendo']:
        ec['dias_restantes'] -= 1
        if ec['dias_restantes'] <= 0:
            ec['chovendo']       = False
            ec['dias_restantes'] = 0
            jogador.clima        = "sol"
        else:
            _regar_terra_arada(mapas_mundo)
    else:
        if jogador.dia_atual % _CICLO_CHUVA_DIAS == 0:
            if _random.random() < _CHANCE_CHUVA_BASE:
                ec['chovendo']       = True
                ec['dias_restantes'] = _random.randint(_DURACAO_CHUVA_MINIMA, _DURACAO_CHUVA_MAXIMA)
                jogador.clima        = "chuva"
                _regar_terra_arada(mapas_mundo)

def atualizar_chuva(estado_chuva):
    if not estado_chuva['chovendo']:
        return
    ec         = estado_chuva
    ec['frame'] += 1
    novas_gotas = []
    for gx, gy in ec['gotas']:
        gx = (gx + _GOTA_SPREAD) % SCREEN_W
        gy += _GOTA_VEL
        if gy >= SCREEN_H:
            gy = _random.randint(-20, -1)
            gx = _random.randint(0, SCREEN_W - 1)
        novas_gotas.append((gx, gy))
    ec['gotas'] = novas_gotas

def desenhar_chuva(v, estado_chuva):
    if not estado_chuva['chovendo']:
        return
    gotas   = estado_chuva['gotas']
    v.draw_rain(SCREEN_W, SCREEN_H, estado_chuva['frame'],
                [g[0] for g in gotas], [g[1] for g in gotas],
                _GOTA_W, _GOTA_H)

_FRAMES_POR_5MIN = 25 * FPS

def atualizar_tempo(jogador, estado_ui):
    estado_ui['timer_tempo'] = estado_ui.get('timer_tempo', 0) + 1
    if estado_ui['timer_tempo'] >= _FRAMES_POR_5MIN:
        estado_ui['timer_tempo'] = 0
        jogador.minutos += 5
        if jogador.minutos >= 60:
            jogador.minutos = 0
            jogador.horas  += 1
            if jogador.horas >= 24:
                jogador.horas = 0

def _intensidade_noite(horas, minutos):
    hora_total = horas + minutos / 60.0
    if hora_total < 18.0:
        return 0.0
    elif hora_total < 21.0:
        return ((hora_total - 18.0) / 3.0) * 0.45
    return 0.45

def desenhar_noite(v, jogador):
    intensidade = _intensidade_noite(jogador.horas, jogador.minutos)
    if intensidade > 0.0:
        v.draw_night(SCREEN_W, SCREEN_H, intensidade, (jogador.horas + jogador.minutos) % 2)

def desenhar_barra_bloco(v, jogador, mapa_dict, cam_x, cam_y):
    from objeto import _dano_blocos, _id_para_nome, obter_bloco_frente
    from itens import TODOS_TILES

    res = obter_bloco_frente(jogador, mapa_dict)
    if not res:
        return
    nx, ny, tile_id = res
    dano = _dano_blocos.get((jogador.mapa_atual, nx, ny), 0)
    if dano <= 0:
        return

    tile_data = TODOS_TILES.get(_id_para_nome(mapa_dict, tile_id))
    if not tile_data or not tile_data.hp_max:
        return

    hp_max   = tile_data.hp_max
    hp_atual = max(0, hp_max - dano)
    sx = nx * TILE_SIZE - cam_x
    sy = ny * TILE_SIZE - cam_y

    v.draw_rect(sx - 1, sy - 4 - 1, TILE_SIZE + 2, 3 + 2, 255, 255, 255)
    v.draw_rect(sx, sy - 4, TILE_SIZE, 3, 20, 20, 20)

    fill_w = max(1, int(TILE_SIZE * hp_atual / hp_max))
    ratio  = hp_atual / hp_max
    r, g, b = (50, 200, 50) if ratio > 0.5 else (220, 180, 0) if ratio > 0.25 else (200, 40, 40)
    v.draw_rect(sx, sy - 4, fill_w, 3, r, g, b)

def desenhar_barras_vida(v, jogador, font_sid, cam_y=0):
    BW    = HUD_BAR_W
    BH    = HUD_BAR_H
    hp_x  = HUD_BAR_X
    stm_x = HUD_BAR_X + BW + HUD_BAR_GAP
    by    = HUD_BAR_Y

    def _barra(bx, atual, maximo, rf, gf, bf, r_v, g_v, b_v):
        v.draw_rect(bx - 1, by - 1, BW + 2, BH + 2, 30, 30, 30)
        v.draw_rect(bx, by, BW, BH, r_v, g_v, b_v)
        if maximo > 0 and atual > 0:
            fill_h = max(1, int(BH * atual / maximo))
            fill_y = by + BH - fill_h
            v.draw_rect(bx, fill_y, BW, fill_h, rf, gf, bf)
            v.draw_rect(bx, fill_y, BW, 1, 255, 255, 255)

    ratio = jogador.hp / jogador.hp_max if jogador.hp_max > 0 else 0
    hr, hg, hb = (60, 200, 60) if ratio > 0.6 else (200, 200, 30) if ratio > 0.3 else (220, 40, 40)
    _barra(hp_x,  jogador.hp,   jogador.hp_max,   hr, hg, hb,   20, 50, 20)
    _barra(stm_x, jogador.mana, jogador.mana_max, 210, 190, 30, 55, 50, 10)

    label_y = by - 9
    if label_y >= 0:
        v.draw_text(hp_x,  label_y, "H", font_sid=font_sid, font_w=8, font_h=8)
        v.draw_text(stm_x, label_y, "S", font_sid=font_sid, font_w=8, font_h=8)

def _info_x(jogador, cam_x, map_cols):
    if jogador.grid_x * TILE_SIZE < (map_cols * TILE_SIZE) // 2:
        return SCREEN_W - HUD_INFO_W - 2
    return 2

def desenhar_hud_tempo(v, jogador, estado_chuva, box_sid, font_sid, cam_x=0, map_cols=0):
    ABREV = {"Primavera": "Pri", "Verao": "Ver", "Outono": "Out", "Inverno": "Inv"}
    est   = ABREV.get(jogador.estacao_atual, jogador.estacao_atual[:3])
    ix    = _info_x(jogador, cam_x, map_cols) if map_cols > 0 else HUD_INFO_X

    v.draw_text_box(ix, HUD_INFO_Y, box_w=HUD_INFO_W, box_h=HUD_INFO_H,
                    title="", content=f"Dia:{jogador.dia_atual:02d}\n{est} {jogador.horas:02d}:{jogador.minutos:02d}",
                    box_sid=box_sid, box_tw=8, box_th=8,
                    font_sid=font_sid, font_w=8, font_h=8, line_spacing=2)

    v.draw_text_box(ix, HUD_GOLD_Y, box_w=HUD_GOLD_W, box_h=HUD_GOLD_H,
                    title="", content=f"G${jogador.gold}",
                    box_sid=box_sid, box_tw=8, box_th=8,
                    font_sid=font_sid, font_w=8, font_h=8)

    if estado_chuva.get('chovendo'):
        chuva_x = ix + HUD_INFO_W + 2 if ix < SCREEN_W // 2 else ix - 10
        v.draw_text(chuva_x, HUD_INFO_Y + 12, "*", font_sid=font_sid, font_w=8, font_h=8)

from save_load import salvar_jogo, carregar_jogo

_OPCOES_MENU = ["Inventario", "Status", "Social", "Missoes", "Save", "Load", "HUD Tempo: {}", "Sair"]

def inicializar_estado_menu():
    return {'aberto': False, 'cursor': 0}

def _opcoes_menu(estado):
    hud_label = "ON" if estado.get('hud_tempo_ativo', True) else "OFF"
    return ["Inventario", "Status", "Social", "Missoes", "Save", "Load", f"HUD: {hud_label}", "Sair"]

def processar_input_menu(v, estado):
    opcoes = _opcoes_menu(estado)
    if v.key_pressed(b"up"):
        estado['menu_cursor'] = (estado['menu_cursor'] - 1) % len(opcoes)
    if v.key_pressed(b"down"):
        estado['menu_cursor'] = (estado['menu_cursor'] + 1) % len(opcoes)
    if v.key_pressed(b"x"):
        estado['menu_aberto'] = False
        return None
    if v.key_pressed(b"z"):
        escolha = opcoes[estado['menu_cursor']]
        if escolha not in ("Inventario",) and not escolha.startswith("HUD:"):
            estado['menu_aberto'] = False
        if escolha.startswith("HUD:"):
            estado['hud_tempo_ativo'] = not estado.get('hud_tempo_ativo', True)
            return None
        return escolha
    return None

def desenhar_menu_principal(v, estado, box_sid, font_sid):
    opcoes = _opcoes_menu(estado)
    linhas = ""
    for i, op in enumerate(opcoes):
        linhas += f"{'-> ' if i == estado['menu_cursor'] else '   '}{op}\n\n"
    v.draw_text_box(x=102, y=52, box_w=136, box_h=140, title="Menu",
                    content=linhas + "\n[Cima/Baixo] Mover\n[Z] OK  [X] Fechar",
                    box_sid=box_sid, box_tw=8, box_th=8,
                    font_sid=font_sid, font_w=8, font_h=8)

# ── Cores das estrelas ────────────────────────────────────────────────────
_COR_ESTRELA = {
    0: (80,  80,  80),    # sem estrela (cinza)
    1: (180, 100, 40),    # bronze
    2: (60,  60,  60),    # preta
    3: (220, 185, 30),    # ouro
    4: (200, 220, 240),   # platina
}
_NOME_ESTRELA = {0: "-", 1: "B", 2: "N", 3: "O", 4: "P"}

# ── Config habilidades (nome, attr_nivel, attr_xp, cor RGB) ───────────────
_HABS = [
    ("Coleta",  "hab_coleta",  "xp_coleta",  (80, 200, 100)),
    ("Cultivo", "hab_cultivo", "xp_cultivo", (120, 200, 60)),
    ("Pesca",   "hab_pesca",   "xp_pesca",   (60, 140, 220)),
    ("Social",  "hab_social",  "xp_social",  (200, 100, 200)),
]
_HAB_MAX = 10
_XP_POR_NIVEL_HAB = 100   # XP da hab específica por nível (só visual)

def _draw_barra_pixels(v, x, y, w, h, atual, maximo, r, g, b, r_bg=20, g_bg=20, b_bg=20):
    """Barra de progresso pixel-art com borda."""
    # fundo + borda
    v.draw_rect(x - 1, y - 1, w + 2, h + 2, 50, 50, 50)
    v.draw_rect(x, y, w, h, r_bg, g_bg, b_bg)
    if maximo > 0 and atual > 0:
        fill = max(1, int(w * min(atual, maximo) / maximo))
        v.draw_rect(x, y, fill, h, r, g, b)
        # brilho no topo
        v.draw_rect(x, y, fill, 1, min(r + 80, 255), min(g + 80, 255), min(b + 80, 255))

def _draw_icone_coracao(v, x, y, r=220, g=50, b=80):
    """Desenha um coraçãozinho 7×6 px."""
    v.draw_rect(x + 1, y,     2, 1, r, g, b)
    v.draw_rect(x + 4, y,     2, 1, r, g, b)
    v.draw_rect(x,     y + 1, 7, 3, r, g, b)
    v.draw_rect(x + 1, y + 4, 5, 1, r, g, b)
    v.draw_rect(x + 2, y + 5, 3, 1, r, g, b)

def _draw_icone_mana(v, x, y):
    """Desenha um diamante/cristal 5×7 px para mana/stamina."""
    v.draw_rect(x + 2, y,     1, 1, 160, 210, 255)
    v.draw_rect(x + 1, y + 1, 3, 1, 120, 180, 255)
    v.draw_rect(x,     y + 2, 5, 2, 80, 140, 240)
    v.draw_rect(x + 1, y + 4, 3, 1, 60, 110, 200)
    v.draw_rect(x + 2, y + 5, 1, 1, 40, 90, 180)

def _draw_icone_moeda(v, x, y):
    """Moeda de ouro 7×7 px."""
    v.draw_rect(x + 1, y,     5, 1, 255, 215,   0)
    v.draw_rect(x,     y + 1, 7, 4, 220, 170,   0)
    v.draw_rect(x + 1, y + 2, 5, 2, 255, 200,  30)
    v.draw_rect(x + 1, y + 5, 5, 1, 255, 215,   0)

def _draw_separador(v, x, y, w, r=140, g=110, b=50):
    for sx in range(0, w, 4):
        v.draw_rect(x + sx, y, 2, 1, r, g, b)

def _draw_estrela_5x5(v, x, y, r, g, b):
    """
    Losango 5x5 px com borda preta e fundo colorido.
    Padrao:
      . . B . .
      . B F B .
      B F F F B
      . B F B .
      . . B . .
    """
    bk = (0, 0, 0)
    fc = (r, g, b)
    def px(cx, cy, clr):
        v.draw_rect(x + cx, y + cy, 1, 1, clr[0], clr[1], clr[2])
    # row 0
    px(2, 0, bk)
    # row 1
    px(1, 1, bk); px(2, 1, fc); px(3, 1, bk)
    # row 2
    px(0, 2, bk); px(1, 2, fc); px(2, 2, fc); px(3, 2, fc); px(4, 2, bk)
    # row 3
    px(1, 3, bk); px(2, 3, fc); px(3, 3, bk)
    # row 4
    px(2, 4, bk)

def _draw_icone_estrela_pequena(v, x, y, estrelas):
    cor = _COR_ESTRELA.get(estrelas, (80, 80, 80))
    _draw_estrela_5x5(v, x, y, cor[0], cor[1], cor[2])

def _draw_icone_coxa_frango(v, x, y):
    """Coxa de frango pixel-art 7×7 px para stamina."""
    # osso (cabo)
    v.draw_rect(x + 5, y + 5, 2, 2, 220, 210, 190)
    v.draw_rect(x + 4, y + 4, 2, 2, 220, 210, 190)
    # carne (parte grossa)
    v.draw_rect(x + 1, y,     4, 1, 210, 120,  60)
    v.draw_rect(x,     y + 1, 5, 3, 190,  90,  40)
    v.draw_rect(x + 1, y + 4, 3, 1, 170,  75,  30)
    # brilho
    v.draw_rect(x + 1, y + 1, 2, 1, 240, 160,  90)

def _nome_sem_estrela(nome):
    """Remove sufixo de qualidade ASCII do nome do item para exibição limpa."""
    for sf in (" (B)", " (N)", " (O)", " (P)"):
        if nome.endswith(sf):
            return nome[:-len(sf)]
    return nome

def _estrelas_do_nome(nome):
    """Lê o nível de estrelas diretamente do sufixo do nome do item.
    Não sorteia — apenas decodifica o que já foi aplicado na colheita/pesca.
    Retorna 0 se o item não tem sufixo de qualidade."""
    _mapa = {" (B)": 1, " (N)": 2, " (O)": 3, " (P)": 4}
    for sf, nivel in _mapa.items():
        if nome.endswith(sf):
            return nivel
    return 0

def desenhar_menu_status(v, jogador, estado_chuva, box_sid, font_sid,
                          estado_status=None):
    """
    Menu de Status completo com pixel-art.
    estado_status dict:  cursor_hab (int), modo_distribuir (bool)
    """
    FW, FH = 8, 8
    SCR_W  = getattr(v, 'render_w', SCREEN_W)
    SCR_H  = getattr(v, 'render_h', SCREEN_H)
    MX, MY = 90, 3
    BTH    = 8
    BW     = 180
    BH     = SCR_H - MY * 2
    PAD    = 7
    INNER_BOT = MY + BH - BTH

    # ── painel principal ──────────────────────────────────────────────────────
    v.draw_text_box(x=MX, y=MY, box_w=BW, box_h=BH,
                    title="== STATUS ==", content="",
                    box_sid=box_sid, box_tw=BTH, box_th=BTH,
                    font_sid=font_sid, font_w=FW, font_h=FH)

    cx = MX + PAD
    cy = MY + BTH + FH + 4

    # ── cabeçalho: nome + clima ───────────────────────────────────────────────
    est_nome = jogador.estacao_atual
    clima    = "Chuva" if estado_chuva.get('chovendo') else "Sol"
    ABREV = {"Primavera": "Pri", "Verao": "Ver", "Outono": "Out", "Inverno": "Inv"}
    est_abrev = ABREV.get(est_nome, est_nome[:3])

    v.draw_text(cx, cy, jogador.nome,
                font_sid=font_sid, font_w=FW, font_h=FH)
    cy += FH + 4

    # ── separador decorativo ─────────────────────────────────────────────────
    _draw_separador(v, cx, cy, BW - PAD * 2)
    cy += 5

    # ── HP ───────────────────────────────────────────────────────────────────
    _draw_icone_coracao(v, cx, cy)
    v.draw_text(cx + 10, cy, f"HP {jogador.hp:3d}/{jogador.hp_max}",
                font_sid=font_sid, font_w=FW, font_h=FH)
    cy += FH + 2
    ratio_hp = jogador.hp / max(1, jogador.hp_max)
    r_hp, g_hp, b_hp = (60, 200, 60) if ratio_hp > 0.6 else (200, 200, 30) if ratio_hp > 0.3 else (220, 40, 40)
    _draw_barra_pixels(v, cx, cy, BW - PAD * 2, 4, jogador.hp, jogador.hp_max, r_hp, g_hp, b_hp)
    cy += 8

    # ── Stamina/Mana ─────────────────────────────────────────────────────────
    _draw_icone_mana(v, cx, cy)
    v.draw_text(cx + 10, cy, f"ST {jogador.mana:3d}/{jogador.mana_max}",
                font_sid=font_sid, font_w=FW, font_h=FH)
    cy += FH + 2
    _draw_barra_pixels(v, cx, cy, BW - PAD * 2, 4, jogador.mana, jogador.mana_max, 80, 140, 240)
    cy += 8

    # ── Ouro ─────────────────────────────────────────────────────────────────
    _draw_icone_moeda(v, cx, cy)
    v.draw_text(cx + 10, cy, f"{jogador.gold}G",
                font_sid=font_sid, font_w=FW, font_h=FH)
    cy += FH + 5

    # ── separador ────────────────────────────────────────────────────────────
    _draw_separador(v, cx, cy, BW - PAD * 2)
    cy += 5

    # ── XP Geral ─────────────────────────────────────────────────────────────
    xp_hab    = getattr(jogador, 'xp_hab',       0)
    pts_hab   = getattr(jogador, 'pontos_hab',   0)
    xp_limite = getattr(jogador, 'xp_por_ponto', 100)

    if pts_hab > 0:
        # fundo ambar para destacar (engine nao aceita cor no draw_text)
        _ptxt = f">> {pts_hab} ponto(s) disponivel! <<"
        v.draw_rect(cx - 1, cy - 1, len(_ptxt) * FW + 4, FH + 3, 70, 50, 0)
        v.draw_text(cx, cy, _ptxt, font_sid=font_sid, font_w=FW, font_h=FH)
        cy += FH + 2
    else:
        v.draw_text(cx, cy, f"XP Geral: {xp_hab}/{xp_limite}",
                    font_sid=font_sid, font_w=FW, font_h=FH)
        cy += FH + 2

    _draw_barra_pixels(v, cx, cy, BW - PAD * 2, 4, xp_hab, xp_limite, 100, 200, 255)
    cy += 9

    # ── separador ────────────────────────────────────────────────────────────
    _draw_separador(v, cx, cy, BW - PAD * 2)
    cy += 5

    # ── Habilidades ──────────────────────────────────────────────────────────
    cursor_hab    = estado_status.get('cursor_hab', 0)    if estado_status else 0
    modo_distrib  = estado_status.get('modo_distribuir', False) if estado_status else False

    BAR_W  = max(20, BW - PAD * 2 - FW * 14 - 6)
    BAR_X  = cx + FW * 14
    HAB_H  = FH + 5      # altura de cada linha de habilidade

    for i, (nome_h, attr_n, attr_xp, cor_h) in enumerate(_HABS):
        nivel = getattr(jogador, attr_n, 1)
        sel   = (i == cursor_hab)

        # Fundo de seleção
        if sel and modo_distrib:
            v.draw_rect(cx - 2, cy - 1, BW - PAD * 2 + 4, HAB_H + 1, 35, 55, 35)
        elif sel:
            v.draw_rect(cx - 2, cy - 1, BW - PAD * 2 + 4, HAB_H + 1, 30, 30, 55)

        # Nome + nível
        label = f"{nome_h:7s} {nivel:2d}"
        v.draw_text(cx, cy, label, font_sid=font_sid, font_w=FW, font_h=FH)

        # Barra de nível
        _draw_barra_pixels(v, BAR_X, cy + 1, BAR_W, FH - 2,
                           nivel, _HAB_MAX, cor_h[0], cor_h[1], cor_h[2])

        # Seta "+" se pode subir (fundo verde escuro para indicar acao disponivel)
        if sel and pts_hab > 0 and nivel < _HAB_MAX:
            v.draw_rect(BAR_X + BAR_W + 2, cy - 1, FW + 2, FH + 2, 0, 55, 0)
            v.draw_text(BAR_X + BAR_W + 3, cy, "+",
                        font_sid=font_sid, font_w=FW, font_h=FH)

        cy += HAB_H

    # ── Hora no rodapé ────────────────────────────────────────────────────────
    rod_y = INNER_BOT - BTH - FH * 2 - 6
    _draw_separador(v, cx, rod_y - 3, BW - PAD * 2)

    v.draw_text(cx, rod_y,
                f"{jogador.horas:02d}:{jogador.minutos:02d} {clima}",
                font_sid=font_sid, font_w=FW, font_h=FH)
    v.draw_text(cx ,rod_y+ FH + 2, f"{est_abrev} Dia: {jogador.dia_atual:02d}",
                font_sid=font_sid, font_w=FW, font_h=FH)


    if modo_distrib:
        ctrl = "^v:escolher  Z:ok  X:cancela"
    elif pts_hab > 0:
        ctrl = "Z:distribuir ponto  X:fechar"
    else:
        ctrl = "X: Fechar"
    v.draw_text(cx, rod_y + FH + 12, ctrl[:((BW - PAD * 2) // FW)],
                font_sid=font_sid, font_w=FW, font_h=FH)

def processar_input_status_menu(v, estado, jogador):
    """
    Processa input da tela de Status/Habilidades.
    Retorna True enquanto a tela deve continuar aberta.
    """
    _CHAVES_HAB = ["coleta", "cultivo", "pesca", "social"]
    n   = len(_CHAVES_HAB)
    cur = estado.get('status_cursor_hab', 0)
    modo = estado.get('status_modo_distrib', False)
    pts  = getattr(jogador, 'pontos_hab', 0)

    if v.key_pressed(b"up"):
        estado['status_cursor_hab'] = (cur - 1) % n
    elif v.key_pressed(b"down"):
        estado['status_cursor_hab'] = (cur + 1) % n

    if v.key_pressed(b"z") or v.key_pressed(b"return"):
        if pts > 0 and not modo:
            # Entra no modo distribuição
            estado['status_modo_distrib'] = True
        elif modo:
            # Gasta 1 ponto na habilidade selecionada
            chave = _CHAVES_HAB[estado['status_cursor_hab']]
            msg = jogador.distribuir_ponto(chave)
            print(f"[STATUS] {msg}")
            if getattr(jogador, 'pontos_hab', 0) <= 0:
                estado['status_modo_distrib'] = False

    if v.key_pressed(b"x"):
        if modo:
            estado['status_modo_distrib'] = False
        else:
            estado['mostrar_status_menu'] = False
            estado['status_modo_distrib'] = False
            return False

    return True

def desenhar_estrelas_slot(v, sx, sy, slot_size, item, jogador, font_sid, fw=8, fh=8):
    if item is None:
        return
    nome = item if isinstance(item, str) else getattr(item, 'nome', '')
    est = _estrelas_do_nome(nome)
    if est <= 0:
        return
    cor = _COR_ESTRELA.get(est, (80, 80, 80))
    _draw_estrela_5x5(v, sx, sy + slot_size - 5, cor[0], cor[1], cor[2])

def inicializar_estado_ui():
    return {
        'mostrar_status':      False,
        'inv_pagina':          0,
        'inv_cursor':          0,
        'inv_hotbar_ativo':    False,
        'inv_hotbar_cursor':   1,
        'mostrar_loja':        False,
        'loja_modo':           "comprar",
        'loja_cursor':         0,
        'loja_scroll':         0,
        'loja_modo_qtd':       False,
        'loja_qtd_cursor':     1,
        'loja_item_sel':       None,
        'loja_itens_vendidos': None,
        'msg_interacao':       "",
        'msg_interacao_timer': 0,
        'menu_aberto':         False,
        'menu_cursor':         0,
        'mostrar_status_menu': False,
        # sub-estado da tela de status (habilidades)
        'status_cursor_hab':   0,
        'status_modo_distrib': False,
        'hud_tempo_ativo':     False,
        'dialogo_ativo':       False,
        'dialogo_texto':       "",
        'dialogo_chars':       0.0,
        'dialogo_vel':         1.5,
        'dialogo_vel_rapida':  6.0,
        'dialogo_pagina_ini':  0,
        'dialogo_esperando':   False,
        # Notificação de XP ganho
        'xp_notif_texto':      '',
        'xp_notif_timer':      0,
    }

def _dialogo_quebrar(texto, cols):
    palavras = texto.split(' ')
    linhas   = []
    linha    = ''
    for p in palavras:
        while len(p) > cols:
            espaco = cols - len(linha) - (1 if linha else 0)
            if linha:
                linha += ' ' + p[:espaco - 1]
                linhas.append(linha)
                p     = p[espaco - 1:]
                linha = ''
            else:
                linhas.append(p[:cols])
                p = p[cols:]
        teste = (linha + ' ' + p).strip() if linha else p
        if len(teste) <= cols:
            linha = teste
        else:
            linhas.append(linha)
            linha = p
    if linha:
        linhas.append(linha)
    return linhas

def abrir_dialogo(estado, texto):
    estado.update({
        'dialogo_ativo':      True,
        'dialogo_texto':      texto,
        'dialogo_chars':      0.0,
        'dialogo_pagina_ini': 0,
        'dialogo_esperando':  False,
    })

def atualizar_dialogo(v, estado):
    if not estado['dialogo_ativo']:
        return False

    d          = estado
    linhas     = _dialogo_quebrar(d['dialogo_texto'], 28)
    ini        = d['dialogo_pagina_ini']
    fim        = ini + 3
    pag_linhas = linhas[ini:fim]
    chars_pag  = sum(len(l) for l in pag_linhas)
    pressionou = v.key_pressed(b"x")

    if d['dialogo_esperando']:
        if pressionou:
            if fim >= len(linhas):
                d['dialogo_ativo']     = False
                d['dialogo_esperando'] = False
            else:
                d['dialogo_pagina_ini'] = fim
                d['dialogo_chars']      = 0.0
                d['dialogo_esperando']  = False
        return True

    d['dialogo_chars'] = min(d['dialogo_chars'] + (d['dialogo_vel_rapida'] if pressionou else d['dialogo_vel']),
                             float(chars_pag))
    if d['dialogo_chars'] >= chars_pag:
        d['dialogo_chars']     = float(chars_pag)
        d['dialogo_esperando'] = True

    return True

def desenhar_dialogo(v, estado, box_sid, font_sid):
    if not estado['dialogo_ativo']:
        return

    d          = estado
    linhas     = _dialogo_quebrar(d['dialogo_texto'], 28)
    pag_linhas = linhas[d['dialogo_pagina_ini']: d['dialogo_pagina_ini'] + 3]
    chars_rev  = int(d['dialogo_chars'])

    texto_visivel = []
    restante = chars_rev
    for linha in pag_linhas:
        if restante <= 0:
            texto_visivel.append('')
        elif restante >= len(linha):
            texto_visivel.append(linha)
            restante -= len(linha)
        else:
            texto_visivel.append(linha[:restante])
            restante = 0

    BOX_H = 52
    SCR_W = getattr(v, 'render_w', SCREEN_W)
    SCR_H = getattr(v, 'render_h', SCREEN_H)
    v.draw_text_box(x=0, y=184, box_w=364, box_h=60,
                    title="", content='\n'.join(texto_visivel),
                    box_sid=box_sid, box_tw=8, box_th=8,
                    font_sid=font_sid, font_w=8, font_h=8)

    if d['dialogo_esperando'] and int(time.time() * 4) % 2 == 0:
        v.draw_text(SCR_W - 16, SCR_H - 14, "+", font_sid=font_sid, font_w=8, font_h=8)

def desenhar_npcs(v, todos_npcs, nome_mapa_atual, cam_x, cam_y):
    TILE_W = TILE_H = 16
    for npc in todos_npcs.values():
        if npc.mapa_atual != nome_mapa_atual:
            continue
        sx = npc.pixel_x - cam_x
        sy = npc.pixel_y - cam_y
        if sx + TILE_W < 0 or sx > SCREEN_W or sy + TILE_H < 0 or sy > SCREEN_H:
            continue
        if npc.sprite_id is None:
            continue

        col, lin, flip = npc._col_sprite()
        oid = getattr(npc, "oid", None)
        if oid is not None:
            v.set_object_sprite(oid, npc.sprite_id)
            v.set_object_tile(oid, col, lin)
            v.set_object_pos(oid, sx, sy)
            v.set_object_flip(oid, 1 if flip else 0, 0)
        else:
            sid_flip = getattr(npc, "sprite_id_flip", None)
            if flip and sid_flip is not None:
                v.draw_sprite_part(sid_flip, sx, sy, col * TILE_W, lin * TILE_H, TILE_W, TILE_H)
            else:
                v.draw_sprite_part(npc.sprite_id, sx, sy, col * TILE_W, lin * TILE_H, TILE_W, TILE_H)

_MAX_AMIZADE  = 2500
_CORACOES_MAX = 10


def processar_final_de_semana(todos_npcs):
    for npc in todos_npcs.values():
        if not npc.conversou_esta_semana:
            npc.afeto -= 25
        npc.conversou_esta_semana = False
        npc.presentes_semana      = 0
        while npc.afeto >= 255:
            npc.nivel_amizade += 1
            npc.afeto         -= 255
        if npc.afeto < 0:
            npc.afeto = 0

def _barra_amizade(pontos):
    return _barra_coracoes(pontos, _MAX_AMIZADE, _CORACOES_MAX)

def inicializar_estado_social():
    return {
        'mostrar_social':    False,
        'social_cursor':     0,
        'social_scroll':     0,
        'social_aba':        0,
        'gosto_cursor':      0,
        'gosto_ativo':       False,
        'gosto_scroll':      0,
        'mostrar_missoes':   False,
        'missoes_cursor':    0,
        'missoes_scroll':    0,
        'missoes_desc_scroll': 0,
        'missao_dialogo':        False,
        'missao_dialogo_npc':    None,
        'missao_dialogo_obj':    None,
        'missao_dialogo_cursor': 0,
        'entrega_dialogo':       False,
        'entrega_dialogo_npc':   None,
        'entrega_dialogo_obj':   None,
    }

def _missoes_aceitas_npc(npc):
    return [m for m in npc.missoes if m.id in npc.missoes_aceitas]

def _coletar_missoes_ativas(todos_npcs):
    return [
        (npc, m)
        for npc in todos_npcs.values()
        for m in npc.missoes
        if m.id in npc.missoes_aceitas and m.id not in npc.missoes_concluidas
    ]

def _coletar_missoes_disponiveis(jogador, todos_npcs):
    return [
        (npc, m)
        for npc in todos_npcs.values()
        for m in npc.missoes
        if m.id not in npc.missoes_concluidas and m.disponivel(jogador.dia_atual, jogador.estacao_atual)
    ]

def _barra_coracoes(pontos, max_p=2500, total=10):
    cheios = min(int(pontos / (max_p / total)), total)
    return "♥" * cheios + "♡" * (total - cheios)

def _status_missao_progresso(jogador, missao):
    tem  = jogador.invetario.get(missao.item_requerido, 0)
    prog = min(tem, missao.quantidade)
    return f"[{'#' * prog + '.' * (missao.quantidade - prog)}] {prog}/{missao.quantidade}"

ESTACOES_ABREV = {"Primavera": "Pri", "Verao": "Ver", "Outono": "Out", "Inverno": "Inv"}

def _prazo_missao(missao):
    if missao.dia_fim is None:
        return "Sem prazo"
    return f"{ESTACOES_ABREV.get(missao.estacao_fim, missao.estacao_fim[:3])} {missao.dia_fim}"

def processar_dialogo_missao(v, estado_social, jogador):
    es = estado_social
    if not es['missao_dialogo']:
        return False

    if v.key_pressed(b"left") or v.key_pressed(b"up"):
        es['missao_dialogo_cursor'] = 0
    elif v.key_pressed(b"right") or v.key_pressed(b"down"):
        es['missao_dialogo_cursor'] = 1

    if v.key_pressed(b"z"):
        if es['missao_dialogo_cursor'] == 0:
            npc    = es['missao_dialogo_npc']
            missao = es['missao_dialogo_obj']
            if missao.id not in npc.missoes_aceitas:
                npc.missoes_aceitas.append(missao.id)
        es['missao_dialogo']     = False
        es['missao_dialogo_npc'] = None
        es['missao_dialogo_obj'] = None
        return False

    if v.key_pressed(b"x"):
        es['missao_dialogo'] = False
        return False

    return True

def desenhar_dialogo_missao(v, estado_social, box_sid, font_sid):
    es = estado_social
    if not es['missao_dialogo']:
        return
    npc    = es['missao_dialogo_npc']
    missao = es['missao_dialogo_obj']
    cursor = es['missao_dialogo_cursor']

    conteudo = (
        f"{missao.dialogo_pedido}\n\n------------------------\n"
        f"Item:       {missao.item_requerido} x{missao.quantidade}\n"
        f"Recompensa: {missao.recompensa_gold}G  +{missao.recompensa_afeto} afeto\n"
        f"Prazo:      {_prazo_missao(missao)}\n------------------------\n"
        f"{'-> ' if cursor == 0 else '   '}Aceitar   {'-> ' if cursor == 1 else '   '}Recusar\n"
        f"[Esq/Dir] Escolher  [Z] OK  [X] Fechar"
    )
    SCR_W = getattr(v, 'render_w', SCREEN_W)
    SCR_H = getattr(v, 'render_h', SCREEN_H)
    PAD   = 10
    v.draw_text_box(x=PAD, y=PAD, box_w=SCR_W - PAD * 2, box_h=SCR_H - PAD * 2,
                    title=f"Missao de {npc.nome}", content=conteudo,
                    box_sid=box_sid, box_tw=8, box_th=8,
                    font_sid=font_sid, font_w=8, font_h=8, line_spacing=1)

def processar_dialogo_entrega(v, estado_social, jogador):
    es = estado_social
    if not es['entrega_dialogo']:
        return False

    if v.key_pressed(b"z") or v.key_pressed(b"x"):
        if v.key_pressed(b"z"):
            _concluir_missao(jogador, es['entrega_dialogo_npc'], es['entrega_dialogo_obj'])
        es['entrega_dialogo']     = False
        es['entrega_dialogo_npc'] = None
        es['entrega_dialogo_obj'] = None
        return False

    return True

def _concluir_missao(jogador, npc, missao):
    jogador.remover_item(missao.item_requerido, missao.quantidade)
    jogador.gold += missao.recompensa_gold
    jogador.amizades[npc.nome] = max(0, jogador.amizades.get(npc.nome, 0) + missao.recompensa_afeto)
    npc.missoes_concluidas.append(missao.id)
    if missao.id in npc.missoes_aceitas:
        npc.missoes_aceitas.remove(missao.id)
    npc.missao_ativa = None

def desenhar_dialogo_entrega(v, estado_social, jogador, box_sid, font_sid):
    es = estado_social
    if not es['entrega_dialogo']:
        return
    npc    = es['entrega_dialogo_npc']
    missao = es['entrega_dialogo_obj']
    conteudo = (
        f"{npc.nome}: Você trouxe os {missao.item_requerido}!\nMuito obrigado!\n\n"
        f"------------------------\nEntregando: {missao.item_requerido} x{missao.quantidade}\n"
        f"Recompensa: +{missao.recompensa_gold}G  +{missao.recompensa_afeto} afeto\n"
        f"------------------------\n[Z] Entregar   [X] Cancelar"
    )
    SCR_W = getattr(v, 'render_w', SCREEN_W)
    SCR_H = getattr(v, 'render_h', SCREEN_H)
    PAD   = 10
    v.draw_text_box(x=PAD, y=PAD, box_w=SCR_W - PAD * 2, box_h=SCR_H - PAD * 2,
                    title="Entrega de Missao", content=conteudo,
                    box_sid=box_sid, box_tw=8, box_th=8,
                    font_sid=font_sid, font_w=8, font_h=8, line_spacing=1)

_NPC_VIS = 5

def _montar_lista_gostos(npc):
    resultado = []
    for nome in npc.gostos:
        resultado.append((nome, "Adora", (220, 70, 100)))
    for nome in npc.bons:
        resultado.append((nome, "Gosta", (70, 190, 90)))
    for nome in npc.desgostos:
        resultado.append((nome, "Odeia", (100, 110, 220)))
    return resultado

def _sprite_representante_categoria(categoria, todos_itens_ref):
    for nome, obj in todos_itens_ref.items():
        if obj.tipo_presente == categoria:
            return nome
    return None

def processar_input_social(v, estado_social, todos_npcs):
    """
    Navega o menu Social estilo Stardew Valley.

    Navegação geral (quando gosto_ativo=False):
      Cima/Baixo   → troca aba (Perfil / Gostos / Presentes)
      Esq/Dir      → troca NPC na lista esquerda
      Enter        → na aba Gostos, ATIVA o cursor da grade
      X / Space    → fecha o menu social

    Aba Gostos com grade ATIVA (gosto_ativo=True):
      ←→↑↓        → move cursor no grid de slots
      Z            → abre tooltip do item selecionado
      Enter        → DESATIVA o cursor da grade (volta à navegação normal)
      X            → DESATIVA o cursor da grade (volta à navegação normal)

    Tooltip aberto (gosto_tooltip=True):
      Z / Enter / X → fecha tooltip
    """
    from itens import todos_itens as _todos_itens

    es    = estado_social
    lista = list(todos_npcs.values())
    n     = len(lista)

    # Garante campos novos (compatibilidade com saves antigos)
    es.setdefault('gosto_cursor',  0)
    es.setdefault('gosto_ativo',   False)
    es.setdefault('gosto_tooltip', False)

    if n == 0:
        if v.key_pressed(b"x") or v.key_pressed(b"space"):
            es['mostrar_social'] = False
            return False
        return True

    aba     = es.get('social_aba', 0)
    npc_sel = lista[es['social_cursor']]

    # Lista de gostos descobertos para saber o total
    descobertos   = getattr(npc_sel, "gostos_descobertos", {})
    lista_desc    = list(descobertos.keys())
    total_g       = len(lista_desc)

    # Cálculo de colunas da grade (mesmo usado no desenho)
    PW_EST        = SCREEN_W - (4 + 88 + 2) - 18
    SLOT, GAP_SL  = 14, 2
    COLS          = max(1, PW_EST // (SLOT + GAP_SL))

    # ─────────────────────────────────────────────────────────────────────
    # PRIORIDADE 1: Tooltip aberto → qualquer tecla fecha
    # ─────────────────────────────────────────────────────────────────────
    if es['gosto_tooltip']:
        if v.key_pressed(b"z") or v.key_pressed(b"return") or v.key_pressed(b"x"):
            es['gosto_tooltip'] = False
        return True

    # ─────────────────────────────────────────────────────────────────────
    # PRIORIDADE 2: Grade de gostos ATIVA → navega itens
    # ─────────────────────────────────────────────────────────────────────
    if aba == 1 and es['gosto_ativo']:

        # Enter → DESATIVA a grade, volta à navegação normal
        if v.key_pressed(b"return"):
            es['gosto_ativo'] = False
            return True

        # X → também desativa a grade (sem fechar o menu social)
        if v.key_pressed(b"x"):
            es['gosto_ativo'] = False
            return True

        # Z → abre tooltip do item sob o cursor
        if v.key_pressed(b"z"):
            if total_g > 0:
                es['gosto_tooltip'] = True
            return True

        # Setas → move cursor na grade
        if v.key_pressed(b"up"):
            es['gosto_cursor'] = max(0, es['gosto_cursor'] - COLS)
        elif v.key_pressed(b"down"):
            es['gosto_cursor'] = min(max(0, total_g - 1), es['gosto_cursor'] + COLS)
        elif v.key_pressed(b"left"):
            es['gosto_cursor'] = max(0, es['gosto_cursor'] - 1)
        elif v.key_pressed(b"right"):
            es['gosto_cursor'] = min(max(0, total_g - 1), es['gosto_cursor'] + 1)

        return True

    # ─────────────────────────────────────────────────────────────────────
    # PRIORIDADE 3: Navegação normal (aba / NPC / fechar)
    # ─────────────────────────────────────────────────────────────────────

    # X / Space → fecha o menu social
    if v.key_pressed(b"x") or v.key_pressed(b"space"):
        es['mostrar_social'] = False
        return False

    # Cima/Baixo → troca aba
    if v.key_pressed(b"up"):
        es['social_aba'] = (aba - 1) % 3
    elif v.key_pressed(b"down"):
        es['social_aba'] = (aba + 1) % 3

    # Esq/Dir → troca NPC
    if v.key_pressed(b"left"):
        es['social_cursor'] = (es['social_cursor'] - 1) % n
        # Ajusta scroll
        c = es['social_cursor']
        if c < es['social_scroll']:
            es['social_scroll'] = c
        elif c == n - 1:
            es['social_scroll'] = max(0, n - _NPC_VIS)
        # Reset cursor de gostos ao trocar NPC
        es['gosto_cursor'] = 0
        es['gosto_ativo']  = False
    elif v.key_pressed(b"right"):
        es['social_cursor'] = (es['social_cursor'] + 1) % n
        c = es['social_cursor']
        if c >= es['social_scroll'] + _NPC_VIS:
            es['social_scroll'] = c - _NPC_VIS + 1
        elif c == 0:
            es['social_scroll'] = 0
        es['gosto_cursor'] = 0
        es['gosto_ativo']  = False

    # Enter na aba Gostos → ATIVA a grade de itens
    if v.key_pressed(b"return"):
        if es.get('social_aba', 0) == 1 and total_g > 0:
            es['gosto_ativo']  = True
            es['gosto_cursor'] = 0

    return True

def desenhar_menu_social(v, jogador, estado_social, todos_npcs, box_sid, font_sid,itens_sprite_ids=None):
    from itens import todos_itens as _todos_itens

    es    = estado_social
    lista = list(todos_npcs.values())
    n     = len(lista)

    FW, FH  = 8, 8
    MX, MY  = 42, 4
    GAP     = 2
    LISTA_W = 88
    PERF_X  = MX + LISTA_W + GAP
    PERF_W  = 190
    BH      = SCREEN_H - MY * 2         # 236
    # margem interna das caixas: box_tw=8 de cada lado
    _PAD = 9   # 8px borda + 1px gap interno

    # ── Sem NPCs ─────────────────────────────────────────────────────────────
    if n == 0:
        v.draw_text_box(x=42, y=4, box_w=280, box_h=236,
                        title="Social",
                        content="Nenhum personagem\nencontrado.\n\n[X] Fechar",
                        box_sid=box_sid, box_tw=8, box_th=8,
                        font_sid=font_sid, font_w=FW, font_h=FH, line_spacing=1)
        return

    cursor = max(0, min(es['social_cursor'], n - 1))
    scroll = max(0, min(es['social_scroll'], max(0, n - _NPC_VIS)))
    es['social_cursor'] = cursor
    es['social_scroll'] = scroll
    aba = es.get('social_aba', 0)

    # ════════════════════════════════════════════════════════════════════════
    # PAINEL ESQUERDO — borda via draw_text_box, conteúdo via draw_text
    # ════════════════════════════════════════════════════════════════════════
    v.draw_text_box(x=MX, y=MY, box_w=LISTA_W, box_h=BH,
                    title="Social", content="",
                    box_sid=box_sid, box_tw=8, box_th=8,
                    font_sid=font_sid, font_w=FW, font_h=FH)

    # Origem da área interna:
    #   X = MX + box_tw(8) + 1 gap = MX + 9
    #   Y = MY + box_th(8) + FH(título) + line_spacing(1) + 2 gap = MY + 19
    LX     = MX + _PAD
    LY     = MY + 8 + FH + 3
    LW     = LISTA_W - _PAD * 2
    ITEM_H = 18   # FH(nome=8) + coracoes(6) + gap(4)

    # Seta ▲ scroll (draw_rect)
    if scroll > 0:
        cx = LX + LW // 2
        v.draw_rect(cx,     LY - 7, 1, 1, 200, 200, 200)
        v.draw_rect(cx - 1, LY - 6, 3, 1, 200, 200, 200)
        v.draw_rect(cx - 2, LY - 5, 5, 1, 200, 200, 200)

    for i in range(scroll, min(scroll + _NPC_VIS, n)):
        npc    = lista[i]
        pontos = jogador.amizades.get(npc.nome, 0)
        cheios = min(int(pontos / (_MAX_AMIZADE / _CORACOES_MAX)), _CORACOES_MAX)
        iy     = LY + (i - scroll) * ITEM_H
        sel    = (i == cursor)

        # Nome NPC (draw_text — texto inline, sem padding extra)
        prefixo = ">" if sel else " "
        v.draw_text(LX, iy, f"{prefixo}{npc.nome[:8]}",
                    font_sid=font_sid, font_w=FW, font_h=FH)

        # Corações 5×5 pixel-art (draw_rect)
        COR_W, COR_GAP = 5, 2
        coracoes_vis = min(cheios, 5)
        for ci in range(5):
            cx = LX + ci * (COR_W + COR_GAP)
            cy = iy + FH + 2
            if ci < coracoes_vis:
                v.draw_rect(cx + 1, cy,     3, 1, 255, 130, 150)
                v.draw_rect(cx,     cy + 1, 5, 2, 220,  50,  80)
                v.draw_rect(cx + 1, cy + 3, 3, 1, 200,  40,  60)
                v.draw_rect(cx + 2, cy + 4, 1, 1, 180,  30,  50)
            else:
                v.draw_rect(cx + 1, cy,     3, 1,  80,  80,  80)
                v.draw_rect(cx,     cy + 1, 5, 2,  60,  60,  60)
                v.draw_rect(cx + 1, cy + 3, 3, 1,  55,  55,  55)
                v.draw_rect(cx + 2, cy + 4, 1, 1,  50,  50,  50)

    # Seta ▼ scroll (draw_rect)
    if scroll + _NPC_VIS < n:
        by = LY + _NPC_VIS * ITEM_H + 1
        cx = LX + LW // 2

    # ════════════════════════════════════════════════════════════════════════
    # PAINEL DIREITO — borda via draw_text_box, conteúdo via draw_text
    # ════════════════════════════════════════════════════════════════════════
    npc_sel = lista[cursor]
    pontos  = jogador.amizades.get(npc_sel.nome, 0)
    cheios  = min(int(pontos / (_MAX_AMIZADE / _CORACOES_MAX)), _CORACOES_MAX)
    ABAS_NOMES = ["Perfil", "Gosto", "Presente"]

    v.draw_text_box(x=PERF_X, y=MY, box_w=PERF_W, box_h=BH,
                    title="", content="",
                    box_sid=box_sid, box_tw=8, box_th=8,
                    font_sid=font_sid, font_w=FW, font_h=FH)

    PX = PERF_X + _PAD
    PW = PERF_W - _PAD * 2

    # ── Abas verticais — cada aba em sua própria linha (draw_rect fundo + draw_text rótulo) ──
    ABA_H   = FH + 4          # altura de cada aba
    ABA_GAP = 1               # espaço entre abas
    AY_ABA  = 10 # começa abaixo do título do painel

    for ai, nome_aba in enumerate(ABAS_NOMES):
        ay = AY_ABA + ai * (ABA_H + ABA_GAP)
        
        # Prefixo ">" na aba ativa
        prefixo = ">" if ai == aba else " "
        v.draw_text(PX + 2, ay + 2, f"{prefixo}{nome_aba}",
                    font_sid=font_sid, font_w=FW, font_h=FH)

    # Início do conteúdo abaixo das abas
    CY = AY_ABA + len(ABAS_NOMES) * (ABA_H + ABA_GAP) + 4

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 0 — PERFIL
    # ─────────────────────────────────────────────────────────────────────────
    if aba == 0:
        # Barra de corações (draw_rect)
        _desenhar_barra_coracoes(v, PX, CY, pontos, _MAX_AMIZADE, total=10, gap=1)
        CY += 10

        # Pontos (draw_text)
        v.draw_text(PX, CY, f"Amizade: {pontos}/{_MAX_AMIZADE}",
                    font_sid=font_sid, font_w=FW, font_h=FH)
        CY += FH + 3

        # Separador pontilhado (draw_rect)
        for sx in range(0, PW, 4):
            v.draw_rect(PX + sx, CY, 2, 1, 120, 100, 50)
        CY += 4

        # Aniversário — ícone bolo (draw_rect) + texto (draw_text)
        ests = ["Primavera", "Verao", "Outono", "Inverno"]
        if npc_sel.aniversario:
            est_i, dia = npc_sel.aniversario
            aniv_str = f"{ests[est_i % 4][:3]} {dia:02d}"
        else:
            aniv_str = "???"
        v.draw_rect(PX,     CY + 2, 8, 5, 200, 150, 80)
        v.draw_rect(PX + 3, CY,     2, 3, 230, 220, 80)
        v.draw_rect(PX + 3, CY - 1, 2, 1, 255, 200, 60)
        v.draw_text(PX + 10, CY, f"Aniv: {aniv_str}",
                    font_sid=font_sid, font_w=FW, font_h=FH)
        CY += FH + 4

        # Separador (draw_rect)
        for sx in range(0, PW, 4):
            v.draw_rect(PX + sx, CY, 2, 1, 120, 100, 50)
        CY += 4

        # Gênero / estado civil — ícone (draw_rect) + texto (draw_text)
        estado_civil = "Solteiro(a)" if npc_sel.solteiro else "Casado(a)"
        gc = (180, 120, 180) if npc_sel.genero and npc_sel.genero.startswith("F") \
             else (120, 160, 220)
        v.draw_rect(PX,     CY + 1, 6, 6, *gc)
        v.draw_rect(PX + 1, CY + 2, 4, 4, gc[0] // 2, gc[1] // 2, gc[2] // 2)
        v.draw_text(PX + 9, CY, f"{npc_sel.genero[:1]}  {estado_civil[:11]}",
                    font_sid=font_sid, font_w=FW, font_h=FH)
        CY += FH + 4

        # Separador (draw_rect)
        for sx in range(0, PW, 4):
            v.draw_rect(PX + sx, CY, 2, 1, 120, 100, 50)
        CY += 4

        # Missões — ícone pergaminho (draw_rect) + texto (draw_text)
        miss_ativas = [m for m in npc_sel.missoes
                       if m.id in npc_sel.missoes_aceitas
                       and m.id not in npc_sel.missoes_concluidas]
        miss_conc = len(npc_sel.missoes_concluidas)
        v.draw_rect(PX,     CY,     7, 8, 210, 190, 130)
        v.draw_rect(PX + 1, CY + 2, 5, 1, 140, 120, 80)
        v.draw_rect(PX + 1, CY + 4, 4, 1, 140, 120, 80)
        v.draw_text(PX + 9, CY, f"Missoes: {miss_conc} ok",
                    font_sid=font_sid, font_w=FW, font_h=FH)
        CY += FH + 2
        if miss_ativas:
            # Largura interna disponível (sem o ícone de 9px)
            _max_c  = (PW - 9) // FW
            _id_txt = miss_ativas[0].id
            # Quebra em 2 linhas se necessário
            _linha1 = _id_txt[:_max_c]
            _linha2 = _id_txt[_max_c: _max_c * 2]
            v.draw_text(PX + 9, CY, f"Ativa:", font_sid=font_sid, font_w=FW, font_h=FH)
            v.draw_text(PX + 9, CY+8, f"{_linha1}\n", font_sid=font_sid, font_w=FW, font_h=FH)
            CY += FH + 1
            if _linha2:
                v.draw_text(PX + 9, CY, _linha2,
                            font_sid=font_sid, font_w=FW, font_h=FH)
                CY += FH + 1

        # Rodapé 2 linhas (draw_rect sep + draw_text controles)
        rod_y = MY + BH - FH * 2 - 7
        v.draw_rect(PX, rod_y - 2, PW, 1, 180, 155, 60)
        v.draw_text(PX, rod_y,          "</> Aba   ^v NPC",
                    font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(PX, rod_y + FH + 1, "X Fechar",
                    font_sid=font_sid, font_w=FW, font_h=FH)

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 1 — GOSTOS  (descobertos ao presentear)
    # ─────────────────────────────────────────────────────────────────────────
    elif aba == 1:
        # gostos_descobertos = {nome_item: "Adora"|"Gosta"|"Odeia"}
        descobertos = getattr(npc_sel, "gostos_descobertos", {})

        SLOT     = 14
        GAP_SL   = 2
        COLS     = max(1, PW // (SLOT + GAP_SL))
        rod_y    = MY + BH - FH * 2 - 7
        AREA_BOT = rod_y - 4

        _COR = {
            "Adora": (220,  70, 100),
            "Gosta": ( 70, 190,  90),
            "Odeia": (100, 110, 220),
        }

        if not descobertos:
            # Ainda nenhum presente dado — exibe slots ? e instrução
            for si in range(COLS):
                sx = PX + si * (SLOT + GAP_SL)
                v.draw_rect(sx, CY, SLOT, SLOT, 22, 20, 18)
                v.draw_rect(sx,        CY,        SLOT, 1,  55, 50, 45)
                v.draw_rect(sx,        CY,        1, SLOT,  55, 50, 45)
                v.draw_rect(sx+SLOT-1, CY,        1, SLOT,  55, 50, 45)
                v.draw_rect(sx,        CY+SLOT-1, SLOT, 1,  55, 50, 45)
                v.draw_text(sx + (SLOT - FW) // 2, CY + (SLOT - FH) // 2,
                            "?", font_sid=font_sid, font_w=FW, font_h=FH)
            CY += SLOT + GAP_SL + 4
            for msg in ("Presenteie o NPC", "para descobrir!"):
                v.draw_text(PX + (PW - len(msg) * FW) // 2, CY, msg,
                            font_sid=font_sid, font_w=FW, font_h=FH)
                CY += FH + 2
        else:
            # Agrupa por reação na ordem Adora → Gosta → Odeia
            grupos_desc = {"Adora": [], "Gosta": [], "Odeia": []}
            for nome_it, reac in descobertos.items():
                grupos_desc.get(reac, grupos_desc["Gosta"]).append(nome_it)

            for reac_label in ("Adora", "Gosta", "Odeia"):
                itens_grupo = grupos_desc[reac_label]
                if not itens_grupo:
                    continue
                if CY + FH + 4 > AREA_BOT:
                    break

                cor = _COR[reac_label]

                # Faixa de título do grupo
                v.draw_rect(PX - 1, CY, PW + 2, FH + 3,
                            cor[0] // 4, cor[1] // 4, cor[2] // 4)
                v.draw_rect(PX - 1, CY, PW + 2, 1, *cor)
                v.draw_rect(PX + 1, CY + 2, 4, 4, *cor)   # bolinha colorida
                v.draw_text(PX + 7, CY + 1, reac_label,
                            font_sid=font_sid, font_w=FW, font_h=FH)
                CY += FH + 4

                n_itens  = len(itens_grupo)
                max_rows = max(1, (AREA_BOT - CY) // (SLOT + GAP_SL))
                itens_vis = itens_grupo[: COLS * max_rows]
                linhas   = (len(itens_vis) + COLS - 1) // COLS

                for idx, nome_it in enumerate(itens_vis):
                    col_i = idx % COLS
                    row_i = idx // COLS
                    sx    = PX + col_i * (SLOT + GAP_SL)
                    sy    = CY + row_i * (SLOT + GAP_SL)

                    # Fundo com tom da reação
                    v.draw_rect(sx, sy, SLOT, SLOT,
                                cor[0] // 6, cor[1] // 6, cor[2] // 6)
                    # Borda colorida
                    v.draw_rect(sx,        sy,        SLOT, 1, *cor)
                    v.draw_rect(sx,        sy,        1, SLOT, *cor)
                    v.draw_rect(sx+SLOT-1, sy,        1, SLOT, *cor)
                    v.draw_rect(sx,        sy+SLOT-1, SLOT, 1, *cor)

                    # Sprite do item
                    if nome_it in _todos_itens and itens_sprite_ids is not None:
                        obj = _todos_itens[nome_it]
                        sid = itens_sprite_ids.get(obj.sprite)
                        if sid is not None:
                            rx, ry, iw, ih = obj.get_sprite_rect()
                            ox = sx + (SLOT - iw) // 2
                            oy = sy + (SLOT - ih) // 2
                            v.draw_sprite_part(sid, ox, oy, rx, ry, iw, ih)

                CY += linhas * (SLOT + GAP_SL) + 3

        # Rodapé
        v.draw_rect(PX, rod_y - 2, PW, 1, 180, 155, 60)
        v.draw_text(PX, rod_y,          "^v Aba  </> NPC",
                    font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(PX, rod_y + FH + 1, "X Fechar",
                    font_sid=font_sid, font_w=FW, font_h=FH)

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 2 — PRESENTES  (presentes dados esta semana)
    # ─────────────────────────────────────────────────────────────────────────
    else:
        rod_y  = MY + BH - FH * 2 - 7
        SLOT   = 16
        GAP_SL = 3
        COLS   = max(1, PW // (SLOT + GAP_SL))

        presentes_semana = getattr(npc_sel, 'presentes_semana', 0)
        LIMITE_SEMANA    = 2
        restam           = max(0, LIMITE_SEMANA - presentes_semana)

        # ── Título ───────────────────────────────────────────────────────────
        v.draw_rect(PX - 1, CY, PW + 2, FH + 3, 50, 38, 15)
        v.draw_rect(PX - 1, CY, PW + 2, 1, 200, 170, 60)
        # ícone presentinho pixel-art
        v.draw_rect(PX + 1, CY + 1, 6, 6, 180,  60,  60)
        v.draw_rect(PX + 1, CY + 1, 6, 2, 220, 100, 100)
        v.draw_rect(PX + 3, CY,     2, 7, 230, 210,  60)
        v.draw_rect(PX + 1, CY + 3, 6, 1, 230, 210,  60)
        v.draw_text(PX + 10, CY + 1, "Esta semana",
                    font_sid=font_sid, font_w=FW, font_h=FH)
        CY += FH + 4

        # ── Ícones de presentes restantes ─────────────────────────────────────
        for pi in range(LIMITE_SEMANA):
            px_cor = PX + pi * 11
            dado   = pi < presentes_semana
            if dado:
                v.draw_rect(px_cor + 1, CY,     4, 4, 200,  60,  80)
                v.draw_rect(px_cor + 1, CY,     4, 2, 230, 100, 120)
                v.draw_rect(px_cor + 2, CY - 1, 2, 5, 230, 200,  60)
                v.draw_rect(px_cor + 1, CY + 2, 4, 1, 230, 200,  60)
            else:
                v.draw_rect(px_cor + 1, CY,     4, 4,  55,  50,  45)
                v.draw_rect(px_cor + 1, CY,     4, 1,  90,  85,  80)
                v.draw_rect(px_cor + 2, CY - 1, 2, 5,  90,  85,  80)
        lbl = f"+{restam} restam" if restam > 0 else "Limite!"
        cr  = (130, 220, 100) if restam > 0 else (220, 80, 80)
        v.draw_rect(PX + LIMITE_SEMANA * 11 + 2, CY,
                    len(lbl) * FW, FH, cr[0] // 4, cr[1] // 4, cr[2] // 4)
        v.draw_text(PX + LIMITE_SEMANA * 11 + 3, CY, lbl,
                    font_sid=font_sid, font_w=FW, font_h=FH)
        CY += 9

        # separador
        for sx in range(0, PW, 4):
            v.draw_rect(PX + sx, CY, 2, 1, 100, 85, 40)
        CY += 4

        # ── Histórico total de itens dados ────────────────────────────────────
        itens_dados  = getattr(npc_sel, 'itens_dados', {})
        dados_sorted = sorted(itens_dados.items(), key=lambda kv: -kv[1])

        if not dados_sorted:
            # ícone caixinha vazia
            v.draw_rect(PX + PW // 2 - 8, CY + 4,  16, 14, 30, 28, 22)
            v.draw_rect(PX + PW // 2 - 8, CY + 4,  16,  6, 45, 40, 32)
            v.draw_rect(PX + PW // 2 - 3, CY + 2,   6, 16, 55, 50, 30)
            v.draw_rect(PX + PW // 2 - 8, CY + 11,  16,  1, 55, 50, 30)
            msg = "Nenhum ainda"
            v.draw_text(PX + (PW - len(msg) * FW) // 2, CY + 22,
                        msg, font_sid=font_sid, font_w=FW, font_h=FH)
        else:
            SLOT_H   = SLOT + FH + GAP_SL + 2
            ROWS_VIS = max(1, (rod_y - CY - 4) // SLOT_H)

            for idx, (nome_it, qtd) in enumerate(dados_sorted[: COLS * ROWS_VIS]):
                col_i = idx % COLS
                row_i = idx // COLS
                ix    = PX + col_i * (SLOT + GAP_SL)
                iy    = CY + row_i * SLOT_H

                # slot
                v.draw_rect(ix, iy, SLOT, SLOT, 20, 18, 14)
                v.draw_rect(ix,        iy,        SLOT, 1,  70, 65, 50)
                v.draw_rect(ix,        iy,        1, SLOT,  70, 65, 50)
                v.draw_rect(ix+SLOT-1, iy,        1, SLOT,  70, 65, 50)
                v.draw_rect(ix,        iy+SLOT-1, SLOT, 1,  70, 65, 50)

                # sprite
                if nome_it in _todos_itens and itens_sprite_ids is not None:
                    obj = _todos_itens[nome_it]
                    sid = itens_sprite_ids.get(obj.sprite)
                    if sid is not None:
                        rx, ry, iw, ih = obj.get_sprite_rect()
                        ox = ix + (SLOT - iw) // 2
                        oy = iy + (SLOT - ih) // 2
                        v.draw_sprite_part(sid, ox, oy, rx, ry, iw, ih)

                # quantidade
                qtd_str = f"x{qtd}" if qtd < 100 else "x99+"
                v.draw_text(ix + (SLOT - len(qtd_str) * FW) // 2,
                            iy + SLOT + 1, qtd_str,
                            font_sid=font_sid, font_w=FW, font_h=FH)

        # Rodapé
        v.draw_rect(PX, rod_y - 2, PW, 1, 180, 155, 60)
        v.draw_text(PX, rod_y,          "^v Aba  </> NPC",
                    font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(PX, rod_y + FH + 1, "X Fechar",
                    font_sid=font_sid, font_w=FW, font_h=FH)

def _desenhar_coracao_pixel(v, cx, cy, cheio):
    r, g, b   = (220, 50, 80) if cheio else (60, 60, 60)
    hr, hg, hb = (255, 120, 140) if cheio else (r, g, b)
    mascara = [
        (0,1),(0,2),(0,4),(0,5),
        (1,0),(1,1),(1,2),(1,3),(1,4),(1,5),(1,6),
        (2,0),(2,1),(2,2),(2,3),(2,4),(2,5),(2,6),
        (3,1),(3,2),(3,3),(3,4),(3,5),
        (4,2),(4,3),(4,4),
        (5,3),
    ]
    for row, col in mascara:
        px = cx - 3 + col
        py = cy - 2 + row
        v.draw_rect(px, py, 1, 1, *(hr, hg, hb) if row == 0 and cheio else (r, g, b))

def _desenhar_barra_coracoes(v, x, y, pontos, max_p=2500, total=10, gap=2):
    cheios = min(int(pontos / (max_p / total)), total)
    for i in range(total):
        _desenhar_coracao_pixel(v, x + i * (7 + gap) + 3, y + 3, i < cheios)

def _desenhar_slot_item(v, x, y, nome_item, todos_itens_ref, itens_sprite_ids, destaque=False, tamanho=16):
    if destaque:
        v.draw_rect(x - 1, y - 1, tamanho + 2, tamanho + 2, 255, 220, 80)
        v.draw_rect(x, y, tamanho, tamanho, 30, 30, 30)
    else:
        v.draw_rect(x, y, tamanho, tamanho, 20, 20, 20)
        v.draw_rect(x, y, tamanho, 1, 80, 80, 80)
        v.draw_rect(x, y, 1, tamanho, 80, 80, 80)
        v.draw_rect(x + tamanho - 1, y, 1, tamanho, 80, 80, 80)
        v.draw_rect(x, y + tamanho - 1, tamanho, 1, 80, 80, 80)

    if nome_item and nome_item in todos_itens_ref and itens_sprite_ids is not None:
        obj = todos_itens_ref[nome_item]
        sid = itens_sprite_ids.get(obj.sprite)
        if sid is not None:
            rx, ry, iw, ih = obj.get_sprite_rect()
            v.draw_sprite_part(sid, x + (tamanho - iw) // 2, y + (tamanho - ih) // 2, rx, ry, iw, ih)

_MISS_VIS = 5

def processar_input_missoes(v, estado_social, jogador, todos_npcs):
    es     = estado_social
    if v.key_pressed(b"x") or v.key_pressed(b"space"):
        es['mostrar_missoes'] = False
        return False

    missoes = _coletar_missoes_ativas(todos_npcs)
    total   = len(missoes)
    es.setdefault('missoes_desc_scroll', 0)

    prev_cursor = es['missoes_cursor']

    if v.key_pressed(b"up"):
        es['missoes_cursor'] = max(0, es['missoes_cursor'] - 1)
        if es['missoes_cursor'] < es['missoes_scroll']:
            es['missoes_scroll'] = es['missoes_cursor']
    elif v.key_pressed(b"down"):
        es['missoes_cursor'] = min(max(0, total - 1), es['missoes_cursor'] + 1)
        if es['missoes_cursor'] >= es['missoes_scroll'] + _MISS_VIS:
            es['missoes_scroll'] = es['missoes_cursor'] - _MISS_VIS + 1

    if es['missoes_cursor'] != prev_cursor:
        es['missoes_desc_scroll'] = 0

    if v.key_pressed(b"z"):
        es['missoes_desc_scroll'] += 1
    elif v.key_pressed(b"c"):
        es['missoes_desc_scroll'] = max(0, es['missoes_desc_scroll'] - 1)

    return True

def _desenhar_barra_progresso(v, x, y, atual, maximo, largura, altura=4):
    v.draw_rect(x - 1, y - 1, largura + 2, altura + 2, 100, 100, 100)
    v.draw_rect(x, y, largura, altura, 30, 30, 30)
    if maximo <= 0:
        return
    ratio  = min(atual / maximo, 1.0)
    fill_w = max(0, int(largura * ratio))
    if fill_w == 0:
        return
    r, g, b = (60, 210, 80) if ratio >= 1.0 else (80, 200, 60) if ratio > 0.5 else (210, 180, 30) if ratio > 0.25 else (200, 50, 40)
    v.draw_rect(x, y, fill_w, altura, r, g, b)
    v.draw_rect(x, y, fill_w, 1, min(r + 60, 255), min(g + 60, 255), min(b + 60, 255))

def desenhar_menu_missoes(v, jogador, estado_social, todos_npcs, box_sid, font_sid, itens_sprite_ids=None):
    from itens import todos_itens as _todos_itens
    es      = estado_social
    missoes = _coletar_missoes_ativas(todos_npcs)
    total   = len(missoes)

    FW, FH  = 8, 8
    MX, MY  = 4, 4
    GAP     = 2
    LISTA_W = 139
    DET_X   = MX + LISTA_W + GAP
    DET_W   = 200
    BH      = SCREEN_H - MY * 2
    _PAD    = 9

    if total == 0:
        v.draw_text_box(x=42, y=4, box_w=280, box_h=236,
                        title="Missoes",
                        content="Nenhuma missao\nativa no momento.\n\nFale com os NPCs\npara receber\nmissoes!\n\n[X] Fechar",
                        box_sid=box_sid, box_tw=8, box_th=8,
                        font_sid=font_sid, font_w=FW, font_h=FH, line_spacing=1)
        return

    cursor = max(0, min(es['missoes_cursor'], total - 1))
    scroll = max(0, min(es['missoes_scroll'], max(0, total - _MISS_VIS)))
    es['missoes_cursor'] = cursor
    es['missoes_scroll'] = scroll
    es.setdefault('missoes_desc_scroll', 0)

    v.draw_text_box(x=MX, y=MY, box_w=LISTA_W, box_h=BH,
                    title="Missoes*", content="",
                    box_sid=box_sid, box_tw=8, box_th=8,
                    font_sid=font_sid, font_w=FW, font_h=FH)

    LX          = MX + _PAD
    LY          = MY + 8 + FH + 3
    LW          = LISTA_W - _PAD * 2
    MISS_ITEM_H = 22

    if scroll > 0:
        cx = LX + LW // 2
        v.draw_rect(cx, LY - 7, 1, 1, 200, 200, 200)
        v.draw_rect(cx - 1, LY - 6, 3, 1, 200, 200, 200)
        v.draw_rect(cx - 2, LY - 5, 5, 1, 200, 200, 200)

    for i in range(scroll, min(scroll + _MISS_VIS, total)):
        npc_m, m = missoes[i]
        iy = LY + (i - scroll) * MISS_ITEM_H
        v.draw_text(LX, iy, f"{'>' if i == cursor else ' '}{npc_m.nome[:(LW // FW) - 1]}",
                    font_sid=font_sid, font_w=FW, font_h=FH)

    if scroll + _MISS_VIS < total:
        by = LY + _MISS_VIS * MISS_ITEM_H + 1
        cx = LX + LW // 2
        v.draw_rect(cx - 2, by, 5, 1, 200, 200, 200)
        v.draw_rect(cx - 1, by + 1, 3, 1, 200, 200, 200)
        v.draw_rect(cx, by + 2, 1, 1, 200, 200, 200)

    npc_sel, miss_sel = missoes[cursor]
    tem      = jogador.invetario.get(miss_sel.item_requerido, 0)
    prog     = min(tem, miss_sel.quantidade)
    completa = prog >= miss_sel.quantidade

    v.draw_text_box(x=DET_X, y=MY, box_w=DET_W, box_h=BH,
                    title="", content="",
                    box_sid=box_sid, box_tw=8, box_th=8,
                    font_sid=font_sid, font_w=FW, font_h=FH)

    PX   = DET_X + _PAD
    PY   = MY + 8 + FH + 3
    PW   = DET_W - _PAD * 2
    SLOT = 24
    _desenhar_slot_item(v, PX, PY, miss_sel.item_requerido, _todos_itens, itens_sprite_ids,
                        destaque=completa, tamanho=SLOT)

    TX       = PX + SLOT + 5
    TW       = PW - SLOT - 5
    ty0      = max(PY, PY + (SLOT - FH * 2 - 3) // 2)
    max_chars = TW // FW
    v.draw_text(TX, ty0, miss_sel.item_requerido[:max_chars], font_sid=font_sid, font_w=FW, font_h=FH)
    v.draw_text(TX, ty0 + FH + 3, f"x{miss_sel.quantidade}", font_sid=font_sid, font_w=FW, font_h=FH)

    CY = PY + SLOT + 4
    v.draw_text(PX, CY, f"{prog}/{miss_sel.quantidade}", font_sid=font_sid, font_w=FW, font_h=FH)
    CY += FH + 2

    if completa:
        v.draw_text(PX + 2, CY + 2, "PRONTO! Entregue ao NPC", font_sid=font_sid, font_w=FW, font_h=FH)
    else:
        v.draw_text(PX, CY, f"Faltam: {miss_sel.quantidade - prog}", font_sid=font_sid, font_w=FW, font_h=FH)
    CY += FH + 4

    for sx in range(0, PW, 4):
        v.draw_rect(PX + sx, CY, 2, 1, 110, 90, 45)
    CY += 4

    rod_y      = MY + BH - FH * 2 - 8
    AREA_TOPO  = CY
    INFO_H     = 4 + FH * 2 + 6 + 4 + FH + 2 + FH + 2 + FH + 3
    DESC_BOT   = rod_y - INFO_H - 4
    LINHAS_VIS = max(1, (DESC_BOT - AREA_TOPO) // (FH + 1))

    desc     = miss_sel.descricao or "Sem descricao."
    chars_pl = max(1, PW // FW)

    def _wrap(texto, largura):
        linhas   = []
        linha    = ""
        for p in texto.split():
            if not linha:
                linha = p
            elif len(linha) + 1 + len(p) <= largura:
                linha += " " + p
            else:
                linhas.append(linha)
                linha = p
        if linha:
            linhas.append(linha)
        return linhas or [""]

    linhas_desc  = _wrap(desc, chars_pl)
    total_linhas = len(linhas_desc)

    max_scroll_desc = max(0, total_linhas - LINHAS_VIS)
    es['missoes_desc_scroll'] = max(0, min(es['missoes_desc_scroll'], max_scroll_desc))
    dscroll = es['missoes_desc_scroll']

    if dscroll > 0:
        cx = PX + PW // 2
        v.draw_rect(cx, AREA_TOPO, 1, 1, 180, 160, 80)
        v.draw_rect(cx - 1, AREA_TOPO + 1, 3, 1, 180, 160, 80)
        v.draw_rect(cx - 2, AREA_TOPO + 2, 5, 1, 180, 160, 80)

    for li, linha in enumerate(linhas_desc[dscroll: dscroll + LINHAS_VIS]):
        v.draw_text(PX, AREA_TOPO + li * (FH + 1), linha, font_sid=font_sid, font_w=FW, font_h=FH)

    if dscroll < max_scroll_desc:
        cx  = PX + PW // 2
        bot = AREA_TOPO + LINHAS_VIS * (FH + 1) + 1
        v.draw_rect(cx - 2, bot, 5, 1, 180, 160, 80)
        v.draw_rect(cx - 1, bot + 1, 3, 1, 180, 160, 80)
        v.draw_rect(cx, bot + 2, 1, 1, 180, 160, 80)

    if total_linhas > LINHAS_VIS:
        pag_str = f"{dscroll + 1}/{total_linhas}"
        v.draw_text(PX + PW - len(pag_str) * FW, AREA_TOPO, pag_str, font_sid=font_sid, font_w=FW, font_h=FH)

    CY = DESC_BOT + 2
    for sx in range(0, PW, 4):
        v.draw_rect(PX + sx, CY, 2, 1, 110, 90, 45)
    CY += 4

    prazo   = _prazo_missao(miss_sel)
    est_ini = ESTACOES_ABREV.get(miss_sel.estacao_inicio, miss_sel.estacao_inicio[:3])
    v.draw_rect(PX, CY, 8, 7, 80, 120, 180)
    v.draw_rect(PX, CY, 8, 2, 60, 90, 150)
    v.draw_rect(PX + 2, CY + 3, 4, 1, 200, 220, 255)
    v.draw_text(PX + 10, CY, f"Inicio: {est_ini} {miss_sel.dia_inicio}", font_sid=font_sid, font_w=FW, font_h=FH)
    CY += FH + 2
    v.draw_text(PX + 10, CY, f"Prazo:  {prazo}", font_sid=font_sid, font_w=FW, font_h=FH)
    CY += FH + 4

    for sx in range(0, PW, 4):
        v.draw_rect(PX + sx, CY, 2, 1, 110, 90, 45)
    CY += 4

    v.draw_text(PX, CY, "Recompensa:", font_sid=font_sid, font_w=FW, font_h=FH)
    CY += FH + 2

    v.draw_rect(PX + 1, CY, 5, 1, 255, 215, 0)
    v.draw_rect(PX, CY + 1, 7, 4, 220, 170, 0)
    v.draw_rect(PX + 1, CY + 2, 5, 2, 255, 200, 30)
    v.draw_rect(PX + 1, CY + 5, 5, 1, 255, 215, 0)
    v.draw_text(PX + 10, CY + 1, f"{miss_sel.recompensa_gold}G", font_sid=font_sid, font_w=FW, font_h=FH)
    CY += FH + 2

    v.draw_rect(PX + 1, CY, 2, 1, 255, 120, 150)
    v.draw_rect(PX + 4, CY, 2, 1, 255, 120, 150)
    v.draw_rect(PX, CY + 1, 7, 3, 220, 50, 80)
    v.draw_rect(PX + 1, CY + 4, 5, 1, 200, 40, 60)
    v.draw_rect(PX + 2, CY + 5, 3, 1, 180, 30, 50)
    v.draw_rect(PX + 3, CY + 6, 1, 1, 160, 20, 40)
    v.draw_text(PX + 10, CY + 1, f"+{miss_sel.recompensa_afeto} amizade", font_sid=font_sid, font_w=FW, font_h=FH)

    v.draw_rect(PX, rod_y - 2, PW, 1, 180, 155, 60)
    linha_a = "^v Miss   Z Descrição"
    linha_b = "X Fechar"
    v.draw_text(PX + (PW - len(linha_a) * FW) // 2, rod_y, linha_a, font_sid=font_sid, font_w=FW, font_h=FH)
    v.draw_text(PX + (PW - len(linha_b) * FW) // 2, rod_y + FH + 1, linha_b, font_sid=font_sid, font_w=FW, font_h=FH)

def aniversarios_hoje(jogador, todos_npcs):
    ests    = ["Primavera", "Verao", "Outono", "Inverno"]
    est_idx = ests.index(jogador.estacao_atual) if jogador.estacao_atual in ests else -1
    return [
        npc.nome
        for npc in todos_npcs.values()
        if npc.aniversario and npc.aniversario[0] == est_idx and npc.aniversario[1] == jogador.dia_atual
    ]