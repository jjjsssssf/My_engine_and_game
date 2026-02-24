# game.py
import engine
from funcoes import *
from itens import todos_itens
from artes import *

def main():
    v = engine.Video(SCREEN_W, SCREEN_H, b"RPG Classico", scale=3)
    v.set_background(16, 16, 60)

    font_sid   = v.load_sprite(b"ascii.png")
    box_sid    = v.load_sprite(b"frame.png")
    player_sid = v.load_sprite(b"player_sprites.png")

    id_tiles_fazenda = v.load_sprite(b"tileset.png")
    id_tiles_fazenda2 = v.load_sprite(b"terras.png")
    tilesets = { b"tileset.png": id_tiles_fazenda }

    items_sid = v.load_sprite(b"items.png")

    itens_sprite_ids = {
        b"tileset.png": id_tiles_fazenda,
        b"items.png":   items_sid,
        b"terras.png":  id_tiles_fazenda2
    }

    from artes import mapas_mundo
    nome_mapa_atual = "fazenda"
    mapa_atual_dict = mapas_mundo[nome_mapa_atual]
    map_rows = len(mapa_atual_dict["arte"])
    map_cols = len(mapa_atual_dict["arte"][0]) if map_rows > 0 else 0

    from player import Player
    jogador = Player(
        engine_video=v,
        start_grid_x=2,
        start_grid_y=2,
        sprite_id=player_sid,
        tile_size=TILE_SIZE
    )
    jogador.mapa_atual = nome_mapa_atual

    jogador.adicionar_item("Enchada",  1)
    jogador.adicionar_item("Machado",  1)
    jogador.adicionar_item("Picareta", 1)
    jogador.adicionar_item("Regador",  1)

    jogador.hotbar[1] = "Enchada"
    jogador.hotbar[2] = "Picareta"

    estado      = inicializar_estado_ui()
    estado_cx   = inicializar_estado_caixa()   # ← novo estado da caixa/relatorio
    estado_chuva = inicializar_estado_chuva()  # ← sistema de chuva

    texto_loja  = ""
    item_sel    = None

    while v.running:
        start_time = time.time()
        v.poll_events()

        # ── Tela de relatório (pós-dormir) ─────────────────────────────────────
        # Tem prioridade máxima: bloqueia tudo até o jogador apertar Enter/E
        if estado_cx['mostrar_relatorio']:
            atualizar_tela_relatorio(v, estado_cx)

            v.clear()
            draw_world(v, mapa_atual_dict, 0, 0, itens_sprite_ids)
            v.draw()
            desenhar_tela_relatorio(v, estado_cx, box_sid, font_sid,
                                    SCREEN_W, SCREEN_H)
            v.present()
            controlar_framerate(start_time)
            continue   # pula o resto do loop

        # ── Menu caixa de vendas ────────────────────────────────────────────────
        if estado_cx['mostrar_caixa']:
            atualizar_caixa_vendas(v, jogador, estado_cx)

            cam_x, cam_y = atualizar_camera(v, jogador, map_cols, map_rows)
            v.clear()
            draw_world(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            v.draw()
            desenhar_hotbar(v, jogador, itens_sprite_ids, cam_y)
            desenhar_caixa_vendas(v, jogador, estado_cx, box_sid, font_sid,
                                  SCREEN_W, SCREEN_H)
            v.present()
            controlar_framerate(start_time)
            continue

        # ── Movimento (só quando nenhum menu aberto) ────────────────────────────
        if not estado['mostrar_status'] and not estado['mostrar_loja']:
            jogador.update(mapa_atual_dict)

        # ── Toggle inventário ───────────────────────────────────────────────────
        if v.key_pressed(b"space"):
            estado['mostrar_status'] = not estado['mostrar_status']
            estado['inv_cursor'] = 0

        # ── INVENTÁRIO ──────────────────────────────────────────────────────────
        if estado['mostrar_status']:
            texto_inv, max_pag, estado['inv_cursor'], item_sel = jogador.obter_pagina_inventario(
                pagina=estado['inv_pagina'],
                itens_por_pagina=4,
                cursor_idx=estado['inv_cursor']
            )
            estado['inv_pagina'], estado['inv_cursor'] = processar_input_inventario(
                v, jogador, estado['inv_pagina'], estado['inv_cursor'], max_pag, item_sel
            )
            if v.key_pressed(b"return") and item_sel:
                jogador.usar_item(item_sel)
            if v.key_pressed(b"z") and item_sel:
                jogador.remover_item(item_sel, 1)

        # ── LOJA ────────────────────────────────────────────────────────────────
        elif estado['mostrar_loja']:
            if v.key_pressed(b"x"):
                estado['mostrar_loja'] = False

            lista_atual = gerar_lista_loja(jogador, estado['loja_modo'], todos_itens)
            itens_pagina, max_paginas, estado['loja_pagina'] = calcular_paginacao_loja(
                lista_atual, estado['loja_pagina'], itens_por_pagina=5
            )
            estado['loja_modo'], estado['loja_cursor'], estado['loja_pagina'] = processar_input_loja(
                v, estado['loja_modo'], estado['loja_cursor'],
                estado['loja_pagina'], itens_pagina
            )
            texto_loja, item_sel = gerar_texto_loja(
                jogador, estado['loja_modo'], itens_pagina, estado['loja_cursor'],
                estado['loja_pagina'], max_paginas, estado['mensagem_loja'], todos_itens
            )
            estado['mensagem_loja'] = processar_transacao_loja(
                v, jogador, estado['loja_modo'], item_sel,
                todos_itens, estado['mensagem_loja']
            )

        else:
            # ── HOTBAR ──────────────────────────────────────────────────────────
            msg_hotbar = processar_input_hotbar(v, jogador, mapa_atual_dict)
            if msg_hotbar:
                estado['msg_interacao']       = msg_hotbar
                estado['msg_interacao_timer'] = 180

            # ── ENTER: interação com tile à frente ───────────────────────────
            if v.key_pressed(b"z"):
                resultado = verificar_interacao(jogador, mapa_atual_dict)

                if resultado == "__ABRIR_LOJA__":
                    estado['mostrar_loja'] = True

                elif resultado == "__ABRIR_CAIXA__":
                    # Abre o menu de caixa de vendas
                    estado_cx['mostrar_caixa']   = True
                    estado_cx['caixa_cursor']    = 0
                    estado_cx['caixa_pagina']    = 0
                    estado_cx['caixa_modo_qtd']  = False

                elif resultado == "__DORMIR__":
                    # Processa vendas, avança dia e exibe relatório
                    relatorio = processar_vendas_e_dormir(jogador, estado_chuva)
                    estado_cx['mostrar_relatorio'] = True
                    estado_cx['relatorio_dados']   = relatorio
                    estado_cx['relatorio_pagina']  = 0

                elif resultado.startswith("__TROCAR_MAPA__"):
                    nome_mapa_atual = resultado.replace("__TROCAR_MAPA__", "")
                    mapa_atual_dict = mapas_mundo[nome_mapa_atual]
                    jogador.mapa_atual = nome_mapa_atual
                    map_rows = len(mapa_atual_dict["arte"])
                    map_cols = len(mapa_atual_dict["arte"][0]) if map_rows > 0 else 0

                elif resultado:
                    estado['msg_interacao']       = resultado
                    estado['msg_interacao_timer'] = 180

        # ── Câmera ──────────────────────────────────────────────────────────────
        cam_x, cam_y = atualizar_camera(v, jogador, map_cols, map_rows)

        # ── Avança o relógio de jogo ─────────────────────────────────────────────
        atualizar_tempo(jogador, estado)

        # ── RENDERIZAÇÃO ────────────────────────────────────────────────────────
        v.clear()
        draw_world(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
        v.draw()

        # ── Noite (escurece após 18h, progressivo até 22h) ──────────────────────
        desenhar_noite(v, jogador)

        # ── Chuva (overlay azul + gotas, por cima da noite) ─────────────────────
        atualizar_chuva(estado_chuva)
        desenhar_chuva(v, estado_chuva)

        # ── HUD: hotbar + barra de tempo ────────────────────────────────────────
        desenhar_hotbar(v, jogador, itens_sprite_ids, cam_y)
        desenhar_hud_tempo(v, jogador, estado_chuva, box_sid, font_sid, cam_y)

        if estado['msg_interacao_timer'] > 0:
            estado['msg_interacao_timer'] -= 1
            v.draw_text_box(x=0, y=SCREEN_H - 48,box_w=SCREEN_W, box_h=48,title="", content=estado['msg_interacao'],box_sid=box_sid, box_tw=8, box_th=8,font_sid=font_sid, font_w=8, font_h=8)
        else:
            estado['msg_interacao'] = ""

        if estado['mostrar_status']:
            estado['inv_cursor'], item_sel = desenhar_ui_inventario(
                v, jogador, estado['inv_pagina'], estado['inv_cursor'], box_sid, font_sid
            )

        if estado['mostrar_loja']:
            desenhar_ui_loja(v, texto_loja, box_sid, font_sid)

        v.present()
        controlar_framerate(start_time)


if __name__ == "__main__":
    main()