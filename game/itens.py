import random
from artes import *

# itens.py

class Item:
    def __init__(self, nome, tipo,
                 descrica="",
                 slot_equipado=None,
                 recupar_hp=0, recupar_mn=0,
                 bonus_hp=0,   bonus_mn=0,
                 preco=0,      compra=0,
                 compravel=True, vendivel=True,
                 tipo_presente="", estrelas=0,
                 tile_colocar=None,
                 # --- sprite na hotbar ---
                 sprite=b"tileset.png",
                 col=0, lin=0,
                 start_x=0, start_y=0,
                 w=16, h=16):

        self.nome           = nome
        self.tipo           = tipo
        self.descrica       = descrica
        self.slot_equipado  = slot_equipado
        self.sloat_equipado = slot_equipado   # alias antigo para não quebrar player.py
        self.recupar_hp     = recupar_hp
        self.recupar_mn     = recupar_mn
        self.bonus_hp       = bonus_hp
        self.bonus_mn       = bonus_mn
        self.preco          = preco
        self.compra         = compra
        self.compravel      = compravel
        self.vendivel       = vendivel
        self.tipo_presente  = tipo_presente
        self.estrelas       = estrelas
        self.tile_colocar   = tile_colocar

        # sprite
        self.sprite   = sprite
        self.col      = col
        self.lin      = lin
        self.start_x  = start_x
        self.start_y  = start_y
        self.w        = w
        self.h        = h

    def get_sprite_rect(self):
        """Retorna (rec_x, rec_y, w, h) para draw_sprite_part."""
        return (
            self.start_x + self.col * self.w,
            self.start_y + self.lin * self.h,
            self.w,
            self.h
        )

todos_itens = {

# --- FERRAMENTAS (Equipável, slot "Primeira Mão") ---
    "Enchada": Item(
        "Enchada", "Equipavel",
        descrica="Use para arar a terra",
        slot_equipado="Primeira Mão",
        vendivel=False, compravel=False,
        col=6, lin=1, sprite=b"items.png"
    ),
    "Machado": Item(
        "Machado", "Equipavel",
        descrica="Corta madeira",
        slot_equipado="Primeira Mão",
        vendivel=False, compravel=False,
        col=2, lin=1, sprite=b"items.png"
    ),
    "Picareta": Item(
        "Picareta", "Equipavel",
        descrica="Quebra pedras",
        slot_equipado="Primeira Mão",
        vendivel=False, compravel=False,
        col=3, lin=1, sprite=b"items.png"
    ),
    "Regador": Item(
        "Regador", "Equipavel",
        descrica="Rega as plantas",
        slot_equipado="Primeira Mão",
        vendivel=False, compravel=False,
        col=3, lin=0, sprite=b"items.png"
    ),
    "Foice": Item(
        "Foice", "Equipavel",
        descrica="Corta matos",
        slot_equipado="Primeira Mão",
        vendivel=False, compravel=False,
        col=7, lin=1, sprite=b"items.png"
    ),
    "Vara de Pesca": Item(
        "Vara de Pesca", "Equipavel",
        descrica="Pesca peixes comuns",
        slot_equipado="Primeira Mão",
        vendivel=False, compravel=False,
        col=5, lin=1, sprite=b"items.png"
    ),
    "Vara de Pesca Profissional": Item(
        "Vara de Pesca Profissional", "Equipavel",
        descrica="Pesca ótimos peixes",
        slot_equipado="Primeira Mão",
        vendivel=False, compravel=False,
        col=6, lin=0, sprite=b"items.png"
    ),

# --- LIXO ---
    "Bota Velha": Item(
        "Bota Velha", "Material",
        preco=2, compravel=False, tipo_presente="Lixo",
        col=0, lin=3,
    ),
    "Lixo": Item(
        "Lixo", "Material",
        preco=1, compravel=False, tipo_presente="Lixo",
        col=1, lin=3,
    ),
    "Alga": Item(
        "Alga", "Consumivel",
        recupar_hp=5, recupar_mn=2,
        preco=5, compravel=False, tipo_presente="Lixo",
        col=2, lin=3,
    ),
    "Lata de Refrigerante": Item(
        "Lata de Refrigerante", "Material",
        preco=4, compravel=False, tipo_presente="Lixo",
        col=3, lin=3,
    ),

# --- PEIXES ---
    "Peixe Sol": Item(
        "Peixe Sol", "Consumivel",
        recupar_hp=5, recupar_mn=15,
        preco=35, compravel=False, tipo_presente="Peixe",
        col=0, lin=4,
    ),
    "Sardinha": Item(
        "Sardinha", "Consumivel",
        recupar_hp=20, recupar_mn=5,
        preco=25, compravel=False, tipo_presente="Peixe",
        col=1, lin=4,
    ),
    "Lambari": Item(
        "Lambari", "Consumivel",
        recupar_hp=15, recupar_mn=4,
        preco=20, compravel=False, tipo_presente="Peixe",
        col=2, lin=4,
    ),
    "Tilápia": Item(
        "Tilápia", "Consumivel",
        recupar_hp=30, recupar_mn=8,
        preco=40, compravel=False, tipo_presente="Peixe",
        col=3, lin=4,
    ),
    "Truta": Item(
        "Truta", "Consumivel",
        recupar_hp=35, recupar_mn=10,
        preco=50, compravel=False, tipo_presente="Peixe",
        col=4, lin=4,
    ),
    "Bagre": Item(
        "Bagre", "Consumivel",
        recupar_hp=40, recupar_mn=6,
        preco=55, compravel=False, tipo_presente="Peixe",
        col=5, lin=4,
    ),
    "Carpa": Item(
        "Carpa", "Consumivel",
        recupar_hp=45, recupar_mn=10,
        preco=65, compravel=False, tipo_presente="Peixe",
        col=6, lin=4,
    ),
    "Dourado": Item(
        "Dourado", "Consumivel",
        recupar_hp=70, recupar_mn=20,
        preco=120, compravel=False, tipo_presente="Peixe",
        col=7, lin=4,
    ),
    "Salmão Real": Item(
        "Salmão Real", "Consumivel",
        recupar_hp=90, recupar_mn=30,
        preco=180, compravel=False, tipo_presente="Peixe",
        col=8, lin=4,
    ),
    "Pirarucu": Item(
        "Pirarucu", "Consumivel",
        recupar_hp=120, recupar_mn=25,
        preco=250, compravel=False, tipo_presente="Peixe",
        col=9, lin=4,
    ),
    "Carpa Noturna": Item(
        "Carpa Noturna", "Consumivel",
        recupar_hp=120, recupar_mn=25,
        preco=350, compravel=False, tipo_presente="Peixe",
        col=10, lin=4,
    ),

# --- MATERIAIS / BLOCOS ---
    "Madeira": Item(
        "Madeira", "Material",
        compra=10, preco=3, tipo_presente="Outro",
        tile_colocar=10,
        col=2, lin=9, sprite=b"items.png"
    ),
    "Cerca": Item(
        "Cerca", "Material",
        compravel=False, preco=5, tipo_presente="Outro",
        tile_colocar=2,   # tile_id 2 = cerca no mapa
        col=2, lin=9,
    ),

# --- FERTILIZANTES ---
    "Fertilizante Básico": Item(
        "Fertilizante Básico", "Material",
        preco=20, compra=40, tipo_presente="Outro",
        descrica="Melhora levemente a qualidade (+1 Estrela)",
        col=2, lin=2,
    ),
    "Fertilizante Premium": Item(
        "Fertilizante Premium", "Material",
        preco=100, compra=250, tipo_presente="Outro",
        descrica="Garante alta qualidade (+2 Estrelas)",
        col=3, lin=2,
    ),

# --- SEMENTES ---
    "Semente de Beterraba": Item(
        "Semente de Beterraba", "Semente",
        preco=4, compra=8, tipo_presente="Outro",
        col=0, lin=1,
    ),
    "Semente de Cenora": Item(
        "Semente de Cenora", "Semente",
        preco=3, compra=6, tipo_presente="Outro",
        col=1, lin=1,
    ),
    "Semente de Rabanete": Item(
        "Semente de Rabanete", "Semente",
        preco=5, compra=10, tipo_presente="Outro",
        col=2, lin=1,
    ),
    "Semente de Mandioca": Item(
        "Semente de Mandioca", "Semente",
        preco=6, compra=12, tipo_presente="Outro",
        col=3, lin=1,
    ),
    "Semente de Batata": Item(
        "Semente de Batata", "Semente",
        preco=5, compra=10, tipo_presente="Outro",
        col=4, lin=1,
    ),
    "Semente de Vagem": Item(
        "Semente de Vagem", "Semente",
        preco=4, compra=8, tipo_presente="Outro",
        col=5, lin=1,
    ),
    "Semente de Morango": Item(
        "Semente de Morango", "Semente",
        preco=15, compra=30, tipo_presente="Outro",
        col=6, lin=1,
    ),
    "Semente de Café": Item(
        "Semente de Café", "Semente",
        preco=20, compra=40, tipo_presente="Outro",
        col=7, lin=1,
    ),

# --- COLHEITA ---
    "Beterraba": Item(
        "Beterraba", "Consumivel",
        recupar_hp=8, recupar_mn=2, preco=18, tipo_presente="Cultivo",
        col=0, lin=5,
    ),
    "Cenora": Item(
        "Cenora", "Consumivel",
        recupar_hp=6, preco=15, tipo_presente="Cultivo",
        col=1, lin=5,
    ),
    "Rabanete": Item(
        "Rabanete", "Consumivel",
        recupar_hp=10, preco=22, tipo_presente="Cultivo",
        col=2, lin=5,
    ),
    "Mandioca": Item(
        "Mandioca", "Consumivel",
        recupar_hp=14, preco=28, tipo_presente="Cultivo",
        col=3, lin=5,
    ),
    "Batata": Item(
        "Batata", "Consumivel",
        recupar_hp=12, preco=25, tipo_presente="Cultivo",
        col=4, lin=5,
    ),
    "Vagem": Item(
        "Vagem", "Consumivel",
        recupar_hp=5, recupar_mn=5, preco=16, tipo_presente="Cultivo",
        col=5, lin=5,
    ),
    "Morango": Item(
        "Morango", "Consumivel",
        recupar_hp=20, recupar_mn=5, preco=45, tipo_presente="Cultivo",
        col=6, lin=5,
    ),
    "Café": Item(
        "Café", "Consumivel",
        recupar_hp=5, recupar_mn=30, preco=80, tipo_presente="Cultivo",
        col=7, lin=5,
    ),
}

class TileData:
    def __init__(self, id_tile, nome, mensagem="", hp_max=1, ferramentas_aceitas=None, drops=None, tile_apos_quebrar=0, arar_para=None):
        self.id = id_tile
        self.nome = nome
        self.mensagem = mensagem
        self.hp_max = hp_max
        self.ferramentas_aceitas = ferramentas_aceitas or {}
        self.drops = drops or {}
        self.tile_apos_quebrar = tile_apos_quebrar
        self.arar_para = arar_para

TODOS_TILES = {
    0: TileData(0, "Chão", arar_para=1),
    1: TileData(0, "Terra arada", ferramentas_aceitas={"Picareta": 1}, arar_para=0),

}

def obter_item_estrelado(nome_original, qtd_estrelas):
    if qtd_estrelas <= 0:
        return nome_original
    sufixo = "★" * qtd_estrelas
    nome_estrelado = f"{nome_original} {sufixo}"    
    if nome_estrelado in todos_itens:
        return nome_estrelado        
    if nome_original in todos_itens:
        item_orig = todos_itens[nome_original]        
        novo_preco = item_orig.preco + (qtd_estrelas * 30)
        
        nova_versao = itens(
            nome=nome_estrelado,
            tipo=item_orig.tipo,
            descrica=item_orig.descrica + f" (Qualidade: {qtd_estrelas} estrelas)",
            sloat_equipado=item_orig.sloat_equipado,
            recupar_hp=item_orig.recupar_hp,
            recupar_mn=item_orig.recupar_mn,
            bonus_hp=item_orig.bonus_hp,
            bonus_mn=item_orig.bonus_mn,
            preco=novo_preco,
            compra=item_orig.compra * (1 + (0.5 * qtd_estrelas)),
            compravel=False,
            vendivel=True,
            char=item_orig.char,
            tipo_presente=item_orig.tipo_presente,
            estrelas=qtd_estrelas
        )        
        todos_itens[nome_estrelado] = nova_versao
        return nome_estrelado
    
    return nome_original

# itens.py
class Planta:
    def __init__(self, nome, dias_total, itens_colheita, estagios_tiles, regrow=None, estacoes_plantio=None):
        self.nome = nome
        self.dias_total = dias_total
        self.itens_colheita = itens_colheita
        self.estagios_tiles = estagios_tiles 
        self.regrow = regrow 
        self.estacoes_plantio = estacoes_plantio or ["Primavera", "Verao", "Outono", "Inverno"]

TODAS_PLANTAS = {
    "Semente de Beterraba": Planta(
        nome="Beterraba",
        dias_total=4,
        itens_colheita=[("Beterraba", 1)],
        estagios_tiles=[16, 17, 18, 19],
        regrow=None,
        estacoes_plantio=["Primavera"]
    ),
    "Semente de Morango": Planta( 
        nome="Morango",
        dias_total=5,
        itens_colheita=[("Morango", 3)],
        estagios_tiles=[20, 21, 22, 23], 
        regrow=3,
        estacoes_plantio=["Primavera", "Verao"]
    )
}

import heapq

def a_star(start, goal, mapa_art, obstaculos_lut):
    w = len(mapa_art[0])
    h = len(mapa_art)
    queue = []
    heapq.heappush(queue, (0, start))
    came_from = {start: None}
    cost_so_far = {start: 0}
    while queue:
        _, current = heapq.heappop(queue)
        if current == goal:
            break
        cx, cy = current
        vizinhos = [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]        
        for next_node in vizinhos:
            nx, ny = next_node
            if 0 <= nx < w and 0 <= ny < h:
                try:
                    char_at = mapa_art[ny][nx]
                    char_id = ord(char_at) if len(char_at) == 1 else 0
                    if char_id < len(obstaculos_lut) and obstaculos_lut[char_id]:
                        continue
                except:
                    continue

                new_cost = cost_so_far[current] + 1
                if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                    cost_so_far[next_node] = new_cost
                    priority = new_cost + abs(goal[0] - nx) + abs(goal[1] - ny)
                    heapq.heappush(queue, (priority, next_node))
                    came_from[next_node] = current
    path = []
    curr = goal
    if curr not in came_from: return []
    while curr != start:
        path.append(curr)
        curr = came_from[curr]
    path.reverse()
    return path

def processar_movimento_npcs(todos_npcs, tempo_horas, mapa_art, obstaculos_lut):
    for nome, npc in todos_npcs.items():
        if tempo_horas in npc.agenda:
            destino_desejado = npc.agenda[tempo_horas]
            if npc.destino_atual != destino_desejado:
                npc.destino_atual = destino_desejado
                npc.caminho_atual = a_star((npc.x, npc.y), destino_desejado, mapa_art, obstaculos_lut)
        if npc.caminho_atual:
            proximo = npc.caminho_atual[0] 
            npc.x, npc.y = npc.caminho_atual.pop(0)


    
    def esta_disponivel(self, ano_atual, estacao_atual, dia_atual):
        if self.completa:
            return False        
        if ano_atual != self.ano:
            return False        
        if self.estacao is not None and estacao_atual != self.estacao:
            return False        
        if dia_atual >= self.dia_inicio and dia_atual <= self.dia_fim:
            return True
        
        return False

class Missao:
    def __init__(self, npc_nome, item_pedido, quantidade, recompensa_gold, 
                 dia_inicio=1, dia_fim=28, estacao=None, ano=1):
        self.npc_nome = npc_nome
        self.item_pedido = item_pedido
        self.quantidade = quantidade
        self.recompensa_gold = recompensa_gold
        self.dia_inicio = dia_inicio
        self.dia_fim = dia_fim
        self.estacao = estacao
        self.ano = ano
        self.completa = False
    
    def esta_disponivel(self, ano_atual, estacao_atual, dia_atual):
        if self.completa:
            return False
        if ano_atual != self.ano:
            return False
        if self.estacao is not None and estacao_atual != self.estacao:
            return False
        if dia_atual >= self.dia_inicio and dia_atual <= self.dia_fim:
            return True
        return False

missoes_jogo = {
    "marco_sementes_primavera": Missao(
        npc_nome="Marco",
        item_pedido="Semente de Cenora",
        quantidade=10,
        recompensa_gold=150,
        dia_inicio=1,
        dia_fim=15,
        estacao=0,  # Primavera
        ano=1
    ),
    
    "marco_cenouras_gerais": Missao(
        npc_nome="Marco",
        item_pedido="Cenora",
        quantidade=20,
        recompensa_gold=300,
        dia_inicio=1,
        dia_fim=28,
        estacao=None,  # Qualquer estação
        ano=1
    ),
    
    "marco_madeira_teste": Missao(
        npc_nome="Marco",
        item_pedido="Madeira",
        quantidade=5,
        recompensa_gold=50,
        dia_inicio=1,
        dia_fim=28,
        estacao=None,
        ano=1
    ),
    
    "marco_peixes_verao": Missao(
        npc_nome="Marco",
        item_pedido="Sardinha",
        quantidade=15,
        recompensa_gold=400,
        dia_inicio=10,
        dia_fim=25,
        estacao=1,  # Verão
        ano=1
    ),
}

class NPC:
    def __init__(self, nome, char, color, x, y, agenda, falas=None, amizade=0, gostos=None, bons=None, desgostos=None,
        genero="?", solteiro=False, mapa_atual="vila", mapa_inicial="vila", posicao_inicial=None,
        aniversario=None, missoes=None):
        self.nome = nome
        self.char = char
        self.color = color
        self.x = x
        self.y = y
        self.spawn_x = x
        self.spawn_y = y
        self.posicao_inicial = posicao_inicial or {}
        self.agenda = agenda
        self.mapa_inicial = mapa_inicial 
        self.mapa_spawn = mapa_inicial
        self.meta_global = None 
        self.spawn_forcado = None
        self.destino_imediato = None 
        self.caminho_atual = []
        self.genero = genero
        self.solteiro = solteiro
        self.mapa_atual = mapa_atual
        self.amizade = amizade
        self.gostos = gostos if gostos else []
        self.bons = bons if bons else []
        self.desgostos = desgostos if desgostos else []
        self.conversou_hoje = False
        self.presentes_semana = 0
        self.falas = falas if falas else {0: ["Olá."]}
        self.recebeu_presente_hoje = False
        self.aniversario = aniversario
        self.missoes = missoes if missoes else []
        self.tem_papel_missao = False
    
    def atualizar_missoes(self, ano, estacao, dia):
        for missao in self.missoes:
            missao.verificar_disponibilidade(ano, estacao, dia)
    
    def resetar_dia(self):
        self.x = self.spawn_x
        self.y = self.spawn_y
        self.mapa_atual = self.mapa_spawn
        self.caminho_atual = []
        self.destino_imediato = None
        self.meta_global = None
        self.spawn_forcado = None
        self.conversou_hoje = False
        self.recebeu_presente_hoje = False
        
    def atualizar(self, horas, minutos, mapa_art, obstaculos_lut, nome_mapa_player, portais_mapa_atual):
        horario_atual = horas + (minutos / 100.0)
        
        # Verifica se tem agenda neste horário
        if horario_atual in self.agenda:
            dados_agenda = self.agenda[horario_atual]
            if len(dados_agenda) == 5:
                mapa_dest, dx, dy, sx, sy = dados_agenda
                self.meta_global = (mapa_dest, dx, dy)
                self.spawn_forcado = (sx, sy)
        
        if not self.meta_global:
            return
        
        mapa_destino, dest_x, dest_y = self.meta_global
        novo_destino = None
        
        # Define o destino imediato
        if self.mapa_atual == mapa_destino:
            novo_destino = (dest_x, dest_y)
            self.spawn_forcado = None 
        else:
            # Precisa ir até um portal
            for coord_portal, dados_portal in portais_mapa_atual.items():
                if dados_portal["destino"] == mapa_destino:
                    novo_destino = coord_portal
                    break
        
        if not novo_destino:
            return
        
        # Recalcula caminho se mudou o destino
        if novo_destino != self.destino_imediato:
            self.destino_imediato = novo_destino
            self.caminho_atual = []
        
        # === MOVIMENTO ===
        
        # Se NPC está no mapa do player: usa pathfinding completo
        if self.mapa_atual == nome_mapa_player:
            if not self.caminho_atual and (self.x, self.y) != self.destino_imediato:
                self.caminho_atual = a_star((self.x, self.y), self.destino_imediato, mapa_art, obstaculos_lut)
            
            if self.caminho_atual:
                proximo_passo = self.caminho_atual.pop(0)
                self.x, self.y = proximo_passo
        
        # Se NPC está em OUTRO mapa: movimento simulado (mais rápido)
        else:
            if (self.x, self.y) != self.destino_imediato:
                # Movimento simplificado: vai direto ao destino em linha reta
                dx = self.destino_imediato[0] - self.x
                dy = self.destino_imediato[1] - self.y
                
                # Move 1 tile por vez (em Manhattan distance)
                if abs(dx) > 0:
                    self.x += 1 if dx > 0 else -1
                elif abs(dy) > 0:
                    self.y += 1 if dy > 0 else -1
        
        # === PORTAL ===
        if (self.x, self.y) in portais_mapa_atual:
            portal = portais_mapa_atual[(self.x, self.y)]
            if portal["destino"] == mapa_destino:
                self.mapa_atual = portal["destino"]
                if self.spawn_forcado:
                    self.x, self.y = self.spawn_forcado
                else:
                    self.x, self.y = portal["spawn"]
                self.caminho_atual = []
                self.destino_imediato = None

todos_npcs = {
    "Vendedor": NPC(
        nome="Marco",
        char="M",
        color="#F8E048",
        x=58, y=6,
        agenda={
            6.30: ("mercado", 6, 4, 16, 18),
            7.30: ("vila", 59, 16, 81, 4),
        },
        mapa_atual="vila",
        mapa_inicial="vila",
        amizade=0,
        gostos=["Diamante"],
        bons=["Peixe", "Cerveja"],
        desgostos=["Lixo", "Mineral"],
        aniversario=(0, 10),
    ),
}
