import json as _json
import os   as _os

_SAVE_PATH    = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "save.json")
_SAVE_VERSION = 4

def salvar_jogo(jogador, mapas_mundo, estado_chuva=None, estado_ui=None):
    from objeto import serializar_baus
    from itens  import todos_npcs

    # ── 1. Mapas: arte + plantações ──────────────────────────────────────────
    mapas_serial = {}
    for nome_mapa, mapa_dict in mapas_mundo.items():
        plantas_mapa = {
            f"{cx},{cy}": _limpar_dados_planta(dados)
            for (cx, cy), dados in mapa_dict.get("plantacoes", {}).items()
        }
        mapas_serial[nome_mapa] = {
            "arte":       mapa_dict.get("arte", []),
            "plantacoes": plantas_mapa,
        }

    # ── 2. NPCs: tudo que define o estado social e posicional ───────────────
    npcs_serial = {}
    for nome_npc, npc in todos_npcs.items():
        npcs_serial[nome_npc] = {
            # Posição e movimento
            "x":                  npc.x,
            "y":                  npc.y,
            "mapa_atual":         npc.mapa_atual,
            "direcao":            getattr(npc, "direcao", "baixo"),
            # Navegação (serializada como listas — tuplas não são JSON)
            "meta_global":        list(npc.meta_global) if npc.meta_global else None,
            "destino_imediato":   list(npc.destino_imediato) if npc.destino_imediato else None,
            "caminho_atual":      [list(p) for p in getattr(npc, "caminho_atual", [])],
            # Social — flags diárias
            "afeto":                   getattr(npc, "afeto",                   0),
            "nivel_amizade":           getattr(npc, "nivel_amizade",           0),
            "conversou_hoje":          getattr(npc, "conversou_hoje",          False),
            "conversou_esta_semana":   getattr(npc, "conversou_esta_semana",   False),
            "recebeu_presente_hoje":   getattr(npc, "recebeu_presente_hoje",   False),
            "presentes_semana":        getattr(npc, "presentes_semana",        0),
            # Missões
            "missoes_aceitas":         list(getattr(npc, "missoes_aceitas",    [])),
            "missoes_concluidas":      list(getattr(npc, "missoes_concluidas", [])),
            # Histórico de presentes e gostos descobertos
            "itens_dados":             dict(getattr(npc, "itens_dados",        {})),
            "gostos_descobertos":      dict(getattr(npc, "gostos_descobertos", {})),
        }

    # ── 3. Clima ─────────────────────────────────────────────────────────────
    chuva_serial = {}
    if estado_chuva is not None:
        chuva_serial = {
            "chovendo":       estado_chuva.get("chovendo",       False),
            "dias_restantes": estado_chuva.get("dias_restantes", 0),
        }

    # ── 4. Relógio: timer_tempo para retomar de onde parou ──────────────────
    timer_tempo_serial = 0
    if estado_ui is not None:
        timer_tempo_serial = estado_ui.get("timer_tempo", 0)

    # ── 5. Jogador ────────────────────────────────────────────────────────────
    jogador_serial = {
        # Identificação e localização
        "nome":       jogador.nome,
        "mapa_atual": jogador.mapa_atual,
        "grid_x":     jogador.grid_x,
        "grid_y":     jogador.grid_y,
        "direcao":    jogador.direcao,
        # Vida e status
        "hp":         jogador.hp,       "hp_max":   jogador.hp_max,
        "mana":       jogador.mana,     "mana_max": jogador.mana_max,
        "xp":         jogador.xp,       "xp_max":   jogador.xp_max,
        "nivel":      jogador.nivel,
        "pontos":     jogador.pontos,
        "gold":       jogador.gold,
        # Níveis de habilidade
        "nivel_pesca":    getattr(jogador, "nivel_pesca",    1),
        "nivel_pescaria": getattr(jogador, "nivel_pescaria", 1),
        "nivel_pantil":   getattr(jogador, "nivel_pantil",   1),
        "nivel_coleta":   getattr(jogador, "nivel_coleta",   1),
        # Tempo do mundo
        "dia_atual":      jogador.dia_atual,
        "estacao_atual":  jogador.estacao_atual,
        "horas":          jogador.horas,
        "minutos":        jogador.minutos,
        "timer_tempo":    timer_tempo_serial,   # ← NOVO: frames do relógio
        "ano":            getattr(jogador, "ano",  1),
        "dias":           getattr(jogador, "dias", 1),
        # Clima (estado do jogador)
        "clima":             getattr(jogador, "clima",             "sol"),
        "dias_sem_chuva":    jogador.dias_sem_chuva,
        "proxima_chuva_em":  jogador.proxima_chuva_em,
        # Inventário e equipamentos
        "invetario":         dict(jogador.invetario),
        "hotbar":            {str(k): v for k, v in jogador.hotbar.items()},
        "item_selecionado":  jogador.item_selecionado,
        "itens_equipados":   dict(jogador.itens_equipados),
        "caixa_vendas":      jogador.caixa_vendas if isinstance(jogador.caixa_vendas, dict) else {},
        # Social
        "amizades":          dict(jogador.amizades),
        "magias_conhecidas": list(getattr(jogador, "magias_conhecidas", [])),
    }

    # ── 6. Monta e escreve o JSON ─────────────────────────────────────────────
    dados = {
        "_versao": _SAVE_VERSION,
        "jogador": jogador_serial,
        "mapas":   mapas_serial,
        "baus":    serializar_baus(),
        "npcs":    npcs_serial,
        "chuva":   chuva_serial,    # ← NOVO bloco
    }

    try:
        with open(_SAVE_PATH, "w", encoding="utf-8") as f:
            _json.dump(dados, f, ensure_ascii=False, indent=2)
        return "Jogo salvo!"
    except Exception as e:
        return f"Erro ao salvar: {e}"

def carregar_jogo(jogador, mapas_mundo, estado_chuva=None, estado_ui=None):
    """
    Carrega save.json e restaura o estado completo do jogo.

    Parâmetros novos (opcionais — mesmos de salvar_jogo):
        estado_chuva  — dict do clima (modificado in-place se fornecido)
        estado_ui     — dict da UI   (timer_tempo restaurado se fornecido)

    Retorna uma tupla igual à versão original para não quebrar game.py:
        (nome_mapa, mapa_dict, map_rows, map_cols, mensagem)
    """
    if not _os.path.exists(_SAVE_PATH):
        return None, None, 0, 0, "Nenhum save encontrado."

    try:
        with open(_SAVE_PATH, "r", encoding="utf-8") as f:
            dados = _json.load(f)
    except Exception as e:
        return None, None, 0, 0, f"Erro ao ler save: {e}"

    versao = dados.get("_versao", 1)
    jd     = dados.get("jogador", {})

    # ── 1. Jogador — campos simples ──────────────────────────────────────────
    _campos_simples = (
        "nome", "direcao", "hp", "hp_max", "mana", "mana_max",
        "xp", "xp_max", "nivel", "pontos", "gold",
        "nivel_pesca", "nivel_pescaria", "nivel_pantil", "nivel_coleta",
        "dia_atual", "estacao_atual", "horas", "minutos",
        "ano", "dias", "clima", "dias_sem_chuva", "proxima_chuva_em",
        "invetario", "item_selecionado", "itens_equipados",
        "caixa_vendas", "amizades", "magias_conhecidas",
    )
    for campo in _campos_simples:
        if campo in jd:
            setattr(jogador, campo, jd[campo])

    # hotbar: chaves são strings no JSON, precisam ser int
    if "hotbar" in jd:
        jogador.hotbar = {int(k): v for k, v in jd["hotbar"].items()}

    # ── 2. Relógio: restaura o timer_tempo ───────────────────────────────────
    # Sem isso, o relógio reinicia do zero e pode pular horas logo ao acordar.
    if estado_ui is not None and "timer_tempo" in jd:
        estado_ui["timer_tempo"] = jd["timer_tempo"]

    # ── 3. Mapas: arte + plantações ──────────────────────────────────────────
    for nome_mapa, mapa_dados in dados.get("mapas", {}).items():
        if nome_mapa not in mapas_mundo:
            continue
        mapa_dict = mapas_mundo[nome_mapa]
        if mapa_dados.get("arte"):
            mapa_dict["arte"] = mapa_dados["arte"]
        mapa_dict["plantacoes"] = {
            tuple(map(int, k.split(","))): v
            for k, v in mapa_dados.get("plantacoes", {}).items()
        }

    # ── 4. Baús ───────────────────────────────────────────────────────────────
    from objeto import desserializar_baus, _registrar_baus_do_mapa
    if "baus" in dados:
        desserializar_baus(dados["baus"])
    for mapa_dict in mapas_mundo.values():
        _registrar_baus_do_mapa(mapa_dict)

    # ── 5. NPCs — restaura estado completo ───────────────────────────────────
    from itens import todos_npcs
    for nome_npc, npc_dados in dados.get("npcs", {}).items():
        npc = todos_npcs.get(nome_npc)
        if npc is None:
            continue

        # Posição no mundo
        if "x"          in npc_dados: npc.x         = npc_dados["x"]
        if "y"          in npc_dados: npc.y         = npc_dados["y"]
        if "mapa_atual" in npc_dados: npc.mapa_atual = npc_dados["mapa_atual"]
        if "direcao"    in npc_dados: npc.direcao   = npc_dados["direcao"]

        # Navegação (listas → tuplas internas)
        mg = npc_dados.get("meta_global")
        npc.meta_global = tuple(mg) if mg else None

        di = npc_dados.get("destino_imediato")
        npc.destino_imediato = tuple(di) if di else None

        caminho_raw = npc_dados.get("caminho_atual", [])
        npc.caminho_atual = [tuple(p) for p in caminho_raw]

        # Sincroniza pixel com grid restaurado
        npc._teleportar_pixel()

        # Flags sociais diárias
        _campos_npc_sociais = (
            "afeto", "nivel_amizade",
            "conversou_hoje", "conversou_esta_semana",
            "recebeu_presente_hoje", "presentes_semana",
        )
        for campo in _campos_npc_sociais:
            if campo in npc_dados:
                setattr(npc, campo, npc_dados[campo])

        # Missões e histórico
        if "missoes_aceitas"    in npc_dados:
            npc.missoes_aceitas    = list(npc_dados["missoes_aceitas"])
        if "missoes_concluidas" in npc_dados:
            npc.missoes_concluidas = list(npc_dados["missoes_concluidas"])
        if "itens_dados"        in npc_dados:
            npc.itens_dados        = dict(npc_dados["itens_dados"])
        if "gostos_descobertos" in npc_dados:
            npc.gostos_descobertos = dict(npc_dados["gostos_descobertos"])

        # Garante que o atributo existe mesmo em saves antigos
        if not hasattr(npc, "gostos_descobertos"):
            npc.gostos_descobertos = {}

    # ── 6. Clima — restaura chovendo e dias_restantes ────────────────────────
    if estado_chuva is not None and "chuva" in dados:
        cd = dados["chuva"]
        estado_chuva["chovendo"]       = cd.get("chovendo",       False)
        estado_chuva["dias_restantes"] = cd.get("dias_restantes", 0)
        # Atualiza também o campo no jogador para consistência
        jogador.clima = "chuva" if estado_chuva["chovendo"] else "sol"

    # ── 7. Teleporta o jogador para o mapa salvo ──────────────────────────────
    from artes import aplicar_troca_mapa
    mapa_salvo = jd.get("mapa_atual", jogador.mapa_atual)
    gx         = jd.get("grid_x",    jogador.grid_x)
    gy         = jd.get("grid_y",    jogador.grid_y)
    resultado  = aplicar_troca_mapa(
        f"__TROCAR_MAPA__{mapa_salvo}|x{gx}|y{gy}",
        jogador
    )
    # aplicar_troca_mapa retorna (nome_mapa, mapa_dict, map_rows, map_cols)
    nome_mapa, mapa_dict, map_rows, map_cols = resultado
    return nome_mapa, mapa_dict, map_rows, map_cols, "Jogo carregado!"

def _limpar_dados_planta(dados):
    return {k: v for k, v in dados.items() if not k.startswith("_")}