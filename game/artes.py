# artes.py  —  gerado dinamicamente a partir dos JSONs de mapa.
# Nenhum tile está hardcoded aqui. Tudo vem do tile_registry salvo pelo editor.

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

def _abs(caminho):
    if os.path.isabs(caminho):
        return caminho
    # Adicionamos "editor" no meio do caminho para ele buscar na pasta certa
    return os.path.join(HERE, "editor", caminho)

def _converter_camada(layer_cells, registry):
    """
    Converte uma camada de células {s, c, l} / None para uma grade de tile_ids inteiros.
    Usa o registry já resolvido: {(sheet_name, col, lin): visual_id}.
    Células None           →  0 (transparente / vazio).
    Células sem registro   →  0 (tratado como vazio — sem colisão acidental).
    """
    result = []
    for row in layer_cells:
        new_row = []
        for cell in row:
            if cell is None:
                new_row.append(0)
            else:
                sn  = cell.get("_sn", "")
                vid = registry.get((sn, cell["c"], cell["l"]), 0)
                new_row.append(vid)
        result.append(new_row)
    return result


def _resolve_sheet_names(layer_cells, sheet_names):
    """
    Substitui o índice numérico 's' de cada célula pelo nome real da sheet,
    guardando em '_sn'. Evita repetir a resolução a cada tile no loop acima.
    """
    for row in layer_cells:
        for cell in row:
            if cell is not None and "_sn" not in cell:
                s = cell.get("s", 0)
                cell["_sn"] = sheet_names[s] if s < len(sheet_names) else ""


def _build_blocos(tile_registry_raw):
    """
    Constrói blocos e v2id a partir do tile_registry salvo pelo editor.

    VARIANTES: tiles com mesmo ID semântico mas sprites diferentes recebem
    um visual_id único para que o jogo renderize o sprite correto de cada um.

    Esquema de visual_id:
      - Primeiro visual de cada ID usa o próprio ID (ex: 3).
      - Variantes adicionais usam IDs negativos derivados: -(tid*10000 + idx).
        Negativos nunca colidem com IDs reais do designer.

    Cada bloco inclui "tile_id" com o ID semântico original, para que colisão,
    ações e outras lógicas do jogo continuem funcionando pelo ID real.

    IMPORTANTE: as entradas são ordenadas por (tile_id, sheet, col, lin) antes
    de serem processadas. Isso garante ordem determinística independente da
    ordem do JSON — sem isso, qual visual_id recebe o tile_id canônico varia
    a cada execução e a hitbox pode ficar no visual errado.

    Retorna:
        blocos:  { visual_id : { sprite, col, l, w, h, solid, tile_id, ... } }
        v2id:    { (sheet_name, col, lin) : visual_id }
    """
    blocos   = {}
    v2id     = {}
    id_count = {}   # quantas variantes já registradas por tile_id semântico

    # Coleta e ordena para garantir ordem determinística
    entradas = []
    for key_str, props in tile_registry_raw.items():
        key          = json.loads(key_str)
        sn, col, lin = key[0], key[1], key[2]
        tid          = props.get("id")
        if tid is None:
            continue
        entradas.append((tid, sn, col, lin, props))
    entradas.sort(key=lambda e: (e[0], e[1], e[2], e[3]))

    for tid, sn, col, lin, props in entradas:
        # Primeiro visual usa o próprio ID; variantes ficam negativos
        count     = id_count.get(tid, 0)
        visual_id = tid if count == 0 else -(tid * 10000 + count)
        id_count[tid] = count + 1

        v2id[(sn, col, lin)] = visual_id

        bloco = {
            "sprite":  sn.encode("utf-8"),
            "col":     col,
            "l":       lin,
            "w":       16,
            "h":       16,
            "solid":   props.get("solid", False),
            "tile_id": tid,   # ID semântico real (colisão, ações, etc.)
        }
        for campo in ("fundo", "nome", "nomes", "acao", "mensagem", "destino",
                      "tipo_trocar", "spawn_x", "spawn_y", "item_data", "tile_hitbox",
                      "loja_nomes", "loja_tipos"):
            val = props.get(campo)
            if val is not None and val != "":
                bloco[campo] = val
        blocos[visual_id] = bloco

    return blocos, v2id


# ─────────────────────────────────────────────────────────────────────────────
# Função pública principal
# ─────────────────────────────────────────────────────────────────────────────

def carregar_mapa_json(caminho):
    """
    Carrega um mapa salvo pelo Editor e retorna o dict que o jogo usa:

        {
            "arte":   [[tile_id, ...]],   # camada principal (layer 1)
            "chao":   [[tile_id, ...]],   # camada de chão   (layer 0)
            "topo":   [[tile_id, ...]],   # camada topo       (layer 2)
            "blocos": { tile_id: {...} }, # definições de todos os tiles
        }

    Compatível com:
      - Formato novo (editor v4/v5): células são dicts {s, c, l}
      - Formato antigo (v2):         células são inteiros (tile_id direto)
    """
    caminho = _abs(caminho)
    with open(caminho, "r", encoding="utf-8") as f:
        data = json.load(f)

    sheet_names    = data.get("spritesheets", [])
    layers_raw     = data.get("layers", [])
    tile_reg_raw   = data.get("tile_registry", {})
    npc_sprites    = data.get("npc_sprites", {})

    # Constrói os dicionários de blocos a partir do registry embutido no JSON
    blocos, v2id = _build_blocos(tile_reg_raw)

    # ── Detecta formato ───────────────────────────────────────────────────────
    def _eh_novo_formato(layer):
        for row in layer:
            for cell in row:
                if cell is not None and isinstance(cell, dict):
                    return True
                if isinstance(cell, int) and cell != 0:
                    return False
        return False

    if layers_raw and _eh_novo_formato(layers_raw[0]):
        # Formato novo: resolve nomes de sheet uma vez só
        for layer in layers_raw:
            _resolve_sheet_names(layer, sheet_names)

        chao = _converter_camada(layers_raw[0], v2id) if len(layers_raw) > 0 else []
        arte = _converter_camada(layers_raw[1], v2id) if len(layers_raw) > 1 else []
        topo = _converter_camada(layers_raw[2], v2id) if len(layers_raw) > 2 else []
    else:
        # Formato antigo — IDs diretos, sem conversão
        chao = layers_raw[0] if len(layers_raw) > 0 else []
        arte = layers_raw[1] if len(layers_raw) > 1 else []
        topo = layers_raw[2] if len(layers_raw) > 2 else []

    return {
        "arte":        arte,
        "chao":        chao,
        "topo":        topo,
        "blocos":      blocos,
        "npc_sprites": npc_sprites,
    }



# ─────────────────────────────────────────────────────────────────────────────
# Troca de mapa  —  chamada pelo game.py ao receber __TROCAR_MAPA__
# ─────────────────────────────────────────────────────────────────────────────

def aplicar_troca_mapa(resultado, jogador):
    """
    Parseia '__TROCAR_MAPA__<destino>[|x<N>][|y<N>]', carrega o mapa destino
    se necessário (procura mapa_<destino>.json na pasta do jogo/editor),
    posiciona o jogador e retorna (nome, mapa_dict, rows, cols).

    Se o destino não for encontrado, mantém o mapa atual sem mudar nada.
    """
    payload = resultado[len("__TROCAR_MAPA__"):]
    partes  = payload.split("|")
    destino = partes[0]
    spawn_x = None
    spawn_y = None

    for p in partes[1:]:
        if p.startswith("x"):
            try: spawn_x = int(p[1:])
            except ValueError: pass
        elif p.startswith("y"):
            try: spawn_y = int(p[1:])
            except ValueError: pass

    # Carrega o mapa se ainda não estiver em memória
    if destino and destino not in mapas_mundo:
        candidatos = [
            f"mapa_{destino}.json",
            f"{destino}.json",
        ]
        for nome_arquivo in candidatos:
            try:
                mapas_mundo[destino] = carregar_mapa_json(nome_arquivo)
                print(f"[INFO] Mapa '{destino}' carregado de '{nome_arquivo}'")
                break
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"[WARN] Erro ao carregar '{nome_arquivo}': {e}")
        else:
            print(f"[WARN] Mapa '{destino}' não encontrado.")

    # Se não conseguiu carregar, fica no mapa atual
    if not destino or destino not in mapas_mundo:
        mapa_dict = mapas_mundo.get(jogador.mapa_atual, {})
        rows = len(mapa_dict.get("arte", []))
        cols = len(mapa_dict["arte"][0]) if rows > 0 else 0
        return jogador.mapa_atual, mapa_dict, rows, cols

    mapa_dict = mapas_mundo[destino]
    jogador.mapa_atual = destino
    map_rows = len(mapa_dict["arte"])
    map_cols = len(mapa_dict["arte"][0]) if map_rows > 0 else 0

    if spawn_x is not None: jogador.grid_x = spawn_x
    if spawn_y is not None: jogador.grid_y = spawn_y

    # Teletransporta os pixels imediatamente para não haver deslizamento
    tile_size = getattr(jogador, 'tile_size', 16)
    jogador.pixel_x = jogador.grid_x * tile_size
    jogador.pixel_y = jogador.grid_y * tile_size

    return destino, mapa_dict, map_rows, map_cols


# ─────────────────────────────────────────────────────────────────────────────
# Mapas do mundo  —  adicione / remova entradas aqui
# ─────────────────────────────────────────────────────────────────────────────

mapas_mundo = {
    "fazenda": carregar_mapa_json("mapa_fazenda.json"),
    #"vila":    carregar_mapa_json("mapa_vila.json"),
    # "caverna": carregar_mapa_json("mapa_caverna.json"),
}


# ─────────────────────────────────────────────────────────────────────────────
# Registro automático de sprites  —  cache global {nome_bytes: sprite_id}
# ─────────────────────────────────────────────────────────────────────────────

# Guarda os IDs carregados para evitar chamar load_sprite duas vezes no mesmo PNG.
_sprite_cache: dict[bytes, int] = {}

# Pastas onde os PNGs podem estar (editor primeiro, depois raiz do jogo).
_SPRITE_DIRS: list[str] = [
    os.path.join(HERE, "editor"),
    HERE,
]


def _caminho_png(nome_bytes: bytes) -> bytes | None:
    """
    Dado o nome de um arquivo PNG (ex: b"terras.png"), procura em _SPRITE_DIRS
    e retorna o caminho absoluto em bytes, ou None se não encontrar.
    """
    nome_str = nome_bytes.decode("utf-8")
    for pasta in _SPRITE_DIRS:
        caminho = os.path.join(pasta, nome_str)
        if os.path.isfile(caminho):
            return caminho.encode("utf-8")
    return None


def inicializar_sprites(engine_video) -> dict[bytes, int]:
    """
    Varre todos os mapas em ``mapas_mundo`` e carrega automaticamente cada
    spritesheet referenciada nos blocos, evitando duplicatas.

    Retorna ``sprite_ids``: dict {nome_png_bytes: sprite_id_int}

    Uso em game.py::

        from artes import mapas_mundo, aplicar_troca_mapa, inicializar_sprites
        sprite_ids = inicializar_sprites(v)   # substitui todos os load_sprite manuais
    """
    global _sprite_cache

    for mapa_dict in mapas_mundo.values():
        for bloco in mapa_dict.get("blocos", {}).values():
            sprite_nome = bloco.get("sprite")
            if not sprite_nome or sprite_nome in _sprite_cache:
                continue
            caminho = _caminho_png(sprite_nome)
            if caminho is None:
                print(f"[WARN] Spritesheet não encontrada: {sprite_nome!r}")
                continue
            try:
                sid = engine_video.load_sprite(caminho)
                _sprite_cache[sprite_nome] = sid
                print(f"[INFO] Sprite carregado: {sprite_nome!r} → id {sid}")
            except Exception as e:
                print(f"[WARN] Erro ao carregar sprite {sprite_nome!r}: {e}")

    return _sprite_cache


def carregar_sprite_extra(engine_video, nome: bytes) -> int | None:
    """
    Carrega um PNG avulso (ex: b"player_sprites.png", b"ascii.png") que não
    vem de nenhum mapa, e o adiciona ao cache.  Retorna o sprite_id ou None.

    Útil para font, frame, player — arquivos fixos que o game.py ainda precisa
    carregar explicitamente, mas sem precisar montar o caminho manualmente.
    """
    global _sprite_cache

    if nome in _sprite_cache:
        return _sprite_cache[nome]

    caminho = _caminho_png(nome)
    if caminho is None:
        print(f"[WARN] Arquivo não encontrado: {nome!r}")
        return None
    try:
        sid = engine_video.load_sprite(caminho)
        _sprite_cache[nome] = sid
        return sid
    except Exception as e:
        print(f"[WARN] Erro ao carregar {nome!r}: {e}")
        return None