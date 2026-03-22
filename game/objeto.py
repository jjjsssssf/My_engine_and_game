from itens import *
_dano_blocos = {}
# objeto.py
import random

# ---------------------------------------------------------------------------
# Helpers: converte entre nome-de-tile e ID numérico do mapa
# ---------------------------------------------------------------------------

def _nome_para_id(mapa_dict, nome_tile):
    """Dado um nome de tile (ex: 'terra_arada'), retorna o visual_id numerico.
    USA APENAS o campo 'nome' — o nome individual especifico de cada tile.
    NAO usa 'nomes' (lista do grupo semantico que contamina todos os tiles do grupo).
    """
    for tid, info in mapa_dict.get("blocos", {}).items():
        if info.get("nome") == nome_tile:
            return tid
    return None

def _id_para_nome(mapa_dict, tile_id):
    """Dado um tile_id numerico, retorna o nome especifico do tile ou ''.
    USA APENAS o campo 'nome' — o nome individual especifico do tile.
    NAO usa 'nomes' (lista do grupo que retornaria nome errado).
    """
    blocos = mapa_dict.get("blocos", {})
    info = blocos.get(tile_id, {})
    return info.get("nome", "")

# Nomes que representam terra arada (seca) e terra molhada
_NOMES_TERRA_ARADA  = {"terra_arada"}
_NOMES_TERRA_MOLHADA = {"terra_molhada"}
_NOMES_PLANTAVEL    = _NOMES_TERRA_ARADA | _NOMES_TERRA_MOLHADA

# ---------------------------------------------------------------------------
# Atualiza visual da planta no mapa (usa nomes de tile)
# ---------------------------------------------------------------------------
def _atualizar_tile_planta(mapa_dict, nx, ny):
    from itens import TODAS_PLANTAS
    dados = mapa_dict["plantacoes"][(nx, ny)]
    planta = TODAS_PLANTAS[dados["semente"]]

    # Calcular o estágio atual de crescimento
    dias_necessarios = planta.dias_total + dados.get("dias_penalidade", 0)
    if dados["dias_idade"] >= dias_necessarios:
        idx_estagio = len(planta.estagios_tiles) - 1
    else:
        proporcao = dados["dias_idade"] / max(1, dias_necessarios)
        idx_estagio = int(proporcao * len(planta.estagios_tiles))
        idx_estagio = min(idx_estagio, len(planta.estagios_tiles) - 2)

    # Guarda o nome do estagio nos dados — o renderer le diretamente daqui
    dados["_estagio_nome"] = planta.estagios_tiles[idx_estagio]

    # Coloca no arte o tile de terra correto como marcador (arada ou molhada)
    nome_fundo = "terra_molhada" if dados.get("regada", False) else "terra_arada"
    id_fundo = _nome_para_id(mapa_dict, nome_fundo)
    if id_fundo is not None:
        mapa_dict["arte"][ny][nx] = id_fundo

# --- 1. Ação para quando usar a semente no inventário / hotbar ---
def plantar_semente(jogador, mapa_dict, nx, ny, nome_semente):
    from itens import TODAS_PLANTAS
    tile_id = mapa_dict["arte"][ny][nx]
    nome_tile = _id_para_nome(mapa_dict, tile_id)

    if nome_tile not in _NOMES_PLANTAVEL:
        return "A terra precisa estar arada"

    if "plantacoes" in mapa_dict and (nx, ny) in mapa_dict["plantacoes"]:
        return "Já tem uma planta aqui."

    planta_info = TODAS_PLANTAS.get(nome_semente)
    if not planta_info: return "Semente inválida."

    if jogador.estacao_atual not in planta_info.estacoes_plantio:
        return f"Sementes de {planta_info.nome} murchariam na {jogador.estacao_atual}."

    if "plantacoes" not in mapa_dict:
        mapa_dict["plantacoes"] = {}

    mapa_dict["plantacoes"][(nx, ny)] = {
        "semente":       nome_semente,
        "dias_idade":    0,
        "regada":        (nome_tile in _NOMES_TERRA_MOLHADA),
        "dias_plantada": 0,
        "dias_penalidade": 0,
        "estrelas_bonus": 0,   # bônus de fertilizante (0-4)
    }

    _atualizar_tile_planta(mapa_dict, nx, ny)
    jogador.adicionar_item(nome_semente, -1)

    # XP de plantar — usa xp_ganho do item se definido
    if hasattr(jogador, 'ganhar_xp_hab'):
        from itens import todos_itens as _ti
        _item_s = _ti.get(nome_semente)
        _bonus  = getattr(_item_s, 'xp_ganho', 0) if _item_s else 0
        jogador.ganhar_xp_hab('plantar', _bonus)

    slot = jogador.item_selecionado
    if jogador.invetario.get(nome_semente, 0) <= 0:
        jogador.hotbar[slot] = None

    return f"Você plantou {nome_semente}!"

# --- 2. Função que o Player chama quando vai dormir ---
def atualizar_plantacoes_do_mundo(mapas_mundo, estacao_atual):
    for nome, mapa_dict in mapas_mundo.items():
        if "plantacoes" not in mapa_dict:
            continue
            
        plantas_mortas = []
        
        for (nx, ny), dados in mapa_dict["plantacoes"].items():
            from itens import TODAS_PLANTAS
            planta = TODAS_PLANTAS[dados["semente"]]
            
            # Garante que as variáveis novas existam
            if "dias_plantada" not in dados: dados["dias_plantada"] = 0
            if "dias_penalidade" not in dados: dados["dias_penalidade"] = 0
            
            # Aumenta o tempo que a planta existe no chão
            dados["dias_plantada"] += 1
            
            if estacao_atual not in planta.estacoes_plantio:
                plantas_mortas.append((nx, ny))
                continue
            
            if not dados.get("regada", False):
                if dados["dias_plantada"] % 2 == 0:
                    if random.random() < 0.20:
                        plantas_mortas.append((nx, ny))
                        continue
                dados["dias_penalidade"] += 3
            else:
                # Se FOI REGADA, ela está protegida e cresce normalmente
                dados["dias_idade"] += 1

            # Quando dorme, a planta sempre amanhece seca e precisando de água de novo
            dados["regada"] = False
            
            _atualizar_tile_planta(mapa_dict, nx, ny)

        for px, py in plantas_mortas:
            del mapa_dict["plantacoes"][(px, py)]
            # Volta para terra arada (seca) ou chão dependendo do que havia
            id_terra_arada = _nome_para_id(mapa_dict, "terra_arada")
            id_chao        = _nome_para_id(mapa_dict, "chao")
            mapa_dict["arte"][py][px] = id_terra_arada if id_terra_arada is not None else (id_chao or 0)
        map_rows = len(mapa_dict["arte"])
        map_cols = len(mapa_dict["arte"][0]) if map_rows > 0 else 0
        # Ao acordar: converte terra_molhada de volta para terra_arada
        id_molhada = _nome_para_id(mapa_dict, "terra_molhada")
        id_arada   = _nome_para_id(mapa_dict, "terra_arada")
        if id_molhada is not None and id_arada is not None:
            for y in range(map_rows):
                for x in range(map_cols):
                    if mapa_dict["arte"][y][x] == id_molhada:
                        mapa_dict["arte"][y][x] = id_arada

# --- 3. Integração com o botão de Interagir (Espaço) ---
def colher_planta(jogador, mapa_dict, nx, ny):
    from itens import TODAS_PLANTAS
    # --- REGRA DA MÃO VAZIA ---
    if jogador.itens_equipados.get("Primeira Mão") is not None:
        return "Guarde o item da mão para conseguir colher!"
    dados = mapa_dict["plantacoes"][(nx, ny)]
    planta = TODAS_PLANTAS[dados["semente"]]
    # Leva em conta a penalidade de dias sem água na hora da colheita
    dias_necessarios = planta.dias_total + dados.get("dias_penalidade", 0)
    if dados["dias_idade"] < dias_necessarios:
        return f"A {planta.nome} ainda não está madura."
    # Calcula estrelas finais = base do item + bônus fertilizante + bônus habilidade
    _bonus_ferti = dados.get("estrelas_bonus", 0)
    _estrelas_finais = 0   # calculado abaixo por item

    # Entrega os itens ao jogador, com versão estrelada se tiver bônus
    from itens import todos_itens as _ti_colh, obter_item_estrelado
    for item_nome, qtd in planta.itens_colheita:
        _obj_base = _ti_colh.get(item_nome)
        _est_base = getattr(_obj_base, 'estrelas', 0) if _obj_base else 0
        # bônus da habilidade do jogador
        _est_hab  = 0
        if hasattr(jogador, 'bonus_estrelas_item') and _obj_base:
            _est_hab = jogador.bonus_estrelas_item(_obj_base) - _est_base
        _estrelas_finais = min(4, _est_base + _bonus_ferti + _est_hab)
        if _estrelas_finais > 0:
            item_nome_real = obter_item_estrelado(item_nome, _estrelas_finais)
        else:
            item_nome_real = item_nome
        jogador.adicionar_item(item_nome_real, qtd)

    # XP de colheita — usa xp_ganho do item colhido
    if hasattr(jogador, 'ganhar_xp_hab'):
        from itens import todos_itens as _ti2
        for _nome_c, _ in planta.itens_colheita:
            _obj_c = _ti2.get(_nome_c)
            _bonus_c = getattr(_obj_c, 'xp_ganho', 0) if _obj_c else 0
            jogador.ganhar_xp_hab('colher', _bonus_c)
            break   # XP uma vez por colheita

    # --- SISTEMA DE REGROW CORRIGIDO ---
    if getattr(planta, 'regrow', None) is not None:
        dados["dias_penalidade"] = 0 
        dados["dias_idade"] = planta.dias_total - planta.regrow
        dados["regada"] = False 
        _atualizar_tile_planta(mapa_dict, nx, ny)
        
        _qual = f" [{_estrelas_finais}★]" if _estrelas_finais > 0 else ""
        return f"+ Colhido! {planta.nome}{_qual} volta em {planta.regrow} dias."
    else:
        del mapa_dict["plantacoes"][(nx, ny)]
        mapa_dict["arte"][ny][nx] = 1 
        _qual = f" [{_estrelas_finais}★]" if _estrelas_finais > 0 else ""
        return f"Você colheu {planta.nome}{_qual}!"

def verificar_interacao(jogador, mapa_dict):
    resultado = obter_bloco_frente(jogador, mapa_dict)
    if not resultado: return ""
    nx, ny, tile_id = resultado
    
    # 1º Checa se é uma planta antes de ser um baú/loja normal
    if "plantacoes" in mapa_dict and (nx, ny) in mapa_dict["plantacoes"]:
        return colher_planta(jogador, mapa_dict, nx, ny)

def _get_blocos(mapa_dict):
    return mapa_dict.get("blocos", {})

def obter_bloco_frente(jogador, mapa_dict):
    mapa = mapa_dict["arte"]
    map_rows = len(mapa)
    map_cols = len(mapa[0]) if map_rows > 0 else 0
    dir_map = {
        "cima":     (0, -1),
        "baixo":    (0,  1),
        "esquerda": (-1, 0),
        "direita":  (1,  0),
    }
    dx, dy = dir_map.get(jogador.direcao, (0, 0))
    nx = jogador.grid_x + dx
    ny = jogador.grid_y + dy
    if 0 <= nx < map_cols and 0 <= ny < map_rows:
        return nx, ny, mapa[ny][nx]
    return None

def verificar_chao(jogador, mapa_dict):
    mapa = mapa_dict["arte"]
    map_rows = len(mapa)
    map_cols = len(mapa[0]) if map_rows > 0 else 0
    gx, gy = jogador.grid_x, jogador.grid_y
    if 0 <= gx < map_cols and 0 <= gy < map_rows:
        return mapa[gy][gx]
    return None

def substituir_bloco(mapas_mundo, mapa_id, nx, ny, novo_tile_id):
    mapa_dict = mapas_mundo.get(mapa_id)
    if not mapa_dict:
        return False
    mapa = mapa_dict["arte"]
    map_rows = len(mapa)
    map_cols = len(mapa[0]) if map_rows > 0 else 0
    if 0 <= nx < map_cols and 0 <= ny < map_rows:
        mapa[ny][nx] = novo_tile_id
        return True
    return False

def verificar_interacao_mensagem(jogador, mapa_dict):
    resultado = obter_bloco_frente(jogador, mapa_dict)
    if not resultado:
        return ""
    nx, ny, tile_id = resultado

    # Mostra info da plantação (estado, qualidade, fertilizante)
    if "plantacoes" in mapa_dict and (nx, ny) in mapa_dict["plantacoes"]:
        from itens import TODAS_PLANTAS
        dados = mapa_dict["plantacoes"][(nx, ny)]
        planta = TODAS_PLANTAS.get(dados["semente"])
        if planta:
            dias_nec = planta.dias_total + dados.get("dias_penalidade", 0)
            restam   = max(0, dias_nec - dados["dias_idade"])
            bonus_f  = dados.get("estrelas_bonus", 0)
            regada   = "Regada" if dados.get("regada") else "Seca"
            qual_txt = f" Qualidade:{bonus_f}*" if bonus_f > 0 else ""
            if restam == 0:
                return f"{planta.nome}: pronta! {regada}{qual_txt}"
            return f"{planta.nome}: {restam}d para amadurecer. {regada}{qual_txt}"

    blocos = _get_blocos(mapa_dict)
    bloco_info = blocos.get(tile_id, {})
    if "mensagem" in bloco_info:
        return bloco_info["mensagem"]
        
    # Puxa a mensagem lá do itens.py
    tile_data = TODOS_TILES.get(tile_id)
    if tile_data and tile_data.mensagem:
        return tile_data.mensagem
        
    return ""

def colocar_bloco(jogador, mapa_dict):
    resultado = obter_bloco_frente(jogador, mapa_dict)
    if not resultado:
        return ""

    nx, ny, tile_id = resultado
    slot = jogador.item_selecionado
    nome_item = jogador.hotbar.get(slot)

    if not nome_item:
        return ""

    from itens import todos_itens
    item = todos_itens.get(nome_item)
    if not item:
        return ""

    from artes import mapas_mundo

    nome_tile_atual = _id_para_nome(mapa_dict, tile_id)

    # --- SISTEMA DE PLANTIO ---
    if item.tipo == "Semente":
        from itens import TODAS_PLANTAS
        planta_info = TODAS_PLANTAS.get(nome_item)

        if not planta_info:
            return "Semente não configurada nas plantas."

        if jogador.estacao_atual not in planta_info.estacoes_plantio:
            return f"A {planta_info.nome} não cresce na {jogador.estacao_atual}."

        if nome_tile_atual not in _NOMES_PLANTAVEL:
            return "A terra precisa estar arada"

        if "plantacoes" not in mapa_dict:
            mapa_dict["plantacoes"] = {}

        mapa_dict["plantacoes"][(nx, ny)] = {
            "semente":         nome_item,
            "dias_idade":      0,
            "regada":          (nome_tile_atual in _NOMES_TERRA_MOLHADA),
            "dias_plantada":   0,
            "dias_penalidade": 0,
            "estrelas_bonus":  0,   # bônus de fertilizante (0-4)
        }

        _atualizar_tile_planta(mapa_dict, nx, ny)

        jogador.adicionar_item(nome_item, -1)

        # XP de plantar via colocar_bloco
        if hasattr(jogador, 'ganhar_xp_hab'):
            from itens import todos_itens as _ti3
            _item_b = _ti3.get(nome_item)
            _bonus_b = getattr(_item_b, 'xp_ganho', 0) if _item_b else 0
            jogador.ganhar_xp_hab('plantar', _bonus_b)

        if jogador.invetario.get(nome_item, 0) <= 0:
            jogador.hotbar[slot] = None

        return ""

    # --- FERTILIZANTE ---
    # Aplica fertilizante na plantação à frente
    if nome_item in ("Fertilizante Basico", "Fertilizante Premium"):
        if "plantacoes" in mapa_dict and (nx, ny) in mapa_dict["plantacoes"]:
            dados_p = mapa_dict["plantacoes"][(nx, ny)]
            bonus_atual = dados_p.get("estrelas_bonus", 0)
            bonus_add   = 2 if nome_item == "Fertilizante Premium" else 1
            if bonus_atual >= 4:
                return "A planta já tem qualidade máxima!"
            dados_p["estrelas_bonus"] = min(4, bonus_atual + bonus_add)
            jogador.adicionar_item(nome_item, -1)
            if jogador.invetario.get(nome_item, 0) <= 0:
                jogador.hotbar[slot] = None
            novo_bonus = dados_p["estrelas_bonus"]
            return f"Fertilizante aplicado! Qualidade: {novo_bonus}★"
        return "Não há plantação aqui para fertilizar."

    # --- COLOCAR BLOCOS NORMAIS (Madeira, Cerca, etc.) ---
    if item.tile_colocar is not None:
        # tile_colocar agora é o nome do tile (string)
        nome_destino = item.tile_colocar
        # Permite colocar em chão, terra arada ou terra molhada
        if nome_tile_atual in {"chao", "terra_arada", "terra_molhada"} or nome_tile_atual == "":
            id_destino = _nome_para_id(mapa_dict, nome_destino)
            if id_destino is None:
                return f"Tile '{nome_destino}' não encontrado no mapa."
            substituir_bloco(mapas_mundo, jogador.mapa_atual, nx, ny, id_destino)

            jogador.adicionar_item(nome_item, -1)
            if jogador.invetario.get(nome_item, 0) <= 0:
                jogador.hotbar[slot] = None
            return ""
        return "Espaço ocupado."

    return ""

def quebrar_bloco(jogador, mapa_dict):
    from artes import mapas_mundo

    res = obter_bloco_frente(jogador, mapa_dict)
    if not res:
        return ""

    nx, ny, tile_id = res
    ferramenta = jogador.itens_equipados.get("Primeira Mão")
    chave = (jogador.mapa_atual, nx, ny)
    custo = 2

    # ==========================================
    # --- REGADOR ---
    # ==========================================
    if ferramenta == "Regador":
        if jogador.mana < custo:
            return "Sem energia."

        # 1. Tem planta em cima da terra → rega a planta
        if "plantacoes" in mapa_dict and (nx, ny) in mapa_dict["plantacoes"]:
            dados = mapa_dict["plantacoes"][(nx, ny)]
            if not dados.get("regada", False):
                jogador.mana -= custo
                dados["regada"] = True
                _atualizar_tile_planta(mapa_dict, nx, ny)
                return "Planta regada!"
            else:
                return "A planta já está regada."

        # 2. Terra arada seca → molha a terra
        nome_tile = _id_para_nome(mapa_dict, tile_id)
        if nome_tile in _NOMES_TERRA_ARADA:
            jogador.mana -= custo
            id_molhada = _nome_para_id(mapa_dict, "terra_molhada")
            if id_molhada is None:
                return "Tile 'terra_molhada' não encontrado no mapa."
            substituir_bloco(mapas_mundo, jogador.mapa_atual, nx, ny, id_molhada)
            return "Terra regada!"

        return "Não dá pra regar isso."

    # Busca TileData pelo nome do tile
    nome_tile = _id_para_nome(mapa_dict, tile_id)
    tile_data = TODOS_TILES.get(nome_tile)

    if not tile_data:
        return ""

    # --- ENCHADA ---
    if ferramenta == "Enchada":
        if tile_data.arar_para is not None:
            if jogador.mana < custo:
                return "Sem energia."
            jogador.mana -= custo
            id_arado = _nome_para_id(mapa_dict, tile_data.arar_para)
            if id_arado is None:
                return f"Tile '{tile_data.arar_para}' não encontrado no mapa."
            substituir_bloco(mapas_mundo, jogador.mapa_atual, nx, ny, id_arado)
            return ""
        return "Não dá pra arar isso."

    # --- OUTRAS FERRAMENTAS ---
    if not tile_data.ferramentas_aceitas:
        return ""

    if ferramenta not in tile_data.ferramentas_aceitas:
        ferramenta_req = list(tile_data.ferramentas_aceitas.keys())[0]
        return f"Precisa de: {ferramenta_req}."

    if jogador.mana < custo:
        return "Sem energia."

    dano = tile_data.ferramentas_aceitas[ferramenta]
    jogador.mana -= custo

    _dano_blocos[chave] = _dano_blocos.get(chave, 0) + dano
    restante = tile_data.hp_max - _dano_blocos[chave]

    if restante <= 0:
        nome_substituir = tile_data.bloco_substituido
        id_substituir = _nome_para_id(mapa_dict, nome_substituir) if nome_substituir else 0
        substituir_bloco(mapas_mundo, jogador.mapa_atual, nx, ny, id_substituir or 0)
        _dano_blocos.pop(chave, None)

        # Entrega drops
        for item_nome, qtd in tile_data.drops.items():
            jogador.adicionar_item(item_nome, qtd)
    return ""

def _acao_dormir(jogador, mapa_dict, nx, ny, bloco_info):
    return "__DORMIR__"

def _acao_loja(jogador, mapa_dict, nx, ny, bloco_info):
    import json as _json
    nomes = bloco_info.get("loja_nomes", "")   # ex: "Semente,Fertilizante"
    tipos = bloco_info.get("loja_tipos", "")   # ex: "Cultivo,Outro"
    if nomes or tipos:
        payload = _json.dumps({"nomes": nomes, "tipos": tipos})
        return f"__ABRIR_LOJA__:{payload}"
    return "__ABRIR_LOJA__"

def _acao_caixa(jogador, mapa_dict, nx, ny, bloco_info):
    return "__ABRIR_CAIXA__"

def _acao_trocar_mapa(jogador, mapa_dict, nx, ny, bloco_info):
    destino = bloco_info.get("destino", "")
    spawn_x = bloco_info.get("spawn_x", None)
    spawn_y = bloco_info.get("spawn_y", None)
    suffix = destino
    if spawn_x is not None: suffix += f"|x{spawn_x}"
    if spawn_y is not None: suffix += f"|y{spawn_y}"
    return f"__TROCAR_MAPA__{suffix}"

# ══════════════════════════════════════════════════════════════════════
#  AÇÕES DE PESCA — tile_mar / tile_lago / tile_mangi
# ══════════════════════════════════════════════════════════════════════
# Retornam "__PESCA__:<tipo>" quando o jogador tem vara equipada,
# ou uma mensagem de erro caso contrário.
# game.py interpreta o retorno assim:
#   if resultado.startswith("__PESCA__:"):
#       tipo = resultado.split(":")[1]
#       estado_pesca = PescaMiniGame(..., tipo_agua=tipo)

def _checar_vara(jogador) -> str:
    """
    Verifica se o jogador tem uma vara de pesca equipada.
    Retorna "" se OK, ou uma mensagem de erro.
    """
    from pesca import VARAS_VALIDAS
    vara = jogador.itens_equipados.get("Primeira Mão", "")
    if vara not in VARAS_VALIDAS:
        return "Equipe uma vara de pesca para pescar aqui."
    return ""

def _acao_tile_mar(jogador, mapa_dict, nx, ny, bloco_info):
    erro = _checar_vara(jogador)
    if erro:
        return erro
    return "__PESCA__:tile_mar"

def _acao_tile_lago(jogador, mapa_dict, nx, ny, bloco_info):
    erro = _checar_vara(jogador)
    if erro:
        return erro
    return "__PESCA__:tile_lago"

def _acao_tile_mangi(jogador, mapa_dict, nx, ny, bloco_info):
    erro = _checar_vara(jogador)
    if erro:
        return erro
    return "__PESCA__:tile_mangi"

def verificar_passagem(jogador, mapa_dict):
    """
    Verifica se o tile onde o jogador ESTÁ tem ação trocar_mapa com
    tipo_trocar == 'passagem'. Retorna o resultado de trocar_mapa ou ''.
    """
    mapa = mapa_dict["arte"]
    map_rows = len(mapa)
    map_cols = len(mapa[0]) if map_rows > 0 else 0
    gx, gy = jogador.grid_x, jogador.grid_y
    if not (0 <= gx < map_cols and 0 <= gy < map_rows):
        return ""
    tile_id    = mapa[gy][gx]
    blocos     = _get_blocos(mapa_dict)
    bloco_info = blocos.get(tile_id, {})
    acao_obj   = bloco_info.get("acao", "")
    nome_obj   = bloco_info.get("nome", "")
    tipo       = bloco_info.get("tipo_trocar", "porta")
    if tipo != "passagem":
        return ""
    # Só dispara se a ação for trocar_mapa (por nome ou ação)
    if nome_obj == "trocar_mapa" or acao_obj == "trocar_mapa":
        return _acao_trocar_mapa(jogador, mapa_dict, gx, gy, bloco_info)
    return ""

# ══════════════════════════════════════════════════════════════════════
#  SISTEMA DE BAÚ
# ══════════════════════════════════════════════════════════════════════

# Armazenamento persistente dos baús: { nome_bau: { nome_item: qtd } }
_baus_mundo = {}

# Constantes de animação / UI
BAU_ANIM_TICKS_POR_FRAME = 10
BAU_COLS                 = 6
BAU_ROWS                 = 6
BAU_SLOTS                = BAU_COLS * BAU_ROWS      # 36 slots posicionais
BAU_SLOT_W, BAU_SLOT_H   = 16, 16
BAU_SLOT_PAD             = 2
BAU_ITENS_POR_PAG        = BAU_SLOTS   # compatibilidade

# O baú usa lista posicional de 36 slots: _baus_mundo[chave] = [(nome,qtd)|None, ...]

def _base_nome_bau(nome):
    """'bau2' -> 'bau'  |  'bau_grande1' -> 'bau_grande'"""
    i = len(nome)
    while i > 0 and nome[i - 1].isdigit():
        i -= 1
    return nome[:i]

def _frames_bau(mapa_dict, nome_bau):
    base = _base_nome_bau(nome_bau)
    frames = {}
    for tid, info in mapa_dict.get("blocos", {}).items():
        n = info.get("nome", "")
        if n.startswith(base) and len(n) > len(base) and n[len(base):].isdigit():
            frames[int(n[len(base):])] = tid
    return [frames[k] for k in sorted(frames)]

def _chave_bau(nome_bau):
    return _base_nome_bau(nome_bau)

def _slots_bau(nome_bau):
    """Retorna (criando se necessário) a lista posicional de 36 slots do baú."""
    chave = _chave_bau(nome_bau)
    if chave not in _baus_mundo:
        _baus_mundo[chave] = [None] * BAU_SLOTS
    # Migração: se for dict antigo, converte para lista
    if isinstance(_baus_mundo[chave], dict):
        old   = _baus_mundo[chave]
        slots = [None] * BAU_SLOTS
        for i, (nome, qtd) in enumerate(old.items()):
            if i >= BAU_SLOTS:
                break
            slots[i] = (nome, qtd)
        _baus_mundo[chave] = slots
    return _baus_mundo[chave]

def _itens_bau(nome_bau):
    """Compatibilidade: retorna dict {nome: qtd} a partir da lista de slots."""
    slots = _slots_bau(nome_bau)
    d = {}
    for s in slots:
        if s:
            nome, qtd = s
            d[nome] = d.get(nome, 0) + qtd
    return d

def _inv_como_slots(jogador):
    """Converte inventário do jogador em lista de (nome, qtd) para exibição."""
    return [(n, q) for n, q in jogador.invetario.items() if q > 0]

def _acao_bau(jogador, mapa_dict, nx, ny, bloco_info):
    nome = bloco_info.get("nome", "bau")
    return f"__ABRIR_BAU__{nome}"

def _registrar_baus_do_mapa(mapa_dict):
    """Registra ação de baú para qualquer tile cujo nome comece com 'bau'."""
    for tid, info in mapa_dict.get("blocos", {}).items():
        nome = info.get("nome", "")
        if nome.startswith("bau"):
            _ACOES_NOME[nome] = _acao_bau

def inicializar_estado_bau():
    return {
        'mostrar_bau':    False,
        'bau_nome':       "",
        'bau_painel':     "bau",     # "bau" | "inv"
        'bau_cursor':     0,
        'bau_anim_tick':  0,
        'bau_anim_fase':  "abrindo",
        'bau_msg':        "",
        # sub-estado: escolha de quantidade (pegar/guardar/descartar)
        'bau_modo_qtd':   False,
        'bau_item_sel':   None,
        'bau_qtd_cursor': 1,
        'bau_qtd_acao':   "transferir",  # "transferir" | "descartar"
    }

def atualizar_bau(v, jogador, estado_bau, mapa_dict):
    eb = estado_bau

    # ── Animação ─────────────────────────────────────────────────────────────
    if eb['bau_anim_fase'] == "abrindo":
        frames = _frames_bau(mapa_dict, eb['bau_nome'])
        if not frames:
            eb['bau_anim_fase'] = "aberto"
            return
        eb['bau_anim_tick'] += 1
        if eb['bau_anim_tick'] >= len(frames) * BAU_ANIM_TICKS_POR_FRAME:
            eb['bau_anim_fase'] = "aberto"
            eb['bau_anim_tick'] = 0
        return

    slots_bau = _slots_bau(eb['bau_nome'])
    inv_slots  = _inv_como_slots(jogador)
    INV_TOTAL  = len(inv_slots)

    # =========================================================================
    # SUB-ESTADO: escolha de quantidade (pegar / guardar / descartar)
    # =========================================================================
    if eb['bau_modo_qtd']:
        nome  = eb['bau_item_sel']
        acao  = eb['bau_qtd_acao']

        if acao == "descartar":
            qtd_disp = sum(s[1] for s in slots_bau if s and s[0] == nome)
        elif eb['bau_painel'] == "bau":
            qtd_disp = sum(s[1] for s in slots_bau if s and s[0] == nome)
        else:
            qtd_disp = jogador.invetario.get(nome, 0)
        max_qtd = max(1, qtd_disp)

        if v.key_pressed(b"up"):
            eb['bau_qtd_cursor'] = min(eb['bau_qtd_cursor'] + 1, max_qtd)
        elif v.key_pressed(b"down"):
            eb['bau_qtd_cursor'] = max(eb['bau_qtd_cursor'] - 1, 1)
        elif v.key_pressed(b"z"):
            qtd = eb['bau_qtd_cursor']
            if acao == "descartar":
                # Remove do baú
                restante = qtd
                for i, s in enumerate(slots_bau):
                    if s and s[0] == nome and restante > 0:
                        tirar = min(s[1], restante)
                        nova  = s[1] - tirar
                        slots_bau[i] = (nome, nova) if nova > 0 else None
                        restante -= tirar
                eb['bau_msg'] = f"Descartou {qtd - restante}x {nome}."
            elif eb['bau_painel'] == "bau":
                # Pega do baú → inventário
                restante = qtd
                for i, s in enumerate(slots_bau):
                    if s and s[0] == nome and restante > 0:
                        tirar = min(s[1], restante)
                        nova  = s[1] - tirar
                        slots_bau[i] = (nome, nova) if nova > 0 else None
                        restante -= tirar
                jogador.adicionar_item(nome, qtd - restante)
                eb['bau_msg'] = f"Pegou {qtd - restante}x {nome}."
            else:
                # Guarda inventário → baú
                real = min(qtd, jogador.invetario.get(nome, 0))
                jogador.remover_item(nome, real)
                if jogador.invetario.get(nome, 0) <= 0:
                    for s in range(1, 10):
                        if jogador.hotbar.get(s) == nome:
                            jogador.hotbar[s] = None
                for i in range(BAU_SLOTS):
                    if slots_bau[i] is None:
                        slots_bau[i] = (nome, real)
                        break
                else:
                    jogador.adicionar_item(nome, real)
                    eb['bau_msg'] = "Bau cheio!"
                    eb['bau_modo_qtd'] = False
                    eb['bau_item_sel'] = None
                    eb['bau_qtd_cursor'] = 1
                    return
                eb['bau_msg'] = f"Guardou {real}x {nome}."
            eb['bau_modo_qtd']   = False
            eb['bau_item_sel']   = None
            eb['bau_qtd_cursor'] = 1
        elif v.key_pressed(b"space") or v.key_pressed(b"x"):
            eb['bau_modo_qtd']   = False
            eb['bau_item_sel']   = None
            eb['bau_qtd_cursor'] = 1
            eb['bau_msg']        = ""
        return

    # =========================================================================
    # NAVEGAÇÃO PRINCIPAL
    # =========================================================================
    if v.key_pressed(b"space"):
        eb['mostrar_bau'] = False
        eb['bau_msg']     = ""
        return

    # Enter — alterna foco bau <-> inv
    if v.key_pressed(b"return"):
        eb['bau_painel'] = "inv" if eb['bau_painel'] == "bau" else "bau"
        eb['bau_cursor'] = 0
        eb['bau_msg']    = ""
        return

    if eb['bau_painel'] == "bau":
        cursor  = eb['bau_cursor']
        max_idx = BAU_SLOTS - 1
        if v.key_pressed(b"down"):  cursor = min(cursor + BAU_COLS, max_idx)
        if v.key_pressed(b"up"):    cursor = max(cursor - BAU_COLS, 0)
        if v.key_pressed(b"right"): cursor = min(cursor + 1, max_idx)
        if v.key_pressed(b"left"):  cursor = max(cursor - 1, 0)
        eb['bau_cursor'] = cursor

        item_atual = slots_bau[cursor]

        # Z — pega item do baú → inventário
        if v.key_pressed(b"z") and item_atual is not None:
            nome, qtd = item_atual
            if qtd > 1:
                eb['bau_modo_qtd']   = True
                eb['bau_item_sel']   = nome
                eb['bau_qtd_cursor'] = 1
                eb['bau_qtd_acao']   = "transferir"
            else:
                slots_bau[cursor] = None
                jogador.adicionar_item(nome, 1)
                eb['bau_msg'] = f"Pegou 1x {nome}."

        # X — jogar fora item do baú
        elif v.key_pressed(b"x") and item_atual is not None:
            nome, qtd = item_atual
            if qtd > 1:
                eb['bau_modo_qtd']   = True
                eb['bau_item_sel']   = nome
                eb['bau_qtd_cursor'] = 1
                eb['bau_qtd_acao']   = "descartar"
            else:
                slots_bau[cursor] = None
                eb['bau_msg'] = f"Descartou 1x {nome}."

    else:
        INV_COLS_NAV = 5
        cursor  = eb['bau_cursor']
        max_idx = max(0, INV_TOTAL - 1)
        if v.key_pressed(b"down"):  cursor = min(cursor + INV_COLS_NAV, max_idx)
        if v.key_pressed(b"up"):    cursor = max(cursor - INV_COLS_NAV, 0)
        if v.key_pressed(b"right"): cursor = min(cursor + 1, max_idx)
        if v.key_pressed(b"left"):  cursor = max(cursor - 1, 0)
        eb['bau_cursor'] = cursor

        # Z — guarda item no baú
        if v.key_pressed(b"z") and cursor < INV_TOTAL:
            nome, qtd = inv_slots[cursor]
            tem_vazio = any(s is None for s in slots_bau)
            if not tem_vazio:
                eb['bau_msg'] = "Bau cheio!"
            elif qtd > 1:
                eb['bau_modo_qtd']   = True
                eb['bau_item_sel']   = nome
                eb['bau_qtd_cursor'] = 1
                eb['bau_qtd_acao']   = "transferir"
            else:
                jogador.remover_item(nome, 1)
                if jogador.invetario.get(nome, 0) <= 0:
                    for s in range(1, 10):
                        if jogador.hotbar.get(s) == nome:
                            jogador.hotbar[s] = None
                for i in range(BAU_SLOTS):
                    if slots_bau[i] is None:
                        slots_bau[i] = (nome, 1)
                        break
                eb['bau_msg'] = f"Guardou 1x {nome}."

def desenhar_bau(v, jogador, estado_bau, mapa_dict,
                 box_sid, font_sid, itens_sprite_ids, SCREEN_W, SCREEN_H):
    from itens import todos_itens as _ti
    from funcoes import (
        _draw_icone_coracao, _draw_icone_coxa_frango, _draw_icone_moeda,
        _draw_estrela_5x5, _COR_ESTRELA, _nome_sem_estrela,
    )
    eb = estado_bau
    FW, FH = 8, 8

    # ── Animação ─────────────────────────────────────────────────────────────
    if eb['bau_anim_fase'] == "abrindo":
        frames = _frames_bau(mapa_dict, eb['bau_nome'])
        if frames:
            frame_idx = min(eb['bau_anim_tick'] // BAU_ANIM_TICKS_POR_FRAME, len(frames) - 1)
            tid  = frames[frame_idx]
            info = mapa_dict.get("blocos", {}).get(tid, {})
            cx   = (SCREEN_W - info.get("w", 16)) // 2
            cy   = (SCREEN_H - info.get("h", 16)) // 2
            sid  = itens_sprite_ids.get(info.get("sprite", b""))
            if sid is not None:
                rx = info.get("start_x", 0) + info.get("col", 0) * info.get("w", 16)
                ry = info.get("start_y", 0) + info.get("l",   0) * info.get("h", 16)
                v.draw_rect(0, 0, SCREEN_W, SCREEN_H, 0, 0, 0)
                v.draw_sprite_part(sid, cx, cy, rx, ry, info.get("w", 16), info.get("h", 16))
        v.draw_text_box(x=0, y=SCREEN_H - 28, box_w=SCREEN_W, box_h=48,
                        title="", content="Abrindo...",
                        box_sid=box_sid, box_tw=8, box_th=8,
                        font_sid=font_sid, font_w=FW, font_h=FH, line_spacing=2)
        return

    slots_bau = _slots_bau(eb['bau_nome'])
    inv_slots  = _inv_como_slots(jogador)

    # ── Sub-tela de quantidade ────────────────────────────────────────────────
    if eb['bau_modo_qtd']:
        nome    = eb['bau_item_sel']
        qtd_cur = eb['bau_qtd_cursor']
        acao    = eb['bau_qtd_acao']
        if acao == "descartar":
            qtd_disp  = sum(s[1] for s in slots_bau if s and s[0] == nome)
            acao_txt  = "Descartar"
        elif eb['bau_painel'] == "bau":
            qtd_disp  = sum(s[1] for s in slots_bau if s and s[0] == nome)
            acao_txt  = "Pegar"
        else:
            qtd_disp  = jogador.invetario.get(nome, 0)
            acao_txt  = "Guardar"
        conteudo = (
            f"{nome}\n"
            f"Disponivel: x{qtd_disp}\n"
            f"------------------------\n\n"
            f"Quantidade:\n\n"
            f"  [ {qtd_cur:>3} ]\n\n"
            f"------------------------\n"
            f"Cima/Baixo: ajustar\n"
            f"Z: {acao_txt}   X: Cancelar"
        )
        v.draw_text_box(x=0, y=0, box_w=SCREEN_W, box_h=SCREEN_H,
                        title="Quantos?", content=conteudo,
                        box_sid=box_sid, box_tw=8, box_th=8,
                        font_sid=font_sid, font_w=FW, font_h=FH, line_spacing=2)
        return

    # =========================================================================
    # LAYOUT PRINCIPAL — dimensões reduzidas e centralizadas
    # =========================================================================
    SLOT_S  = 16          # slot menor (era BAU_SLOT_W, provavelmente 16 ou 18)
    SLOT_P  = 2           # padding entre slots
    BTH     = 8           # borda da caixa (box_tw)
    MY      = 6           # margem vertical

    # Baú: 5 colunas × 6 linhas
    BAU_COLS_D = 8
    BAU_ROWS_D = 3
    BAU_GRID_W = 100   # 5*16-2 = 78
    BAU_BOX_W  = BAU_GRID_W + BTH * 2 + 2 + 40                  # 78+18 = 96
    BAU_BOX_H  = SCREEN_H - MY * 2                           # 232

    # Inventário: 5 colunas
    INV_COLS_D  = 8
    INV_TOTAL_D = getattr(jogador, 'espacos_inventario', 12)
    INV_ROWS_D  = (INV_TOTAL_D + INV_COLS_D - 1) // INV_COLS_D
    INV_GRID_W  = 100   # 78
    INV_BOX_W   = INV_GRID_W + BTH * 2 + 2 + 40                   # 96

    GAP = 4
    TOTAL_W = BAU_BOX_W + GAP + INV_BOX_W                    # 196
    MX = (SCREEN_W - TOTAL_W) // 2                           # centralizado

    INV_BOX_X = MX + BAU_BOX_W + GAP

    GX  = MX + BTH + 1
    GY  = MY + BTH + FH + 6

    IGX = INV_BOX_X + BTH + 1
    IGY = GY

    BAU_IPW = BAU_BOX_W - BTH * 2 - 2
    IPW     = INV_BOX_W - BTH * 2 - 2
    max_c   = max(1, IPW // FW)

    INNER_BOT     = MY + BAU_BOX_H - BTH
    INNER_BOT_INV = INNER_BOT

    cursor     = eb['bau_cursor']
    inv_cursor = eb['bau_cursor'] if eb['bau_painel'] == "inv" else 0
    # ── Títulos das caixas ────────────────────────────────────────────────────
    titulo_bau = "Bau [foco]" if eb['bau_painel'] == "bau" else "Bau"
    v.draw_text_box(x=MX, y=MY, box_w=BAU_BOX_W, box_h=BAU_BOX_H,
                    title=titulo_bau, content="",
                    box_sid=box_sid, box_tw=BTH, box_th=BTH,
                    font_sid=font_sid, font_w=FW, font_h=FH)

    titulo_inv = "Inventario [foco]" if eb['bau_painel'] == "inv" else "Inventario"
    v.draw_text_box(x=INV_BOX_X, y=MY, box_w=INV_BOX_W, box_h=BAU_BOX_H,
                    title=titulo_inv, content="",
                    box_sid=box_sid, box_tw=BTH, box_th=BTH,
                    font_sid=font_sid, font_w=FW, font_h=FH)

    # ── helper: desenha um slot ───────────────────────────────────────────────
    def _slot(sx, sy, item, sel):
        if sel:
            v.draw_rect(sx - 1, sy - 1, SLOT_S + 2, SLOT_S + 2, 255, 220, 80)
            v.draw_rect(sx, sy, SLOT_S, SLOT_S, 35, 35, 35)
        else:
            v.draw_rect(sx, sy, SLOT_S, SLOT_S, 20, 20, 20)
            v.draw_rect(sx,            sy,            SLOT_S, 1, 80, 80, 80)
            v.draw_rect(sx,            sy,            1, SLOT_S, 80, 80, 80)
            v.draw_rect(sx + SLOT_S-1, sy,            1, SLOT_S, 80, 80, 80)
            v.draw_rect(sx,            sy + SLOT_S-1, SLOT_S, 1, 80, 80, 80)
        if item:
            nome_i, qtd_i = item
            obj_i = _ti.get(nome_i)
            if obj_i and itens_sprite_ids:
                sid = itens_sprite_ids.get(obj_i.sprite)
                if sid is not None:
                    rx, ry2, iw, ih = obj_i.get_sprite_rect()
                    ox = sx + (SLOT_S - min(iw, SLOT_S)) // 2
                    oy = sy + (SLOT_S - min(ih, SLOT_S)) // 2
                    v.draw_sprite_part(sid, ox, oy, rx, ry2,
                                       min(iw, SLOT_S), min(ih, SLOT_S))
            # ── estrela de qualidade (canto inferior-esquerdo) ────────────────
            if obj_i and hasattr(jogador, 'bonus_estrelas_item'):
                _est = jogador.bonus_estrelas_item(obj_i)
                if _est > 0:
                    _cor = _COR_ESTRELA.get(_est, (80, 80, 80))
                    _draw_estrela_5x5(v, sx, sy + SLOT_S - 5,
                                      _cor[0], _cor[1], _cor[2])

    # ── Grade do baú ─────────────────────────────────────────────────────────
    for idx in range(BAU_COLS_D * BAU_ROWS_D):
        row = idx // BAU_COLS_D
        col = idx % BAU_COLS_D
        sx  = GX + col * (SLOT_S + SLOT_P)
        sy  = GY + row * (SLOT_S + SLOT_P)
        sel = (idx == cursor) and eb['bau_painel'] == "bau"
        item = slots_bau[idx] if idx < len(slots_bau) else None
        _slot(sx, sy, item, sel)

    # ── Grade do inventário ───────────────────────────────────────────────────
    for idx in range(INV_TOTAL_D):
        row = idx // INV_COLS_D
        col = idx % INV_COLS_D
        sx  = IGX + col * (SLOT_S + SLOT_P)
        sy  = IGY + row * (SLOT_S + SLOT_P)
        item = inv_slots[idx] if idx < len(inv_slots) else None
        sel  = (idx == inv_cursor) and eb['bau_painel'] == "inv"
        _slot(sx, sy, item, sel)

    # ── Painel de descrição + preço ──────────────────────────────────────────
    # Determina item com foco
    if eb['bau_painel'] == "bau" and cursor < len(slots_bau) and slots_bau[cursor]:
        nome_d, qtd_d = slots_bau[cursor]
    elif eb['bau_painel'] == "inv" and inv_cursor < len(inv_slots):
        nome_d, qtd_d = inv_slots[inv_cursor]
    else:
        nome_d = None
        qtd_d  = 0

    obj_d = _ti.get(nome_d) if nome_d else None

    # Área de descrição abaixo das grades do inventário
    INV_GRID_H = INV_ROWS_D * (SLOT_S + SLOT_P) - SLOT_P
    DESC_Y = IGY + INV_GRID_H + 5

    if nome_d and obj_d:
        # ── linha separadora ─────────────────────────────────────────────────
        for sx in range(0, IPW, 4):
            v.draw_rect(IGX + sx, DESC_Y - 2, 2, 1, 120, 100, 50)

        # ── ícone do item + nome + tipo ──────────────────────────────────────
        ICON  = 16
        _nome_base = _nome_sem_estrela(nome_d)
        _max_c = max(1, (IPW - ICON - 5) // FW)
        # fundo do slot do ícone (igual ao slot normal)
        v.draw_rect(IGX, DESC_Y, ICON, ICON, 20, 20, 20)
        v.draw_rect(IGX,          DESC_Y,          ICON, 1, 80, 80, 80)
        v.draw_rect(IGX,          DESC_Y,          1, ICON, 80, 80, 80)
        v.draw_rect(IGX + ICON-1, DESC_Y,          1, ICON, 80, 80, 80)
        v.draw_rect(IGX,          DESC_Y + ICON-1, ICON, 1, 80, 80, 80)
        # sprite do item
        if itens_sprite_ids:
            _sid_d = itens_sprite_ids.get(obj_d.sprite)
            if _sid_d is not None:
                _rx, _ry, _iw, _ih = obj_d.get_sprite_rect()
                _ox = IGX + (ICON - min(_iw, ICON)) // 2
                _oy = DESC_Y + (ICON - min(_ih, ICON)) // 2
                v.draw_sprite_part(_sid_d, _ox, _oy,
                                   _rx, _ry, min(_iw, ICON), min(_ih, ICON))
        TX = IGX + ICON + 4
        v.draw_text(TX, DESC_Y, _nome_base[:_max_c],
                    font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(TX, DESC_Y + FH + 2,
                    f"[{obj_d.tipo}]"[:_max_c],
                    font_sid=font_sid, font_w=FW, font_h=FH)

        DESC_Y += ICON + 5

        # ── estrela de qualidade ─────────────────────────────────────────────
        if hasattr(jogador, 'bonus_estrelas_item'):
            _est_d = jogador.bonus_estrelas_item(obj_d)
            _nomes_est = {1: "Bronze", 2: "Prata", 3: "Ouro", 4: "Platina"}
            if _est_d > 0:
                _cor_e = _COR_ESTRELA.get(_est_d, (80, 80, 80))
                _draw_estrela_5x5(v, IGX, DESC_Y,
                                  _cor_e[0], _cor_e[1], _cor_e[2])
                v.draw_text(IGX + 8, DESC_Y,
                            _nomes_est.get(_est_d, "")[:_max_c - 2],
                            font_sid=font_sid, font_w=FW, font_h=FH)
                DESC_Y += FH + 3

        # ── separador ────────────────────────────────────────────────────────
        for sx in range(0, IPW, 4):
            v.draw_rect(IGX + sx, DESC_Y, 2, 1, 120, 100, 50)
        DESC_Y += 5

        # ── quantidade na mochila/bau ─────────────────────────────────────────
        # ícone mochila pixel-art 8×7
        v.draw_rect(IGX + 2, DESC_Y,     4, 1, 200, 170, 90)
        v.draw_rect(IGX + 1, DESC_Y,     1, 2, 200, 170, 90)
        v.draw_rect(IGX + 6, DESC_Y,     1, 2, 200, 170, 90)
        v.draw_rect(IGX,     DESC_Y + 2, 8, 5, 160, 130, 60)
        v.draw_rect(IGX + 1, DESC_Y + 6, 6, 1, 140, 110, 50)
        v.draw_text(IGX + 11, DESC_Y + 1, f"x{qtd_d}",
                    font_sid=font_sid, font_w=FW, font_h=FH)
        DESC_Y += FH + 5

        # ── separador ────────────────────────────────────────────────────────
        for sx in range(0, IPW, 4):
            v.draw_rect(IGX + sx, DESC_Y, 2, 1, 120, 100, 50)
        DESC_Y += 5

        # ── descrição (word-wrap compacto) ────────────────────────────────────
        desc     = getattr(obj_d, 'descrica', '') or ''
        limite_d = INNER_BOT_INV - FH * 4 - 12   # reserva espaço pros stats
        linha_d  = ""
        for palavra in desc.split():
            if DESC_Y + FH > limite_d:
                break
            if not linha_d:
                linha_d = palavra
            elif len(linha_d) + 1 + len(palavra) <= max_c:
                linha_d += " " + palavra
            else:
                v.draw_text(IGX, DESC_Y, linha_d,
                            font_sid=font_sid, font_w=FW, font_h=FH)
                DESC_Y += FH + 1
                linha_d = palavra
        if linha_d and DESC_Y + FH <= limite_d:
            v.draw_text(IGX, DESC_Y, linha_d,
                        font_sid=font_sid, font_w=FW, font_h=FH)
            DESC_Y += FH + 2

        # ── Stats: HP, STM, Gold ──────────────────────────────────────────────
        stats_hp  = getattr(obj_d, 'recupar_hp', 0) or 0
        stats_st  = getattr(obj_d, 'recupar_mn', 0) or 0
        stats_hpm = getattr(obj_d, 'bonus_hp',   0) or 0
        stats_g   = getattr(obj_d, 'preco',       0) or 0
        limite_st = INNER_BOT_INV - 4

        if stats_hp or stats_st or stats_hpm or stats_g:
            for sx in range(0, IPW, 4):
                v.draw_rect(IGX + sx, DESC_Y, 2, 1, 120, 100, 50)
            DESC_Y += 5

            if stats_hp and DESC_Y + FH <= limite_st:
                _draw_icone_coracao(v, IGX, DESC_Y)
                v.draw_text(IGX + 11, DESC_Y, f"HP  +{stats_hp}",
                            font_sid=font_sid, font_w=FW, font_h=FH)
                DESC_Y += FH + 3

            if stats_hpm and DESC_Y + FH <= limite_st:
                _draw_icone_coracao(v, IGX, DESC_Y, r=180, g=80, b=200)
                v.draw_text(IGX + 11, DESC_Y, f"HPmax +{stats_hpm}",
                            font_sid=font_sid, font_w=FW, font_h=FH)
                DESC_Y += FH + 3

            if stats_st and DESC_Y + FH <= limite_st:
                _draw_icone_coxa_frango(v, IGX, DESC_Y)
                v.draw_text(IGX + 11, DESC_Y, f"STM +{stats_st}",
                            font_sid=font_sid, font_w=FW, font_h=FH)
                DESC_Y += FH + 3

            if stats_g and DESC_Y + FH <= limite_st:
                _draw_icone_moeda(v, IGX, DESC_Y)
                v.draw_text(IGX + 11, DESC_Y, f"{stats_g}G",
                            font_sid=font_sid, font_w=FW, font_h=FH)

    # ── Rodapé baú ────────────────────────────────────────────────────────────
    rod_y = INNER_BOT - FH * 2 - 15
    for sx in range(0, BAU_IPW, 4):
        v.draw_rect(MX + BTH + sx, rod_y - 2, 2, 1, 180, 155, 60)

    msg = eb.get('bau_msg', '')
    if msg:
        v.draw_text(MX + BTH, rod_y, msg[:BAU_IPW // FW],
                    font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(MX + BTH, rod_y + FH + 1,
                    "Enter:trocar"[:BAU_IPW // FW],
                    font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(MX + BTH, rod_y + FH + 11,
                    "Space:sair"[:BAU_IPW // FW],
                    font_sid=font_sid, font_w=FW, font_h=FH)
    else:
        if eb['bau_painel'] == "bau":
            ctrl  = "Z:pegar X:fora"
            ctrl2 = "Enter:inventario"
            ctrl3 = "Space:sair"
        else:
            ctrl  = "Z:guardar"
            ctrl2 = "Enter:bau"
            ctrl3 = "Space:sair"
        v.draw_text(MX + BTH, rod_y, ctrl[:BAU_IPW // FW],
                    font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(MX + BTH, rod_y + FH + 1, ctrl2[:BAU_IPW // FW],
                    font_sid=font_sid, font_w=FW, font_h=FH)
        v.draw_text(MX + BTH, rod_y + FH + 11, ctrl3[:BAU_IPW // FW],
                    font_sid=font_sid, font_w=FW, font_h=FH)

def serializar_baus():
    """Retorna cópia serializável do estado dos baús (para salvar_jogo)."""
    return {k: list(v) for k, v in _baus_mundo.items()}

def desserializar_baus(dados):
    """Restaura o estado dos baús a partir de dados carregados (para carregar_jogo)."""
    global _baus_mundo
    _baus_mundo = {k: list(v) for k, v in dados.items()}


# ── Registro de baús como ação nomeada ─────────────────────────────────────
_ACOES_NOME = {
    "loja":        _acao_loja,
    "caixa":       _acao_caixa,
    "cama":        _acao_dormir,
    "trocar_mapa": _acao_trocar_mapa,
    # Tipos de água — disparados via editor com nome do tile
    "tile_mar":    _acao_tile_mar,
    "tile_lago":   _acao_tile_lago,
    "tile_mangi":  _acao_tile_mangi,
}

# Fallback legado: JSONs antigos sem campo "nome" ainda funcionam por ID
_ACOES_TILE_LEGADO = {
    11: _acao_loja,
    12: _acao_caixa,
    13: _acao_dormir,
}

def registrar_acao(nome_obj, funcao):
    """Registra uma nova ação pelo nome do objeto (para mods / expansões)."""
    _ACOES_NOME[nome_obj] = funcao

def registrar_acao_tile(tile_id, funcao):
    """Legado: registra ação por ID numérico."""
    _ACOES_TILE_LEGADO[tile_id] = funcao

def verificar_interacao(jogador, mapa_dict):
    resultado = obter_bloco_frente(jogador, mapa_dict)
    if not resultado:
        return ""

    nx, ny, tile_id = resultado
    blocos     = _get_blocos(mapa_dict)
    bloco_info = blocos.get(tile_id, {})

    # 1. Plantas têm prioridade absoluta
    if "plantacoes" in mapa_dict and (nx, ny) in mapa_dict["plantacoes"]:
        return colher_planta(jogador, mapa_dict, nx, ny)

    nome_obj  = bloco_info.get("nome", "")
    acao_obj  = bloco_info.get("acao", "")
    tipo_troca = bloco_info.get("tipo_trocar", "porta")

    # 2. Tiles de passagem (pisar) NÃO respondem ao Z — ignorar aqui
    is_troca = (nome_obj == "trocar_mapa" or acao_obj == "trocar_mapa")
    if is_troca and tipo_troca == "passagem":
        return ""

    # 3. Resolve pelo NOME do objeto (sistema novo — vem do editor)
    if nome_obj and nome_obj in _ACOES_NOME:
        return _ACOES_NOME[nome_obj](jogador, mapa_dict, nx, ny, bloco_info)
    if acao_obj and acao_obj in _ACOES_NOME:
        return _ACOES_NOME[acao_obj](jogador, mapa_dict, nx, ny, bloco_info)

    # 4. Fallback legado: resolve por ID numérico (JSONs sem nome configurado)
    if tile_id in _ACOES_TILE_LEGADO:
        return _ACOES_TILE_LEGADO[tile_id](jogador, mapa_dict, nx, ny, bloco_info)

    # 5. Bloco sólido sem ação conhecida → exibe mensagem ou genérico
    if bloco_info.get("solid", False):
        return verificar_interacao_mensagem(jogador, mapa_dict) or "Não consigo passar."

    return ""

# ══════════════════════════════════════════════════════════════════════
#  SISTEMA DE NPCs
# ══════════════════════════════════════════════════════════════════════

# ---------- Portais como dicionário compatível com NPC.atualizar_tick ----------

def _portais_do_mapa(mapa_dict):
    """
    Extrai os portais de um mapa_dict no formato que o NPC.atualizar_tick espera:
        { (tx, ty): {"destino": str, "spawn": (sx, sy)} }

    Lê diretamente dos blocos: tiles com nome/acao == "trocar_mapa".
    """
    portais = {}
    blocos  = mapa_dict.get("blocos", {})
    mapa    = mapa_dict.get("arte", [])
    map_rows = len(mapa)
    map_cols = len(mapa[0]) if map_rows > 0 else 0

    for vy in range(map_rows):
        for vx in range(map_cols):
            tile_id    = mapa[vy][vx]
            bloco_info = blocos.get(tile_id, {})
            nome_obj   = bloco_info.get("nome", "")
            acao_obj   = bloco_info.get("acao", "")
            if nome_obj == "trocar_mapa" or acao_obj == "trocar_mapa":
                destino = bloco_info.get("destino", "")
                sx      = bloco_info.get("spawn_x", vx)
                sy      = bloco_info.get("spawn_y", vy)
                if destino:
                    portais[(vx, vy)] = {"destino": destino, "spawn": (sx, sy)}
    return portais

# ---------- Tick central: move todos os NPCs num frame --------------------

_TICK_NPC = 6   # avança 1 passo de grid a cada N frames

def atualizar_npcs(frame_contador, jogador, mapas_mundo):
    """
    Deve ser chamado todo frame no loop principal do game.py.

    - A cada frame: desliza os pixels e anima.
    - A cada _TICK_NPC frames: decide o próximo tile (pathfinding/agenda).

    Colisão bidirecional:
      - NPC não entra em tile ocupado pelo jogador.
      - NPC não entra em tile ocupado por outro NPC.
      - (O player já checa NPCs no lado dele via _todos_npcs.)
    """
    from itens import todos_npcs
    from artes import mapas_mundo as _mw

    nome_mapa_player = jogador.mapa_atual
    # Conjunto rápido de posições ocupadas: (mapa, x, y)
    # Rebuild a cada tick de pathfinding, não todo frame (custo baixo)
    def _posicoes_bloqueadas_npc(npc_ignorado):
        """Retorna set de (mapa, x, y) de todos os NPCs exceto o atual."""
        return {(n.mapa_atual, n.x, n.y)
                for n in todos_npcs.values() if n is not npc_ignorado}

    for npc in todos_npcs.values():
        # ── Deslizamento de pixel (todo frame) ──────────────────────────
        npc._deslizar()
        npc.animar()

        # ── Pathfinding (a cada N frames) ───────────────────────────────
        if frame_contador % _TICK_NPC != 0:
            continue

        mapa_npc = mapas_mundo.get(npc.mapa_atual)
        if not mapa_npc:
            continue

        mapa_art  = mapa_npc.get("arte", [])
        blocos    = mapa_npc.get("blocos", {})
        portais   = _portais_do_mapa(mapa_npc)

        # Posições proibidas: jogador + outros NPCs
        pos_player = (jogador.mapa_atual, jogador.grid_x, jogador.grid_y)
        pos_npcs   = _posicoes_bloqueadas_npc(npc)

        npc.atualizar_tick(
            jogador.horas, jogador.minutos,
            mapa_art, blocos,
            nome_mapa_player, portais,
            pos_player=pos_player,
            pos_outros_npcs=pos_npcs,
        )

def resetar_npcs_dia():
    """Chame ao dormir: volta todos os NPCs ao spawn e reseta flags diárias."""
    from itens import todos_npcs
    for npc in todos_npcs.values():
        npc.resetar_dia()

# ---------- Conversa -------------------------------------------------------

def dar_presente(jogador, npc, item_obj):
    # Regras de limite
    if npc.recebeu_presente_hoje:
        return False, f"{npc.nome} já recebeu um presente hoje!"
    
    # Checa se é aniversário (Exemplo: jogador.dia == npc.aniversario_dia)
    eh_aniversario = False 
    if hasattr(jogador, 'dia') and npc.aniversario == (jogador.estacao_idx, jogador.dias):
        eh_aniversario = True

    if npc.presentes_semana >= 2 and not eh_aniversario:
        return False, f"{npc.nome} não quer mais presentes esta semana."

    # Cálculo de pontos baseado na sua nova lógica
    pontos = 0
    reacao = ""
    
    if item_obj.nome in npc.gostos:
        pontos = 150
        reacao = "Eu amei isso! Muito obrigado!"
    elif item_obj.nome in npc.bons:
        pontos = 60
        reacao = "Oh, que legal, obrigado."
    elif item_obj.nome in npc.desgostos:
        pontos = -150
        reacao = "Eca... eu odeio isso."
    else:
        pontos = 20 # Neutro
        reacao = "Obrigado."

    # Bônus de aniversário (Geralmente 8x no Stardew, mas aqui podemos aplicar a lógica de permitir o extra)
    npc.afeto += pontos
    npc.recebeu_presente_hoje = True
    npc.presentes_semana += 1
    
    return True, f"{npc.nome}: {reacao} ({'+' if pontos>=0 else ''}{pontos} afeto)"

def conversar_npc(jogador, npc):
    if not npc.conversou_hoje:
        npc.afeto += 20
        npc.conversou_hoje = True
        npc.conversou_esta_semana = True
        return f"Você conversou com {npc.nome}. (+20 afeto)"
    return ""

# ---------- Presente -------------------------------------------------------

def dar_presente_npc(jogador, npc, nome_item, todos_itens):
    """
    Tenta dar nome_item ao NPC.
    Retorna (sucesso: bool, mensagem: str).

    Regras:
      - 1 presente/dia (salvo aniversário)
      - 2 presentes/semana (salvo aniversário)
      - Gostos: +80  |  Bons (nome ou tipo_presente): +45
      - Neutro: +20  |  Desgostos: -40
      - Bônus por estrelas: +10 * estrelas
      - Aniversário: pontos × 2
    """
    item_obj = todos_itens.get(nome_item)
    if not item_obj:
        return False, "Item desconhecido."
    if jogador.invetario.get(nome_item, 0) <= 0:
        return False, "Você não tem esse item."

    # Verifica aniversário
    eh_aniversario = False
    if npc.aniversario:
        est_aniv, dia_aniv = npc.aniversario
        est_idx = ["Primavera","Verao","Outono","Inverno"].index(jogador.estacao_atual) \
                  if jogador.estacao_atual in ["Primavera","Verao","Outono","Inverno"] else -1
        if est_idx == est_aniv and jogador.dia_atual == dia_aniv:
            eh_aniversario = True

    if not eh_aniversario:
        if npc.recebeu_presente_hoje:
            return False, f"{npc.nome}: Já recebi um presente hoje, obrigado!"
        if npc.presentes_semana >= 2:
            return False, f"{npc.nome}: Já recebi presentes demais essa semana."

    # Calcula pontos e label de descoberta
    tipo_pres = item_obj.tipo_presente
    if nome_item in npc.gostos:
        pontos        = 80
        reacao        = "Eu ADORO isso! Muito obrigado!"
        label_gosto   = "Adora"
    elif nome_item in npc.bons or (tipo_pres and tipo_pres in npc.bons):
        pontos        = 45
        reacao        = "Obrigado, eu gosto disso!"
        label_gosto   = "Gosta"
    elif nome_item in npc.desgostos or (tipo_pres and tipo_pres in npc.desgostos):
        pontos        = -40
        reacao        = "Ugh... por que me daria isso?"
        label_gosto   = "Odeia"
    else:
        pontos        = 20
        reacao        = "Obrigado, aceito seu presente."
        label_gosto   = "Gosta"

    # Bônus estrelas
    estrelas = getattr(item_obj, 'estrelas', 0)
    if estrelas > 0 and pontos > 0:
        pontos += estrelas * 10
        reacao += f" (qualidade: {estrelas}★)"

    # Dobra no aniversário
    if eh_aniversario and pontos > 0:
        pontos *= 2
        reacao += f"\nÉ meu aniversário! Adoro o presente!"

    # Multiplica pontos pelo bônus social do jogador
    if hasattr(jogador, 'bonus_amizade'):
        pontos = int(pontos * jogador.bonus_amizade())

    # Aplica
    jogador.amizades[npc.nome] = max(0, jogador.amizades.get(npc.nome, 0) + pontos)
    jogador.remover_item(nome_item, 1)

    # XP social por dar presente
    if hasattr(jogador, 'ganhar_xp_hab'):
        _bonus_pres = getattr(todos_itens.get(nome_item), 'xp_ganho', 0)
        jogador.ganhar_xp_hab('presente', _bonus_pres)

    if not eh_aniversario:
        npc.presentes_semana += 1
    npc.recebeu_presente_hoje = True
    npc.conversou_hoje        = True

    # ── Registra descoberta de gosto ─────────────────────────────────────────
    # gostos_descobertos = {nome_item: "Adora"|"Gosta"|"Odeia"}
    # Usado pela aba Gosto do menu Social para mostrar o que o jogador já sabe.
    if not hasattr(npc, "gostos_descobertos"):
        npc.gostos_descobertos = {}
    npc.gostos_descobertos[nome_item] = label_gosto

    sinal = "+" if pontos >= 0 else ""
    return True, f"{npc.nome}: {reacao} ({sinal}{pontos})"

# ---------- NPC na posição -------------------------------------------------

def npc_na_posicao(x, y, nome_mapa, todos_npcs):
    """Retorna o NPC que está em (x,y) no mapa, ou None."""
    for npc in todos_npcs.values():
        if npc.mapa_atual == nome_mapa and npc.x == x and npc.y == y:
            return npc
    return None

# ---------- Interagir com NPC à frente ------------------------------------
def interagir_frente_npc(jogador, mapa_dict, todos_npcs, todos_itens, apenas_conversar=False):
    """
    Verifica se há um NPC à frente do jogador.
    Retorna um dict com 'tipo' ou string vazia se não houver NPC.

    Tipos de retorno:
      {'tipo': 'dialogo',   'npc': npc, 'texto': str}
      {'tipo': 'missao',    'npc': npc, 'missao': Missao}
      {'tipo': 'entrega',   'npc': npc, 'missao': Missao, 'texto': str}
      {'tipo': 'presente',  'npc': npc, 'texto': str}
      ""  — nenhum NPC à frente
    """
    res = obter_bloco_frente(jogador, mapa_dict)
    if not res:
        return ""

    nx, ny, _ = res
    npc = npc_na_posicao(nx, ny, jogador.mapa_atual, todos_npcs)
    if not npc:
        return ""

    # Vira o NPC para encarar o player
    _oposto = {"cima": "baixo", "baixo": "cima", "esquerda": "direita", "direita": "esquerda"}
    npc.direcao     = _oposto.get(jogador.direcao, npc.direcao)
    npc.frame_atual = 0

    # ── 1. PRESENTE (X pressionado com item na hotbar) ───────────────────────
    if not apenas_conversar:
        slot      = jogador.item_selecionado
        nome_item = jogador.hotbar.get(slot)
        if nome_item and nome_item in todos_itens:
            item_obj = todos_itens[nome_item]
            TIPOS_PRESENTE = {"Material", "Consumivel", "Semente"}
            if item_obj.tipo in TIPOS_PRESENTE or item_obj.tipo_presente:
                sucesso, mensagem = dar_presente_npc(jogador, npc, nome_item, todos_itens)
                if sucesso:
                    npc.itens_dados[nome_item] = npc.itens_dados.get(nome_item, 0) + 1
                if jogador.invetario.get(nome_item, 0) <= 0:
                    jogador.hotbar[slot] = None
                return {'tipo': 'presente', 'npc': npc, 'texto': mensagem}

        # Sem item presente na hotbar — verifica missão/entrega via X
        for mid in list(npc.missoes_aceitas):
            missao = next((m for m in npc.missoes if m.id == mid), None)
            if missao is None:
                continue
            tem = jogador.invetario.get(missao.item_requerido, 0)
            if tem >= missao.quantidade:
                return {'tipo': 'entrega', 'npc': npc, 'missao': missao,
                        'texto': f"{npc.nome}: Você trouxe os {missao.item_requerido}!"}

        for missao in npc.missoes:
            if missao.id in npc.missoes_concluidas:
                continue
            if missao.id in npc.missoes_aceitas:
                tem = jogador.invetario.get(missao.item_requerido, 0)
                return {'tipo': 'dialogo', 'npc': npc,
                        'texto': f"{npc.nome}: Ainda espero pelos {missao.item_requerido}... ({tem}/{missao.quantidade})"}
            if missao.disponivel(jogador.dia_atual, jogador.estacao_atual):
                return {'tipo': 'missao', 'npc': npc, 'missao': missao}

    # ── 2. CONVERSA normal (Z — sempre retorna só dialogo) ───────────────────
    if not npc.conversou_hoje:
        ganho = 20
        jogador.amizades[npc.nome] = max(0, jogador.amizades.get(npc.nome, 0) + ganho)
        npc.conversou_hoje        = True
        npc.conversou_esta_semana = True

    pontos_amizade = jogador.amizades.get(npc.nome, 0)
    nivel_atual = min(int(pontos_amizade / (2500 / 10)), 10)
    niveis_disp = sorted(npc.falas.keys())
    melhor = 0
    for n in niveis_disp:
        if nivel_atual >= n:
            melhor = n
        else:
            break

    pool  = npc.falas.get(melhor, ["Olá!"])
    fala  = random.choice(pool)
    return {'tipo': 'dialogo', 'npc': npc, 'texto': f"{npc.nome}: {fala}"}