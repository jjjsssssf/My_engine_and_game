import random
import heapq
# itens.py

# ══════════════════════════════════════════════════════════════════════
#  ITEM
# ══════════════════════════════════════════════════════════════════════

class Item:
    def __init__(self, nome, tipo,
                 descrica="",
                 slot_equipado=None,
                 recupar_hp=0, recupar_mn=0,
                 bonus_hp=0,   bonus_mn=0,
                 preco=0,      compra=0,
                 compravel=True, vendivel=True,
                 tipo_presente="", estrelas=0,
                 xp_ganho=0,
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
        self.xp_ganho       = xp_ganho
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

# --- FERRAMENTAS ---
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

# --- PEIXES_Mar ---
    "Sardinha": Item(
        "Sardinha", "Consumivel",
        descrica="Pequena e prateada, viaja em cardumes enormes pelas águas costeiras.",
        recupar_hp=10, recupar_mn=3,
        preco=30, compravel=False, tipo_presente="Peixe",
        col=0, lin=4,
    ),
    "Corvina": Item(
        "Corvina", "Consumivel",
        descrica="Cinza prateada com flancos dourados. Grunhe ao ser capturada — daí o nome.",
        recupar_hp=22, recupar_mn=6,
        preco=45, compravel=False, tipo_presente="Peixe",
        col=0, lin=4,
    ),

    "Robalo Flecha": Item(
        "Robalo Flecha", "Consumivel",
        descrica="Esguio e veloz, dispara como uma flecha ao fugir do anzol. Carne branca e nobre.",
        recupar_hp=42, recupar_mn=16,
        preco=130, compravel=False, tipo_presente="Peixe",
        col=0, lin=4,
    ),
    "Olhete": Item(
        "Olhete", "Consumivel",
        descrica="Olhos grandes e corpo esverdeado. Luta com força surpreendente quando fisgado.",
        recupar_hp=48, recupar_mn=18,
        preco=150, compravel=False, tipo_presente="Peixe",
        col=0, lin=4,
    ),

    "Beijupirá": Item(
        "Beijupirá", "Consumivel",
        descrica="Corpo torpedinado sem escamas. Veloz, solitário e de carne muito valorizada.",
        recupar_hp=85, recupar_mn=32,
        preco=350, compravel=False, tipo_presente="Peixe",
        col=0, lin=4,
    ),
    "Garoupa": Item(
        "Garoupa", "Consumivel",
        descrica="Rainha dos recifes. Suas manchas escuras se ajustam à cor do fundo para emboscar presas.",
        recupar_hp=95, recupar_mn=35,
        preco=450, compravel=False, tipo_presente="Peixe",
        col=0, lin=4,
    ),

    "Marlin Azul": Item(
        "Marlin Azul", "Consumivel",
        descrica="O Rei dos Mares. Bico afiado, dorso azul-elétrico e saltos épicos. Um troféu rarísimo.",
        recupar_hp=210, recupar_mn=105,
        preco=900, compravel=False, tipo_presente="Peixe",
        col=0, lin=4,
    ),
    "Mero": Item(
        "Mero", "Consumivel",
        descrica="Gigante ancestral das pedras. Pode ultrapassar 300 kg e viver mais de 40 anos.",
        recupar_hp=260, recupar_mn=130,
        preco=1200, compravel=False, tipo_presente="Peixe",
        col=0, lin=4,
    ),

# --- PEIXES_Riacho ---
    "Lambari": Item(
        "Lambari", "Consumivel",
        descrica="Pequeníssimo e arisco. O peixe mais clássico dos riachos brasileiros — difícil pegar, fácil de perder.",
        recupar_hp=10, recupar_mn=3,
        preco=30, compravel=False, tipo_presente="Peixe",
        col=0, lin=5,
    ),
    "Piava": Item(
        "Piava", "Consumivel",
        descrica="Escamas prateadas com reflexos dourados. Prefere corredeiras e foge rapidinho.",
        recupar_hp=18, recupar_mn=4,
        preco=50, compravel=False, tipo_presente="Peixe",
        col=0, lin=5,
    ),

    "Tilápia": Item(
        "Tilápia", "Consumivel",
        descrica="Resistente e territorialista. Invadiu os rios brasileiros e se adaptou como ninguém.",
        recupar_hp=35, recupar_mn=10,
        preco=100, compravel=False, tipo_presente="Peixe",
        col=0, lin=5,
    ),
    "Traíra": Item(
        "Traíra", "Consumivel",
        descrica="Dentes afiados e focinho pontudo. Embosca presas entre raízes e respira ar direto da superfície.",
        recupar_hp=42, recupar_mn=13,
        preco=120, compravel=False, tipo_presente="Peixe",
        col=0, lin=5,
    ),

    "Tucunaré": Item(
        "Tucunaré", "Consumivel",
        descrica="Predador feroz de cores vibrantes. O 'olho' falso na cauda confunde predadores e fascina pescadores.",
        recupar_hp=78, recupar_mn=27,
        preco=400, compravel=False, tipo_presente="Peixe",
        col=0, lin=5,
    ),
    "Pacu": Item(
        "Pacu", "Consumivel",
        descrica="Corpo alto e achatado, dentes que parecem humanos. Come frutos que caem no rio — é um peixe vegetariano!",
        recupar_hp=88, recupar_mn=32,
        preco=300, compravel=False, tipo_presente="Peixe",
        col=0, lin=5,
    ),

    "Dourado": Item(
        "Dourado", "Consumivel",
        descrica="O Rei do Rio. Escamas de ouro reluzente, saltos acrobáticos e luta de tirar o fôlego.",
        recupar_hp=185, recupar_mn=92,
        preco=1000, compravel=False, tipo_presente="Peixe",
        col=0, lin=5,
    ),
    "Surubim": Item(
        "Surubim", "Consumivel",
        descrica="Gigante pintado de manchas negras. Caça nas profundezas à noite e pode passar dos 100 kg.",
        recupar_hp=240, recupar_mn=115,
        preco=950, compravel=False, tipo_presente="Peixe",
        col=0, lin=5,
    ),

# --- PEIXES_Manguezal ---
    "Caranguejo-uçá": Item(
        "Caranguejo-uçá", "Consumivel",
        descrica="O caranguejo mais famoso do manguezal brasileiro. Garra poderosa e carne saborosíssima.",
        recupar_hp=20, recupar_mn=6,
        preco=60, compravel=False, tipo_presente="Peixe",
        col=0, lin=6,
    ),
    "Bagre": Item(
        "Bagre", "Consumivel",
        descrica="Bigodes longos e corpo escorregadio. Vasculha o fundo lodoso do manguezal em busca de comida.",
        recupar_hp=28, recupar_mn=8,
        preco=55, compravel=False, tipo_presente="Peixe",
        col=0, lin=6,
    ),
    "Tainha": Item(
        "Tainha", "Consumivel",
        descrica="Salta em grupo ao ser perseguida, criando um espetáculo de prata na superfície.",
        recupar_hp=32, recupar_mn=10,
        preco=70, compravel=False, tipo_presente="Peixe",
        col=0, lin=6,
    ),
    "Siri": Item(
        "Siri", "Consumivel",
        descrica="Carapaça azulada e nado lateral rápido. Muito apreciado em frutos do mar brasileiros.",
        recupar_hp=18, recupar_mn=5,
        preco=40, compravel=False, tipo_presente="Peixe",
        col=0, lin=6,
    ),

    "Robalo Peva": Item(
        "Robalo Peva", "Consumivel",
        descrica="Menor que o irmão flecha, mas igualmente ágil. Habita a zona de transição entre o mangue e o mar.",
        recupar_hp=50, recupar_mn=18,
        preco=160, compravel=False, tipo_presente="Peixe",
        col=0, lin=6,
    ),
    "Camarão": Item(
        "Camarão", "Consumivel",
        descrica="Nada de costas e pula ao menor susto. No manguezal, é alimento de quase tudo — e de todo mundo.",
        recupar_hp=22, recupar_mn=8,
        preco=45, compravel=False, tipo_presente="Peixe",
        col=0, lin=6,
    ),

    "Corvina Malhada": Item(
        "Corvina Malhada", "Consumivel",
        descrica="Prima da corvina do mar, adaptada às águas salobras do estuário. Listras douradas no flanco.",
        recupar_hp=60, recupar_mn=22,
        preco=180, compravel=False, tipo_presente="Peixe",
        col=0, lin=6,
    ),
    "Curvina": Item(
        "Curvina", "Consumivel",
        descrica="Produz sons graves e ritmados para atrair parceiros — pescadores a ouvem bater no casco do barco.",
        recupar_hp=70, recupar_mn=25,
        preco=200, compravel=False, tipo_presente="Peixe",
        col=0, lin=6,
    ),

    "Snook Gigante": Item(
        "Snook Gigante", "Consumivel",
        descrica="Lenda das bocas de rio. Linha lateral preta marcante e saltos explosivos que quebram linhas.",
        recupar_hp=180, recupar_mn=88,
        preco=800, compravel=False, tipo_presente="Peixe",
        col=0, lin=6,
    ),
    "Guaivira": Item(
        "Guaivira", "Consumivel",
        descrica="Corpo achatado e prateado como uma faca. Dentes afiados e velocidade de ataque impressionante.",
        recupar_hp=200, recupar_mn=95,
        preco=700, compravel=False, tipo_presente="Peixe",
        col=0, lin=6,
    ),

# --- MATERIAIS / BLOCOS ---
    "Madeira": Item(
        "Madeira", "Material",
        compra=10, preco=3, tipo_presente="Outro",
        tile_colocar="madeira",
        col=2, lin=9, sprite=b"items.png"
    ),
    "Cerca": Item(
        "Cerca", "Material",
        compravel=False, preco=5, tipo_presente="Outro",
        tile_colocar="cerca",
        col=2, lin=9,
    ),

# --- FERTILIZANTES ---
    "Fertilizante Basico": Item(
        "Fertilizante Basico", "Material",
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

# --- SEMENTE ---
    # 5 dias → colheita vale 40g  → semente custa 16g na loja
    "Semente de Beterraba": Item(
        "Semente de Beterraba", "Semente",
        descrica="Cresce em 5 dias. Estação: Primavera.",
        preco=5, compra=16, tipo_presente="Outro",
        col=0, lin=1,
    ),
    # 6 dias → colheita vale 50g  → semente custa 20g na loja
    "Semente de Batata": Item(
        "Semente de Batata", "Semente",
        descrica="Cresce em 6 dias. Estação: Primavera.",
        preco=6, compra=20, tipo_presente="Outro",
        col=0, lin=1,
    ),
    # 4 dias → colheita vale 30g  → semente custa 12g na loja (mais barata, ciclo curto)
    "Semente de Alho Poro": Item(
        "Semente de Alho Poro", "Semente",
        descrica="Cresce em 4 dias. Estação: Primavera.",
        preco=4, compra=12, tipo_presente="Outro",
        col=0, lin=1,
    ),
    # 5 dias → colheita vale 38g  → semente custa 15g na loja
    "Semente de Cenoura": Item(
        "Semente de Cenoura", "Semente",
        descrica="Cresce em 5 dias. Estação: Primavera.",
        preco=5, compra=15, tipo_presente="Outro",
        col=0, lin=1,
    ),
    # 7 dias → colheita vale 60g  → semente custa 24g na loja
    "Semente de Cebola": Item(
        "Semente de Cebola", "Semente",
        descrica="Cresce em 7 dias. Estação: Primavera.",
        preco=7, compra=24, tipo_presente="Outro",
        col=0, lin=1,
    ),
    # 10 dias → colheita vale 90g → semente custa 36g na loja
    "Semente de Repolho": Item(
        "Semente de Repolho", "Semente",
        descrica="Cresce em 10 dias. Estação: Primavera.",
        preco=10, compra=36, tipo_presente="Outro",
        col=0, lin=1,
    ),

# --- COLHEITA ---
    # 5 dias
    "Beterraba": Item(
        "Beterraba", "Consumivel",
        descrica="Uma beterraba fresca e nutritiva.",
        recupar_hp=15, recupar_mn=5,
        preco=40, compra=1, tipo_presente="Cultivo",
        xp_ganho=10,
        col=0, lin=1,
    ),
    # 6 dias
    "Batata": Item(
        "Batata", "Consumivel",
        descrica="Uma batata robusta e energética.",
        recupar_hp=18, recupar_mn=4,
        preco=50, tipo_presente="Cultivo",
        xp_ganho=12,
        col=1, lin=1,
    ),
    # 4 dias
    "Alho Poro": Item(
        "Alho Poro", "Consumivel",
        descrica="Um alho poró aromático.",
        recupar_hp=10, recupar_mn=6,
        preco=30, tipo_presente="Cultivo",
        xp_ganho=8,
        col=2, lin=1,
    ),
    # 5 dias
    "Cenoura": Item(
        "Cenoura", "Consumivel",
        descrica="Uma cenoura crocante e saudável.",
        recupar_hp=14, recupar_mn=6,
        preco=38, tipo_presente="Cultivo",
        xp_ganho=10,
        col=3, lin=1,
    ),
    # 7 dias
    "Cebola": Item(
        "Cebola", "Consumivel",
        descrica="Uma cebola pungente e saborosa.",
        recupar_hp=20, recupar_mn=8,
        preco=60, tipo_presente="Cultivo",
        xp_ganho=14,
        col=4, lin=1,
    ),
    # 10 dias
    "Repolho": Item(
        "Repolho", "Consumivel",
        descrica="Um repolho grande e cheio de vitaminas.",
        recupar_hp=30, recupar_mn=12,
        preco=90, tipo_presente="Cultivo",
        xp_ganho=20,
        col=5, lin=1,
    ),

}

# ══════════════════════════════════════════════════════════════════════
#  TILE DATA
# ══════════════════════════════════════════════════════════════════════

class TileData:
    def __init__(self, nome, mensagem="", hp_max=1, ferramentas_aceitas=None, drops=None,
                 bloco_substituido=None, arar_para=None):
        self.nome = nome
        self.mensagem = mensagem
        self.hp_max = hp_max
        self.ferramentas_aceitas = ferramentas_aceitas or {}
        self.drops = drops or {}
        self.bloco_substituido = bloco_substituido
        self.tile_apos_quebrar = bloco_substituido   # alias de compatibilidade
        self.arar_para = arar_para

TODOS_TILES = {
    "terra":         TileData("terra",         arar_para="terra_arada"),
    "terra_arada":   TileData("terra_arada",   ferramentas_aceitas={"Picareta": 1}, bloco_substituido="terra"),
    "terra_molhada": TileData("terra_molhada", ferramentas_aceitas={"Picareta": 1}, bloco_substituido="terra"),
    "pedra": TileData("pedra", ferramentas_aceitas={"Picareta": 1}, bloco_substituido="terra", hp_max=10),
}

# ══════════════════════════════════════════════════════════════════════
#  ITEM ESTRELADO
# ══════════════════════════════════════════════════════════════════════

def obter_item_estrelado(nome_original, qtd_estrelas):
    if qtd_estrelas <= 0:
        return nome_original
    # Sufixo ASCII compatível com fontes bitmap (evita "???")
    _sufixos = {1: " (B)", 2: " (N)", 3: " (O)", 4: " (P)"}
    sufixo = _sufixos.get(qtd_estrelas, f" ({qtd_estrelas})")
    nome_estrelado = f"{nome_original}{sufixo}"
    if nome_estrelado in todos_itens:
        return nome_estrelado
    if nome_original in todos_itens:
        item_orig = todos_itens[nome_original]
        novo_preco = item_orig.preco + (qtd_estrelas * 30)
        nova_versao = Item(
            nome=nome_estrelado,
            tipo=item_orig.tipo,
            descrica=item_orig.descrica,   # sem texto de qualidade na descricao
            slot_equipado=item_orig.slot_equipado,
            recupar_hp=item_orig.recupar_hp,
            recupar_mn=item_orig.recupar_mn,
            bonus_hp=item_orig.bonus_hp,
            bonus_mn=item_orig.bonus_mn,
            preco=novo_preco,
            compra=int(item_orig.compra * (1 + 0.5 * qtd_estrelas)),
            compravel=False,
            vendivel=True,
            tipo_presente=item_orig.tipo_presente,
            estrelas=qtd_estrelas
        )
        todos_itens[nome_estrelado] = nova_versao
        return nome_estrelado
    return nome_original

# ══════════════════════════════════════════════════════════════════════
#  PLANTA
# ══════════════════════════════════════════════════════════════════════

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
        dias_total=5,
        itens_colheita=[("Beterraba", 1)],
        estagios_tiles=["beteraba0", "beteraba1", "beteraba2", "beteraba2", "beteraba3"],
        regrow=None,
        estacoes_plantio=["Primavera"]
    ),
    "Semente de Batata": Planta(
        nome="Batata",
        dias_total=6,
        itens_colheita=[("Batata", 1)],
        estagios_tiles=["batata0", "batata1", "batata1", "batata2", "batata2", "batata3"],
        regrow=None,
        estacoes_plantio=["Primavera"]
    ),
    "Semente de Alho Poró": Planta(
        nome="Alho Poró",
        dias_total=4,
        itens_colheita=[("Alho Poró", 1)],
        estagios_tiles=["poro0", "poro1", "poro2", "poro3",],
        regrow=None,
        estacoes_plantio=["Primavera"]
    ),
    "Semente de Cenoura": Planta(
        nome="Cenoura",
        dias_total=5,
        itens_colheita=[("Cenoura", 1)],
        estagios_tiles=["cenoura0", "cenoura1", "cenoura1", "cenoura2", "cenoura3",],
        regrow=None,
        estacoes_plantio=["Primavera"]
    ),
    "Semente de Cebola": Planta(
        nome="Cebola",
        dias_total=7,
        itens_colheita=[("Cebola", 1)],
        estagios_tiles=["cebola0", "cebola1", "cebola1", "cebola2", "cebola2", "cebola2", "cebola3",],
        regrow=None,
        estacoes_plantio=["Primavera"]
    ),
    "Semente de Repolho": Planta(
        nome="Repolho",
        dias_total=10,
        itens_colheita=[("Repolho", 1)],
        estagios_tiles=["repolho0", "repolho0", "repolho1", "repolho1", "repolho1","repolho1", "repolho2", "repolho2", "repolho2", "repolho3"],
        regrow=None,
        estacoes_plantio=["Primavera"]
    ),
}


# ══════════════════════════════════════════════════════════════════════
#  A* PATHFINDING
# ══════════════════════════════════════════════════════════════════════

def a_star(start, goal, mapa_art, blocos):
    """
    A* em grade de tile_ids inteiros.
    blocos: dict { tile_id: {"solid": bool, ...} } — o mapa_dict["blocos"].
    """
    if not mapa_art or start == goal:
        return []
    map_h = len(mapa_art)
    map_w = len(mapa_art[0]) if map_h > 0 else 0

    import heapq
    fila = []
    heapq.heappush(fila, (0, start))
    veio_de   = {start: None}
    custo_ate = {start: 0}

    while fila:
        _, atual = heapq.heappop(fila)
        if atual == goal:
            break
        cx, cy = atual
        for nx, ny in ((cx+1,cy),(cx-1,cy),(cx,cy+1),(cx,cy-1)):
            if not (0 <= nx < map_w and 0 <= ny < map_h):
                continue
            tile_id = mapa_art[ny][nx]
            info    = blocos.get(tile_id, {"solid": True})
            if info.get("solid", True) and (nx, ny) != goal:
                continue
            novo_custo = custo_ate[atual] + 1
            if (nx,ny) not in custo_ate or novo_custo < custo_ate[(nx,ny)]:
                custo_ate[(nx,ny)] = novo_custo
                prioridade = novo_custo + abs(goal[0]-nx) + abs(goal[1]-ny)
                heapq.heappush(fila, (prioridade, (nx,ny)))
                veio_de[(nx,ny)] = atual

    if goal not in veio_de:
        return []
    caminho, curr = [], goal
    while curr != start:
        caminho.append(curr)
        curr = veio_de[curr]
    caminho.reverse()
    return caminho


# ══════════════════════════════════════════════════════════════════════
#  CLASSE NPC
# ══════════════════════════════════════════════════════════════════════

class NPC:
    TILE_W              = 16
    TILE_H              = 16
    VELOCIDADE_PIXEL    = 1     # pixels/frame
    FRAMES_ANIMACAO     = 14    # frames entre troca de passo

    def __init__(self, nome, sprite_id, tiles, x, y,
                 agenda=None,
                 falas=None,
                 gostos=None, bons=None, desgostos=None,
                 genero="?", solteiro=True,
                 mapa_atual="fazenda", mapa_inicial="fazenda",
                 aniversario=None,
                 missoes=None):

        self.nome       = nome
        self.sprite_id  = sprite_id   # preenchido em game.py após v.load_sprite
        self.sprite_path = None       # caminho do PNG — preenchido por aplicar_sprites_npc()
        self.oid         = None       # object-id na engine (para flip nativo)
        self.tiles      = tiles        # mapeamento dir→cols (pode ser {} se vier do editor)

        # Posição em grid
        self.x, self.y     = x, y
        self.spawn_x       = x
        self.spawn_y       = y

        # Posição em pixel (movimento suave idêntico ao Player)
        self.pixel_x    = x * self.TILE_W
        self.pixel_y    = y * self.TILE_H
        self.destino_px = self.pixel_x
        self.destino_py = self.pixel_y
        self.movendo    = False

        # Animação
        self.direcao        = 'baixo'
        self.frame_atual    = 0        # 0=parado, 1=passo1, 2=passo2
        self.frame_contador = 0
        self.tempo_parado   = 0

        # Pathfinding / agenda
        self.agenda           = agenda or {}
        self.meta_global      = None   # (mapa_dest, dest_x, dest_y)
        self.spawn_forcado    = None   # (sx, sy) ao entrar num novo mapa
        self.destino_imediato = None   # tile (tx, ty) que o A* persegue agora
        self.caminho_atual    = []     # lista de (x,y) retornados pelo A*

        # Mapa
        self.mapa_atual   = mapa_atual
        self.mapa_spawn   = mapa_inicial
        self.mapa_inicial = mapa_inicial

        # Social
        self.genero               = genero
        self.solteiro             = solteiro
        self.afeto = 0
        self.nivel_amizade = 0
        self.conversou_esta_semana = False
        self.missoes_concluidas = []
        self.missao_ativa = None
        self.missoes_aceitas = []    # IDs de missões que o jogador aceitou via diálogo
        self.gostos               = gostos    or []
        self.bons                 = bons      or []
        self.desgostos            = desgostos or []
        self.falas                = falas     or {0: ["Olá."]}
        self.conversou_hoje       = False
        self.presentes_semana     = 0
        self.recebeu_presente_hoje= False
        self.aniversario          = aniversario   # (estacao_idx, dia)
        self.missoes              = missoes or []
        # Histórico de itens dados: {nome_item: qtd_total_dada}
        self.itens_dados          = {}
        # Reações descobertas ao presentear: {nome_item: "Adora"|"Gosta"|"Odeia"}
        self.gostos_descobertos   = {}

    # ------------------------------------------------------------------
    # Animação — idêntica ao Player
    # ------------------------------------------------------------------

    def _col_sprite(self):
        """Retorna (col, lin, usar_sprite_flip).
        - Direcoes com flip=True no editor usam o sprite_id_flip (espelhado).
        - Se a direcao for 'direita' e nao tiver tiles proprios, usa 'esquerda'
          com flip automatico.
        - Suporta formato antigo (int = so col, lin=0) e novo ([col, lin]).
        """
        direcao   = self.direcao
        frame_key = ("parado", "passo1", "passo2")[self.frame_atual]
        d         = self.tiles.get(direcao, {})
        flip      = bool(d.get("flip", False))

        # Fallback: direita sem tiles proprios → usa esquerda com flip
        val = d.get(frame_key, None)
        esq_vazia = (val is None or val == 0 or val == [0, 0] or val == (0, 0))
        if direcao == "direita" and esq_vazia:
            d_esq = self.tiles.get("esquerda", {})
            if d_esq:
                d    = d_esq
                flip = True
                val  = d.get(frame_key, 0)

        if val is None:
            val = 0
        if isinstance(val, (list, tuple)) and len(val) >= 2:
            return int(val[0]), int(val[1]), flip
        return int(val), 0, flip

    def animar(self):
        """Avança a animação — deve ser chamado todo frame."""
        if self.movendo:
            self.tempo_parado = 0
            self.frame_contador += 1
            if self.frame_contador >= self.FRAMES_ANIMACAO:
                self.frame_contador = 0
                self.frame_atual = 2 if self.frame_atual == 1 else 1
        else:
            self.tempo_parado += 1
            if self.tempo_parado > 3 and self.frame_atual != 0:
                self.frame_atual = 0

    def _deslizar(self):
        """Desloca pixel_x/y em direção ao destino, igual ao Player."""
        vel = self.VELOCIDADE_PIXEL

        if self.pixel_x < self.destino_px:
            self.pixel_x = min(self.pixel_x + vel, self.destino_px)
        elif self.pixel_x > self.destino_px:
            self.pixel_x = max(self.pixel_x - vel, self.destino_px)

        if self.pixel_y < self.destino_py:
            self.pixel_y = min(self.pixel_y + vel, self.destino_py)
        elif self.pixel_y > self.destino_py:
            self.pixel_y = max(self.pixel_y - vel, self.destino_py)

        if self.pixel_x == self.destino_px and self.pixel_y == self.destino_py:
            self.movendo = False
            self.x = self.pixel_x // self.TILE_W
            self.y = self.pixel_y // self.TILE_H

    def _iniciar_passo(self, nx, ny):
        """Aponta o NPC para (nx,ny) e inicia o deslizamento de 1 tile."""
        dx = nx - self.x
        dy = ny - self.y
        if   dx > 0: self.direcao = 'direita'
        elif dx < 0: self.direcao = 'esquerda'
        elif dy > 0: self.direcao = 'baixo'
        elif dy < 0: self.direcao = 'cima'
        self.movendo    = True
        self.destino_px = nx * self.TILE_W
        self.destino_py = ny * self.TILE_H

    def _teleportar_pixel(self):
        """Sincroniza pixel_x/y com grid_x/y sem animação."""
        self.pixel_x    = self.x * self.TILE_W
        self.pixel_y    = self.y * self.TILE_H
        self.destino_px = self.pixel_x
        self.destino_py = self.pixel_y
        self.movendo    = False

    def resetar_dia(self):
        """Volta ao spawn, reseta flags diárias."""
        self.x, self.y         = self.spawn_x, self.spawn_y
        self.mapa_atual        = self.mapa_spawn
        self._teleportar_pixel()
        self.caminho_atual     = []
        self.destino_imediato  = None
        self.meta_global       = None
        self.spawn_forcado     = None
        self.conversou_hoje    = False
        self.recebeu_presente_hoje = False

    def atualizar_tick(self, horas, minutos,
                       mapa_art, blocos,
                       nome_mapa_player, portais_mapa_atual,
                       pos_player=None, pos_outros_npcs=None):
        """
        Decide o próximo passo de grid.
        Deve ser chamado a cada N frames (ex.: a cada 6 frames no game.py).
        """
        horario = horas + minutos / 100.0

        # 1. Verifica agenda
        if horario in self.agenda:
            dados = self.agenda[horario]
            if len(dados) == 5:
                mapa_dest, dx, dy, sx, sy = dados
                if self.meta_global != (mapa_dest, dx, dy):
                    self.meta_global      = (mapa_dest, dx, dy)
                    self.spawn_forcado    = (sx, sy)
                    self.caminho_atual    = []
                    self.destino_imediato = None

        if not self.meta_global:
            return

        mapa_destino, dest_x, dest_y = self.meta_global

        # 2. Chegou ao destino final → limpa meta
        if self.mapa_atual == mapa_destino and self.x == dest_x and self.y == dest_y:
            self.meta_global = None
            return

        # 3. Define tile imediato
        if self.mapa_atual == mapa_destino:
            novo_destino   = (dest_x, dest_y)
            self.spawn_forcado = None
        else:
            novo_destino = None
            for (tx, ty), dados_portal in portais_mapa_atual.items():
                if dados_portal.get("destino") == mapa_destino:
                    novo_destino = (tx, ty)
                    break
            if novo_destino is None:
                return

        # 4. Recalcula caminho se destino mudou
        if novo_destino != self.destino_imediato:
            self.destino_imediato = novo_destino
            self.caminho_atual    = []

        # 5. Aguarda terminar passo atual
        if self.movendo:
            return

        # 6. Move
        if self.mapa_atual == nome_mapa_player:
            if not self.caminho_atual and (self.x, self.y) != self.destino_imediato:
                self.caminho_atual = a_star(
                    (self.x, self.y), self.destino_imediato, mapa_art, blocos)
            if self.caminho_atual:
                nx, ny = self.caminho_atual.pop(0)
                self._iniciar_passo(nx, ny)
        else:
            if (self.x, self.y) != self.destino_imediato:
                gdx = self.destino_imediato[0] - self.x
                gdy = self.destino_imediato[1] - self.y
                if abs(gdx) >= abs(gdy):
                    nx, ny = self.x + (1 if gdx > 0 else -1), self.y
                else:
                    nx, ny = self.x, self.y + (1 if gdy > 0 else -1)
                self._iniciar_passo(nx, ny)

        # 7. Portal — pisar num tile de troca de mapa
        for (tx, ty), dados_portal in portais_mapa_atual.items():
            if self.x == tx and self.y == ty:
                if dados_portal.get("destino") == mapa_destino:
                    self.mapa_atual = mapa_destino
                    if self.spawn_forcado:
                        self.x, self.y = self.spawn_forcado
                    else:
                        self.x, self.y = dados_portal.get("spawn", (tx, ty))
                    self._teleportar_pixel()
                    self.caminho_atual    = []
                    self.destino_imediato = None
                    break


def aplicar_sprites_npc(todos_npcs_dict, npc_sprites_json, engine_video=None,
                         diretorio_editor=None):
    """
    Lê o bloco "npc_sprites" salvo pelo mapa_editor e aplica em cada NPC:
      - npc.tiles          ← mapeamento dir→{parado, passo1, passo2, flip}
      - npc.sprite_path    ← nome do arquivo PNG
      - npc.sprite_id      ← ID normal carregado via engine_video.load_sprite
      - npc.sprite_id_flip ← ID da versão espelhada (PNG temporário)

    A versão espelhada é criada com pygame e salva em arquivo temporário,
    pois a engine não suporta flip nativo em draw_sprite_part.
    """
    import os, tempfile
    try:
        import pygame
        _pygame_ok = True
    except ImportError:
        _pygame_ok = False

    for nome, anim in npc_sprites_json.items():
        npc = todos_npcs_dict.get(nome)
        if npc is None:
            continue

        sprite_nome = anim.get("sprite", "")
        npc.sprite_path = sprite_nome

        # Monta o dicionário tiles no formato que NPC._col_sprite() espera
        tiles_novo = {}
        for direcao in ("baixo", "cima", "esquerda", "direita"):
            d = anim.get(direcao, {})
            tiles_novo[direcao] = {
                "parado": d.get("parado", 0),
                "passo1": d.get("passo1", 0),
                "passo2": d.get("passo2", 0),
                "flip":   bool(d.get("flip", False)),
            }
        npc.tiles = tiles_novo

        # Carrega sprite_id via engine se disponível
        npc.sprite_id_flip = None
        if engine_video is not None and sprite_nome and diretorio_editor:
            # Tenta na pasta do editor primeiro, depois na pasta pai (game/)
            caminho_editor = os.path.join(diretorio_editor, sprite_nome)
            caminho_game   = os.path.join(os.path.dirname(diretorio_editor), sprite_nome)
            if os.path.exists(caminho_editor):
                caminho = caminho_editor
            elif os.path.exists(caminho_game):
                caminho = caminho_game
            else:
                caminho = caminho_editor  # mantém o padrão e deixa a engine reportar o erro
            caminho_bytes = caminho.encode("utf-8")
            try:
                npc.sprite_id = engine_video.load_sprite(caminho_bytes)
            except Exception as e:
                print(f"[WARN] Não foi possível carregar sprite de {nome}: {e}")
                continue

            # Cria um tile-object na engine para o NPC (permite flip nativo via set_object_flip)
            # Posição inicial 0,0 — atualizada em desenhar_npcs() todo frame
            if npc.oid is None:
                try:
                    npc.oid = engine_video.add_tile_object(
                        0, 0,           # x, y iniciais (atualizados no draw)
                        npc.sprite_id,
                        0, 0,           # tile_x, tile_y iniciais
                        16, 16,         # tile_w, tile_h
                    )
                except Exception as e:
                    print(f"[WARN] Não foi possível criar oid para NPC {nome}: {e}")

            # Fallback pygame: cria PNG espelhado caso o oid não esteja disponível
            if npc.oid is None and _pygame_ok:
                try:
                    surf      = pygame.image.load(caminho).convert_alpha()
                    surf_flip = pygame.transform.flip(surf, True, False)
                    tmp       = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                    pygame.image.save(surf_flip, tmp.name)
                    tmp.close()
                    npc.sprite_id_flip = engine_video.load_sprite(tmp.name.encode("utf-8"))
                except Exception as e:
                    print(f"[WARN] Flip sprite falhou para {nome}: {e}")

class Missao:
    """
    Representa uma missão que um NPC pode oferecer ao jogador.

    Parâmetros
    ----------
    id              : identificador único (str/int)
    descricao       : texto exibido na UI de missões
    item_requerido  : nome do item que o jogador deve entregar
    quantidade      : quantidade necessária do item
    recompensa_gold : ouro ganho ao completar
    recompensa_afeto: pontos de afeto ganhos ao completar
    dia_inicio      : dia do mês em que a missão fica disponível (1-28)
    dia_fim         : último dia para completar (1-28, None = sem prazo)
    estacao_inicio  : estação em que a missão começa  (ex: "Primavera")
    estacao_fim     : estação em que a missão expira  (None = mesma estação)
    """
    def __init__(self, id, descricao, item_requerido, quantidade,
                 recompensa_gold, recompensa_afeto,
                 dia_inicio=1, dia_fim=None,
                 estacao_inicio="Primavera", estacao_fim=None,
                 dialogo_pedido=None):
        self.id               = id
        self.descricao        = descricao
        self.item_requerido   = item_requerido
        self.quantidade       = quantidade
        self.recompensa_gold  = recompensa_gold
        self.recompensa_afeto = recompensa_afeto
        self.dia_inicio       = dia_inicio
        self.dia_fim          = dia_fim          # None = sem prazo fixo
        self.estacao_inicio   = estacao_inicio
        self.estacao_fim      = estacao_fim or estacao_inicio
        # Fala que o NPC usa ao propor a missão (se None usa descricao)
        self.dialogo_pedido   = dialogo_pedido or descricao

    def disponivel(self, dia_atual, estacao_atual):
        """Retorna True se a missão já começou e ainda não expirou."""
        ESTACOES = ["Primavera", "Verao", "Outono", "Inverno"]
        try:
            idx_atual  = ESTACOES.index(estacao_atual)
            idx_inicio = ESTACOES.index(self.estacao_inicio)
            idx_fim    = ESTACOES.index(self.estacao_fim)
        except ValueError:
            return False

        # Verifica estação de início
        if idx_atual < idx_inicio:
            return False
        if idx_atual == idx_inicio and dia_atual < self.dia_inicio:
            return False

        # Verifica prazo
        if self.dia_fim is not None:
            if idx_atual > idx_fim:
                return False
            if idx_atual == idx_fim and dia_atual > self.dia_fim:
                return False

        return True

    def expirada(self, dia_atual, estacao_atual):
        """Retorna True se o prazo já passou."""
        if self.dia_fim is None:
            return False
        ESTACOES = ["Primavera", "Verao", "Outono", "Inverno"]
        try:
            idx_atual = ESTACOES.index(estacao_atual)
            idx_fim   = ESTACOES.index(self.estacao_fim)
        except ValueError:
            return False
        if idx_atual > idx_fim:
            return True
        if idx_atual == idx_fim and dia_atual > self.dia_fim:
            return True
        return False


def verificar_entrega_missao(jogador, npc):
    if npc.missao_ativa:
        m = npc.missao_ativa
        if jogador.invetario.get(m.item_requerido, 0) >= m.quantidade:
            # Completa missão
            jogador.remover_item(m.item_requerido, m.quantidade)
            jogador.gold += m.recompensa_gold
            jogador.amizades[npc.nome] = max(0, jogador.amizades.get(npc.nome, 0) + m.recompensa_afeto)
            npc.missoes_concluidas.append(m.id)
            npc.missao_ativa = None
            return f"Missão Concluída! Ganhou {m.recompensa_gold}G e {m.recompensa_afeto} de afeto."
    return None

todos_npcs = {
    "Marco": NPC(
        nome        = "Marco",
        sprite_id   = None,
        tiles       = {},   # preenchido por aplicar_sprites_npc() via JSON do editor
        x=1, y=5,
        mapa_atual  = "fazenda",
        mapa_inicial= "fazenda",
        agenda      = {
            6.05:  ("fazenda", 10, 8,  5, 5),
            18.00: ("fazenda",  5, 5,  5, 5),
        },
        falas = {
            0: ["Oi! Sou o Marco.", "Bom dia!", "Como vai?"],
            1: ["Obrigado pelos presentes!", "Você é um bom amigo."],
            2: ["Você é meu melhor amigo!"],
        },
        gostos    = ["Cenoura", "Beterraba"],
        bons      = ["Cultivo", "Batata"],
        desgostos = ["Lixo"],
        genero    = "M",
        solteiro  = True,
        aniversario = (0, 10),   # estacao_idx=0 (Primavera), dia=10
        missoes   = [
            Missao(
                id="marco_cenouras",
                descricao="Marco quer cenouras frescas pra fazer um ensopado.",
                dialogo_pedido="Ei, você teria umas Cenouras pra mim? Preciso de 3 pra fazer um ensopado. Te pago bem!",
                item_requerido="Cenoura",
                quantidade=3,
                recompensa_gold=120,
                recompensa_afeto=80,
                dia_inicio=2,
                dia_fim=20,
                estacao_inicio="Primavera",
                estacao_fim="Primavera",
            ),
            Missao(
                id="marco_beterraba",
                descricao="Marco pediu beterrabas para uma receita especial.",
                dialogo_pedido="Você consegue me trazer 2 Beterrabas? Tenho uma receita especial em mente!",
                item_requerido="Beterraba",
                quantidade=2,
                recompensa_gold=90,
                recompensa_afeto=60,
                dia_inicio=1,
                dia_fim=28,
                estacao_inicio="Primavera",
                estacao_fim="Primavera",
            ),
        ],
    ),
    "Rafa": NPC(
        nome        = "Rafa",
        sprite_id   = None,
        tiles       = {},   # preenchido por aplicar_sprites_npc() via JSON do editor
        x=5, y=5,
        mapa_atual  = "fazenda",
        mapa_inicial= "fazenda",
        agenda      = {
            6.05:  ("fazenda", 11, 11,  5, 5),
            18.00: ("fazenda",  5, 5,  5, 5),
        },
        falas = {
            0: ["Oi! Sou o Rafa.", "Bom dia!", "Como vai?"],
            1: ["Obrigado pelos presentes!", "Você é um bom amigo."],
            2: ["Você é meu melhor amigo!"],
        },
        gostos    = ["Cenoura", "Beterraba"],
        bons      = ["Cultivo", "Batata"],
        desgostos = ["Lixo"],
        genero    = "M",
        solteiro  = True,
        aniversario = (0, 10),   # estacao_idx=0 (Primavera), dia=10
        missoes   = [
            Missao(
                id="Rafa_cenouras",
                descricao="Rafa quer cenouras frescas pra fazer um ensopado.",
                dialogo_pedido="Oi! Você teria 3 Cenouras? Preciso pra um prato que tô tentando fazer.",
                item_requerido="Cenoura",
                quantidade=3,
                recompensa_gold=120,
                recompensa_afeto=80,
                dia_inicio=2,
                dia_fim=20,
                estacao_inicio="Primavera",
                estacao_fim="Primavera",
            ),
            Missao(
                id="Rafa_beterraba",
                descricao="Rafa pediu beterrabas para uma receita especial.",
                dialogo_pedido="Tenho uma receita incrível mas preciso de 2 Beterrabas. Pode me ajudar?",
                item_requerido="Beterraba",
                quantidade=2,
                recompensa_gold=90,
                recompensa_afeto=60,
                dia_inicio=1,
                dia_fim=28,
                estacao_inicio="Primavera",
                estacao_fim="Primavera",
            ),
        ],
    ),
}

def aplicar_sprites_item(item_sprites_json):
    for nome, info in item_sprites_json.items():
        item = todos_itens.get(nome)
        if item is None:
            continue
        spr = info.get("sprite", "")
        if spr:
            item.sprite = spr.encode("utf-8") if isinstance(spr, str) else spr
        col = info.get("col")
        lin = info.get("lin")
        if col is not None:
            item.col = int(col)
        if lin is not None:
            item.lin = int(lin)