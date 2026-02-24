from itens import todos_itens, TODOS_TILES, TODAS_PLANTAS
_dano_blocos = {}
# objeto.py
import random

# --- Função auxiliar para atualizar o tile com o fundo correto ---
def _atualizar_tile_planta(mapa_dict, nx, ny):
    from itens import TODAS_PLANTAS
    dados = mapa_dict["plantacoes"][(nx, ny)]
    planta = TODAS_PLANTAS[dados["semente"]]
    
    # 1. Adicionamos a verificação de dias penalidade aqui
    dias_necessarios = planta.dias_total + dados.get("dias_penalidade", 0)
    
    # 2. Calcular o estágio atual de crescimento
    if dados["dias_idade"] >= dias_necessarios:
        idx_estagio = len(planta.estagios_tiles) - 1
    else:
        proporcao = dados["dias_idade"] / max(1, dias_necessarios)
        idx_estagio = int(proporcao * len(planta.estagios_tiles))
        idx_estagio = min(idx_estagio, len(planta.estagios_tiles) - 2)
        
    base_tile = planta.estagios_tiles[idx_estagio]
    
    # Define o fundo: 9 se regada, 2 se estiver seca
    fundo_id = 2 if dados.get("regada", False) else 1
    
    # Criamos um ID único fundindo o tile da planta + o fundo (Ex: 1109, 1102)
    custom_id = base_tile * 100 + fundo_id
    
    if "blocos" not in mapa_dict:
        mapa_dict["blocos"] = {}
        
    # Se o bloco personalizado ainda não existe na memória, clonamos e mudamos o fundo
    if custom_id not in mapa_dict["blocos"]:
        original = mapa_dict["blocos"].get(base_tile, {})
        novo_bloco = original.copy()
        novo_bloco["fundo"] = fundo_id
        mapa_dict["blocos"][custom_id] = novo_bloco
        
    # Aplica o novo bloco com o fundo correto diretamente no mapa
    mapa_dict["arte"][ny][nx] = custom_id

# --- 1. Ação para quando usar a semente no inventário / hotbar ---
def plantar_semente(jogador, mapa_dict, nx, ny, nome_semente):
    from itens import TODAS_PLANTAS
    tile_id = mapa_dict["arte"][ny][nx]
    
    if tile_id not in (1, 2):
        return "A terra precisa estar arada"
        
    planta_info = TODAS_PLANTAS.get(nome_semente)
    if not planta_info: return "Semente inválida."
        
    if jogador.estacao_atual not in planta_info.estacoes_plantio:
        return f"Sementes de {planta_info.nome} murchariam na {jogador.estacao_atual}."

    if "plantacoes" not in mapa_dict:
        mapa_dict["plantacoes"] = {}

    mapa_dict["plantacoes"][(nx, ny)] = {
        "semente": nome_semente,
        "dias_idade": 0,
        "regada": (tile_id == 2),
        "dias_plantada": 0,
        "dias_penalidade": 0
    }

    _atualizar_tile_planta(mapa_dict, nx, ny)
    jogador.adicionar_item(nome_semente, -1)
    
    # Limpa a hotbar se acabar
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
            mapa_dict["arte"][py][px] = 1
        map_rows = len(mapa_dict["arte"])
        map_cols = len(mapa_dict["arte"][0]) if map_rows > 0 else 0
        for y in range(map_rows):
            for x in range(map_cols):
                if mapa_dict["arte"][y][x] == 2:
                    mapa_dict["arte"][y][x] = 1

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
    # Entrega os itens ao jogador
    for item_nome, qtd in planta.itens_colheita:
        jogador.adicionar_item(item_nome, qtd)
    # --- SISTEMA DE REGROW CORRIGIDO ---
    if getattr(planta, 'regrow', None) is not None:
        dados["dias_penalidade"] = 0 
        dados["dias_idade"] = planta.dias_total - planta.regrow
        dados["regada"] = False 
        _atualizar_tile_planta(mapa_dict, nx, ny)
        
        return f"+ Colhido! {planta.nome} dará frutos de novo em {planta.regrow} dias."
    else:
        del mapa_dict["plantacoes"][(nx, ny)]
        mapa_dict["arte"][ny][nx] = 1 
        return f"Você colheu {planta.nome}!"

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

    # --- NOVO: SISTEMA DE PLANTIO ---
    if item.tipo == "Semente":
        from itens import TODAS_PLANTAS
        planta_info = TODAS_PLANTAS.get(nome_item)
        
        if not planta_info:
            return "Semente não configurada nas plantas."

        # Verifica se a semente pode ser plantada na estação atual
        if jogador.estacao_atual not in planta_info.estacoes_plantio:
            return f"A {planta_info.nome} não cresce na {jogador.estacao_atual}."

        if tile_id not in (1, 2):
            return "A terra precisa estar arada"

        # Inicia o registro no mapa se não existir
        if "plantacoes" not in mapa_dict:
            mapa_dict["plantacoes"] = {}

        # Registra a idade inicial como 0 e salva se a terra já estava molhada
        mapa_dict["plantacoes"][(nx, ny)] = {
            "semente": nome_item,
            "dias_idade": 0,
            "regada": (tile_id == 2)
        }

        # Atualiza o gráfico do bloco para fundir a semente com o fundo da terra (2 ou 9)
        _atualizar_tile_planta(mapa_dict, nx, ny)

        # Remove 1 do inventário
        jogador.adicionar_item(nome_item, -1)
        if jogador.invetario.get(nome_item, 0) <= 0:
            jogador.hotbar[slot] = None
            
        return "" # Retorna vazio para não sujar a tela (ou f"Plantou {nome_item}" se quiser ver a mensagem)

    # --- RESTO DO CÓDIGO NORMAL (colocar blocos normais como Cerca, Parede) ---
    if item.tile_colocar is not None:
        # Permite colocar blocos normais no chão limpo (0) ou em terra arada (2, 9)
        if tile_id in (0, 1, 2): 
            substituir_bloco(mapas_mundo, jogador.mapa_atual, nx, ny, item.tile_colocar)
            
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
    # --- REGADOR (MOVIDO PARA CIMA!) ---
    # ==========================================
    if ferramenta == "Regador":
        if jogador.mana < custo:
            return "Sem energia."
            
        # 1. Primeiro verifica se tem uma planta em cima da terra
        if "plantacoes" in mapa_dict and (nx, ny) in mapa_dict["plantacoes"]:
            dados = mapa_dict["plantacoes"][(nx, ny)]
            if not dados.get("regada", False):
                jogador.mana -= custo
                dados["regada"] = True
                _atualizar_tile_planta(mapa_dict, nx, ny) # Atualiza o visual para fundo 9
                return "Planta regada!"
            else:
                return "A planta já está regada."
                
        # 2. Se não tem planta, verifica se é só a terra seca (bloco 2)
        if tile_id == 1:
            jogador.mana -= custo
            substituir_bloco(mapas_mundo, jogador.mapa_atual, nx, ny, 2)
            return "Terra regada!"
            
        return "Não dá pra regar isso."

    tile_data = TODOS_TILES.get(tile_id)
    
    # Agora sim, se for um bloco desconhecido, ele para aqui
    if not tile_data:
        return ""

    # --- ENCHADA ---
    if ferramenta == "Enchada":
        if tile_data.arar_para is not None:
            if jogador.mana < custo:
                return "Sem energia."
            jogador.mana -= custo
            substituir_bloco(mapas_mundo, jogador.mapa_atual, nx, ny, tile_data.arar_para)
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
        substituir_bloco(mapas_mundo, jogador.mapa_atual, nx, ny, tile_data.tile_apos_quebrar)
        _dano_blocos.pop(chave, None)

        # Entrega os drops do TileData
        for item_nome, qtd in tile_data.drops.items():
            jogador.adicionar_item(item_nome, qtd)
    return ""

def _acao_dormir(jogador, mapa_dict, nx, ny, bloco_info):
    return "__DORMIR__"

def _acao_loja(jogador, mapa_dict, nx, ny, bloco_info):
    return "__ABRIR_LOJA__"

def _acao_caixa(jogador, mapa_dict, nx, ny, bloco_info):
    return "__ABRIR_CAIXA__"

_ACOES_TILE = {
    11: _acao_loja,
    12: _acao_caixa,
    13: _acao_dormir
}

_handlers = {}

def registrar_acao(nome_acao, funcao):
    _handlers[nome_acao] = funcao

def registrar_acao_tile(tile_id, funcao):
    _ACOES_TILE[tile_id] = funcao

def verificar_interacao(jogador, mapa_dict):
    resultado = obter_bloco_frente(jogador, mapa_dict)
    if not resultado:
        return ""

    nx, ny, tile_id = resultado
    blocos = _get_blocos(mapa_dict)
    bloco_info = blocos.get(tile_id, {})
    if "plantacoes" in mapa_dict and (nx, ny) in mapa_dict["plantacoes"]:
        return colher_planta(jogador, mapa_dict, nx, ny)

    if tile_id in _ACOES_TILE:
        return _ACOES_TILE[tile_id](jogador, mapa_dict, nx, ny, bloco_info)

    acao = bloco_info.get("acao", None)
    if acao and acao in _handlers:
        return _handlers[acao](jogador, mapa_dict, nx, ny, bloco_info)

    if acao == "loja":        return "__ABRIR_LOJA__"
    if acao == "dormir":      return "__DORMIR__"
    if acao == "trocar_mapa": return f"__TROCAR_MAPA__{bloco_info.get('destino', '')}"

    if bloco_info.get("solid", False):
        return verificar_interacao_mensagem(jogador, mapa_dict) or "Não consigo passar."

    return ""