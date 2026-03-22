from itens import *

class Player:
    def __init__(self, engine_video, start_grid_x, start_grid_y, sprite_id, tile_size):
        self.engine_video = engine_video
        self.grid_x = start_grid_x
        self.grid_y = start_grid_y
        self.tile_size = tile_size
        self.pixel_x = start_grid_x * tile_size
        self.pixel_y = start_grid_y * tile_size
        self.destino_x = self.pixel_x
        self.destino_y = self.pixel_y
        self.movendo = False
        self.velocidade = 2
        self.tempo_parado = 0
        
        # --- Sistema de Animação ---
        self.sprite_id = sprite_id
        self.tile_w = 16  # Largura do tile no spritesheet
        self.tile_h = 16 # Altura do tile no spritesheet
        
        # Mapeamento de direções para linhas do spritesheet
        self.direcoes = {
            'baixo': 0,
            'esquerda': 1,
            'direita': 2,
            'cima': 3
        }
        
        # Estado de animação
        self.direcao = 'baixo'
        self.frame_atual = 2  # Começa no meio (parado)
        self.frame_contador = 0
        self.frames_por_animacao = 12  # Velocidade da animação
        self.movendo = False
        
        # Cria o objeto usando tile
        self.oid = engine_video.add_tile_object(
            x=1 * self.tile_w,
            y=1 * self.tile_h,
            sprite_id=sprite_id,
            tile_x=0,
            tile_y=0,
            tile_w=self.tile_w,
            tile_h=self.tile_h
        )
        
    # Atributos do jogador
        self.nome = "Jorge"
        self.hp_max = 50
        self.hp = self.hp_max
        self.mana_max = 100
        self.mana = self.mana_max
        self.nivel = 1
        self.pontos = 0
        self.gold = 350
        self.xp_max = 100
        self.xp = 0
        self.ano = 1
        self.dias = 1
        self.clima = "sol"
        self.caixa_vendas = {}
        self.dias_sem_chuva = 0
        self.proxima_chuva_em = random.randint(5, 10)
        self.mapa_atual = ""
        self.invetario = {}
        self.espacos_inventario = 24
        self.hotbar = {i: None for i in range(1, 10)}
        self.item_selecionado = 1
        self.amizades = {}
        self.itens_equipados = {
            "Capacete": None,
            "Peitoral": None,
            "Primeira Mão": None,
            "Segunda Mão": None
        }
        self.horas = 6
        self.minutos = 0

        self.dia_atual = 1
        self.estacao_atual = "Primavera"

        # ── Sistema de Habilidades e XP ──────────────────────────────────────
        # XP geral — ao chegar em xp_por_ponto o jogador pode distribuir 1 ponto
        self.xp_hab         = 0        # XP acumulado no ciclo atual
        self.xp_total       = 0        # XP total acumulado na vida inteira
        self.pontos_hab     = 0        # Pontos prontos para distribuir
        # XP necessário para o PRÓXIMO ponto — dobra a cada level up
        self.xp_por_ponto   = 100      # começa em 100, vai: 100→200→400→800...

        # Níveis por habilidade (1–10)
        self.hab_coleta  = 1
        self.hab_cultivo = 1
        self.hab_pesca   = 1
        self.hab_social  = 1

        # XP acumulado dentro de cada habilidade (para mostrar barra individual)
        self.xp_coleta   = 0
        self.xp_cultivo  = 0
        self.xp_pesca    = 0
        self.xp_social   = 0

        # Referência aos NPCs para colisão — injetada por game.py via set_npcs_ref()
        self._todos_npcs = None

    def set_npcs_ref(self, todos_npcs):
        """Injeta a referência ao dict de NPCs para colisão bidirecional."""
        self._todos_npcs = todos_npcs

    def dormir(self, mapas_mundo):
        """Avança o tempo e processa o mundo."""
        self.dia_atual += 1
        if self.dia_atual > 28:
            self.dia_atual = 1
            estacoes = ["Primavera", "Verao", "Outono", "Inverno"]
            idx = estacoes.index(self.estacao_atual)
            self.estacao_atual = estacoes[(idx + 1) % 4]
        from objeto import atualizar_plantacoes_do_mundo
        atualizar_plantacoes_do_mundo(mapas_mundo, self.estacao_atual)
        return f"Dia {self.dia_atual} da {self.estacao_atual} começou!"

    def atualizar_sprite(self):
        linha = 0 # Como todas as sprites estão na mesma linha, a linha é sempre 0
        col = 0
        flip = False
        
        # Mapeamento baseado no seu spritesheet
        if self.direcao == 'baixo':
            if self.frame_atual == 0: col = 0   # Parado
            elif self.frame_atual == 1: col = 3 # Passo 1
            elif self.frame_atual == 2: col = 6 # Passo 2
            
        elif self.direcao == 'esquerda':
            if self.frame_atual == 0: col = 1   # Parado
            elif self.frame_atual == 1: col = 4 # Passo 1
            elif self.frame_atual == 2: col = 7 # Passo 2
            
        elif self.direcao == 'direita':
            if self.frame_atual == 0: col = 1   # Parado (Mesmo da esquerda)
            elif self.frame_atual == 1: col = 4 # Passo 1
            elif self.frame_atual == 2: col = 7 # Passo 2
            flip = True                         # Vira a imagem da esquerda
            
        elif self.direcao == 'cima':
            if self.frame_atual == 0: col = 2   # Parado
            elif self.frame_atual == 1: col = 5 # Passo 1
            elif self.frame_atual == 2: col = 8 # Passo 2

        # Passamos a coluna PURA direto para a engine, sem multiplicar!
        self.engine_video.set_object_tile(self.oid, tile_x=col, tile_y=linha)
        
        # Ativa/desativa o flip horizontal (se o motor suportar)
        if hasattr(self.engine_video, 'set_object_flip'):
            self.engine_video.set_object_flip(self.oid, flip_h=flip, flip_v=False)

    def animar(self):
        """Sistema de animação com suavização de movimento contínuo"""
        if self.movendo:
            self.tempo_parado = 0  # Zera o tempo parado pois ele está andando
            self.frame_contador += 1
            
            if self.frame_contador >= self.frames_por_animacao: 
                self.frame_contador = 0
                
                # Enquanto segura a tecla, alterna SOMENTE entre o passo 1 e 2
                if self.frame_atual == 1:
                    self.frame_atual = 2
                else:
                    self.frame_atual = 1
                    
                self.atualizar_sprite()
        else:
            # Ele parou? Vamos contar os frames antes de forçar a pose "Parado"
            self.tempo_parado += 1
            
            # Só muda para a coluna 0 (Parado) se ele ficar solto por mais de 3 frames.
            # Isso ignora aquela pausa de 1 frame entre os blocos!
            if self.tempo_parado > 3:
                if self.frame_atual != 0: 
                    self.frame_atual = 0
                    self.atualizar_sprite()

    # ─────────────────────────────────────────────────────────────────────────
    # COLISÃO  —  simples, tile inteiro, estilo GBC
    # ─────────────────────────────────────────────────────────────────────────

    def _tile_solido(self, mapa_dict, gx, gy):
        """Retorna True se qualquer camada tem um tile sólido em (gx, gy)."""
        arte = mapa_dict.get("arte", [])
        rows = len(arte)
        cols = len(arte[0]) if rows > 0 else 0

        if not (0 <= gx < cols and 0 <= gy < rows):
            return True  # fora do mapa = parede sólida

        blocos = mapa_dict["blocos"]
        for layer_key in ("chao", "arte", "topo"):
            grade = mapa_dict.get(layer_key, [])
            if not grade or gy >= len(grade) or gx >= len(grade[gy]):
                continue
            vid = grade[gy][gx]
            if vid and blocos.get(vid, {}).get("solid", False):
                return True
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # MOVIMENTAÇÃO
    # ─────────────────────────────────────────────────────────────────────────

    def _deslizar_para_destino(self, mapa_dict):
        ts = self.tile_size

        # ── Move em X ────────────────────────────────────────────────────────
        if self.pixel_x != self.destino_x:
            if self.pixel_x < self.destino_x:
                self.pixel_x = min(self.pixel_x + self.velocidade, self.destino_x)
            else:
                self.pixel_x = max(self.pixel_x - self.velocidade, self.destino_x)

        # ── Move em Y ────────────────────────────────────────────────────────
        if self.pixel_y != self.destino_y:
            if self.pixel_y < self.destino_y:
                self.pixel_y = min(self.pixel_y + self.velocidade, self.destino_y)
            else:
                self.pixel_y = max(self.pixel_y - self.velocidade, self.destino_y)

        # ── Chegou ao destino ─────────────────────────────────────────────────
        if self.pixel_x == self.destino_x and self.pixel_y == self.destino_y:
            self.movendo = False
            self.grid_x  = self.pixel_x // ts
            self.grid_y  = self.pixel_y // ts

    def update(self, mapa_dict):
        if self.movendo:
            self._deslizar_para_destino(mapa_dict)
        else:
            self._checar_input(mapa_dict)
        self.animar()

    def _checar_input(self, mapa_dict):
        dx, dy = 0, 0
        nova_direcao = self.direcao
        v = self.engine_video
        if v.key_down(b"w") or v.key_down(b"up"):
            dy = -1;  nova_direcao = 'cima'
        elif v.key_down(b"s") or v.key_down(b"down"):
            dy = 1;   nova_direcao = 'baixo'
        elif v.key_down(b"a") or v.key_down(b"left"):
            dx = -1;  nova_direcao = 'esquerda'
        elif v.key_down(b"d") or v.key_down(b"right"):
            dx = 1;   nova_direcao = 'direita'

        if dx != 0 or dy != 0:
            self.direcao = nova_direcao
            ts = self.tile_size

            futuro_x  = self.pixel_x + dx * ts
            futuro_y  = self.pixel_y + dy * ts
            futuro_gx = futuro_x // ts
            futuro_gy = futuro_y // ts

            # Verifica limites do mapa
            arte     = mapa_dict.get("arte", [])
            map_rows = len(arte)
            map_cols = len(arte[0]) if map_rows > 0 else 0
            if not (0 <= futuro_gx < map_cols and 0 <= futuro_gy < map_rows):
                return

            # Colisão com tile
            if self._tile_solido(mapa_dict, futuro_gx, futuro_gy):
                return

            # Colisão com NPC
            npcs_ref = getattr(self, '_todos_npcs', None)
            if npcs_ref:
                for npc in npcs_ref.values():
                    if (getattr(npc, 'mapa_atual', None) == getattr(self, 'mapa_atual', None)
                            and npc.x == futuro_gx and npc.y == futuro_gy):
                        return

            # Inicia deslizamento
            self.movendo   = True
            self.destino_x = futuro_x
            self.destino_y = futuro_y

            # Portais
            portais = mapa_dict.get("portais", {})
            if (futuro_gx, futuro_gy) in portais:
                portal = portais[(futuro_gx, futuro_gy)]
                self.mapa_atual         = portal['destino']
                self.grid_x, self.grid_y = portal['spawn']
                self.pixel_x  = self.grid_x * ts
                self.pixel_y  = self.grid_y * ts
                self.destino_x = self.pixel_x
                self.destino_y = self.pixel_y
                self.movendo   = False
        else:
            self.frame_atual = 1

    def get_pixel_pos(self):
        return self.pixel_x, self.pixel_y

    def passar_tempo(self, minutos_para_passar=1):
        self.minutos += minutos_para_passar
        if self.minutos >= 60:
            self.minutos -= 60
            self.horas += 1
            if self.horas >= 24:
                self.horas = 0
                self.dias += 1
                self.dia_semana_idx = (self.dia_semana_idx + 1) % 7
                self.dias_na_estacao += 1
    
    # ─────────────────────────────────────────────────────────────────────────
    # SISTEMA DE HABILIDADES E XP
    # ─────────────────────────────────────────────────────────────────────────

    # Nível máximo de cada habilidade
    _HAB_MAX = 10
    # XP necessário por ciclo para ganhar 1 ponto de habilidade
    _XP_POR_PONTO = 100

    # Tabela de XP por ação — pode ser sobrescrita por item.xp_ganho
    _XP_ACOES = {
        "plantar":    1,
        "colher":    15,
        "pescar":    20,
        "conversar":  5,
        "presente":  10,
    }

    def ganhar_xp_hab(self, acao: str, bonus_xp: int = 0) -> dict:
        """
        Concede XP de habilidade por uma ação.
        acao: 'plantar' | 'colher' | 'pescar' | 'conversar' | 'presente'
        bonus_xp: XP extra definido no item (item.xp_ganho)
        Retorna dict com xp_ganho, ponto_ganho (bool), mensagem.

        A cada ponto ganho o limiar de XP dobra:
          1º ponto → 100 XP  |  2º → 200  |  3º → 400  |  4º → 800 ...
        """
        base   = self._XP_ACOES.get(acao, 0)
        ganho  = base + bonus_xp

        if ganho <= 0:
            return {"xp_ganho": 0, "ponto_ganho": False, "mensagem": ""}

        # Garante que xp_por_ponto existe (compatibilidade com saves antigos)
        if not hasattr(self, 'xp_por_ponto') or self.xp_por_ponto <= 0:
            self.xp_por_ponto = 100

        # Acumula XP geral
        self.xp_hab   = getattr(self, 'xp_hab',   0) + ganho
        self.xp_total = getattr(self, 'xp_total', 0) + ganho

        # Acumula XP na habilidade específica
        attr_xp = {"plantar": "xp_cultivo", "colher": "xp_coleta",
                   "pescar": "xp_pesca", "conversar": "xp_social",
                   "presente": "xp_social"}.get(acao)
        if attr_xp:
            setattr(self, attr_xp, getattr(self, attr_xp, 0) + ganho)

        # Verifica ciclo de ponto — limiar dobra a cada level up
        ponto_ganho = False
        msg = f"+{ganho} XP [{acao}]"
        while self.xp_hab >= self.xp_por_ponto:
            self.xp_hab    -= self.xp_por_ponto
            self.xp_por_ponto *= 2          # ← dobra o limiar
            self.pontos_hab  = getattr(self, 'pontos_hab', 0) + 1
            ponto_ganho      = True
            msg += "  >>  Ponto de habilidade disponivel!"

        return {"xp_ganho": ganho, "ponto_ganho": ponto_ganho, "mensagem": msg}

    def distribuir_ponto(self, habilidade: str) -> str:
        """
        Gasta 1 ponto_hab para subir 1 nível na habilidade escolhida.
        habilidade: 'coleta' | 'cultivo' | 'pesca' | 'social'
        """
        attr = f"hab_{habilidade}"
        if not hasattr(self, attr):
            return f"Habilidade '{habilidade}' não existe."
        if getattr(self, 'pontos_hab', 0) <= 0:
            return "Sem pontos disponíveis."
        nivel_atual = getattr(self, attr, 1)
        if nivel_atual >= self._HAB_MAX:
            return f"{habilidade.capitalize()} já está no nível máximo ({self._HAB_MAX})!"
        setattr(self, attr, nivel_atual + 1)
        self.pontos_hab -= 1
        return f"{habilidade.capitalize()} agora é nível {nivel_atual + 1}!"

    def bonus_estrelas_item(self, item) -> int:
        """
        Sorteia as estrelas efetivas do item para ESTE jogador com base
        no nível da habilidade correspondente.
          Cultivo  → hab_cultivo
          Colheita → hab_coleta
          Peixe    → hab_pesca

        Tabela de chances por nível N (1-indexado):
          bronze  = 10 + (N-1)*5 %
          prata   = 2.5 + (N-1)*2.5 %
          ouro    = (N-1)*1.5 %
          platina = max(0, (N-4)*0.9) %   (só a partir do nível 4)
        """
        import random as _random

        tipo = getattr(item, 'tipo_presente', '')
        mapa_hab = {
            'Cultivo':  'hab_cultivo',
            'Colheita': 'hab_coleta',
            'Peixe':    'hab_pesca',
        }
        attr = mapa_hab.get(tipo)
        if attr is None:
            return getattr(item, 'estrelas', 0)

        # Itens com estrelas fixas (ex: após fertilizante)
        base = getattr(item, 'estrelas', 0)
        if base > 0:
            return base

        nivel = getattr(self, attr, 1)
        n = nivel - 1   # offset: nível 1 → n=0

        chance_bronze  = 10.0 + n * 5.0
        chance_prata   = 2.5  + n * 2.5
        chance_ouro    = 0.0  + n * 1.5
        chance_platina = max(0.0, (n - 3) * 0.9)

        r = _random.uniform(0, 100)
        if r < chance_platina:
            return 4
        if r < chance_ouro:
            return 3
        if r < chance_prata:
            return 2
        if r < chance_bronze:
            return 1
        return 0

    def bonus_amizade(self) -> float:
        """Multiplicador de pontos de amizade dado pelo nível Social."""
        nivel = getattr(self, 'hab_social', 1)
        return 1.0 + (nivel - 1) * 0.111   # +~11% por nível → 2× no nível 10

    # mantém compatibilidade com código antigo que chama ganhar_xp(qtd)
    def ganhar_xp(self, quantidade):
        self.xp += quantidade
        level_up = False
        if self.xp >= self.xp_max:
            self.xp -= self.xp_max
            self.xp_max = int(self.xp_max * 1.5)
            self.nivel += 1
            self.pontos += 3
            self.hp = self.hp_max
            self.mana = self.mana_max
            level_up = True
        return level_up

    def adicionar_item(self, item_nome, quantidade=1, todos_itens=todos_itens):
        if item_nome not in todos_itens:
            return {"ok": False, "msg": f"Item '{item_nome}' não existe."}

        item_obj = todos_itens[item_nome]
        limite = 1 if item_obj.tipo == "Equipavel" else 999

        if quantidade < 0:
            qtd_remover = abs(quantidade)
            atual = self.invetario.get(item_nome, 0)
            if atual < qtd_remover:
                return {"ok": False, "msg": f"Sem {item_nome} suficiente."}
            self.invetario[item_nome] -= qtd_remover
            if self.invetario[item_nome] <= 0:
                del self.invetario[item_nome]
            return {"ok": True, "msg": f"-{qtd_remover}x {item_nome}"}

        if item_obj.tipo == "Equipavel":
            if item_nome in self.invetario:
                return {"ok": False, "msg": f"Já tem {item_nome}."}
            if len(self.invetario) >= 12:
                return {"ok": False, "msg": "Mochila cheia!"}
            self.invetario[item_nome] = 1
            return {"ok": True, "msg": f"+1x {item_nome}"}

        atual = self.invetario.get(item_nome, 0)
        if atual == 0 and len(self.invetario) >= 12:
            return {"ok": False, "msg": "Mochila cheia!"}

        espaco = limite - atual
        qtd_real = min(quantidade, espaco)
        self.invetario[item_nome] = atual + qtd_real

        if qtd_real < quantidade:
            return {"ok": True, "msg": f"+{qtd_real}x {item_nome} (slot cheio, {quantidade - qtd_real}x perdido)"}
        return {"ok": True, "msg": f"+{qtd_real}x {item_nome}"}

    def analizar_itens(self, item_nome, todos_itens=todos_itens):
        if item_nome not in todos_itens:
            return {"ok": False, "msg": "Item desconhecido."}
        if item_nome not in self.invetario:
            return {"ok": False, "msg": f"Você não tem {item_nome}."}

        item_obj = todos_itens[item_nome]

        if item_obj.tipo == "Consumivel":
            efeito = False
            if item_obj.recupar_hp > 0 and self.hp < self.hp_max:
                self.hp = min(self.hp + item_obj.recupar_hp, self.hp_max)
                efeito = True
            if item_obj.recupar_mn > 0 and self.mana < self.mana_max:
                self.mana = min(self.mana + item_obj.recupar_mn, self.mana_max)
                efeito = True
            if not efeito:
                return {"ok": False, "msg": "HP e mana já estão cheios."}
            self.invetario[item_nome] -= 1
            if self.invetario[item_nome] <= 0:
                del self.invetario[item_nome]
            return {"ok": True, "msg": f"Usou {item_nome}."}

        if item_obj.tipo == "Equipavel":
            slot = item_obj.sloat_equipado
            if slot not in self.itens_equipados:
                return {"ok": False, "msg": f"Slot '{slot}' inválido."}

            item_atual = self.itens_equipados[slot]

            if item_atual == item_nome:
                self._aplicar_stats(item_obj, remover=True)
                self.itens_equipados[slot] = None
                return {"ok": True, "msg": f"{item_nome} desequipado."}

            if item_atual is not None:
                self._aplicar_stats(todos_itens[item_atual], remover=True)

            self.itens_equipados[slot] = item_nome
            self._aplicar_stats(item_obj, remover=False)
            msg = f"Equipou {item_nome}." if item_atual is None else f"Trocou {item_atual} por {item_nome}."
            return {"ok": True, "msg": msg}

        return {"ok": False, "msg": "Tipo de item sem ação."}

    def _aplicar_stats(self, item_obj, remover=False):
        fator = -1 if remover else 1
        self.hp_max += item_obj.bonus_hp * fator
        self.mana_max += item_obj.bonus_mn * fator
        self.hp = min(self.hp, self.hp_max)
        self.mana = min(self.mana, self.mana_max)
    
    def definir_hotbar(self, slot, nome_item):
        if slot not in self.hotbar:
            return {"ok": False, "msg": f"Slot {slot} inválido."}
        if nome_item and nome_item not in self.invetario:
            return {"ok": False, "msg": f"Você não tem {nome_item}."}
        self.hotbar[slot] = nome_item
        return {"ok": True, "msg": f"Slot {slot} definido: {nome_item or 'vazio'}"}

    def usar_hotbar(self, slot, todos_itens=todos_itens):
        if slot not in self.hotbar:
            return {"ok": False, "msg": "Slot inválido."}
        item_nome = self.hotbar[slot]
        if not item_nome:
            return {"ok": False, "msg": "Slot vazio."}
        return self.analizar_itens(item_nome, todos_itens)

    def comprar_item(self, nome_item, todos_itens=todos_itens, quantidade=1):
        if nome_item not in todos_itens:
            return "Item não existe."
        
        item = todos_itens[nome_item]
        
        if not item.compravel:
            return f"{nome_item} não está à venda."
        
        custo_total = item.compra * quantidade
        
        if self.gold < custo_total:
            return f"Dinheiro insuficiente. Precisa de {custo_total}g."
        
        resultado = self.adicionar_item(nome_item, quantidade, todos_itens)
        
        if resultado["ok"]:
            self.gold -= custo_total
            return f"Comprou {quantidade}x {nome_item} por {custo_total}g."
        else:
            return resultado["msg"]

    def vender_item(self, nome_item, todos_itens=todos_itens, quantidade=1):
        if nome_item not in self.invetario:
            return "Você não tem esse item."
        
        if nome_item not in todos_itens:
            return "Item desconhecido."
        
        item = todos_itens[nome_item]
        
        if not item.vendivel:
            return f"{nome_item} não pode ser vendido."
        
        qtd_disponivel = self.invetario.get(nome_item, 0)
        qtd_real = min(quantidade, qtd_disponivel)
        
        if qtd_real <= 0:
            return f"Você não tem {nome_item} suficiente."
        
        ganho_total = item.preco * qtd_real
        
        match = None
        for key in self.invetario.keys():
            if key.lower() == nome_item.lower():
                match = key
                break
        
        if not match:
            return "Item não encontrado no inventário."
        
        self.invetario[match] -= quantidade
        if self.invetario[match] <= 0:
            del self.invetario[match]
            if hasattr(self, 'itens_equipados'):
                for slot, equipado in self.itens_equipados.items():
                    if equipado == match:
                        self.itens_equipados[slot] = None
                        
        self.gold += ganho_total
        return f"Vendeu {quantidade}x {match} por {ganho_total}g."

    def processar_vendas_do_dia(self, todos_itens=todos_itens):
        lucro_total = 0
        resumo = {}

        for nome_item in self.caixa_vendas:
            if nome_item in todos_itens:
                valor = todos_itens[nome_item].preco
                lucro_total += valor
                if nome_item not in resumo:
                    resumo[nome_item] = {"qtd": 0, "valor": 0}
                resumo[nome_item]["qtd"] += 1
                resumo[nome_item]["valor"] += valor

        self.gold += lucro_total
        self.caixa_vendas = []

        return {"lucro_total": lucro_total, "resumo": resumo}
    
    def dar_presente(self, nome_npc, nome_item, todos_itens=todos_itens):
        if self.invetario.get(nome_item, 0) <= 0:
            return {"ok": False, "msg": "Você não tem esse item."}

        item = todos_itens.get(nome_item)
        if not item:
            return {"ok": False, "msg": f"Item '{nome_item}' não existe."}

        self.adicionar_item(todos_itens, nome_item, -1)

        pontos = 40
        if item.estrelas > 0:
            pontos += item.estrelas * 10

        self.amizades[nome_npc] = self.amizades.get(nome_npc, 0) + pontos

        if item.estrelas > 0:
            msg = f"Deu {nome_item} ({item.estrelas}★) para {nome_npc}! (+{pontos} pts)"
        else:
            msg = f"Deu {nome_item} para {nome_npc}. (+{pontos} pts)"

        return {"ok": True, "msg": msg, "pontos": pontos}
    
    def verificar_aniversarios(self, todos_npcs):
        aniversariantes = []
        for nome_npc, npc in todos_npcs.items():
            if not npc.aniversario:
                continue
            estacao_aniv, dia_aniv = npc.aniversario
            if self.estacao_idx == estacao_aniv and self.dias_na_estacao == dia_aniv:
                aniversariantes.append(nome_npc)
        return aniversariantes

    def obter_pagina_inventario(self, todos_itens=todos_itens, pagina=0, itens_por_pagina=4, cursor_idx=0):
        if not hasattr(self, 'itens_equipados'):
            self.itens_equipados = {}

        itens_lista = list(self.invetario.items())
        total_itens = len(itens_lista)
        max_paginas = (total_itens - 1) // itens_por_pagina if total_itens > 0 else 0
        
        pagina = max(0, min(pagina, max_paginas))
        
        inicio = pagina * itens_por_pagina
        fim = inicio + itens_por_pagina
        itens_pagina = itens_lista[inicio:fim]
        
        if cursor_idx >= len(itens_pagina):
            cursor_idx = max(0, len(itens_pagina) - 1)
        if cursor_idx < 0:
            cursor_idx = 0
            
        item_selecionado = itens_pagina[cursor_idx][0] if itens_pagina else None

        conteudo = ""
        if not itens_pagina:
            conteudo = "Sua mochila esta vazia.\n"
        else:
            for i, (nome, qtd) in enumerate(itens_pagina):
                marca = "-> " if i == cursor_idx else "   "
                equipado = " (e)" if nome in self.itens_equipados.values() else ""
                conteudo += f"{marca}{nome}{equipado} x{qtd}\n"
                
        descricao_texto = ""
        if item_selecionado and item_selecionado in todos_itens:
            item_obj = todos_itens[item_selecionado]
            descricao_texto = f"\n- {item_obj.descrica}"
                
        rodape = f"{descricao_texto}\n\nPag {pagina + 1}/{max_paginas + 1}|\n[Up/Down] Move [right/left] Pag\n[Enter] Usar/Equipar  [Z] Jogar fora\n[Space] Sair"
        
        return conteudo + rodape, max_paginas, cursor_idx, item_selecionado

    def remover_item(self, nome_item, qtd=1):
        if nome_item in self.invetario:
            self.invetario[nome_item] -= qtd
            if self.invetario[nome_item] <= 0:
                del self.invetario[nome_item]
                if hasattr(self, 'itens_equipados') and nome_item in self.itens_equipados.values():
                    for slot, item in self.itens_equipados.items():
                        if item == nome_item:
                            self.itens_equipados[slot] = None

    def usar_item(self, nome_item, todos_itens=todos_itens):
        if nome_item not in self.invetario:
            return "Você não tem esse item."
        
        item_obj = todos_itens.get(nome_item)
        if not item_obj:
            return "Item desconhecido."

        if item_obj.tipo == "Consumivel":
            usou = False
            
            if item_obj.recupar_hp > 0:
                if self.hp < self.hp_max:
                    self.hp = min(self.hp + item_obj.recupar_hp, self.hp_max)
                    usou = True
                else:
                    return "HP já está cheio."
            
            if item_obj.recupar_mn > 0:
                if self.mana < self.mana_max:
                    self.mana = min(self.mana + item_obj.recupar_mn, self.mana_max)
                    usou = True
            
            if usou:
                self.invetario[nome_item] -= 1
                if self.invetario[nome_item] <= 0:
                    del self.invetario[nome_item]
                return f"Você usou {nome_item}."
            
            return "Não teve efeito."

        elif item_obj.tipo == "Equipavel":
            slot = item_obj.sloat_equipado
            
            if slot not in self.itens_equipados:
                return f"Slot '{slot}' não existe no personagem."
            
            item_atual_nome = self.itens_equipados[slot]
            
            if item_atual_nome == nome_item:
                if hasattr(self, '_aplicar_stats'):
                    self._aplicar_stats(item_obj, remover=True)
                self.itens_equipados[slot] = None
                return f"{nome_item} desequipado."
            
            msg_inicio = "Equipou "
            if item_atual_nome is not None:
                item_antigo = todos_itens.get(item_atual_nome)
                if item_antigo and hasattr(self, '_aplicar_stats'):
                    self._aplicar_stats(item_antigo, remover=True)
                msg_inicio = f"Trocou {item_atual_nome} por "
            
            self.itens_equipados[slot] = nome_item
            if hasattr(self, '_aplicar_stats'):
                self._aplicar_stats(item_obj, remover=False)
            
            return f"{msg_inicio}{nome_item}!"

        return "Tipo de item inválido."