# game.py
import engine
import os
from funcoes import *
from objeto import (
    verificar_passagem,
    atualizar_npcs,
    resetar_npcs_dia,
    interagir_frente_npc,
    inicializar_estado_bau,
    atualizar_bau,
    desenhar_bau,
    _registrar_baus_do_mapa,
    serializar_baus,
    desserializar_baus,
)
from itens import todos_itens, todos_npcs, aplicar_sprites_npc, aplicar_sprites_item
from artes import mapas_mundo, aplicar_troca_mapa, inicializar_sprites, carregar_sprite_extra
from pesca import PescaMiniGame, processar_resultado_pesca
desenhar_dialogo

def main():
    v = engine.Video(SCREEN_W, SCREEN_H, b"", scale=5)
    v.set_background(0, 0, 0)

    DIRETORIO_EDITOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "editor")

    # ── Sprites ─────────────────────────────────────────────────────────────
    # Arquivos fixos do jogo (font, caixa de diálogo, player) — carregados uma vez.
    font_sid   = carregar_sprite_extra(v, b"ascii.png")
    box_sid    = carregar_sprite_extra(v, b"frame.png")
    player_sid = carregar_sprite_extra(v, b"player_sprites.png")
    arte_mar_sid = carregar_sprite_extra(v, b"arte_mar.png")

    # Todos os tilesets referenciados nos mapas são carregados automaticamente.
    # O dict retornado é exatamente o itens_sprite_ids que as funções de draw esperam.
    itens_sprite_ids = inicializar_sprites(v)

    # Garante que os sprites de itens (items.png, tileset.png) estejam no dict —
    # podem não aparecer nos mapas mas são usados pela hotbar e inventário.
    for _spr in (b"items.png", b"tileset.png"):
        if _spr not in itens_sprite_ids:
            _sid = carregar_sprite_extra(v, _spr)
            if _sid is not None:
                itens_sprite_ids[_spr] = _sid

    # ── Mapa inicial ────────────────────────────────────────────────────────
    nome_mapa_atual = "fazenda"
    mapa_atual_dict = mapas_mundo[nome_mapa_atual]
    map_rows = len(mapa_atual_dict["arte"])
    map_cols = len(mapa_atual_dict["arte"][0]) if map_rows > 0 else 0

    # ── Sprite dos NPCs ─────────────────────────────────────────────────────
    # Os tiles de animação vêm do JSON do mapa (campo "npc_sprites"),
    # editados diretamente na aba "NPCs" do mapa_editor.
    # aplicar_sprites_npc() lê esse bloco, preenche npc.tiles e carrega sprite_id.
    npc_sprites_json = mapa_atual_dict.get("npc_sprites", {})
    if npc_sprites_json:
        aplicar_sprites_npc(
            todos_npcs_dict   = todos_npcs,
            npc_sprites_json  = npc_sprites_json,
            engine_video      = v,
            diretorio_editor  = DIRETORIO_EDITOR,
        )

    # ── Sprites dos Itens ────────────────────────────────────────────────────
    # item_sprites vem da aba "Sprites Itens" do mapa_editor.
    # Sobrescreve item.sprite/col/lin definidos em itens.py com os valores
    # escolhidos visualmente no editor, sem precisar editar itens.py.
    item_sprites_json = mapa_atual_dict.get("item_sprites", {})
    if item_sprites_json:
        aplicar_sprites_item(item_sprites_json)
    # Fallback: NPCs sem sprite configurado no editor usam player_sprites.png
    for npc in todos_npcs.values():
        if npc.sprite_id is None:
            npc.sprite_id = player_sid   # placeholder visual

    # ── Jogador ─────────────────────────────────────────────────────────────
    from player import Player
    jogador = Player(
        engine_video=v,
        start_grid_x=2,
        start_grid_y=2,
        sprite_id=player_sid,
        tile_size=TILE_SIZE,
    )
    jogador.mapa_atual = nome_mapa_atual

    # Injeta referência dos NPCs para colisão bidirecional player↔NPC
    jogador.set_npcs_ref(todos_npcs)

    jogador.adicionar_item("Enchada",  1)
    jogador.adicionar_item("Vara de Pesca",  1)
    jogador.adicionar_item("Picareta", 1)
    jogador.adicionar_item("Regador",  1)
    jogador.adicionar_item("Vara de Pesca Profissional", 1)
    jogador.hotbar[1] = "Enchada"
    jogador.hotbar[2] = "Vara de Pesca Profissional"
    jogador.hotbar[3] = "Vara de Pesca"

    # ── Estados UI ──────────────────────────────────────────────────────────
    estado       = inicializar_estado_ui()
    estado_cx    = inicializar_estado_caixa()
    estado_chuva = inicializar_estado_chuva()
    estado_social= inicializar_estado_social()
    estado_bau   = inicializar_estado_bau()
    estado_pesca = None   # PescaMiniGame ativo, ou None

    # Registra baús do mapa inicial
    _registrar_baus_do_mapa(mapa_atual_dict)

    texto_loja = ""
    item_sel   = None

    # Contador de frames para atualizar NPCs
    frame_contador = 0

    # ── Loop principal ───────────────────────────────────────────────────────
    while v.running:
        v.poll_events()
        frame_contador += 1

        # ── Tela cheia / janela com F ────────────────────────────────────────
        if v.key_pressed(b"f"):
            v.toggle_fullscreen()

        # SCR_W / SCR_H refletem o render atual da engine
        # (muda ao entrar/sair de fullscreen)
        SCR_W = v.render_w
        SCR_H = v.render_h

        # ── Helper: escurece só o mapa, antes de qualquer menu ───────────────
        def _overlay_menu():
            v.draw_overlay(0, 0, SCR_W, SCR_H, 0, 0, 0, 0.55)

        # ── Diálogo estilo Pokémon (congela tudo enquanto ativo) ────────────
        if estado['dialogo_ativo']:
            atualizar_dialogo(v, estado)
            cam_x, cam_y = atualizar_camera(v, jogador, map_cols, map_rows)
            v.clear()
            draw_world(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            desenhar_npcs(v, todos_npcs, nome_mapa_atual, cam_x, cam_y)
            v.draw()
            draw_world_topo(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            desenhar_barra_bloco(v, jogador, mapa_atual_dict, cam_x, cam_y)
            desenhar_noite(v, jogador)
            atualizar_chuva(estado_chuva)
            desenhar_chuva(v, estado_chuva)
            desenhar_hotbar(v, jogador, itens_sprite_ids, cam_y, estado, font_sid)
            if estado.get('hud_tempo_ativo'):
                desenhar_hud_tempo(v, jogador, estado_chuva, box_sid, font_sid, cam_x, map_cols)
            desenhar_barras_vida(v, jogador, font_sid, cam_y)
            desenhar_dialogo(v, estado, box_sid, font_sid)
            v.present()
            v.cap_fps(60)
            continue

        # ── Tela de baú (congela tudo enquanto ativo) ───────────────────────
        if estado_bau['mostrar_bau']:
            atualizar_bau(v, jogador, estado_bau, mapa_atual_dict)
            cam_x, cam_y = atualizar_camera(v, jogador, map_cols, map_rows)
            v.clear()
            draw_world(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            desenhar_npcs(v, todos_npcs, nome_mapa_atual, cam_x, cam_y)
            v.draw()
            draw_world_topo(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            _overlay_menu()
            desenhar_bau(v, jogador, estado_bau, mapa_atual_dict,
                         box_sid, font_sid, itens_sprite_ids, SCR_W, SCR_H)
            v.present()
            v.cap_fps(60)
            continue

        # ── Mini-game de pesca (congela tudo enquanto ativo) ─────────────────
        if estado_pesca is not None:
            if not estado_pesca.encerrado:
                # Atualiza inputs + lógica do mini-game
                estado_pesca.atualizar(v)
                # Renderiza: mundo visível atrás do overlay do mini-game
                cam_x, cam_y = atualizar_camera(v, jogador, map_cols, map_rows)
                v.clear()
                draw_world(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
                desenhar_npcs(v, todos_npcs, nome_mapa_atual, cam_x, cam_y)
                v.draw()
                draw_world_topo(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
                desenhar_noite(v, jogador)
                atualizar_chuva(estado_chuva)
                desenhar_chuva(v, estado_chuva)
                # Desenha o mini-game sobre tudo (inclui overlay escuro interno)
                estado_pesca.desenhar(v)
                v.present()
                v.cap_fps(60)
                continue
            else:
                # Mini-game encerrou: processa resultado e exibe como diálogo
                msg = processar_resultado_pesca(estado_pesca, jogador)
                abrir_dialogo(estado, msg)
                estado_pesca = None

        # ── Tela de relatório (pós-dormir) ─────────────────────────────────
        if estado_cx['mostrar_relatorio']:
            atualizar_tela_relatorio(v, estado_cx)
            cam_x, cam_y = atualizar_camera(v, jogador, map_cols, map_rows)
            v.clear()
            draw_world(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            desenhar_npcs(v, todos_npcs, nome_mapa_atual, cam_x, cam_y)
            v.draw()
            draw_world_topo(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            _overlay_menu()
            desenhar_tela_relatorio(v, estado_cx, box_sid, font_sid, SCR_W, SCR_H)
            v.present()
            v.cap_fps(60)
            continue

        # ── Menu caixa de vendas ────────────────────────────────────────────
        if estado_cx['mostrar_caixa']:
            atualizar_caixa_vendas(v, jogador, estado_cx)
            cam_x, cam_y = atualizar_camera(v, jogador, map_cols, map_rows)
            v.clear()
            draw_world(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            desenhar_npcs(v, todos_npcs, nome_mapa_atual, cam_x, cam_y)
            v.draw()
            draw_world_topo(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            _overlay_menu()
            desenhar_hotbar(v, jogador, itens_sprite_ids, cam_y, font_sid=font_sid)
            desenhar_barras_vida(v, jogador, font_sid, cam_y)
            desenhar_caixa_vendas(v, jogador, estado_cx, box_sid, font_sid, SCR_W, SCR_H)
            v.present()
            v.cap_fps(60)
            continue

        # ── Diálogo de proposta de missão ───────────────────────────────────
        if estado_social['missao_dialogo']:
            processar_dialogo_missao(v, estado_social, jogador)
            cam_x, cam_y = atualizar_camera(v, jogador, map_cols, map_rows)
            v.clear()
            draw_world(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            desenhar_npcs(v, todos_npcs, nome_mapa_atual, cam_x, cam_y)
            v.draw()
            draw_world_topo(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            _overlay_menu()
            desenhar_dialogo_missao(v, estado_social, box_sid, font_sid)
            v.present()
            v.cap_fps(60)
            continue

        # ── Diálogo de entrega de missão ─────────────────────────────────────
        if estado_social['entrega_dialogo']:
            processar_dialogo_entrega(v, estado_social, jogador)
            cam_x, cam_y = atualizar_camera(v, jogador, map_cols, map_rows)
            v.clear()
            draw_world(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            desenhar_npcs(v, todos_npcs, nome_mapa_atual, cam_x, cam_y)
            v.draw()
            draw_world_topo(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            _overlay_menu()
            desenhar_dialogo_entrega(v, estado_social, jogador, box_sid, font_sid)
            v.present()
            v.cap_fps(60)
            continue

        # ── Menu Social ─────────────────────────────────────────────────────
        if estado_social['mostrar_social']:
            processar_input_social(v, estado_social, todos_npcs)
            cam_x, cam_y = atualizar_camera(v, jogador, map_cols, map_rows)
            v.clear()
            draw_world(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            desenhar_npcs(v, todos_npcs, nome_mapa_atual, cam_x, cam_y)
            v.draw()
            draw_world_topo(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            _overlay_menu()
            desenhar_menu_social(v, jogador, estado_social, todos_npcs, box_sid, font_sid, itens_sprite_ids)
            v.present()
            v.cap_fps(60)
            continue

        # ── Menu Missões ─────────────────────────────────────────────────────
        if estado_social['mostrar_missoes']:
            processar_input_missoes(v, estado_social, jogador, todos_npcs)
            cam_x, cam_y = atualizar_camera(v, jogador, map_cols, map_rows)
            v.clear()
            draw_world(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            desenhar_npcs(v, todos_npcs, nome_mapa_atual, cam_x, cam_y)
            v.draw()
            draw_world_topo(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)
            _overlay_menu()
            desenhar_menu_missoes(v, jogador, estado_social, todos_npcs, box_sid, font_sid, itens_sprite_ids)
            v.present()
            v.cap_fps(60)
            continue

        # ── Menu Status ─────────────────────────────────────────────────────
        if estado.get('mostrar_status_menu'):
            processar_input_status_menu(v, estado, jogador)

        # ── Atualiza todos os NPCs (deslizamento + pathfinding) ─────────────
        atualizar_npcs(frame_contador, jogador, mapas_mundo)

        # ── Movimento do jogador ────────────────────────────────────────────
        bloqueado = (
            estado['menu_aberto']
            or estado['mostrar_status']
            or estado['mostrar_loja']
            or estado.get('hotbar_ativa')
            or estado.get('mostrar_status_menu')
        )
        if not bloqueado:
            jogador.update(mapa_atual_dict)

        # ── Helper: True quando qualquer menu/tela exclusiva está aberta ────────
        # Usado para bloquear inputs do mundo (space, z, x, m) nesses contextos.
        def _em_algum_menu():
            return (
                estado['menu_aberto']
                or estado['mostrar_status']
                or estado['mostrar_loja']
                or estado.get('mostrar_status_menu')
                or estado_social.get('mostrar_social')
                or estado_social.get('mostrar_missoes')
                or estado_social.get('missao_dialogo')
                or estado_social.get('entrega_dialogo')
                or estado_cx['mostrar_caixa']
                or estado_cx['mostrar_relatorio']
                or estado_bau['mostrar_bau']
                or estado['dialogo_ativo']
                or estado_pesca is not None
            )

        # ── Toggle menu principal (Space) ───────────────────────────────────
        if v.key_pressed(b"space") and not _em_algum_menu():
            estado['menu_aberto'] = True
            estado['menu_cursor'] = 0

        # ── MENU PRINCIPAL ──────────────────────────────────────────────────
        if estado['menu_aberto']:
            escolha = processar_input_menu(v, estado)

            if escolha == "Inventario":
                estado['menu_aberto']    = False
                estado['mostrar_status'] = True
                estado['inv_cursor']     = 0

            elif escolha == "Status":
                estado['menu_aberto']         = False
                estado['mostrar_status_menu'] = True

            elif escolha == "Social":
                estado['menu_aberto']           = False
                estado_social['mostrar_social'] = True
                estado_social['social_cursor']  = 0
                estado_social['social_scroll']  = 0

            elif escolha == "Missoes":
                estado['menu_aberto']            = False
                estado_social['mostrar_missoes'] = True
                estado_social['missoes_cursor']  = 0
                estado_social['missoes_scroll']  = 0

            elif escolha == "Save":
                salvar_jogo(jogador, mapas_mundo)   # ação silenciosa, sem caixa

            elif escolha == "Load":
                res = carregar_jogo(jogador, mapas_mundo)
                if isinstance(res, tuple):
                    nome_mapa_atual, mapa_atual_dict, map_rows, map_cols, _msg = res

            elif escolha == "Sair":
                break

        # ── INVENTÁRIO ──────────────────────────────────────────────────────
        elif estado['mostrar_status']:
            # Todo o input (Z usar, X jogar fora, Space sair, Enter hotbar)
            # está encapsulado em processar_input_inventario.
            processar_input_inventario(v, jogador, estado, todos_itens)


        # ── LOJA ────────────────────────────────────────────────────────────
        elif estado['mostrar_loja']:
            atualizar_loja(v, jogador, estado, todos_itens,
                           itens_vendidos=estado.get('loja_itens_vendidos'))

        else:
            # ── HOTBAR ──────────────────────────────────────────────────────
            processar_input_hotbar(v, jogador, mapa_atual_dict, estado)
            # Ações da hotbar são visíveis no mundo — sem caixa de texto

            # ── Passagem automática (pisar no tile) ──────────────────────────
            res_passagem = verificar_passagem(jogador, mapa_atual_dict)
            if res_passagem and res_passagem.startswith("__TROCAR_MAPA__"):
                nome_mapa_atual, mapa_atual_dict, map_rows, map_cols = \
                    aplicar_troca_mapa(res_passagem, jogador)
                _registrar_baus_do_mapa(mapa_atual_dict)

            # ── Z: conversar com NPC / interação com tile ────────────────────
            if v.key_pressed(b"z") and not estado.get('hotbar_ativa') and not _em_algum_menu():

                # 1) Tenta conversar com NPC (apenas conversa, sem missão)
                res_npc = interagir_frente_npc(
                    jogador, mapa_atual_dict, todos_npcs, todos_itens,
                    apenas_conversar=True)

                if res_npc and isinstance(res_npc, dict):
                    # Z só abre diálogo de texto — missão/entrega ficam no X
                    abrir_dialogo(estado, res_npc.get('texto', ''))

                elif not res_npc:
                    # 2) Sem NPC → interação com tile
                    resultado = verificar_interacao(jogador, mapa_atual_dict)

                    if resultado == "__ABRIR_LOJA__" or resultado.startswith("__ABRIR_LOJA__:"):
                        estado['mostrar_loja'] = True
                        if ":" in resultado:
                            import json as _json
                            try:
                                _payload = _json.loads(resultado.split(":", 1)[1])
                                _nomes = tuple(n.strip() for n in _payload.get("nomes", "").split(",") if n.strip())
                                _tipos = tuple(t.strip() for t in _payload.get("tipos", "").split(",") if t.strip())
                                estado['loja_itens_vendidos'] = {k: v for k, v in [("nome", _nomes), ("tipo", _tipos)] if v}
                            except Exception:
                                estado['loja_itens_vendidos'] = None
                        else:
                            estado['loja_itens_vendidos'] = None

                    elif resultado == "__ABRIR_CAIXA__":
                        estado_cx['mostrar_caixa']   = True
                        estado_cx['caixa_cursor']    = 0
                        estado_cx['caixa_pagina']    = 0
                        estado_cx['caixa_modo_qtd']  = False

                    elif resultado == "__DORMIR__":
                        relatorio = processar_vendas_e_dormir(jogador, estado_chuva)
                        resetar_npcs_dia()
                        estado_cx['mostrar_relatorio'] = True
                        estado_cx['relatorio_dados']   = relatorio
                        estado_cx['relatorio_pagina']  = 0

                    elif resultado and resultado.startswith("__ABRIR_BAU__"):
                        nome_bau = resultado[len("__ABRIR_BAU__"):]
                        estado_bau['mostrar_bau']       = True
                        estado_bau['bau_nome']          = nome_bau
                        estado_bau['bau_modo']          = "bau"
                        estado_bau['bau_painel']        = "bau"
                        estado_bau['bau_cursor']        = 0
                        estado_bau['bau_pagina']        = 0
                        estado_bau['bau_anim_tick']     = 0
                        estado_bau['bau_anim_fase']     = "abrindo"
                        estado_bau['bau_msg']           = ""
                        estado_bau['bau_modo_qtd']      = False
                        estado_bau['bau_item_sel']      = None
                        estado_bau['bau_qtd_cursor']    = 1
                        estado_bau['bau_qtd_acao']      = "transferir"
                        estado_bau['bau_org_ativo']     = False
                        estado_bau['bau_org_slot']      = None
                        estado_bau['bau_org_entrada']   = False
                        estado_bau['bau_lixeira_qtd']   = False
                        estado_bau['bau_lixeira_cursor']= 1

                    elif resultado and resultado.startswith("__TROCAR_MAPA__"):
                        nome_mapa_atual, mapa_atual_dict, map_rows, map_cols = \
                            aplicar_troca_mapa(resultado, jogador)
                        _registrar_baus_do_mapa(mapa_atual_dict)

                    elif resultado and resultado.startswith("__PESCA__:"):
                        # "__PESCA__:tile_mar" / "__PESCA__:tile_lago" / "__PESCA__:tile_mangi"
                        tipo_agua = resultado.split(":")[1]
                        # Custo de stamina ao lançar a vara
                        jogador.mana = max(0, jogador.mana - 10)
                        estado_pesca = PescaMiniGame(
                            v, jogador, font_sid, box_sid,
                            itens_sprite_ids, arte_mar_sid,
                            tipo_agua=tipo_agua,
                            estado_chuva=estado_chuva,
                        )

                    elif resultado and resultado not in ("", "__ABRIR_LOJA__",
                                                          "__ABRIR_CAIXA__", "__DORMIR__"):
                        # Mensagem de erro genérica (ex: "Equipe uma vara de pesca!")
                        abrir_dialogo(estado, resultado)

            # ── X com NPC: missão / entrega / presente ────────────────────────
            if v.key_pressed(b"x") and not estado.get('hotbar_ativa') and not _em_algum_menu():
                res_x = interagir_frente_npc(
                    jogador, mapa_atual_dict, todos_npcs, todos_itens,
                    apenas_conversar=False)
                if res_x and isinstance(res_x, dict):
                    tipo = res_x['tipo']
                    if tipo == 'missao':
                        estado_social['missao_dialogo']        = True
                        estado_social['missao_dialogo_npc']    = res_x['npc']
                        estado_social['missao_dialogo_obj']    = res_x['missao']
                        estado_social['missao_dialogo_cursor'] = 0
                    elif tipo == 'entrega':
                        estado_social['entrega_dialogo']     = True
                        estado_social['entrega_dialogo_npc'] = res_x['npc']
                        estado_social['entrega_dialogo_obj'] = res_x['missao']
                    elif tipo == 'presente':
                        abrir_dialogo(estado, res_x['texto'])
                    elif tipo == 'dialogo':
                        abrir_dialogo(estado, res_x['texto'])

            # ── M: atalho para o menu de missões ─────────────────────────────
            if v.key_pressed(b"m") and not _em_algum_menu():
                estado_social['mostrar_missoes'] = True
                estado_social['missoes_cursor']  = 0
                estado_social['missoes_scroll']  = 0

        # ── Câmera ──────────────────────────────────────────────────────────
        cam_x, cam_y = atualizar_camera(v, jogador, map_cols, map_rows)

        # ── Relógio de jogo ─────────────────────────────────────────────────
        atualizar_tempo(jogador, estado)

        # ── Aniversários do dia (exibe uma vez) ─────────────────────────────
        if frame_contador == 1:
            anivs = aniversarios_hoje(jogador, todos_npcs)
            if anivs:
                abrir_dialogo(estado, f"Hoje é aniversário de: {', '.join(anivs)}!")

        # ── RENDERIZAÇÃO ────────────────────────────────────────────────────
        v.clear()

        # Chão e camada principal
        draw_world(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)

        # NPCs — entre o mundo e o topo (passam "atrás" de telhados)
        desenhar_npcs(v, todos_npcs, nome_mapa_atual, cam_x, cam_y)

        # Objeto do jogador (gerenciado pela engine)
        v.draw()

        # Telhados / topos de árvores — sobre tudo
        draw_world_topo(v, mapa_atual_dict, cam_x, cam_y, itens_sprite_ids)

        # Barra de vida do bloco sendo quebrado
        desenhar_barra_bloco(v, jogador, mapa_atual_dict, cam_x, cam_y)

        # Efeitos atmosféricos
        desenhar_noite(v, jogador)
        atualizar_chuva(estado_chuva)
        desenhar_chuva(v, estado_chuva)

        # ── Overlay escuro quando qualquer menu está aberto ──────────────────
        _qualquer_menu = (
            estado['menu_aberto']
            or estado['mostrar_status']
            or estado['mostrar_loja']
            or estado.get('mostrar_status_menu')
        )
        if _qualquer_menu:
            _overlay_menu()

        # HUD
        desenhar_hotbar(v, jogador, itens_sprite_ids, cam_y, estado, font_sid)
        if estado.get('hud_tempo_ativo'):
            desenhar_hud_tempo(v, jogador, estado_chuva, box_sid, font_sid, cam_x, map_cols)
        desenhar_barras_vida(v, jogador, font_sid, cam_y)

        # Diálogo estilo Pokémon (só aparece quando ativo — já tratado acima)
        # msg_interacao_timer mantido para compatibilidade com outros sistemas (loja etc.)
        if estado['msg_interacao_timer'] > 0:
            estado['msg_interacao_timer'] -= 1

        # Menus sobrepostos
        if estado['menu_aberto']:
            desenhar_menu_principal(v, estado, box_sid, font_sid)

        elif estado['mostrar_status']:
            estado['inv_cursor'], item_sel = desenhar_ui_inventario(
                v, jogador, estado['inv_pagina'], estado['inv_cursor'],
                box_sid, font_sid,
                itens_sprite_ids=itens_sprite_ids,
                estado=estado,
            )

        if estado.get('mostrar_status_menu'):
            desenhar_menu_status(v, jogador, estado_chuva, box_sid, font_sid,
                                 estado_status={
                                     'cursor_hab':      estado.get('status_cursor_hab', 0),
                                     'modo_distribuir': estado.get('status_modo_distrib', False),
                                 })

        if estado['mostrar_loja']:
            desenhar_ui_loja(v, texto_loja, box_sid, font_sid,
                             estado=estado, jogador=jogador,
                             itens_sprite_ids=itens_sprite_ids,
                             itens_vendidos=estado.get('loja_itens_vendidos'))

        # XP notification popup
        desenhar_xp_notif(v, estado, font_sid)

        v.present()
        v.cap_fps(60)


if __name__ == "__main__":
    main()