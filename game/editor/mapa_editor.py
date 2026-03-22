import pygame
import sys
import os
import json
import copy
import tkinter as tk
from tkinter import filedialog, simpledialog
# ─── Layout ────────────────────────────────────────────────────────────────────
EDITOR_W, EDITOR_H = 1440, 900
PANEL_W            = 440
TOOLBAR_H          = 54
TAB_H              = 30
TILE_SIZE          = 16
ZOOM_DEFAULT       = 2.0
ZOOM_MIN           = 0.25
ZOOM_MAX           = 12.0
ZOOM_SPEED         = 0.11
SHEET_LIST_H       = 80
SHEET_PREVIEW_H    = 205
PALETTE_ITEM_H     = 30

# ─── Cores ─────────────────────────────────────────────────────────────────────
BG           = (14, 15, 22)
GRID_A       = (30, 33, 52)
GRID_B       = (22, 25, 40)
PANEL_BG     = (19, 21, 34)
PANEL_SEP    = (35, 40, 65)
HDR_BG       = (28, 32, 52)
ACCENT       = (72, 160, 255)
ACCENT2      = (255, 160, 60)
SEL_C        = (250, 210, 40)
TEXT         = (210, 215, 235)
DIM          = (95, 105, 140)
BTN_BG       = (38, 44, 72)
BTN_ON       = (60, 180, 80)
BTN_ON_T     = (10, 10, 20)
WARN         = (255, 80, 80)
VAR_C        = (180, 90, 255)
LAYER_COLORS = [(75, 200, 110), (85, 150, 255), (255, 130, 70)]
LAYER_NAMES  = ["0-Chao", "1-Meio", "2-Topo"]

ACOES_DISPONIVEIS = ["", "loja", "caixa", "cama", "trocar_mapa",
                     "tile_mar", "tile_lago", "tile_mangi"]
ACOES_LABELS      = ["nenhuma", "loja", "caixa", "cama", "trocar_mapa",
                     "Mar", "Lago", "Manguezal"]

# ─── Item-Tile ────────────────────────────────────────────────────────────────
ITEM_TIPOS    = ["Consumivel", "Equipavel", "Semente", "Material"]
ITEM_SLOTS    = ["", "Primeira Mao", "Segunda Mao", "Capacete", "Peitoral", "Botas"]
ITEM_PRESENTE = ["", "Peixe", "Cultivo", "Colheita", "Outros"]

#tileset.png
# ─── Utils ─────────────────────────────────────────────────────────────────────
def make_checker(size=16):
    s = pygame.Surface((size, size))
    h = size // 2
    s.fill((65, 68, 88))
    pygame.draw.rect(s, (42, 44, 62), (0, 0, h, h))
    pygame.draw.rect(s, (42, 44, 62), (h, h, h, h))
    return s

def txt(surf, text, x, y, font, color=TEXT, align="left"):
    r = font.render(str(text), True, color)
    if align == "center": x -= r.get_width() // 2
    elif align == "right": x -= r.get_width()
    surf.blit(r, (x, y))
    return r.get_height()

def txt_ml(surf, text, x, y, font, color=TEXT, max_w=220, line_h=14):
    """Texto com quebra automática de linha. Retorna altura total usada."""
    words = str(text).split(" ")
    line  = ""
    cy    = y
    for word in words:
        test = (line + " " + word).strip()
        if font.size(test)[0] > max_w and line:
            surf.blit(font.render(line, True, color), (x, cy))
            cy  += line_h
            line = word
        else:
            line = test
    if line:
        surf.blit(font.render(line, True, color), (x, cy))
        cy += line_h
    return cy - y

def field_row(surf, label, value, rect, font_xs,
              editing=False, buf="",
              lbl_color=None, val_color=None, accent=None,
              is_bool=False, is_choice=False):
    """Desenha linha label+campo. Retorna o rect do campo desenhado."""
    lbl_color = lbl_color or DIM
    val_color = val_color or TEXT
    accent    = accent    or ACCENT
    # Label à esquerda do rect
    txt(surf, label, rect.x - 4, rect.y + 3, font_xs, lbl_color, "right")
    if is_bool:
        on = bool(value)
        rrect(surf, BTN_ON if on else BTN_BG, rect, rad=3)
        txt(surf, "SIM" if on else "NAO",
            rect.centerx, rect.y + 4, font_xs,
            BTN_ON_T if on else DIM, "center")
    elif is_choice:
        rrect(surf, (40, 50, 80), rect, rad=3, bw=1, bc=ACCENT2)
        disp = str(value) if value not in (None, "") else "—"
        # Trunca se não couber
        while font_xs.size(disp + " ▶")[0] > rect.w - 8 and len(disp) > 2:
            disp = disp[:-1]
        txt(surf, disp + " ▶", rect.x + 5, rect.y + 4, font_xs, ACCENT2)
    else:
        rrect(surf, (25,28,45) if editing else BTN_BG, rect, rad=3,
              bw=1, bc=accent if editing else PANEL_SEP)
        disp = (buf + "|") if editing else (str(value) if value not in (None, "") else "—")
        col  = SEL_C if editing else (val_color if value not in (None, "", 0) else DIM)
        # Trunca texto longo para não vazar do campo
        while font_xs.size(disp)[0] > rect.w - 8 and len(disp) > 3:
            disp = disp[:-1]
        txt(surf, disp, rect.x + 5, rect.y + 4, font_xs, col)
    return rect

def rrect(surf, color, rect, rad=5, bw=0, bc=None):
    pygame.draw.rect(surf, color, rect, border_radius=rad)
    if bw and bc:
        pygame.draw.rect(surf, bc, rect, bw, border_radius=rad)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def make_cell(s, c, l):
    return {"s": s, "c": c, "l": l}


# ─── TileRegistry ──────────────────────────────────────────────────────────────
class TileRegistry:
    """
    Mapeia (sheet_name, col, lin) → props do tile.

    VARIANTES: múltiplos sprites com o MESMO ID são 100% válidos e esperados.
    O jogo renderiza o sprite salvo no mapa, mas usa as props (solid, acao…) do ID.
    Portanto TODAS as variantes do mesmo ID devem ter as mesmas props semânticas.

    CONFLITO REAL (find_semantic_conflicts): mesmo ID com solid/nome/acao
    DIFERENTES entre entradas — isso quebraria o comportamento do jogo.
    find_id_conflicts() do v5 foi REMOVIDO pois confundia variantes com erros.
    """

    def __init__(self):
        self._props = {}

    # ── CRUD básico ───────────────────────────────────────────────────────────
    def get(self, sn, col, lin):
        return self._props.get((sn, col, lin))

    def set(self, sn, col, lin, props):
        self._props[(sn, col, lin)] = props

    def remove(self, sn, col, lin):
        self._props.pop((sn, col, lin), None)

    def has(self, sn, col, lin):
        return (sn, col, lin) in self._props

    # ── Serialização ──────────────────────────────────────────────────────────
    def to_dict(self):
        return {json.dumps([k[0], k[1], k[2]]): v for k, v in self._props.items()}

    def from_dict(self, d):
        self._props.clear()
        for ks, v in d.items():
            k = json.loads(ks)
            self._props[(k[0], k[1], k[2])] = v

    # ── Helpers ───────────────────────────────────────────────────────────────
    def next_free_id(self):
        used = {v["id"] for v in self._props.values() if "id" in v}
        i = 0
        while i in used:
            i += 1
        return i

    def variants_of(self, tid):
        """Lista (sn, col, lin) de todos os visuais que compartilham tid."""
        return [(sn, c, l)
                for (sn, c, l), p in self._props.items()
                if p.get("id") == tid]

    def find_semantic_conflicts(self):
        """
        Retorna {tid: {campo: [valores_distintos]}} apenas quando o MESMO ID
        tem props semânticas divergentes (solid, acao…).
        'nome' é INTENCIONAL ser diferente por variante (cada estágio tem seu nome).
        'nomes' é lista compartilhada — também não é conflito.
        """
        by_id = {}
        for (sn, c, l), props in self._props.items():
            tid = props.get("id")
            if tid is None:
                continue
            by_id.setdefault(tid, []).append(props)

        result = {}
        for tid, all_p in by_id.items():
            if len(all_p) <= 1:
                continue
            for campo in ("solid", "acao", "mensagem", "destino",
                          "tipo_trocar", "spawn_x", "spawn_y"):
                vals = {str(p.get(campo, "")) for p in all_p}
                if len(vals) > 1:
                    result.setdefault(tid, {})[campo] = list(vals)
        return result

    def propagate_semantic(self, tid, source_props):
        """
        Copia solid/nome/acao/mensagem/destino/fundo para TODAS as variantes
        do tid — mantém consistência automática ao editar qualquer variante.
        Para 'nomes', faz MERGE da lista (não sobrescreve).
        """
        # "nome" NÃO é propagado — cada variante visual tem seu próprio nome
        # (ex: terra, terra_arada, broto…). A lista compartilhada é "nomes".
        campos = ("solid", "planta", "acao", "mensagem", "destino", "fundo",
                  "tipo_trocar", "spawn_x", "spawn_y", "loja_nomes", "loja_tipos")
        for vsn, vc, vl in self.variants_of(tid):
            vp = (self._props.get((vsn, vc, vl)) or {}).copy()
            for c in campos:
                if c in source_props:
                    vp[c] = source_props[c]
                else:
                    vp.pop(c, None)
            # 'nomes' é propagado por accumulate_nome_for_id — não sobrescreve aqui
            self._props[(vsn, vc, vl)] = vp

    def accumulate_nome_for_id(self, tid, novo_nome):
        """
        Sempre que um tile recebe um nome E já tem um ID, esse nome é
        adicionado à lista 'nomes' de TODAS as variantes do ID (sem duplicar).
        Garante que nomes=[lista_acumulada] fique sempre sincronizado.
        """
        if not novo_nome:
            return
        # Coleta nomes já existentes de qualquer variante
        nomes_set = []
        for vsn, vc, vl in self.variants_of(tid):
            vp = self._props.get((vsn, vc, vl)) or {}
            existentes = vp.get("nomes", [])
            if isinstance(existentes, list):
                for n in existentes:
                    if n not in nomes_set:
                        nomes_set.append(n)
        # Adiciona o novo nome se ainda não estiver
        if novo_nome not in nomes_set:
            nomes_set.append(novo_nome)
        # Propaga para todas as variantes
        for vsn, vc, vl in self.variants_of(tid):
            vp = (self._props.get((vsn, vc, vl)) or {}).copy()
            vp["nomes"] = nomes_set[:]
            self._props[(vsn, vc, vl)] = vp

    def build_visual_para_id(self):
        return {(sn, c, l): p["id"]
                for (sn, c, l), p in self._props.items()
                if "id" in p}

    def build_blocos_padrao(self):
        result = {}
        for (sn, col, lin), props in self._props.items():
            tid = props.get("id")
            if tid is None or tid in result:
                continue
            bloco = {
                "sprite": sn.encode("utf-8"),
                "col": col, "l": lin, "w": 16, "h": 16,
                "solid": props.get("solid", False),
            }
            for campo in ("fundo", "nome", "nomes", "planta", "acao", "mensagem", "destino",
                          "tipo_trocar", "spawn_x", "spawn_y"):
                v = props.get(campo)
                if v is not None and v != "" and v != []:
                    bloco[campo] = v
            result[tid] = bloco
        return result

    # ── tile_definitions.json ─────────────────────────────────────────────────
    def load_tile_definitions(self, path):
        warns = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return [f"Erro: {e}"]

        for tile in data.get("tiles", []):
            tid  = tile.get("id")
            sn   = tile.get("sprite", "")
            col  = tile.get("col", 0)
            lin  = tile.get("lin", 0)
            if tid is None or not sn:
                continue

            props = {"id": tid}
            for campo in ("nome", "solid", "planta", "fundo", "acao", "mensagem", "destino",
                          "tipo_trocar", "spawn_x", "spawn_y", "loja_nomes", "loja_tipos"):
                v = tile.get(campo)
                if v is not None and v not in ("", False):
                    props[campo] = v
            # Campo nomes: lista de nomes de estágios
            nomes_raw = tile.get("nomes")
            if nomes_raw:
                if isinstance(nomes_raw, list):
                    props["nomes"] = nomes_raw
                elif isinstance(nomes_raw, str) and nomes_raw.strip():
                    props["nomes"] = [n.strip() for n in nomes_raw.split(",") if n.strip()]

            self.set(sn, col, lin, props)
            for var in tile.get("variantes", []):
                vsn      = var.get("sprite", sn)
                vprops   = props.copy()
                # Restaura o nome individual da variante (se salvo)
                var_nome = var.get("nome", "")
                if var_nome:
                    vprops["nome"] = var_nome
                else:
                    vprops.pop("nome", None)
                self.set(vsn, var.get("col", 0), var.get("lin", 0), vprops)

        return warns

    def export_tile_definitions(self, path):
        by_id = {}
        for (sn, col, lin), props in self._props.items():
            tid = props.get("id")
            if tid is None:
                continue
            by_id.setdefault(tid, []).append((sn, col, lin, props))

        tiles = []
        for tid in sorted(by_id.keys()):
            entries = by_id[tid]
            sn, col, lin, props = entries[0]
            td = {
                "id":         tid,
                "nome":       props.get("nome", ""),
                "nomes":      props.get("nomes", []),
                "planta":     props.get("planta", False),
                "sprite":     sn,
                "col":        col,
                "lin":        lin,
                "solid":      props.get("solid", False),
                "fundo":      props.get("fundo", None),
                "acao":       props.get("acao", ""),
                "mensagem":   props.get("mensagem", ""),
                "destino":    props.get("destino", ""),
                "tipo_trocar":props.get("tipo_trocar", "porta"),
                "spawn_x":    props.get("spawn_x", None),
                "spawn_y":    props.get("spawn_y", None),
                "loja_nomes": props.get("loja_nomes", ""),
                "loja_tipos": props.get("loja_tipos", ""),
                "variantes":  [
                    {"sprite": vs, "col": vc, "lin": vl,
                     "nome": vprops.get("nome", "")}   # cada variante guarda seu próprio nome
                    for vs, vc, vl, vprops in entries[1:]
                ],
            }
            tiles.append(td)

        with open(path, "w", encoding="utf-8") as f:
            json.dump({"_versao": "1.0", "tiles": tiles}, f,
                      indent=2, ensure_ascii=False)


# ─── SheetManager ──────────────────────────────────────────────────────────────
class SheetManager:
    def __init__(self):
        self.paths  = []
        self.names  = []
        self.surfs  = []
        self._cache = {}

    def add(self, path):
        path = os.path.abspath(path)
        if path in self.paths:
            return self.paths.index(path)
        try:
            surf = pygame.image.load(path).convert_alpha()
        except Exception as e:
            print(f"[WARN] {path}: {e}")
            surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            surf.fill((80, 20, 80))
        idx = len(self.paths)
        self.paths.append(path)
        self.names.append(os.path.basename(path))
        self.surfs.append(surf)
        return idx

    def remove(self, idx):
        if not (0 <= idx < len(self.paths)):
            return
        self.paths.pop(idx)
        self.names.pop(idx)
        self.surfs.pop(idx)
        # Reindexar cache: entradas com s>idx ficam com s-1
        new_cache = {}
        for (s, c, l, px), surf in self._cache.items():
            if s == idx:
                continue
            ns = s if s < idx else s - 1
            new_cache[(ns, c, l, px)] = surf
        self._cache = new_cache

    def get_raw(self, s, c, l):
        surf = self.surfs[s]
        rect = pygame.Rect(c * TILE_SIZE, l * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        if rect.right > surf.get_width() or rect.bottom > surf.get_height():
            return make_checker()
        out = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        out.blit(surf, (0, 0), rect)
        return out

    def get_scaled(self, s, c, l, px):
        key = (s, c, l, px)
        if key not in self._cache:
            self._cache[key] = pygame.transform.scale(
                self.get_raw(s, c, l), (px, px))
        return self._cache[key]

    def clear_cache(self):
        self._cache.clear()

    def idx_of(self, name):
        try:
            return self.names.index(name)
        except ValueError:
            return -1

    def ncols(self, s): return self.surfs[s].get_width()  // TILE_SIZE
    def nrows(self, s): return self.surfs[s].get_height() // TILE_SIZE
    def count(self):    return len(self.paths)


# ─── AddTilesDialog ────────────────────────────────────────────────────────────
class AddTilesDialog:
    """
    Diálogo visual para importar sheets de uma pasta externa.
    Mostra todos os PNGs com preview e checkbox. Importa só os selecionados.
    """

    def __init__(self, screen, font_sm, font_xs, mgr):
        self.screen   = screen
        self.font_sm  = font_sm
        self.font_xs  = font_xs
        self.mgr      = mgr
        self.folder   = ""
        self.found    = []      # [(abs_path, basename, preview_surf)]
        self.checked  = set()   # índices selecionados
        self._scroll  = 0
        self._rects   = {}      # {i: rect do item}
        self._folder_r = None
        self._all_r    = None
        self._none_r   = None
        self._ok_r     = None
        self._ca_r     = None

    def _scan(self, folder):
        self.folder  = folder
        self.found   = []
        self.checked = set()
        if not os.path.isdir(folder):
            return
        for name in sorted(os.listdir(folder)):
            if not name.lower().endswith(".png"):
                continue
            path = os.path.join(folder, name)
            try:
                surf = pygame.image.load(path).convert_alpha()
                prev = pygame.Surface((24, 24), pygame.SRCALPHA)
                prev.blit(surf, (0, 0), (0, 0, min(24, surf.get_width()),
                                         min(24, surf.get_height())))
            except Exception:
                prev = make_checker(24)
            self.found.append((path, name, prev))
        # Pré-seleciona PNGs que ainda não estão carregados
        for i, (p, _, _) in enumerate(self.found):
            if os.path.abspath(p) not in self.mgr.paths:
                self.checked.add(i)

    def run(self):
        """Bloqueia até confirmar ou cancelar. Retorna lista de paths."""
        clock = pygame.time.Clock()
        # Abre seletor de pasta imediatamente
        root = tk.Tk(); root.withdraw()
        folder = filedialog.askdirectory(title="Selecionar pasta de tiles")
        root.destroy()
        if folder:
            self._scan(folder)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return []
                    if event.key == pygame.K_RETURN:
                        return self._confirm()

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mp = pygame.mouse.get_pos()
                    if self._folder_r and self._folder_r.collidepoint(mp):
                        root = tk.Tk(); root.withdraw()
                        f = filedialog.askdirectory(title="Selecionar pasta de tiles")
                        root.destroy()
                        if f: self._scan(f)
                    elif self._all_r and self._all_r.collidepoint(mp):
                        self.checked = set(range(len(self.found)))
                    elif self._none_r and self._none_r.collidepoint(mp):
                        self.checked.clear()
                    elif self._ok_r and self._ok_r.collidepoint(mp):
                        return self._confirm()
                    elif self._ca_r and self._ca_r.collidepoint(mp):
                        return []
                    else:
                        for i, r in self._rects.items():
                            if r.collidepoint(mp):
                                if i in self.checked:
                                    self.checked.discard(i)
                                else:
                                    self.checked.add(i)

                if event.type == pygame.MOUSEWHEEL:
                    max_s = max(0, len(self.found) * 34 - 300)
                    self._scroll = clamp(self._scroll - event.y * 24, 0, max_s)

            self._draw()
            clock.tick(60)

    def _confirm(self):
        return [self.found[i][0] for i in sorted(self.checked)]

    def _draw(self):
        w, h = self.screen.get_size()
        ov   = pygame.Surface((w, h), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        self.screen.blit(ov, (0, 0))

        DW, DH = 520, 540
        dx = (w - DW) // 2
        dy = (h - DH) // 2

        pygame.draw.rect(self.screen, HDR_BG, (dx, dy, DW, DH), border_radius=10)
        pygame.draw.rect(self.screen, ACCENT,  (dx, dy, DW, DH), 2, border_radius=10)
        txt(self.screen, "ADICIONAR TILES DE PASTA",
            dx + DW // 2, dy + 10, self.font_sm, ACCENT, "center")

        # ── Botão selecionar pasta ─────────────────────────────────────────────
        fr = pygame.Rect(dx + 10, dy + 36, DW - 20, 26)
        self._folder_r = fr
        rrect(self.screen, BTN_BG, fr, rad=4, bw=1, bc=ACCENT)
        label = (self.folder[-55:] if len(self.folder) > 55 else self.folder) \
                or "[ Clique aqui para escolher uma pasta ]"
        txt(self.screen, label, fr.x + 8, fr.y + 6, self.font_xs, ACCENT2)

        # ── Botões Todos / Nenhum ──────────────────────────────────────────────
        self._all_r  = pygame.Rect(dx + 10,      dy + 68, 90, 20)
        self._none_r = pygame.Rect(dx + 108,     dy + 68, 90, 20)
        rrect(self.screen, BTN_BG, self._all_r,  rad=3); txt(self.screen, "Todos",  self._all_r.centerx,  dy + 72, self.font_xs, TEXT, "center")
        rrect(self.screen, BTN_BG, self._none_r, rad=3); txt(self.screen, "Nenhum", self._none_r.centerx, dy + 72, self.font_xs, TEXT, "center")
        info = f"{len(self.found)} PNGs  ·  {len(self.checked)} selecionados"
        txt(self.screen, info, dx + DW - 10, dy + 72, self.font_xs, DIM, "right")

        # ── Lista de PNGs ─────────────────────────────────────────────────────
        list_r = pygame.Rect(dx + 6, dy + 94, DW - 12, DH - 160)
        pygame.draw.rect(self.screen, (12, 13, 22), list_r)
        pygame.draw.rect(self.screen, PANEL_SEP, list_r, 1)
        self.screen.set_clip(list_r)
        self._rects.clear()

        for i, (path, name, prev) in enumerate(self.found):
            iy  = list_r.y + i * 34 - self._scroll
            if iy + 34 < list_r.y or iy > list_r.bottom:
                continue
            sel     = i in self.checked
            already = os.path.abspath(path) in self.mgr.paths
            ir      = pygame.Rect(list_r.x + 2, iy + 1, list_r.w - 4, 32)
            self._rects[i] = ir
            rrect(self.screen, (30, 55, 30) if sel else (20, 20, 35), ir, rad=3)
            if sel:
                pygame.draw.rect(self.screen, BTN_ON, ir, 1, border_radius=3)

            # Checkbox
            cb = pygame.Rect(ir.x + 4, iy + 8, 16, 16)
            rrect(self.screen, BTN_ON if sel else BTN_BG, cb, rad=2)
            if sel:
                txt(self.screen, "v", cb.x + 3, cb.y + 2, self.font_xs, BTN_ON_T)

            # Preview tile (0,0)
            self.screen.blit(prev, (ir.x + 26, iy + 4))

            # Nome + indicador
            label = name + ("  [já carregada]" if already else "")
            txt(self.screen, label, ir.x + 58, iy + 10, self.font_xs,
                DIM if already else TEXT)

        self.screen.set_clip(None)

        # Scrollbar
        total_h = len(self.found) * 34
        if total_h > list_r.h:
            ratio = list_r.h / total_h
            bh = max(16, int(list_r.h * ratio))
            by = list_r.y + int(self._scroll / total_h * list_r.h)
            pygame.draw.rect(self.screen, ACCENT,
                             (list_r.right - 4, by, 4, bh), border_radius=2)

        # ── Botões OK / Cancelar ──────────────────────────────────────────────
        self._ok_r = pygame.Rect(dx + 10,       dy + DH - 52, 230, 36)
        self._ca_r = pygame.Rect(dx + DW - 240, dy + DH - 52, 230, 36)
        rrect(self.screen, BTN_ON,  self._ok_r, rad=6)
        txt(self.screen, f"Importar  ({len(self.checked)} sheets)",
            self._ok_r.centerx, self._ok_r.y + 11, self.font_xs, BTN_ON_T, "center")
        rrect(self.screen, BTN_BG, self._ca_r, rad=6, bw=1, bc=WARN)
        txt(self.screen, "Cancelar",
            self._ca_r.centerx, self._ca_r.y + 11, self.font_xs, WARN, "center")

        pygame.display.flip()



# ─── PropsPanel ────────────────────────────────────────────────────────────────
class PropsPanel:
    def __init__(self, registry, mgr):
        self.registry       = registry
        self.mgr            = mgr
        self._editor        = None
        self._editing_field = None
        self._input_buf     = ""
        self._sn            = ""
        self._col           = 0
        self._lin           = 0
        self._rect          = pygame.Rect(0, 0, 1, 1)
        self._rects         = {}
        self._btn_auto_id   = None
        self._btn_solid     = None
        self._btn_planta    = None
        self._btn_fundo_x   = None
        self._btn_acao_prev = None
        self._btn_acao_next = None
        self._btn_remove    = None
        self._btn_tipo_trocar = None
        self._btn_json_browse = None
        self._var_btns      = []
        self._nomes_remove_btns = []


    def set_editor(self, e):
        self._editor = e

    def set_tile(self, sn, col, lin):
        self._sn  = sn
        self._col = col
        self._lin = lin
        self._editing_field = None
        self._input_buf     = ""

    def _props(self):
        return self.registry.get(self._sn, self._col, self._lin)

    def _start_edit(self, field, cur):
        self._editing_field = field
        self._input_buf     = str(cur) if cur is not None else ""
        pygame.key.start_text_input()

    def _commit_input(self):
        field = self._editing_field
        buf   = self._input_buf.strip()
        self._editing_field = None
        self._input_buf     = ""
        pygame.key.stop_text_input()

        props = self._props()
        has   = props is not None
        p     = props.copy() if has else {}

        if field == "id":
            if not buf: return
            try:    p["id"] = int(buf)
            except: return
        elif field == "fundo_id":
            if not has: return
            if not buf: p.pop("fundo", None)
            else:
                try:    p["fundo"] = int(buf)
                except: return
        elif field in ("spawn_x", "spawn_y"):
            if not buf: p.pop(field, None)
            else:
                try:    p[field] = int(buf)
                except: return
        else:
            if buf: p[field] = buf
            else:   p.pop(field, None)

        # Campo especial: nomes como lista
        if field == "nomes" and field in p:
            raw = p["nomes"]
            if isinstance(raw, str):
                lista = [n.strip() for n in raw.split(",") if n.strip()]
                if lista:
                    p["nomes"] = lista
                else:
                    p.pop("nomes", None)

        # Campos de loja: normaliza espaços entre vírgulas
        if field in ("loja_nomes", "loja_tipos") and field in p:
            raw = p[field]
            if isinstance(raw, str):
                limpo = ",".join(v.strip() for v in raw.split(",") if v.strip())
                if limpo:
                    p[field] = limpo
                else:
                    p.pop(field, None)

        self.registry.set(self._sn, self._col, self._lin, p)
        # Propaga props semânticas para todas as variantes do mesmo ID
        tid = p.get("id")
        if tid is not None and field != "id":
            self.registry.propagate_semantic(tid, p)
        # Quando o nome muda, acumula automaticamente na lista 'nomes' do ID
        if field == "nome" and tid is not None and buf:
            self.registry.accumulate_nome_for_id(tid, buf)
        # Quando o ID é definido e o tile já tem nome, também acumula
        if field == "id" and tid is not None:
            nome_atual = p.get("nome", "")
            if nome_atual:
                self.registry.accumulate_nome_for_id(tid, nome_atual)

    def _ciclar_acao(self, props, has, delta):
        p     = props.copy() if has else {"id": self.registry.next_free_id()}
        atual = p.get("acao") or ""
        idx   = ACOES_DISPONIVEIS.index(atual) if atual in ACOES_DISPONIVEIS else 0
        novo  = ACOES_DISPONIVEIS[(idx + delta) % len(ACOES_DISPONIVEIS)]
        if novo: p["acao"] = novo
        else:    p.pop("acao", None)
        # Limpa campos exclusivos de trocar_mapa ao sair dela
        if novo != "trocar_mapa":
            for f in ("destino", "tipo_trocar", "spawn_x", "spawn_y"):
                p.pop(f, None)
        # Limpa campos exclusivos de loja ao sair dela
        if novo != "loja":
            for f in ("loja_nomes", "loja_tipos"):
                p.pop(f, None)
        self.registry.set(self._sn, self._col, self._lin, p)
        tid = p.get("id")
        if tid is not None:
            self.registry.propagate_semantic(tid, p)

    def _ciclar_tipo_trocar(self, props, has):
        p     = props.copy() if has else {"id": self.registry.next_free_id()}
        atual = p.get("tipo_trocar", "porta")
        novo  = "passagem" if atual == "porta" else "porta"
        p["tipo_trocar"] = novo
        self.registry.set(self._sn, self._col, self._lin, p)
        tid = p.get("id")
        if tid is not None:
            self.registry.propagate_semantic(tid, p)

    def draw(self, surf, rect, font, font_sm, font_xs):
        self._rect = rect
        self._rects.clear()
        self._var_btns.clear()
        self._nomes_remove_btns = []
        x, y, w, h = rect.x, rect.y, rect.w, rect.h
        LW = 76

        pygame.draw.line(surf, PANEL_SEP, (x, y), (x + w, y), 1)
        pygame.draw.rect(surf, (13, 15, 26), rect)
        txt(surf, "─── PROPRIEDADES DO TILE ───",
            x + w // 2, y + 6, font_sm, ACCENT, "center")

        props = self._props()
        has   = props is not None
        ry    = y + 26

        # ── ID + auto ─────────────────────────────────────────────────────────
        txt(surf, "Tile ID:", x + 8, ry + 3, font_xs, DIM)
        id_val = str(props["id"]) if has and props.get("id") is not None else "—"
        ir     = pygame.Rect(x + LW, ry, 52, 20)
        self._rects["id"] = ir
        ed     = self._editing_field == "id"
        rrect(surf, (25,28,45) if ed else BTN_BG, ir, rad=3,
              bw=1, bc=ACCENT if ed else PANEL_SEP)
        txt(surf, (self._input_buf + "|") if ed else id_val,
            ir.x + 4, ir.y + 4, font_xs, SEL_C if ed else TEXT)
        ab = pygame.Rect(ir.right + 4, ry, 38, 20)
        self._btn_auto_id = ab
        rrect(surf, BTN_BG, ab, rad=3)
        txt(surf, "auto", ab.centerx, ab.y + 4, font_xs, DIM, "center")
        ry += 26

        # ── Nome ──────────────────────────────────────────────────────────────
        txt(surf, "Nome:", x + 8, ry + 3, font_xs, DIM)
        nome_v = props.get("nome", "") if has else ""
        ir     = pygame.Rect(x + LW, ry, w - LW - 12, 20)
        self._rects["nome"] = ir
        ed     = self._editing_field == "nome"
        rrect(surf, (25,28,45) if ed else BTN_BG, ir, rad=3,
              bw=1, bc=ACCENT2 if ed else (ACCENT2 if nome_v else PANEL_SEP))
        txt(surf, (self._input_buf + "|") if ed else (nome_v or "—"),
            ir.x + 4, ir.y + 4, font_xs,
            SEL_C if ed else (ACCENT2 if nome_v else DIM))
        ry += 26

        # ── Nomes acumulados (somente leitura — preenchido automaticamente pelo Nome) ──
        nomes_raw = props.get("nomes", []) if has else []
        if isinstance(nomes_raw, str):
            nomes_raw = [n.strip() for n in nomes_raw.split(",") if n.strip()]
        nomes_v = ", ".join(nomes_raw) if nomes_raw else ""
        txt(surf, "Nomes:", x + 8, ry + 3, font_xs, DIM)
        # Fundo do campo
        nr_bg = pygame.Rect(x + LW, ry, w - LW - 12, 20)
        rrect(surf, (14, 16, 28), nr_bg, rad=3,
              bw=1, bc=VAR_C if nomes_raw else PANEL_SEP)
        if nomes_raw:
            # Mostra cada nome como "tag" com [x] para remover
            tx2 = nr_bg.x + 4
            self._nomes_remove_btns = []
            for ni, nm in enumerate(nomes_raw):
                tag_w = min(len(nm) * 7 + 20, nr_bg.w - 8)
                tag_r = pygame.Rect(tx2, ry + 2, tag_w, 16)
                if tag_r.right > nr_bg.right - 4:
                    break
                rrect(surf, (50, 30, 80), tag_r, rad=3)
                txt(surf, nm, tag_r.x + 3, tag_r.y + 3, font_xs, VAR_C)
                # Botão "x" no canto direito da tag
                xbtn = pygame.Rect(tag_r.right - 14, ry + 3, 12, 14)
                rrect(surf, (80, 30, 50), xbtn, rad=2)
                txt(surf, "x", xbtn.centerx, xbtn.y + 2, font_xs, WARN, "center")
                self._nomes_remove_btns.append((xbtn, ni))
                tx2 = tag_r.right + 4
        else:
            txt(surf, "— (defina Nome + ID para acumular)", nr_bg.x + 4, ry + 4,
                font_xs, (50, 50, 80))
        ry += 26

        # ── Sólido ────────────────────────────────────────────────────────────
        txt(surf, "Sólido:", x + 8, ry + 3, font_xs, DIM)
        is_solid = has and props.get("solid", False)
        sb       = pygame.Rect(x + LW, ry, 64, 20)
        self._btn_solid = sb
        rrect(surf, BTN_ON if is_solid else BTN_BG, sb, rad=3)
        txt(surf, "SIM" if is_solid else "NÃO",
            sb.centerx, sb.y + 4, font_xs,
            BTN_ON_T if is_solid else DIM, "center")
        ry += 26


        # ── Planta ────────────────────────────────────────────────────────────
        txt(surf, "Planta:", x + 8, ry + 3, font_xs, DIM)
        is_planta = has and props.get("planta", False)
        pb        = pygame.Rect(x + LW, ry, 64, 20)
        self._btn_planta = pb
        COR_PLANTA = (40, 160, 80)
        rrect(surf, COR_PLANTA if is_planta else BTN_BG, pb, rad=3)
        txt(surf, "SIM" if is_planta else "NÃO",
            pb.centerx, pb.y + 4, font_xs,
            BTN_ON_T if is_planta else DIM, "center")
        if is_planta:
            # Dica: fundo automático gerenciado pelo jogo
            txt(surf, "← fundo auto (terra)", pb.right + 6, ry + 4,
                font_xs, (40, 160, 80))
        ry += 26

        # ── Fundo ID (escondido quando é planta — o fundo é automático) ──────
        if not is_planta:
            txt(surf, "Fundo ID:", x + 8, ry + 3, font_xs, DIM)
            fundo_v = props.get("fundo") if has else None
            ir      = pygame.Rect(x + LW, ry, 48, 20)
            self._rects["fundo_id"] = ir
            ed      = self._editing_field == "fundo_id"
            rrect(surf, (25,28,45) if ed else BTN_BG, ir, rad=3,
                  bw=1, bc=ACCENT if ed else PANEL_SEP)
            txt(surf, (self._input_buf + "|") if ed
                else (str(fundo_v) if fundo_v is not None else "—"),
                ir.x + 4, ir.y + 4, font_xs, SEL_C if ed else TEXT)
            xb = pygame.Rect(ir.right + 4, ry, 22, 20)
            self._btn_fundo_x = xb
            rrect(surf, BTN_BG, xb, rad=3)
            txt(surf, "X", xb.centerx, xb.y + 4, font_xs, WARN, "center")
            ry += 26
        else:
            self._btn_fundo_x = None
            # Limpa fundo manual se virou planta
            if has and "fundo" in props:
                p2 = props.copy()
                p2.pop("fundo", None)
                self.registry.set(self._sn, self._col, self._lin, p2)

        # ── Ação ──────────────────────────────────────────────────────────────
        txt(surf, "Ação:", x + 8, ry + 3, font_xs, DIM)
        acao_v   = props.get("acao") if has else None
        acao_idx = ACOES_DISPONIVEIS.index(acao_v) if acao_v in ACOES_DISPONIVEIS else 0
        prev_r   = pygame.Rect(x + LW, ry, 20, 20)
        lbl_r    = pygame.Rect(x + LW + 22, ry, w - LW - 22 - 24 - 12, 20)
        next_r   = pygame.Rect(lbl_r.right + 2, ry, 20, 20)
        self._btn_acao_prev = prev_r
        self._btn_acao_next = next_r
        rrect(surf, BTN_BG, prev_r, rad=3)
        txt(surf, "<", prev_r.centerx, prev_r.y + 4, font_xs, TEXT, "center")
        rrect(surf, BTN_BG, next_r, rad=3)
        txt(surf, ">", next_r.centerx, next_r.y + 4, font_xs, TEXT, "center")
        rrect(surf, (20,22,38), lbl_r, rad=3,
              bw=1, bc=ACCENT2 if acao_v else PANEL_SEP)
        txt(surf, ACOES_LABELS[acao_idx],
            lbl_r.centerx, lbl_r.y + 4, font_xs,
            ACCENT2 if acao_v else DIM, "center")
        ry += 26

        # ── Mensagem ──────────────────────────────────────────────────────────
        txt(surf, "Msg:", x + 8, ry + 3, font_xs, DIM)
        msg_v = props.get("mensagem", "") if has else ""
        ir    = pygame.Rect(x + LW, ry, w - LW - 12, 20)
        self._rects["mensagem"] = ir
        ed    = self._editing_field == "mensagem"
        rrect(surf, (25,28,45) if ed else BTN_BG, ir, rad=3,
              bw=1, bc=ACCENT if ed else PANEL_SEP)
        disp = (self._input_buf + "|") if ed else (
            msg_v[:17] + "…" if len(msg_v) > 17 else (msg_v or "—"))
        txt(surf, disp, ir.x + 4, ir.y + 4, font_xs,
            SEL_C if ed else (TEXT if msg_v else DIM))
        ry += 26

        # ── Destino, Tipo, Spawn e JSON (só para trocar_mapa) ────────────────────
        if acao_v == "trocar_mapa":
            # -- Destino --
            txt(surf, "Destino:", x + 8, ry + 3, font_xs, DIM)
            dest_v = props.get("destino", "") if has else ""
            ir     = pygame.Rect(x + LW, ry, w - LW - 12, 20)
            self._rects["destino"] = ir
            ed     = self._editing_field == "destino"
            rrect(surf, (25,28,45) if ed else BTN_BG, ir, rad=3,
                  bw=1, bc=ACCENT if ed else (WARN if not dest_v else PANEL_SEP))
            txt(surf, (self._input_buf + "|") if ed
                else (dest_v or "← obrigatório!"),
                ir.x + 4, ir.y + 4, font_xs,
                SEL_C if ed else (TEXT if dest_v else WARN))
            ry += 26

            # -- Tipo de troca --
            tipo_v = (props.get("tipo_trocar", "porta") if has else "porta")
            txt(surf, "Tipo:", x + 8, ry + 3, font_xs, DIM)
            tipo_r = pygame.Rect(x + LW, ry, w - LW - 12, 20)
            self._btn_tipo_trocar = tipo_r
            cor_tipo = (60, 180, 80) if tipo_v == "passagem" else (72, 100, 200)
            rrect(surf, cor_tipo, tipo_r, rad=3)
            txt(surf, f"[{tipo_v.upper()}]  (clique p/ alternar)",
                tipo_r.centerx, tipo_r.y + 4, font_xs, (230, 230, 230), "center")
            ry += 26

            # -- Spawn X --
            txt(surf, "Spawn X:", x + 8, ry + 3, font_xs, DIM)
            sx_v = props.get("spawn_x") if has else None
            sx_r = pygame.Rect(x + LW, ry, 48, 20)
            self._rects["spawn_x"] = sx_r
            ed2  = self._editing_field == "spawn_x"
            rrect(surf, (25,28,45) if ed2 else BTN_BG, sx_r, rad=3,
                  bw=1, bc=ACCENT if ed2 else PANEL_SEP)
            txt(surf, (self._input_buf + "|") if ed2
                else (str(sx_v) if sx_v is not None else "—"),
                sx_r.x + 4, sx_r.y + 4, font_xs, SEL_C if ed2 else TEXT)

            # -- Spawn Y --
            txt(surf, "Spawn Y:", x + 8 + 80, ry + 3, font_xs, DIM)
            sy_v = props.get("spawn_y") if has else None
            sy_r = pygame.Rect(x + LW + 100, ry, 48, 20)
            self._rects["spawn_y"] = sy_r
            ed3  = self._editing_field == "spawn_y"
            rrect(surf, (25,28,45) if ed3 else BTN_BG, sy_r, rad=3,
                  bw=1, bc=ACCENT if ed3 else PANEL_SEP)
            txt(surf, (self._input_buf + "|") if ed3
                else (str(sy_v) if sy_v is not None else "—"),
                sy_r.x + 4, sy_r.y + 4, font_xs, SEL_C if ed3 else TEXT)
            ry += 26

            # -- Botao: escolher destino via JSON --
            json_btn = pygame.Rect(x + 8, ry, w - 16, 20)
            self._btn_json_browse = json_btn
            rrect(surf, BTN_BG, json_btn, rad=3, bw=1, bc=ACCENT2)
            txt(surf, "Escolher destino via JSON...",
                json_btn.centerx, json_btn.y + 4, font_xs, ACCENT2, "center")
            ry += 26

        # ── Loja: filtros de itens vendidos ───────────────────────────────────
        if acao_v == "loja":
            # -- Nomes (prefixos) --
            txt(surf, "Nomes:", x + 8, ry + 3, font_xs, DIM)
            nomes_v = props.get("loja_nomes", "") if has else ""
            ir      = pygame.Rect(x + LW, ry, w - LW - 12, 20)
            self._rects["loja_nomes"] = ir
            ed      = self._editing_field == "loja_nomes"
            rrect(surf, (25, 28, 45) if ed else BTN_BG, ir, rad=3,
                  bw=1, bc=ACCENT if ed else PANEL_SEP)
            disp = (self._input_buf + "|") if ed else (
                nomes_v[:17] + "…" if len(nomes_v) > 17 else (nomes_v or "—"))
            txt(surf, disp, ir.x + 4, ir.y + 4, font_xs,
                SEL_C if ed else (TEXT if nomes_v else DIM))
            ry += 26

            # -- Tipos --
            txt(surf, "Tipos:", x + 8, ry + 3, font_xs, DIM)
            tipos_v = props.get("loja_tipos", "") if has else ""
            ir2     = pygame.Rect(x + LW, ry, w - LW - 12, 20)
            self._rects["loja_tipos"] = ir2
            ed2     = self._editing_field == "loja_tipos"
            rrect(surf, (25, 28, 45) if ed2 else BTN_BG, ir2, rad=3,
                  bw=1, bc=ACCENT if ed2 else PANEL_SEP)
            disp2 = (self._input_buf + "|") if ed2 else (
                tipos_v[:17] + "…" if len(tipos_v) > 17 else (tipos_v or "—"))
            txt(surf, disp2, ir2.x + 4, ir2.y + 4, font_xs,
                SEL_C if ed2 else (TEXT if tipos_v else DIM))
            ry += 26

            # Dicas
            txt(surf, "Ex: Semente,Fertilizante",
                x + 8, ry + 2, font_xs, DIM)
            ry += 14
            txt(surf, "Ex: Cultivo,Outro",
                x + 8, ry + 2, font_xs, DIM)
            ry += 18

        # ── Água: Mar / Lago / Manguezal ──────────────────────────────────────
        # Exibido quando a ação selecionada é um dos tipos de água de pesca.
        # Mostra um resumo informativo dos peixes do ambiente — somente leitura.
        _TIPOS_AGUA = {"tile_mar", "tile_lago", "tile_mangi"}
        _NOMES_AGUA = {"tile_mar": "Mar", "tile_lago": "Lago", "tile_mangi": "Manguezal"}
        _PEIXES_AGUA_RESUMO = {
            "tile_mar": [
                ("Lixo",     "Bota Velha, Lixo, Alga"),
                ("Comum",    "Sardinha, Peixe Sol, Lambari"),
                ("Incomum",  "Tilapia, Bagre (noite), Truta (chuva)"),
                ("Raro",     "Dourado (amanhecer), Pirarucu, Salmao Real"),
                ("Lendario", "Carpa Noturna (22h-4h)"),
            ],
            "tile_lago": [
                ("Lixo",     "Bota Velha, Lixo, Alga"),
                ("Comum",    "Lambari, Peixe Sol (sol), Sardinha"),
                ("Incomum",  "Carpa, Bagre (noite), Tilapia"),
                ("Raro",     "Dourado (manha), Truta (chuva), Salmao"),
                ("Lendario", "Carpa Noturna (20h-4h)"),
            ],
            "tile_mangi": [
                ("Lixo",     "Alga, Bota Velha, Lixo"),
                ("Comum",    "Lambari, Sardinha (sol), Bagre"),
                ("Incomum",  "Tilapia, Truta (chuva), Carpa"),
                ("Raro",     "Pirarucu (manha), Dourado (tarde)"),
                ("Lendario", "Carpa Noturna (21h-5h) / Pirarucu"),
            ],
        }

        if acao_v in _TIPOS_AGUA or (nome_v in _TIPOS_AGUA if has else False):
            chave_agua = acao_v if acao_v in _TIPOS_AGUA else nome_v
            nome_agua  = _NOMES_AGUA.get(chave_agua, chave_agua)

            # Cabeçalho do painel de pesca
            cab_r = pygame.Rect(x + 8, ry, w - 16, 18)
            rrect(surf, (15, 35, 75), cab_r, rad=3, bw=1, bc=(60, 120, 200))
            txt(surf, f"PESCA: {nome_agua.upper()}",
                cab_r.centerx, cab_r.y + 4, font_xs, (100, 200, 255), "center")
            ry += 22

            # Dica de vara
            txt(surf, "Req: Vara de Pesca equipada",
                x + 12, ry + 2, font_xs, (160, 160, 80))
            ry += 16

            # Tabela de peixes por raridade
            _COR_RAR = {
                "Lixo":     (110, 110, 110),
                "Comum":    (190, 190, 190),
                "Incomum":  ( 80, 190,  80),
                "Raro":     ( 80, 130, 255),
                "Lendario": (230, 170,  40),
            }
            for rar_label, peixes_str in _PEIXES_AGUA_RESUMO.get(chave_agua, []):
                cor_rar = _COR_RAR.get(rar_label, DIM)
                txt(surf, f"{rar_label}:", x + 12, ry + 2, font_xs, cor_rar)
                txt_ml(surf, peixes_str, x + 68, ry + 2, font_xs,
                       color=(160, 160, 160), max_w=w - 80, line_h=13)
                ry += 14

            ry += 4   # espaço extra após a tabela

        # ── Variantes do mesmo ID ─────────────────────────────────────────────
        if has and props.get("id") is not None:
            tid      = props["id"]
            variants = self.registry.variants_of(tid)
            if len(variants) > 1:
                txt(surf, f"Variantes ({len(variants)}):",
                    x + 8, ry + 3, font_xs, VAR_C)
                vx = x + LW
                for vsn, vc, vl in variants[:8]:
                    is_cur = (vsn == self._sn and vc == self._col and vl == self._lin)
                    vidx   = self.mgr.idx_of(vsn)
                    vbtn   = pygame.Rect(vx, ry, 26, 26)
                    self._var_btns.append((vbtn, vsn, vc, vl))
                    rrect(surf, (30,18,55) if is_cur else BTN_BG, vbtn,
                          rad=3, bw=2, bc=SEL_C if is_cur else VAR_C)
                    if vidx >= 0:
                        try:
                            surf.blit(self.mgr.get_scaled(vidx, vc, vl, 22),
                                      (vbtn.x + 2, vbtn.y + 2))
                        except Exception:
                            pass
                    vx += 28
                ry += 32

        # ── Remover ───────────────────────────────────────────────────────────
        rb = pygame.Rect(x + 8, ry, w - 16, 20)
        self._btn_remove = rb
        rrect(surf, (55,18,18) if has else BTN_BG, rb, rad=3)
        txt(surf, "Remover este visual" if has else "Tile não registrado",
            rb.centerx, rb.y + 4, font_xs, WARN if has else DIM, "center")
        ry += 26

        # ── Status / conflito ─────────────────────────────────────────────────
        if has:
            tid   = props.get("id")
            nome  = props.get("nome", "")
            confs = getattr(getattr(self, "_editor", None),
                            "_sem_conflicts", {})
            if tid in confs:
                txt(surf, f"! INCONSISTÊNCIA ID {tid}: {list(confs[tid].keys())}",
                    x + 8, ry + 3, font_xs, WARN)
            elif nome:
                nvars = len(self.registry.variants_of(tid))
                txt(surf, f'ID={tid}  "{nome}"  ·  {nvars} visual(is)',
                    x + 8, ry + 3, font_xs, ACCENT2)
            else:
                nvars = len(self.registry.variants_of(tid))
                txt(surf, f"ID={tid}  (sem nome)  ·  {nvars} visual(is)",
                    x + 8, ry + 3, font_xs, DIM)
        else:
            txt(surf, "Clique em ID ou Nome para registrar.",
                x + 8, ry + 3, font_xs, DIM)

    def handle_event(self, event, mpos):
        in_p  = self._rect.collidepoint(mpos)
        props = self._props()
        has   = props is not None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # ── Variantes ─────────────────────────────────────────────────────
            for vbtn, vsn, vc, vl in self._var_btns:
                if vbtn.collidepoint(mpos):
                    # Troca o visual selecionado no painel e no viewer
                    self.set_tile(vsn, vc, vl)
                    if self._editor:
                        self._editor.panel._jump_to_sheet(vsn, vc, vl)
                    return True

            if not in_p:
                if self._editing_field:
                    self._commit_input()
                return False

            # ── Campos de texto ───────────────────────────────────────────────
            for key, ir in self._rects.items():
                if ir.collidepoint(mpos):
                    if key == "nomes":
                        return True   # somente leitura — ignora clique
                    if not has and key not in ("id", "nome"):
                        return True
                    cur = (props.get("id")     if key == "id"      and has else
                           props.get("fundo")  if key == "fundo_id" and has else
                           props.get(key, "")  if has else "")
                    self._start_edit(key, cur)
                    return True

            # ── Botões [x] para remover nome individual da lista nomes ────────
            for xbtn, ni in self._nomes_remove_btns:
                if xbtn.collidepoint(mpos):
                    if has:
                        p        = props.copy()
                        nomes_l  = list(p.get("nomes", []))
                        if isinstance(nomes_l, list) and 0 <= ni < len(nomes_l):
                            nomes_l.pop(ni)
                        p["nomes"] = nomes_l if nomes_l else []
                        self.registry.set(self._sn, self._col, self._lin, p)
                        tid = p.get("id")
                        if tid is not None:
                            self.registry.propagate_semantic(tid, p)
                    return True

            # ── Botão auto ID ─────────────────────────────────────────────────
            if self._btn_auto_id and self._btn_auto_id.collidepoint(mpos):
                nid = self.registry.next_free_id()
                p   = props.copy() if has else {}
                p["id"] = nid
                self.registry.set(self._sn, self._col, self._lin, p)
                # Se já tem nome, acumula na lista
                nome_atual = p.get("nome", "")
                if nome_atual:
                    self.registry.accumulate_nome_for_id(nid, nome_atual)
                return True

            # ── Botão sólido (propaga para variantes) ─────────────────────────
            if self._btn_solid and self._btn_solid.collidepoint(mpos):
                p     = props.copy() if has else {"id": self.registry.next_free_id()}
                novo_solid = not p.get("solid", False)
                p["solid"] = novo_solid
                self.registry.set(self._sn, self._col, self._lin, p)
                tid = p.get("id")
                if tid is not None:
                    self.registry.propagate_semantic(tid, p)
                return True

            # ── Botão planta (propaga para variantes) ─────────────────────────
            if self._btn_planta and self._btn_planta.collidepoint(mpos):
                p     = props.copy() if has else {"id": self.registry.next_free_id()}
                p["planta"] = not p.get("planta", False)
                # Quando vira planta, remove fundo manual (será automático)
                if p["planta"]:
                    p.pop("fundo", None)
                self.registry.set(self._sn, self._col, self._lin, p)
                tid = p.get("id")
                if tid is not None:
                    self.registry.propagate_semantic(tid, p)
                return True

            # ── Botão X de fundo ──────────────────────────────────────────────
            if self._btn_fundo_x and self._btn_fundo_x.collidepoint(mpos):
                if has and "fundo" in props:
                    p = props.copy()
                    p.pop("fundo")
                    self.registry.set(self._sn, self._col, self._lin, p)
                return True

            # ── Ação < > ──────────────────────────────────────────────────────
            if self._btn_acao_prev and self._btn_acao_prev.collidepoint(mpos):
                self._ciclar_acao(props, has, -1); return True
            if self._btn_acao_next and self._btn_acao_next.collidepoint(mpos):
                self._ciclar_acao(props, has, +1); return True

            # ── Tipo de troca (porta / passagem) ──────────────────────────────
            if self._btn_tipo_trocar and self._btn_tipo_trocar.collidepoint(mpos):
                self._ciclar_tipo_trocar(props, has); return True

            # ── Botao escolher destino via JSON ──────────────────────────────
            if self._btn_json_browse and self._btn_json_browse.collidepoint(mpos):
                root = tk.Tk(); root.withdraw()
                path = filedialog.askopenfilename(
                    title="Selecionar JSON do mapa destino",
                    filetypes=[("JSON","*.json"),("Todos","*.*")])
                root.destroy()
                if path:
                    try:
                        with open(path, "r", encoding="utf-8") as _f:
                            _data = json.load(_f)
                        nome_mapa = _data.get("nome", "")
                        if nome_mapa:
                            p2 = props.copy() if has else {"id": self.registry.next_free_id()}
                            p2["destino"] = nome_mapa
                            self.registry.set(self._sn, self._col, self._lin, p2)
                            tid = p2.get("id")
                            if tid is not None:
                                self.registry.propagate_semantic(tid, p2)
                        else:
                            # Mostra aviso se o JSON nao tiver campo nome
                            print(f"[WARN] JSON sem campo 'nome': {path}")
                    except Exception as e:
                        print(f"[WARN] Nao foi possivel ler o JSON: {e}")
                return True

            # ── Remover ───────────────────────────────────────────────────────
            if self._btn_remove and self._btn_remove.collidepoint(mpos):
                if has:
                    self.registry.remove(self._sn, self._col, self._lin)
                return True

            if in_p and self._editing_field:
                self._commit_input()
                return True



        if event.type == pygame.TEXTINPUT and self._editing_field:
            self._input_buf += event.text
            return True

        if event.type == pygame.KEYDOWN and self._editing_field:
            if event.key == pygame.K_RETURN:
                self._commit_input(); return True
            if event.key == pygame.K_ESCAPE:
                self._editing_field = None
                self._input_buf = ""
                pygame.key.stop_text_input(); return True
            if event.key == pygame.K_BACKSPACE:
                self._input_buf = self._input_buf[:-1]; return True

        return False


# ─── TilePalette ───────────────────────────────────────────────────────────────
class TilePalette:
    """
    Lista todos os tiles por ID. Cada linha mostra o tile principal + mini-
    previews das variantes (clicáveis individualmente para selecionar o visual).
    """

    def __init__(self, registry, mgr):
        self.registry = registry
        self.mgr      = mgr
        self._scroll  = 0
        self._rect    = pygame.Rect(0, 0, 1, 1)
        self._sel_key = None       # (sn, col, lin) do visual selecionado
        self._filter  = ""
        self._editing_filter = False
        self._filter_rect    = None
        self._item_data      = {}  # {i: (main_rect, [(var_rect, sn,c,l)])}
        self._del_btns       = {}  # {i: (del_rect, tid)} botões de deletar por ID
        self._btn_clear_all  = None
        self._confirm_clear  = False  # estado de confirmação p/ limpar tudo

    def _build_entries(self):
        by_id = {}
        for (sn, c, l), props in self.registry._props.items():
            tid = props.get("id")
            if tid is None: continue
            if tid not in by_id:
                # Usa a lista 'nomes' acumulada para exibição; fallback p/ 'nome'
                nomes_l = props.get("nomes", [])
                if isinstance(nomes_l, list) and nomes_l:
                    display = ", ".join(nomes_l)
                else:
                    display = props.get("nome", "")
                by_id[tid] = {"display": display, "variants": []}
            by_id[tid]["variants"].append((sn, c, l))
            # Atualiza display se esta variante tiver lista nomes mais completa
            nomes_l = props.get("nomes", [])
            if isinstance(nomes_l, list) and len(nomes_l) > len(
                    by_id[tid]["display"].split(",")):
                by_id[tid]["display"] = ", ".join(nomes_l)

        entries = []
        for tid in sorted(by_id.keys()):
            display  = by_id[tid]["display"]
            variants = by_id[tid]["variants"]
            if self._filter:
                f = self._filter.lower()
                # Filtra por qualquer nome da lista ou pelo ID
                if f not in display.lower() and f not in str(tid):
                    continue
            entries.append((tid, display, variants))
        return entries

    def selected_cell(self):
        if self._sel_key is None: return None
        sn, col, lin = self._sel_key
        idx = self.mgr.idx_of(sn)
        if idx < 0: return None
        return make_cell(idx, col, lin)

    def delete_tile_by_id(self, tid):
        """Remove todas as entradas do registry que tenham este ID."""
        keys_to_remove = [(sn, c, l)
                          for (sn, c, l), p in list(self.registry._props.items())
                          if p.get("id") == tid]
        for key in keys_to_remove:
            self.registry._props.pop(key, None)
        if self._sel_key and self._sel_key in {k for k in keys_to_remove}:
            self._sel_key = None

    def draw(self, surf, rect, font_sm, font_xs, active_layer):
        self._rect = rect
        x, y, w, h = rect.x, rect.y, rect.w, rect.h
        lc = LAYER_COLORS[active_layer]

        pygame.draw.rect(surf, PANEL_BG, rect)
        pygame.draw.line(surf, PANEL_SEP, (x, y), (x + w, y), 1)
        txt(surf, "PALETA DE TILES", x + w // 2, y + 5, font_sm, lc, "center")

        # Botão limpar tudo
        ca_r = pygame.Rect(x + w - 84, y + 3, 80, 18)
        self._btn_clear_all = ca_r
        if self._confirm_clear:
            rrect(surf, WARN, ca_r, rad=3)
            txt(surf, "CONFIRMAR?", ca_r.centerx, ca_r.y + 3, font_xs, (10,10,20), "center")
        else:
            rrect(surf, (60,20,20), ca_r, rad=3, bw=1, bc=WARN)
            txt(surf, "Limpar tudo", ca_r.centerx, ca_r.y + 3, font_xs, WARN, "center")

        # Filtro
        fy = y + 26
        fr = pygame.Rect(x + 6, fy, w - 12, 20)
        self._filter_rect = fr
        ed = self._editing_filter
        rrect(surf, (20,22,38) if ed else BTN_BG, fr, rad=3,
              bw=1, bc=ACCENT if ed else PANEL_SEP)
        disp = (self._filter + "|") if ed else (self._filter or "Filtrar por nome/id…")
        txt(surf, disp, fr.x + 6, fr.y + 4, font_xs, TEXT if self._filter else DIM)

        list_y = fy + 26
        list_h = h - (list_y - y) - 18
        list_r = pygame.Rect(x, list_y, w, list_h)
        surf.set_clip(list_r)

        entries    = self._build_entries()
        PX         = PALETTE_ITEM_H - 4
        checker    = make_checker(PX // 2)
        total_h    = len(entries) * PALETTE_ITEM_H
        max_scroll = max(0, total_h - list_h)
        self._scroll = clamp(self._scroll, 0, max_scroll)
        self._item_data.clear()
        self._del_btns.clear()

        DEL_W = 18  # largura do botão de deletar
        for i, (tid, nome, variants) in enumerate(entries):
            iy = list_y + i * PALETTE_ITEM_H - self._scroll
            if iy + PALETTE_ITEM_H < list_y or iy > list_y + list_h:
                continue

            is_sel  = (self._sel_key in {(sn,c,l) for sn,c,l in variants}
                       if self._sel_key else False)
            item_r  = pygame.Rect(x + 2, iy + 1, w - 4 - DEL_W - 2, PALETTE_ITEM_H - 2)
            rrect(surf, (35,55,35) if is_sel else BTN_BG, item_r, rad=3)
            if is_sel:
                pygame.draw.rect(surf, lc, item_r, 1, border_radius=3)

            # Botão deletar (lixeira) à direita de cada linha
            del_r = pygame.Rect(x + w - DEL_W - 4, iy + 3, DEL_W, PALETTE_ITEM_H - 6)
            self._del_btns[i] = (del_r, tid)
            rrect(surf, (70, 20, 20), del_r, rad=3, bw=1, bc=(160, 40, 40))
            txt(surf, "X", del_r.centerx, del_r.y + 3, font_xs, WARN, "center")

            # Preview do primeiro visual
            sn0, c0, l0 = variants[0]
            sidx = self.mgr.idx_of(sn0)
            if sidx >= 0:
                try:
                    bg_s = pygame.Surface((PX, PX))
                    bg_s.blit(checker, (0,0));     bg_s.blit(checker, (PX//2,0))
                    bg_s.blit(checker, (0,PX//2)); bg_s.blit(checker, (PX//2,PX//2))
                    surf.blit(bg_s, (x + 4, iy + 2))
                    surf.blit(self.mgr.get_scaled(sidx, c0, l0, PX), (x + 4, iy + 2))
                except Exception:
                    pass

            # Mini-previews das variantes (clicáveis)
            VPX = 14
            vx  = x + 4 + PX + 3
            var_rects = []
            for vi, (vsn, vc, vl) in enumerate(variants):
                vidx = self.mgr.idx_of(vsn)
                if vidx < 0: continue
                vr = pygame.Rect(vx, iy + 2, VPX + 2, PX)
                is_var_sel = self._sel_key == (vsn, vc, vl)
                if is_var_sel:
                    pygame.draw.rect(surf, VAR_C, vr, 1, border_radius=2)
                try:
                    surf.blit(self.mgr.get_scaled(vidx, vc, vl, VPX),
                              (vx + 1, iy + (PX - VPX) // 2 + 2))
                except Exception:
                    pass
                var_rects.append((vr, vsn, vc, vl))
                vx += VPX + 3
                if vx > x + w - 80: break

            self._item_data[i] = (item_r, var_rects)

            # Texto
            tx = x + 4 + PX + 4
            nome_disp = nome if nome else f"(tile {tid})"
            nvars = len(variants)
            txt(surf, f"#{tid}  {nome_disp}",
                tx, iy + 3, font_xs, SEL_C if is_sel else TEXT)
            p0    = self.registry.get(sn0, c0, l0)
            tags  = []
            if p0:
                if p0.get("solid"):  tags.append("sólido")
                if p0.get("acao"):   tags.append(p0["acao"])
                if p0.get("fundo") is not None: tags.append(f"f={p0['fundo']}")
                nomes_p = p0.get("nomes")
                if nomes_p:
                    nomes_str = ",".join(nomes_p) if isinstance(nomes_p, list) else str(nomes_p)
                    tags.append(f"[{nomes_str[:20]}]")
            tag_str = "  ".join(tags) if tags else ""
            var_str = f"  ({nvars}v)" if nvars > 1 else ""
            txt(surf, tag_str + var_str, tx, iy + 15, font_xs, DIM)

        surf.set_clip(None)

        if total_h > list_h and total_h > 0:
            ratio = list_h / total_h
            bh    = max(16, int(list_h * ratio))
            by    = list_y + int(self._scroll / total_h * list_h)
            pygame.draw.rect(surf, ACCENT, (x+w-4, by, 4, bh), border_radius=2)

        txt(surf, f"{len(entries)} tiles  ·  {len(self.registry._props)} entradas",
            x + w // 2, list_y + list_h + 2, font_xs, DIM, "center")

    def handle_event(self, event, mpos):
        if (not self._rect.collidepoint(mpos)
                and event.type not in (pygame.KEYDOWN, pygame.TEXTINPUT)):
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Botão "Limpar tudo"
            if self._btn_clear_all and self._btn_clear_all.collidepoint(mpos):
                if self._confirm_clear:
                    # Confirma: apaga tudo do registry
                    self.registry._props.clear()
                    self._sel_key = None
                    self._confirm_clear = False
                else:
                    self._confirm_clear = True
                return True
            else:
                # Qualquer clique fora do botão "Limpar tudo" cancela confirmação
                self._confirm_clear = False

            if self._filter_rect and self._filter_rect.collidepoint(mpos):
                self._editing_filter = True
                pygame.key.start_text_input()
                return True

            # Botões de deletar por tile
            for i, (del_r, tid) in self._del_btns.items():
                if del_r.collidepoint(mpos):
                    self.delete_tile_by_id(tid)
                    return True

            for i, (main_r, var_rects) in self._item_data.items():
                # Clique em variante específica
                for vr, vsn, vc, vl in var_rects:
                    if vr.collidepoint(mpos):
                        self._sel_key = (vsn, vc, vl)
                        return True
                # Clique na linha → primeiro visual
                if main_r.collidepoint(mpos):
                    entries = self._build_entries()
                    if 0 <= i < len(entries):
                        _, _, variants = entries[i]
                        if variants:
                            self._sel_key = variants[0]
                    return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            # Clique direito cancela confirmação de limpar tudo
            self._confirm_clear = False

        if event.type == pygame.MOUSEWHEEL and self._rect.collidepoint(mpos):
            entries  = self._build_entries()
            list_h   = self._rect.h - 52
            total_h  = len(entries) * PALETTE_ITEM_H
            self._scroll = clamp(
                self._scroll - event.y * 24, 0, max(0, total_h - list_h))
            return True

        if self._editing_filter:
            if event.type == pygame.TEXTINPUT:
                self._filter += event.text; return True
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self._editing_filter = False
                    pygame.key.stop_text_input(); return True
                if event.key == pygame.K_BACKSPACE:
                    self._filter = self._filter[:-1]; return True

        return False


# ─── ItemsPanel ────────────────────────────────────────────────────────────────
class ItemsPanel:
    """
    Aba dedicada a criar e editar itens do jogo.
    Cada item é um dict com todos os campos da classe Item de itens.py.
    Pode importar/exportar para itens_custom.json que o jogo carrega.

    Layout da aba:
        ┌──────────────────────────────┐
        │  [+ Novo]  [Importar] [Exp.] │  ← toolbar
        ├──────────────────────────────┤
        │  Lista de itens com scroll   │
        │  (nome, tipo, preços)        │
        ├──────────────────────────────┤
        │  Editor inline do item sel.  │
        │  (todos os campos + preview) │
        └──────────────────────────────┘
    """

    CAMPOS = [
        # sprite/col/lin são gerenciados pelo mini viewer
        ("Nome",          "nome",          "str",    None),
        ("Tipo",          "tipo",          "choice", ITEM_TIPOS),
        ("Descricao",     "descrica",      "str",    None),
        ("Slot equipado", "slot_equipado", "choice", ITEM_SLOTS),
        ("Tipo presente", "tipo_presente", "choice", ITEM_PRESENTE),
        ("Estrelas",      "estrelas",      "int",    None),
        ("Preco venda",   "preco",         "int",    None),
        ("Preco compra",  "compra",        "int",    None),
        ("Compravel",     "compravel",     "bool",   None),
        ("Vendivel",      "vendivel",      "bool",   None),
        ("Recupera HP",   "recupar_hp",    "int",    None),
        ("Recupera MP",   "recupar_mn",    "int",    None),
        ("Bonus HP max",  "bonus_hp",      "int",    None),
        ("Bonus MP max",  "bonus_mn",      "int",    None),
        ("tile_colocar",  "tile_colocar",  "int",    None),
    ]

    DEFAULTS = {
        "nome": "novo_item", "tipo": "Consumivel", "descrica": "",
        "slot_equipado": "", "tipo_presente": "", "estrelas": 0,
        "preco": 0, "compra": 0, "compravel": True, "vendivel": True,
        "recupar_hp": 0, "recupar_mn": 0, "bonus_hp": 0, "bonus_mn": 0,
        "tile_colocar": None,
        "sprite": "items.png", "col": 0, "lin": 0,
        "start_x": 0, "start_y": 0, "w": 16, "h": 16,
    }

    # Separadores visuais por grupo
    SEPARADORES = {"preco", "recupar_hp"}

    def __init__(self, mgr):
        self.mgr      = mgr
        self.itens    = []     # lista de dicts
        self._sel     = -1     # índice selecionado
        self._rect    = pygame.Rect(0, 0, 1, 1)

        # Scroll da lista
        self._list_scroll = 0
        self._list_h      = 120

        # Scroll do editor
        self._edit_scroll = 0

        # Campo em edição
        self._active  = None
        self._buf     = ""

        # Rects dos widgets (rebuilt cada frame)
        self._item_rects  = {}   # {i: rect} da lista
        self._field_rects = {}   # {chave: rect} do editor
        self._btn_new  = None
        self._btn_del  = None
        self._btn_dup  = None
        self._btn_imp  = None
        self._btn_exp  = None
        self._btn_up   = None
        self._btn_dn   = None

        # Mini sprite viewer
        self._spr_sheet  = -1
        self._spr_col    = 0
        self._spr_lin    = 0
        self._spr_scroll = 0
        self._spr_sc     = 2
        self._spr_rect   = pygame.Rect(0,0,1,1)
        self._spr_cache  = {}
        self._sheet_btns = {}

    # ── dados ──────────────────────────────────────────────────────────────────
    def _item(self):
        if 0 <= self._sel < len(self.itens):
            return self.itens[self._sel]
        return None

    def _new_item(self):
        d = dict(self.DEFAULTS)
        d["nome"] = f"item_{len(self.itens)+1}"
        self.itens.append(d)
        self._sel = len(self.itens) - 1
        self._active = None

    def _delete_item(self):
        if 0 <= self._sel < len(self.itens):
            self.itens.pop(self._sel)
            self._sel = max(0, self._sel - 1) if self.itens else -1
            self._active = None

    def _dup_item(self):
        it = self._item()
        if it:
            import copy as _copy
            d = _copy.deepcopy(it)
            d["nome"] = it["nome"] + "_copia"
            self.itens.insert(self._sel + 1, d)
            self._sel += 1

    def _move(self, delta):
        n = len(self.itens)
        if n < 2: return
        j = self._sel + delta
        if 0 <= j < n:
            self.itens[self._sel], self.itens[j] = self.itens[j], self.itens[self._sel]
            self._sel = j

    # ── import / export ────────────────────────────────────────────────────────
    def exportar(self, path):
        import json as _json
        dados = {"itens": self.itens}
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(dados, f, indent=2, ensure_ascii=False)

    def importar(self, path):
        import json as _json
        with open(path, "r", encoding="utf-8") as f:
            dados = _json.load(f)
        self.itens = dados.get("itens", [])
        self._sel  = 0 if self.itens else -1
        self._active = None

    def to_dict(self):
        return {"itens": self.itens}

    def from_dict(self, d):
        self.itens = d.get("itens", [])
        self._sel  = 0 if self.itens else -1

    # ── commit campo ──────────────────────────────────────────────────────────
    def _commit(self):
        if not self._active: return
        it = self._item()
        if not it: return
        campo = next((c for c in self.CAMPOS if c[1] == self._active), None)
        if not campo: return
        val = self._buf.strip()
        if campo[2] == "int":
            try:    it[self._active] = int(val)
            except: pass
        else:
            it[self._active] = val
        self._active = None
        self._buf    = ""

    # ── handle event ──────────────────────────────────────────────────────────
    def handle_event(self, event, mpos):
        in_panel = self._rect.collidepoint(mpos)

        # Scroll
        if event.type == pygame.MOUSEWHEEL:
            if in_panel:
                # Decide se scrolla lista ou editor
                list_r = self._list_rect()
                edit_r = self._edit_rect()
                if list_r.collidepoint(mpos):
                    max_s = max(0, len(self.itens) * 26 - list_r.h)
                    self._list_scroll = clamp(
                        self._list_scroll - event.y * 20, 0, max_s)
                elif edit_r.collidepoint(mpos):
                    max_s = max(0, len(self.CAMPOS) * 26 - edit_r.h)
                    self._edit_scroll = clamp(
                        self._edit_scroll - event.y * 20, 0, max_s)
                return True

        # Teclado
        if event.type == pygame.KEYDOWN:
            if self._active:
                if event.key == pygame.K_RETURN:
                    self._commit(); return True
                if event.key == pygame.K_ESCAPE:
                    self._active = None; self._buf = ""; return True
                if event.key == pygame.K_BACKSPACE:
                    self._buf = self._buf[:-1]; return True
                if event.key == pygame.K_TAB:
                    self._commit()
                    editaveis = [c[1] for c in self.CAMPOS if c[2] in ("str","int")]
                    idx = editaveis.index(self._active) if self._active in editaveis else -1
                    self._active = editaveis[(idx+1) % len(editaveis)]
                    it = self._item()
                    self._buf = str(it.get(self._active, "")) if it else ""
                    return True

        if event.type == pygame.TEXTINPUT and self._active:
            campo = next((c for c in self.CAMPOS if c[1] == self._active), None)
            if campo and campo[2] == "int":
                if event.text.lstrip("-").isdigit() or event.text == "-":
                    self._buf += event.text
            else:
                self._buf += event.text
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not in_panel:
                self._commit(); return False

            self._commit()

            # Toolbar buttons
            if self._btn_new  and self._btn_new.collidepoint(mpos):
                self._new_item(); return True
            if self._btn_del  and self._btn_del.collidepoint(mpos):
                self._delete_item(); return True
            if self._btn_dup  and self._btn_dup.collidepoint(mpos):
                self._dup_item(); return True
            if self._btn_up   and self._btn_up.collidepoint(mpos):
                self._move(-1); return True
            if self._btn_dn   and self._btn_dn.collidepoint(mpos):
                self._move(+1); return True
            if self._btn_imp  and self._btn_imp.collidepoint(mpos):
                import tkinter as _tk
                from tkinter import filedialog as _fd
                root = _tk.Tk(); root.withdraw()
                path = _fd.askopenfilename(
                    title="Importar itens_custom.json",
                    filetypes=[("JSON","*.json"),("Todos","*.*")])
                root.destroy()
                if path:
                    try:    self.importar(path)
                    except Exception as e: print(f"[WARN] importar itens: {e}")
                return True
            if self._btn_exp  and self._btn_exp.collidepoint(mpos):
                import tkinter as _tk
                from tkinter import filedialog as _fd
                root = _tk.Tk(); root.withdraw()
                path = _fd.asksaveasfilename(
                    title="Exportar itens_custom.json",
                    defaultextension=".json",
                    filetypes=[("JSON","*.json")],
                    initialfile="itens_custom.json")
                root.destroy()
                if path:
                    try:    self.exportar(path)
                    except Exception as e: print(f"[WARN] exportar itens: {e}")
                return True

            # Clique na lista
            for i, r in self._item_rects.items():
                if r.collidepoint(mpos):
                    self._sel = i
                    self._edit_scroll = 0
                    return True

            # Clique nos campos do editor
            it = self._item()
            if it:
                for chave, fr in self._field_rects.items():
                    if fr.collidepoint(mpos):
                        campo = next((c for c in self.CAMPOS if c[1] == chave), None)
                        if not campo: continue
                        if campo[2] == "bool":
                            it[chave] = not it.get(chave, False)
                        elif campo[2] == "choice":
                            opts = campo[3]
                            cur  = it.get(chave, opts[0])
                            idx  = opts.index(cur) if cur in opts else 0
                            it[chave] = opts[(idx+1) % len(opts)]
                        else:
                            self._active = chave
                            self._buf    = str(it.get(chave, ""))
                            pygame.key.start_text_input()
                        return True

        # ── Sprite viewer ─────────────────────────────────────────────────
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._spr_rect.w > 1 and self._spr_rect.collidepoint(mpos):
                if self._spr_sheet >= 0:
                    ts  = TILE_SIZE * self._spr_sc
                    col = (mpos[0] - self._spr_rect.x) // ts
                    lin = (mpos[1] - self._spr_rect.y + self._spr_scroll) // ts
                    nc  = self.mgr.ncols(self._spr_sheet)
                    nr  = self.mgr.nrows(self._spr_sheet)
                    if 0 <= col < nc and 0 <= lin < nr:
                        self._spr_col = col; self._spr_lin = lin
                        it = self._item()
                        if it:
                            it["sprite"] = self.mgr.names[self._spr_sheet]
                            it["col"] = col; it["lin"] = lin
                return True
            for si, sr in self._sheet_btns.items():
                if sr.collidepoint(mpos):
                    self._spr_sheet = si; self._spr_scroll = 0
                    self._spr_cache = {}
                    it = self._item()
                    if it: it["sprite"] = self.mgr.names[si]
                    return True

        if event.type == pygame.MOUSEWHEEL:
            if self._spr_rect.w > 1 and self._spr_rect.collidepoint(mpos):
                if self._spr_sheet >= 0:
                    sh = self.mgr.surfs[self._spr_sheet].get_height() * self._spr_sc
                    self._spr_scroll = clamp(
                        self._spr_scroll - event.y * TILE_SIZE,
                        0, max(0, sh - self._spr_rect.h))
                return True

        return False

    # ── geometry helpers ───────────────────────────────────────────────────────
    def _toolbar_r(self):
        return pygame.Rect(self._rect.x, self._rect.y, self._rect.w, 28)

    def _list_rect(self):
        tb = self._toolbar_r()
        return pygame.Rect(self._rect.x, tb.bottom + 2,
                           self._rect.w, self._list_h)

    def _splitter_r(self):
        lr = self._list_rect()
        return pygame.Rect(self._rect.x, lr.bottom + 2, self._rect.w, 4)

    def _edit_rect(self):
        sp = self._splitter_r()
        return pygame.Rect(self._rect.x, sp.bottom,
                           self._rect.w,
                           self._rect.bottom - sp.bottom)

    def _preview_r(self, edit_r):
        PX = 48
        return pygame.Rect(edit_r.right - PX - 6, edit_r.y + 4, PX, PX)

    # ── draw ──────────────────────────────────────────────────────────────────
    def draw(self, surf, rect, font_sm, font_xs):
        self._rect = rect
        x, y, w, h = rect.x, rect.y, rect.w, rect.h

        pygame.draw.rect(surf, PANEL_BG, rect)
        pygame.draw.line(surf, PANEL_SEP, (x, y), (x+w, y), 1)
        txt(surf, "ITENS DO JOGO", x + w//2, y + 5, font_sm, ACCENT, "center")

        # ── Toolbar ───────────────────────────────────────────────────────────
        tb = self._toolbar_r()
        tb.y += 20; tb.h = 24
        bx = x + 4
        def tbtn(label, w_=40, color=BTN_BG, tc=TEXT):
            nonlocal bx
            r = pygame.Rect(bx, tb.y, w_, 22)
            rrect(surf, color, r, rad=3)
            txt(surf, label, r.centerx, r.y+5, font_xs, tc, "center")
            bx += w_ + 3
            return r
        self._btn_new = tbtn("+ Novo", 52, (30,90,50), (180,255,190))
        self._btn_dup = tbtn("Dup",    38)
        self._btn_del = tbtn("Del",    36, (80,20,20), (220,80,80))
        self._btn_up  = tbtn("▲",      24)
        self._btn_dn  = tbtn("▼",      24)
        bx += 6
        self._btn_imp = tbtn("Import", 46, BTN_BG, ACCENT2)
        self._btn_exp = tbtn("Export", 46, BTN_BG, ACCENT2)

        # ── Lista de itens ────────────────────────────────────────────────────
        lr   = self._list_rect()
        lr.y = tb.bottom + 4
        self._list_h = min(max(80, h // 3), 200)
        lr.h = self._list_h
        pygame.draw.rect(surf, (12,13,22), lr)
        pygame.draw.rect(surf, PANEL_SEP, lr, 1)
        surf.set_clip(lr)
        self._item_rects.clear()

        ITEM_H = 24
        for i, it in enumerate(self.itens):
            iy = lr.y + i * ITEM_H - self._list_scroll
            if iy + ITEM_H < lr.y or iy > lr.bottom: continue
            is_sel = i == self._sel
            ir = pygame.Rect(lr.x+2, iy+1, lr.w-4, ITEM_H-2)
            self._item_rects[i] = ir
            rrect(surf, (40,80,50) if is_sel else (20,22,36), ir, rad=3)
            if is_sel:
                pygame.draw.rect(surf, ACCENT, ir, 1, border_radius=3)
            # Preview mini sprite
            spr = it.get("sprite","")
            sidx = self.mgr.idx_of(spr) if spr else -1
            if sidx >= 0:
                try:
                    mini = self.mgr.get_scaled(sidx, it.get("col",0), it.get("lin",0), 18)
                    surf.blit(mini, (ir.x+3, iy+3))
                except Exception: pass
            # Texto
            nome_i  = it.get("nome","?")
            tipo_i  = it.get("tipo","")
            preco_i = it.get("preco", 0)
            comp_i  = it.get("compra", 0)
            txt(surf, f"{nome_i}", ir.x+24, iy+4, font_xs,
                SEL_C if is_sel else TEXT)
            txt(surf, f"[{tipo_i}]  {preco_i}G/{comp_i}G",
                ir.x+24, iy+13, font_xs, DIM)

        surf.set_clip(None)
        # Scrollbar lista
        total_list = len(self.itens) * ITEM_H
        if total_list > lr.h and total_list > 0:
            ratio = lr.h / total_list
            bh    = max(12, int(lr.h * ratio))
            by    = lr.y + int(self._list_scroll / total_list * lr.h)
            pygame.draw.rect(surf, ACCENT, (lr.right-3, by, 3, bh), border_radius=2)

        # Contagem
        txt(surf, f"{len(self.itens)} item(s)",
            lr.right - 4, lr.bottom + 2, font_xs, DIM, "right")

        # ── Splitter ──────────────────────────────────────────────────────────
        sp = self._splitter_r()
        sp.y = lr.bottom + 2
        pygame.draw.rect(surf, PANEL_SEP, sp)

        # ── Editor inline ─────────────────────────────────────────────────────
        er = self._edit_rect()
        er.y = sp.bottom
        er.h = rect.bottom - er.y
        pygame.draw.rect(surf, (13,15,26), er)

        it = self._item()
        if not it:
            txt(surf, "Crie ou selecione um item acima.",
                er.centerx, er.y + er.h//2 - 6, font_xs, DIM, "center")
            return

        # ── Cabeçalho ────────────────────────────────────────────────────────
        nome_ed = it.get("nome","") or "—"
        txt(surf, f"  {nome_ed}", er.x+4, er.y+4, font_sm, ACCENT2)
        pygame.draw.line(surf, PANEL_SEP, (er.x+4, er.y+20), (er.right-4, er.y+20), 1)

        # Layout: esquerda=campos  direita=sprite viewer
        SPR_W   = er.w // 2
        FIELD_W = er.w - SPR_W - 4

        # ── Campos (esquerda) ─────────────────────────────────────────────────
        fields_r = pygame.Rect(er.x+4, er.y+24, FIELD_W-4, er.h-30)
        surf.set_clip(fields_r)
        self._field_rects.clear()
        LW = 82; FW = fields_r.w - LW - 6
        cy = fields_r.y - self._edit_scroll

        for campo in self.CAMPOS:
            lbl, chave, tipo, extras = campo
            if cy + 24 < fields_r.y or cy > fields_r.bottom:
                cy += 24; continue
            if chave in self.SEPARADORES:
                sep_y = cy - 3
                if fields_r.y <= sep_y <= fields_r.bottom:
                    pygame.draw.line(surf, (35,42,70),
                                     (fields_r.x, sep_y), (fields_r.right, sep_y), 1)
            val     = it.get(chave)
            editing = self._active == chave
            fr      = pygame.Rect(fields_r.x+LW, cy, FW, 20)
            self._field_rects[chave] = fr
            txt(surf, lbl+":", fields_r.x+LW-4, cy+3, font_xs, DIM, "right")
            if tipo == "bool":
                on = bool(val)
                rrect(surf, BTN_ON if on else BTN_BG, fr, rad=3)
                txt(surf, "SIM" if on else "NAO",
                    fr.centerx, fr.y+4, font_xs, BTN_ON_T if on else DIM, "center")
            elif tipo == "choice":
                rrect(surf, (38,50,78), fr, rad=3, bw=1, bc=ACCENT2)
                disp = str(val) if val not in (None,"") else "—"
                txt(surf, disp+" ▶", fr.x+5, fr.y+4, font_xs, ACCENT2)
            else:
                rrect(surf, (25,28,45) if editing else BTN_BG, fr, rad=3,
                      bw=1, bc=ACCENT if editing else PANEL_SEP)
                disp = (self._buf+"|") if editing else (
                    str(val) if val not in (None,"") else "—")
                col  = SEL_C if editing else (TEXT if val not in (None,"",0) else DIM)
                while font_xs.size(disp)[0] > FW-8 and len(disp) > 3:
                    disp = disp[:-1]
                txt(surf, disp, fr.x+5, fr.y+4, font_xs, col)
            cy += 24

        surf.set_clip(None)
        total_ed = len(self.CAMPOS) * 24
        if total_ed > fields_r.h:
            ratio = fields_r.h / total_ed
            bh    = max(10, int(fields_r.h * ratio))
            by    = fields_r.y + int(self._edit_scroll / total_ed * fields_r.h)
            pygame.draw.rect(surf, ACCENT2, (fields_r.right+1, by, 3, bh), border_radius=2)

        # ── Sprite viewer (direita) ───────────────────────────────────────────
        sv_x = er.x + FIELD_W + 2
        sv_y = er.y + 24
        sv_w = SPR_W - 4
        sv_h = er.h - 28

        # Sincroniza com item
        cur_spr  = it.get("sprite","")
        cur_sidx = self.mgr.idx_of(cur_spr) if cur_spr else -1
        if cur_sidx >= 0 and self._spr_sheet != cur_sidx:
            self._spr_sheet = cur_sidx
            self._spr_col   = it.get("col", 0)
            self._spr_lin   = it.get("lin", 0)

        # Botões de sheet
        SHEET_BTN_H = 18
        self._sheet_btns.clear()
        sbx = sv_x
        for si in range(self.mgr.count()):
            sname  = self.mgr.names[si]
            is_act = si == self._spr_sheet
            sw     = min(font_xs.size(sname)[0] + 10, sv_w)
            sbr    = pygame.Rect(sbx, sv_y, sw, SHEET_BTN_H)
            rrect(surf, ACCENT if is_act else BTN_BG, sbr, rad=3)
            sn_d = sname
            while font_xs.size(sn_d)[0] > sw-6 and len(sn_d) > 3:
                sn_d = sn_d[:-1]
            txt(surf, sn_d, sbr.x+3, sbr.y+3, font_xs, BTN_ON_T if is_act else DIM)
            self._sheet_btns[si] = sbr
            sbx += sw + 2
            if sbx >= sv_x + sv_w: break

        # Viewer
        vr = pygame.Rect(sv_x, sv_y + SHEET_BTN_H + 2,
                         sv_w, sv_h - SHEET_BTN_H - 16)
        self._spr_rect = vr
        pygame.draw.rect(surf, (10,11,20), vr)
        pygame.draw.rect(surf, PANEL_SEP, vr, 1)

        if self._spr_sheet >= 0:
            ts  = TILE_SIZE * self._spr_sc
            key = (self._spr_sheet, self._spr_sc)
            if key not in self._spr_cache:
                raw_s = self.mgr.surfs[self._spr_sheet]
                self._spr_cache[key] = pygame.transform.scale(
                    raw_s, (raw_s.get_width()*self._spr_sc,
                            raw_s.get_height()*self._spr_sc))
            surf.set_clip(vr)
            surf.blit(self._spr_cache[key], (vr.x, vr.y - self._spr_scroll))
            nc = self.mgr.ncols(self._spr_sheet)
            nr = self.mgr.nrows(self._spr_sheet)
            for c in range(nc):
                for r in range(nr):
                    cx2 = vr.x + c*ts
                    cy2 = vr.y + r*ts - self._spr_scroll
                    if cy2+ts < vr.y or cy2 > vr.bottom: continue
                    pygame.draw.rect(surf, (30,34,55), (cx2, cy2, ts, ts), 1)
            sc_ = it.get("col", self._spr_col)
            sl_ = it.get("lin", self._spr_lin)
            pygame.draw.rect(surf, SEL_C,
                             (vr.x+sc_*ts, vr.y+sl_*ts-self._spr_scroll, ts, ts), 2)
            surf.set_clip(None)
            sh_h = self.mgr.surfs[self._spr_sheet].get_height() * self._spr_sc
            if sh_h > vr.h:
                ratio = vr.h / sh_h
                bh    = max(10, int(vr.h * ratio))
                by    = vr.y + int(self._spr_scroll / sh_h * vr.h)
                pygame.draw.rect(surf, ACCENT, (vr.right-3, by, 3, bh), border_radius=2)
            txt(surf, f"col={sc_}  lin={sl_}", sv_x, vr.bottom+2, font_xs, DIM)
        else:
            surf.set_clip(None)
            txt(surf, "Nenhuma sheet", vr.centerx, vr.centery, font_xs, DIM, "center")

        txt(surf, "Tab=próx  Enter=ok  Choice/Bool=clique",
            er.x+4, er.bottom-13, font_xs, (45,55,80))



# ─── ItemSpritesPanel ──────────────────────────────────────────────────────────
class ItemSpritesPanel:
    """
    Aba "Sprites Itens" — permite escolher o sprite (col, lin, sheet) de cada
    item importado de todos_itens em itens.py.

    Funciona igual ao NPCPanel mas sem animações:
      - Importar de itens.py    → preenche a lista com todos os itens
      - Selecionar item na lista → ativa o viewer da sheet
      - Clicar no viewer         → define col+lin do item
      - Setas < >                → troca a sheet do item
      - Salvo como "item_sprites" no JSON do mapa

    O jogo lê esse bloco via aplicar_sprites_item() em itens.py para
    sobrescrever item.sprite / item.col / item.lin em tempo de execução.
    """

    LIST_W    = 120
    SC_MIN, SC_MAX, SC_DEF = 1, 8, 2

    def __init__(self, mgr):
        self.mgr          = mgr
        self._rect        = pygame.Rect(0, 0, 1, 1)
        self._item_names  = []       # nomes na ordem de exibição
        self._dados       = {}       # nome → {"sprite": str, "col": int, "lin": int}
        self._sel         = -1       # índice selecionado na lista
        # viewer state
        self._v_scroll    = 0
        self._h_scroll    = 0
        self._v_sc        = self.SC_DEF
        self._v_cache     = {}
        self._list_scroll = 0
        self._status      = ""
        # rects reconstruídos no draw()
        self._btn_import  = None
        self._btn_clear   = None
        self._item_rects  = {}
        self._sheet_btns  = {}
        self._viewer_rect = pygame.Rect(0, 0, 1, 1)
        self._cell_rects  = {}

    # ── dados ──────────────────────────────────────────────────────────────────
    def _blank(self):
        return {"sprite": "", "col": 0, "lin": 0}

    def _entry(self):
        if 0 <= self._sel < len(self._item_names):
            nome = self._item_names[self._sel]
            if nome not in self._dados:
                self._dados[nome] = self._blank()
            return nome, self._dados[nome]
        return None, None

    def to_dict(self):
        out = {}
        for n in self._item_names:
            if n not in self._dados:
                continue
            d = self._dados[n]
            out[n] = {"sprite": d.get("sprite", ""),
                      "col":    int(d.get("col", 0)),
                      "lin":    int(d.get("lin", 0))}
        return out

    def from_dict(self, d):
        self._dados = {}
        for nome, info in d.items():
            self._dados[nome] = {
                "sprite": info.get("sprite", ""),
                "col":    int(info.get("col", 0)),
                "lin":    int(info.get("lin", 0)),
            }
            if nome not in self._item_names:
                self._item_names.append(nome)
        if self._item_names and self._sel < 0:
            self._sel = 0

    # ── importar de itens.py ──────────────────────────────────────────────────
    def importar_de_itens(self):
        try:
            import importlib.util, os, sys
            editor_dir = os.path.dirname(os.path.abspath(__file__))
            game_dir   = os.path.dirname(editor_dir)
            itens_path = os.path.join(game_dir, "itens.py")
            _ins = game_dir not in sys.path
            if _ins:
                sys.path.insert(0, game_dir)
            try:
                spec = importlib.util.spec_from_file_location("itens_isp", itens_path)
                mod  = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                nomes = list(mod.todos_itens.keys())
                # Pré-preenche sprite/col/lin a partir do que já está no item
                for nome in nomes:
                    item = mod.todos_itens[nome]
                    if nome not in self._dados:
                        spr = item.sprite
                        if isinstance(spr, bytes):
                            spr = spr.decode("utf-8")
                        self._dados[nome] = {
                            "sprite": spr,
                            "col":    item.col,
                            "lin":    item.lin,
                        }
                    if nome not in self._item_names:
                        self._item_names.append(nome)
            finally:
                if _ins:
                    sys.path.remove(game_dir)
            novos = sum(1 for n in nomes if n in self._dados)
            if self._sel < 0 and self._item_names:
                self._sel = 0
            self._status = f"OK  {len(nomes)} item(s) importado(s)"
        except Exception as e:
            self._status = f"ERRO: {e}"
        return self._status

    # ── helpers viewer ────────────────────────────────────────────────────────
    def _sheet_surf(self, sidx):
        key = (sidx, self._v_sc)
        if key not in self._v_cache:
            raw = self.mgr.surfs[sidx]
            self._v_cache[key] = pygame.transform.scale(
                raw, (raw.get_width()  * self._v_sc,
                      raw.get_height() * self._v_sc))
        return self._v_cache[key]

    def _sheet_px_w(self, sidx): return self._sheet_surf(sidx).get_width()
    def _sheet_px_h(self, sidx): return self._sheet_surf(sidx).get_height()

    def _clamp_scroll(self, sidx, vr):
        self._v_scroll = clamp(self._v_scroll, 0,
                               max(0, self._sheet_px_h(sidx) - vr.h))
        self._h_scroll = clamp(self._h_scroll, 0,
                               max(0, self._sheet_px_w(sidx) - vr.w))

    # ── draw ──────────────────────────────────────────────────────────────────
    def draw(self, surf, rect, font_sm, font_xs):
        self._rect = rect
        x, y, w, h = rect.x, rect.y, rect.w, rect.h
        pygame.draw.rect(surf, PANEL_BG, rect)

        # ── Toolbar ────────────────────────────────────────────────────────────
        TBAR = 26
        pygame.draw.rect(surf, HDR_BG, pygame.Rect(x, y, w, TBAR))
        txt(surf, "SPRITES DE ITENS", x + 6, y + 6, font_sm, (80, 200, 255))
        self._btn_import = pygame.Rect(x + w - 148, y + 4, 144, 18)
        rrect(surf, (30, 60, 100), self._btn_import, rad=3)
        txt(surf, "Importar de itens.py",
            self._btn_import.centerx, self._btn_import.y + 3,
            font_xs, (160, 210, 255), "center")

        sy = y + TBAR + 2
        if self._status:
            ok = self._status.startswith("OK")
            txt(surf, self._status, x + 4, sy, font_xs,
                (100, 220, 120) if ok else (220, 80, 80))
        body_y = sy + 14
        body_h = h - (body_y - y)

        LW = self.LIST_W

        # ── Lista de itens ─────────────────────────────────────────────────────
        pygame.draw.rect(surf, (11, 13, 22),
                         pygame.Rect(x, body_y, LW, body_h))
        pygame.draw.line(surf, PANEL_SEP,
                         (x + LW, body_y), (x + LW, body_y + body_h), 1)
        txt(surf, "Itens", x + LW // 2, body_y + 2, font_xs, DIM, "center")
        pygame.draw.line(surf, PANEL_SEP,
                         (x, body_y + 14), (x + LW, body_y + 14), 1)

        self._btn_clear = pygame.Rect(x + 3, body_y + body_h - 22, LW - 6, 18)
        has_sel = 0 <= self._sel < len(self._item_names)
        rrect(surf, (70, 20, 20) if has_sel else (28, 28, 40),
              self._btn_clear, rad=3)
        txt(surf, "Limpar Sprite",
            self._btn_clear.centerx, self._btn_clear.y + 3,
            font_xs, (220, 80, 80) if has_sel else DIM, "center")

        clip_l = pygame.Rect(x, body_y + 15, LW, body_h - 40)
        surf.set_clip(clip_l)
        self._item_rects.clear()
        ITEM_H = 22
        for i, nome in enumerate(self._item_names):
            iy = clip_l.y + i * ITEM_H - self._list_scroll
            if iy + ITEM_H < clip_l.y or iy > clip_l.bottom:
                continue
            is_sel = i == self._sel
            ir = pygame.Rect(x + 2, iy + 1, LW - 4, ITEM_H - 2)
            self._item_rects[i] = ir
            rrect(surf, (45, 70, 100) if is_sel else (18, 20, 34), ir, rad=3)
            if is_sel:
                pygame.draw.rect(surf, (80, 160, 255), ir, 1, border_radius=3)
            dados_i  = self._dados.get(nome, {})
            spr_nome = dados_i.get("sprite", "")
            sidx_i   = self.mgr.idx_of(spr_nome) if spr_nome else -1
            if sidx_i >= 0:
                try:
                    mini = self.mgr.get_scaled(sidx_i,
                                               dados_i.get("col", 0),
                                               dados_i.get("lin", 0), 16)
                    surf.blit(mini, (ir.x + 2, iy + 3))
                except Exception:
                    pass
            txt(surf, nome, ir.x + 20, iy + 5,
                font_xs, SEL_C if is_sel else TEXT)
        surf.set_clip(None)

        if not self._item_names:
            txt(surf, "Use Importar",
                x + LW // 2, body_y + 40, font_xs, DIM, "center")
            txt(surf, "de itens.py",
                x + LW // 2, body_y + 52, font_xs, DIM, "center")

        # ── Coluna direita: editor ─────────────────────────────────────────────
        ex = x + LW + 4
        ew = w - LW - 6
        ey = body_y

        nome, dados = self._entry()
        if not nome or not dados:
            txt(surf, "Selecione um item",
                ex + ew // 2, ey + body_h // 2, font_xs, DIM, "center")
            return

        # Nome do item selecionado
        pygame.draw.rect(surf, (22, 25, 40), pygame.Rect(ex, ey, ew, 18))
        txt(surf, nome, ex + 4, ey + 3, font_sm, (80, 200, 255))
        ey += 20

        # ── Seletor de sheet (setas < >) ──────────────────────────────────────
        cur_spr  = dados.get("sprite", "")
        cur_sidx = self.mgr.idx_of(cur_spr) if cur_spr else -1

        pygame.draw.rect(surf, (16, 18, 30), pygame.Rect(ex, ey, ew, 20))
        self._sheet_btns.clear()
        ARW = 18
        can_nav = self.mgr.count() > 1
        btn_prev = pygame.Rect(ex + 2, ey + 2, ARW, 16)
        rrect(surf, BTN_BG if can_nav else (18, 20, 32), btn_prev, rad=3)
        txt(surf, "<", btn_prev.centerx, btn_prev.y + 2, font_xs,
            TEXT if can_nav else DIM, "center")
        self._sheet_btns["prev"] = btn_prev

        btn_next = pygame.Rect(ex + 2 + ARW + 2, ey + 2, ARW, 16)
        rrect(surf, BTN_BG if can_nav else (18, 20, 32), btn_next, rad=3)
        txt(surf, ">", btn_next.centerx, btn_next.y + 2, font_xs,
            TEXT if can_nav else DIM, "center")
        self._sheet_btns["next"] = btn_next

        name_x  = ex + 2 + ARW * 2 + 6
        name_w  = ew - (name_x - ex) - 2
        sname_cur = self.mgr.names[cur_sidx] if cur_sidx >= 0 else "—"
        sn_d = sname_cur
        while font_xs.size(sn_d)[0] > name_w - 4 and len(sn_d) > 3:
            sn_d = sn_d[:-1]
        if sn_d != sname_cur:
            sn_d = sn_d[:-1] + "..."
        txt(surf, sn_d, name_x + name_w // 2, ey + 4, font_xs, ACCENT2, "center")
        cnt_str = f"{cur_sidx+1}/{self.mgr.count()}" if self.mgr.count() > 0 else "0/0"
        txt(surf, cnt_str, ex + ew - 2, ey + 4, font_xs, DIM, "right")
        ey += 24

        # col, lin atual
        cc, cl = int(dados.get("col", 0)), int(dados.get("lin", 0))
        txt(surf, f"col={cc}  lin={cl}",
            ex + 4, ey, font_xs, (80, 200, 255))
        ey += 12

        # Dica de controles
        hint = f"zoom {self._v_sc}x  Ctrl+scroll  |  Shift+scroll=H"
        txt(surf, hint, ex, ey, font_xs, DIM)
        ey += 12

        # ── Viewer ─────────────────────────────────────────────────────────────
        viewer_h = body_h - (ey - body_y) - 6
        vr = pygame.Rect(ex, ey, ew, max(40, viewer_h))
        self._viewer_rect = vr
        pygame.draw.rect(surf, (8, 9, 18), vr)
        pygame.draw.rect(surf, PANEL_SEP, vr, 1)

        self._cell_rects.clear()
        if cur_sidx >= 0:
            self._clamp_scroll(cur_sidx, vr)
            ts   = TILE_SIZE * self._v_sc
            ssrf = self._sheet_surf(cur_sidx)

            surf.set_clip(vr)
            surf.blit(ssrf, (vr.x - self._h_scroll,
                             vr.y - self._v_scroll))

            nc = self.mgr.ncols(cur_sidx)
            nr = self.mgr.nrows(cur_sidx)
            for c in range(nc):
                for r in range(nr):
                    cx_ = vr.x + c * ts - self._h_scroll
                    cy_ = vr.y + r * ts - self._v_scroll
                    if cx_ + ts < vr.x or cx_ > vr.right: continue
                    if cy_ + ts < vr.y or cy_ > vr.bottom: continue
                    crect = pygame.Rect(cx_, cy_, ts, ts)
                    self._cell_rects[(c, r)] = crect
                    pygame.draw.rect(surf, (22, 26, 44), crect, 1)

            # Destaque do tile selecionado
            sel_cx = vr.x + cc * ts - self._h_scroll
            sel_cy = vr.y + cl * ts - self._v_scroll
            if vr.x <= sel_cx < vr.right and vr.y <= sel_cy < vr.bottom:
                pygame.draw.rect(surf, (80, 200, 255),
                                 (sel_cx, sel_cy, ts, ts), 3)

            surf.set_clip(None)

            # Scrollbars
            sh_h = self._sheet_px_h(cur_sidx)
            if sh_h > vr.h:
                ratio = vr.h / sh_h
                bh = max(10, int(vr.h * ratio))
                by = vr.y + int(self._v_scroll / sh_h * vr.h)
                pygame.draw.rect(surf, ACCENT,
                                 (vr.right - 4, by, 4, bh), border_radius=2)
            sh_w = self._sheet_px_w(cur_sidx)
            if sh_w > vr.w:
                ratio = vr.w / sh_w
                bw = max(10, int(vr.w * ratio))
                bx = vr.x + int(self._h_scroll / sh_w * vr.w)
                pygame.draw.rect(surf, ACCENT2,
                                 (bx, vr.bottom - 4, bw, 4), border_radius=2)
        else:
            surf.set_clip(None)
            txt(surf, "Selecione uma sheet acima",
                vr.centerx, vr.centery, font_xs, DIM, "center")

        txt(surf, "LMB=selecionar sprite  |  Ctrl+scroll=zoom  |  Shift+scroll=H",
            ex, vr.bottom + 3, font_xs, (42, 48, 72))

    # ── handle event ──────────────────────────────────────────────────────────
    def handle_event(self, event, mpos):
        in_panel = self._rect.collidepoint(mpos)

        # Scroll e zoom no viewer
        if event.type == pygame.MOUSEWHEEL and in_panel:
            nome, dados = self._entry()
            cur_sidx = -1
            if dados:
                spr = dados.get("sprite", "")
                cur_sidx = self.mgr.idx_of(spr) if spr else -1

            if self._viewer_rect.collidepoint(mpos) and cur_sidx >= 0:
                ctrl  = bool(pygame.key.get_mods() & pygame.KMOD_CTRL)
                shift = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                if ctrl:
                    new_sc = clamp(self._v_sc + event.y, self.SC_MIN, self.SC_MAX)
                    if new_sc != self._v_sc:
                        self._v_sc = new_sc
                        self._v_cache.clear()
                elif shift:
                    max_h = max(0, self._sheet_px_w(cur_sidx) - self._viewer_rect.w)
                    self._h_scroll = clamp(self._h_scroll - event.y * TILE_SIZE, 0, max_h)
                else:
                    max_v = max(0, self._sheet_px_h(cur_sidx) - self._viewer_rect.h)
                    self._v_scroll = clamp(self._v_scroll - event.y * TILE_SIZE, 0, max_v)
            else:
                self._list_scroll = max(0, self._list_scroll - event.y * 16)
            return True

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        if not in_panel:
            return False

        # Botão importar
        if self._btn_import and self._btn_import.collidepoint(mpos):
            print(f"[ItemSpritesPanel] {self.importar_de_itens()}")
            return True

        # Lista de itens
        for i, ir in self._item_rects.items():
            if ir.collidepoint(mpos):
                self._sel      = i
                self._v_scroll = 0
                self._h_scroll = 0
                return True

        # Limpar sprite
        if self._btn_clear and self._btn_clear.collidepoint(mpos):
            if 0 <= self._sel < len(self._item_names):
                nd = self._item_names[self._sel]
                self._dados[nd] = self._blank()
                self._status = f"Sprite de '{nd}' limpo."
            return True

        nome, dados = self._entry()
        if not nome or not dados:
            return False

        # Setas de sheet < >
        for key, sbr in self._sheet_btns.items():
            if sbr.collidepoint(mpos):
                cur_spr2  = dados.get("sprite", "")
                cur_sidx2 = self.mgr.idx_of(cur_spr2) if cur_spr2 else -1
                n = self.mgr.count()
                if n > 0:
                    new_idx = (cur_sidx2 + (-1 if key == "prev" else 1)) % n
                    dados["sprite"] = self.mgr.names[new_idx]
                self._v_cache.clear()
                self._v_scroll = 0
                self._h_scroll = 0
                return True

        # Viewer — clique define col+lin
        if self._viewer_rect.collidepoint(mpos):
            cur_spr  = dados.get("sprite", "")
            cur_sidx = self.mgr.idx_of(cur_spr) if cur_spr else -1
            if cur_sidx >= 0:
                ts  = TILE_SIZE * self._v_sc
                col = (mpos[0] - self._viewer_rect.x + self._h_scroll) // ts
                lin = (mpos[1] - self._viewer_rect.y + self._v_scroll) // ts
                nc  = self.mgr.ncols(cur_sidx)
                nr  = self.mgr.nrows(cur_sidx)
                dados["col"] = clamp(col, 0, nc - 1)
                dados["lin"] = clamp(lin, 0, nr - 1)
            return True

        return False


# ─── NPCPanel ──────────────────────────────────────────────────────────────────
class NPCPanel:
    """
    Aba de sprites/animacoes dos NPCs.

    Viewer identico ao tilemap:
      - Scroll vertical   (roda do mouse)
      - Scroll horizontal (Shift + roda)
      - Zoom              (Ctrl  + roda)
      - Clique LMB        → seleciona col+lin para o dir/frame ativo
      - Scrollbars V e H

    Cada celula guarda (col, lin) — nao apenas col.
    Grid 4 dirs x 3 frames com preview, col+lin, e botao FLIP por linha.
    """

    DIRECOES  = ["baixo", "cima", "esquerda", "direita"]
    FRAMES    = ["parado", "passo1", "passo2"]
    DIR_ARROW = {"baixo": "v", "cima": "^", "esquerda": "<", "direita": ">"}
    DIR_CORES = {
        "baixo":    (80,  160, 255),
        "cima":     (80,  220, 130),
        "esquerda": (255, 180,  60),
        "direita":  (220,  80, 200),
    }
    LIST_W = 108
    SC_MIN, SC_MAX, SC_DEF = 1, 8, 2

    def __init__(self, mgr):
        self.mgr           = mgr
        self._rect         = pygame.Rect(0, 0, 1, 1)
        self._npc_names    = []
        self._sel_npc      = -1
        self._dados        = {}
        self._sel_dir      = "baixo"
        self._sel_frame    = "parado"
        # viewer state — igual ao tilemap
        self._v_scroll     = 0      # scroll vertical
        self._h_scroll     = 0      # scroll horizontal
        self._v_sc         = self.SC_DEF
        self._v_cache      = {}     # (sidx, sc) -> surface escalada
        self._list_scroll  = 0
        self._status       = ""
        # rects reconstruidos em draw()
        self._btn_import   = None
        self._btn_del_npc  = None
        self._npc_rects    = {}
        self._sheet_btns   = {}
        self._viewer_rect  = pygame.Rect(0, 0, 1, 1)
        self._cell_rects   = {}     # (c, r) -> rect na tela
        self._preview_cells= {}     # (dir, frame) -> rect no grid
        self._flip_btns    = {}     # dir -> rect

    # ── Dados ──────────────────────────────────────────────────────────────────
    def _blank_npc(self):
        d = {"sprite": ""}
        for dr in self.DIRECOES:
            # col, lin, flip por frame
            d[dr] = {"parado": (0,0), "passo1": (0,0), "passo2": (0,0), "flip": False}
        return d

    def _npc(self):
        if 0 <= self._sel_npc < len(self._npc_names):
            nome = self._npc_names[self._sel_npc]
            if nome not in self._dados:
                self._dados[nome] = self._blank_npc()
            return nome, self._dados[nome]
        return None, None

    def _get_tile(self, dd, frame):
        """Retorna (col, lin) para um frame, aceitando int legado ou tupla."""
        v = dd.get(frame, (0, 0))
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return int(v[0]), int(v[1])
        return int(v), 0  # compatibilidade com dados antigos (so col)

    def to_dict(self):
        out = {}
        for n in self._npc_names:
            if n not in self._dados:
                continue
            d = self._dados[n]
            entry = {"sprite": d.get("sprite", "")}
            for dr in self.DIRECOES:
                dd = d.get(dr, {})
                entry[dr] = {
                    "parado":  list(self._get_tile(dd, "parado")),
                    "passo1":  list(self._get_tile(dd, "passo1")),
                    "passo2":  list(self._get_tile(dd, "passo2")),
                    "flip":    bool(dd.get("flip", False)),
                }
            out[n] = entry
        return out

    def from_dict(self, d):
        self._dados = {}
        for nome, anim in d.items():
            entry = {"sprite": anim.get("sprite", "")}
            for dr in self.DIRECOES:
                dd = anim.get(dr, {})
                entry[dr] = {
                    "parado":  dd.get("parado", (0,0)),
                    "passo1":  dd.get("passo1", (0,0)),
                    "passo2":  dd.get("passo2", (0,0)),
                    "flip":    bool(dd.get("flip", False)),
                }
            self._dados[nome] = entry
            if nome not in self._npc_names:
                self._npc_names.append(nome)
        if self._npc_names and self._sel_npc < 0:
            self._sel_npc = 0

    # ── Importar de itens.py ───────────────────────────────────────────────────
    def importar_npcs_de_itens(self):
        try:
            import importlib.util, os, sys
            editor_dir = os.path.dirname(os.path.abspath(__file__))
            game_dir   = os.path.dirname(editor_dir)
            itens_path = os.path.join(game_dir, "itens.py")
            _ins = game_dir not in sys.path
            if _ins: sys.path.insert(0, game_dir)
            try:
                spec = importlib.util.spec_from_file_location("itens_editor", itens_path)
                mod  = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                nomes = list(mod.todos_npcs.keys())
            finally:
                if _ins: sys.path.remove(game_dir)
            novos = 0
            for n in nomes:
                if n not in self._dados:
                    self._dados[n] = self._blank_npc()
                    novos += 1
                if n not in self._npc_names:
                    self._npc_names.append(n)
            if self._sel_npc < 0 and self._npc_names:
                self._sel_npc = 0
            self._status = f"OK  {len(nomes)} NPC(s) ({novos} novo(s))"
        except Exception as e:
            self._status = f"ERRO: {e}"
        return self._status

    # ── Helpers de viewer ──────────────────────────────────────────────────────
    def _sheet_surf(self, sidx):
        key = (sidx, self._v_sc)
        if key not in self._v_cache:
            raw = self.mgr.surfs[sidx]
            self._v_cache[key] = pygame.transform.scale(
                raw, (raw.get_width() * self._v_sc,
                      raw.get_height() * self._v_sc))
        return self._v_cache[key]

    def _sheet_px_w(self, sidx): return self._sheet_surf(sidx).get_width()
    def _sheet_px_h(self, sidx): return self._sheet_surf(sidx).get_height()

    def _clamp_scroll(self, sidx, vr):
        ts = TILE_SIZE * self._v_sc
        max_v = max(0, self._sheet_px_h(sidx) - vr.h)
        max_h = max(0, self._sheet_px_w(sidx) - vr.w)
        self._v_scroll = clamp(self._v_scroll, 0, max_v)
        self._h_scroll = clamp(self._h_scroll, 0, max_h)

    # ── Draw ───────────────────────────────────────────────────────────────────
    def draw(self, surf, rect, font_sm, font_xs):
        self._rect = rect
        x, y, w, h = rect.x, rect.y, rect.w, rect.h
        pygame.draw.rect(surf, PANEL_BG, rect)

        # ── Toolbar ────────────────────────────────────────────────────────────
        TBAR = 26
        pygame.draw.rect(surf, HDR_BG, pygame.Rect(x, y, w, TBAR))
        txt(surf, "SPRITES DE NPC", x + 6, y + 6, font_sm, (255, 160, 80))
        self._btn_import = pygame.Rect(x + w - 112, y + 4, 108, 18)
        rrect(surf, (30, 80, 60), self._btn_import, rad=3)
        txt(surf, "Importar de itens.py",
            self._btn_import.centerx, self._btn_import.y + 3,
            font_xs, (180, 255, 190), "center")

        sy = y + TBAR + 2
        if self._status:
            ok = self._status.startswith("OK")
            txt(surf, self._status, x + 4, sy, font_xs,
                (100, 220, 120) if ok else (220, 80, 80))
        body_y = sy + 14
        body_h = h - (body_y - y)

        LW = self.LIST_W

        # ── Coluna esquerda: lista de NPCs ─────────────────────────────────────
        pygame.draw.rect(surf, (11, 13, 22),
                         pygame.Rect(x, body_y, LW, body_h))
        pygame.draw.line(surf, PANEL_SEP,
                         (x + LW, body_y), (x + LW, body_y + body_h), 1)
        txt(surf, "NPCs", x + LW // 2, body_y + 2, font_xs, DIM, "center")
        pygame.draw.line(surf, PANEL_SEP,
                         (x, body_y + 14), (x + LW, body_y + 14), 1)

        self._btn_del_npc = pygame.Rect(x + 3, body_y + body_h - 22, LW - 6, 18)
        has_sel = 0 <= self._sel_npc < len(self._npc_names)
        rrect(surf, (70, 20, 20) if has_sel else (28, 28, 40),
              self._btn_del_npc, rad=3)
        txt(surf, "Limpar Sprites",
            self._btn_del_npc.centerx, self._btn_del_npc.y + 3,
            font_xs, (220, 80, 80) if has_sel else DIM, "center")

        clip_l = pygame.Rect(x, body_y + 15, LW, body_h - 40)
        surf.set_clip(clip_l)
        self._npc_rects.clear()
        NPC_H = 22
        for i, nome in enumerate(self._npc_names):
            iy = clip_l.y + i * NPC_H - self._list_scroll
            if iy + NPC_H < clip_l.y or iy > clip_l.bottom:
                continue
            is_sel = i == self._sel_npc
            ir = pygame.Rect(x + 2, iy + 1, LW - 4, NPC_H - 2)
            self._npc_rects[i] = ir
            rrect(surf, (45, 85, 65) if is_sel else (18, 20, 34), ir, rad=3)
            if is_sel:
                pygame.draw.rect(surf, (255, 160, 80), ir, 1, border_radius=3)
            dados_i  = self._dados.get(nome, {})
            spr_nome = dados_i.get("sprite", "")
            sidx_i   = self.mgr.idx_of(spr_nome) if spr_nome else -1
            if sidx_i >= 0:
                try:
                    cl, ln = self._get_tile(dados_i.get("baixo", {}), "parado")
                    mini = self.mgr.get_scaled(sidx_i, cl, ln, 16)
                    surf.blit(mini, (ir.x + 2, iy + 3))
                except Exception:
                    pass
            txt(surf, nome, ir.x + 20, iy + 5,
                font_xs, SEL_C if is_sel else TEXT)
        surf.set_clip(None)
        if not self._npc_names:
            txt(surf, "Use Importar",
                x + LW // 2, body_y + 40, font_xs, DIM, "center")
            txt(surf, "de itens.py",
                x + LW // 2, body_y + 52, font_xs, DIM, "center")

        # ── Coluna direita: editor ─────────────────────────────────────────────
        ex = x + LW + 4
        ew = w - LW - 6
        ey = body_y

        nome, dados = self._npc()
        if not nome or not dados:
            txt(surf, "Selecione um NPC",
                ex + ew // 2, ey + body_h // 2, font_xs, DIM, "center")
            return

        # Nome
        pygame.draw.rect(surf, (22, 25, 40), pygame.Rect(ex, ey, ew, 18))
        txt(surf, nome, ex + 4, ey + 3, font_sm, (255, 200, 80))
        ey += 20

        # ── Seletor de sheet (setas < >) ──────────────────────────────────────
        cur_spr  = dados.get("sprite", "")
        cur_sidx = self.mgr.idx_of(cur_spr) if cur_spr else -1

        pygame.draw.rect(surf, (16, 18, 30), pygame.Rect(ex, ey, ew, 20))
        self._sheet_btns.clear()

        ARW = 18
        can_nav = self.mgr.count() > 1
        btn_prev = pygame.Rect(ex + 2, ey + 2, ARW, 16)
        rrect(surf, BTN_BG if can_nav else (18, 20, 32), btn_prev, rad=3)
        txt(surf, "<", btn_prev.centerx, btn_prev.y + 2, font_xs,
            TEXT if can_nav else DIM, "center")
        self._sheet_btns["prev"] = btn_prev

        btn_next = pygame.Rect(ex + 2 + ARW + 2, ey + 2, ARW, 16)
        rrect(surf, BTN_BG if can_nav else (18, 20, 32), btn_next, rad=3)
        txt(surf, ">", btn_next.centerx, btn_next.y + 2, font_xs,
            TEXT if can_nav else DIM, "center")
        self._sheet_btns["next"] = btn_next

        name_x  = ex + 2 + ARW * 2 + 6
        name_w  = ew - (name_x - ex) - 2
        sname_cur = self.mgr.names[cur_sidx] if cur_sidx >= 0 else "—"
        sn_d = sname_cur
        while font_xs.size(sn_d)[0] > name_w - 4 and len(sn_d) > 3:
            sn_d = sn_d[:-1]
        if sn_d != sname_cur:
            sn_d = sn_d[:-1] + "..."
        txt(surf, sn_d, name_x + name_w // 2, ey + 4, font_xs, ACCENT2, "center")
        cnt_str = f"{cur_sidx+1}/{self.mgr.count()}" if self.mgr.count() > 0 else "0/0"
        txt(surf, cnt_str, ex + ew - 2, ey + 4, font_xs, DIM, "right")
        ey += 24

        # ── Dica de controles do viewer ────────────────────────────────────────
        dc_sel = self.DIR_CORES[self._sel_dir]
        ar_sel = self.DIR_ARROW[self._sel_dir]
        hint = (f"[{ar_sel} {self._sel_dir} · {self._sel_frame}]  "
                f"zoom {self._v_sc}x  Ctrl+scroll  |  Shift+scroll=H")
        txt(surf, hint, ex, ey, font_xs, dc_sel)
        ey += 12

        # ── Viewer ─────────────────────────────────────────────────────────────
        # Ocupa ~metade do espaco restante
        remaining = body_h - (ey - body_y)
        # espaco para o grid abaixo: 4 linhas * 22 + cabecalho + legenda
        GRID_H    = 12 + len(self.DIRECOES) * 22 + 14
        viewer_h  = max(60, remaining - GRID_H - 4)

        vr = pygame.Rect(ex, ey, ew, viewer_h)
        self._viewer_rect = vr
        pygame.draw.rect(surf, (8, 9, 18), vr)
        pygame.draw.rect(surf, PANEL_SEP, vr, 1)

        self._cell_rects.clear()

        if cur_sidx >= 0:
            self._clamp_scroll(cur_sidx, vr)
            ts   = TILE_SIZE * self._v_sc
            ssrf = self._sheet_surf(cur_sidx)

            surf.set_clip(vr)
            surf.blit(ssrf, (vr.x - self._h_scroll,
                             vr.y - self._v_scroll))

            nc = self.mgr.ncols(cur_sidx)
            nr = self.mgr.nrows(cur_sidx)
            for c in range(nc):
                for r in range(nr):
                    cx_ = vr.x + c * ts - self._h_scroll
                    cy_ = vr.y + r * ts - self._v_scroll
                    if cx_ + ts < vr.x or cx_ > vr.right: continue
                    if cy_ + ts < vr.y or cy_ > vr.bottom: continue
                    crect = pygame.Rect(cx_, cy_, ts, ts)
                    self._cell_rects[(c, r)] = crect
                    pygame.draw.rect(surf, (22, 26, 44), crect, 1)

            # Marca todos os tiles atribuidos com a cor da direcao
            for d_ in self.DIRECOES:
                dd_  = dados.get(d_, {})
                dc_  = self.DIR_CORES[d_]
                ar_  = self.DIR_ARROW[d_]
                for f_ in self.FRAMES:
                    cl, ln = self._get_tile(dd_, f_)
                    is_active = (d_ == self._sel_dir and f_ == self._sel_frame)
                    cx_ = vr.x + cl * ts - self._h_scroll
                    cy_ = vr.y + ln * ts - self._v_scroll
                    if (vr.x <= cx_ < vr.right and
                            vr.y <= cy_ < vr.bottom):
                        bw = 3 if is_active else 1
                        pygame.draw.rect(surf, dc_, (cx_, cy_, ts, ts), bw)
                        if is_active:
                            lbl = ar_ + f_[0].upper()
                            txt(surf, lbl, cx_ + ts // 2, cy_ + 2,
                                font_xs, dc_, "center")

            surf.set_clip(None)

            # Scrollbar vertical
            sh_h = self._sheet_px_h(cur_sidx)
            if sh_h > vr.h:
                ratio = vr.h / sh_h
                bh = max(10, int(vr.h * ratio))
                by = vr.y + int(self._v_scroll / sh_h * vr.h)
                pygame.draw.rect(surf, ACCENT,
                                 (vr.right - 4, by, 4, bh), border_radius=2)
            # Scrollbar horizontal
            sh_w = self._sheet_px_w(cur_sidx)
            if sh_w > vr.w:
                ratio = vr.w / sh_w
                bw = max(10, int(vr.w * ratio))
                bx = vr.x + int(self._h_scroll / sh_w * vr.w)
                pygame.draw.rect(surf, ACCENT2,
                                 (bx, vr.bottom - 4, bw, 4), border_radius=2)
        else:
            surf.set_clip(None)
            txt(surf, "Selecione uma sheet acima",
                vr.centerx, vr.centery, font_xs, DIM, "center")

        ey += viewer_h + 4

        # ── Grid 4 direcoes x 3 frames ────────────────────────────────────────
        # Calcula de fora pra dentro: reserva FLIP_W no final, divide o resto
        DIR_W  = 22
        FLIP_W = 28
        GAP    = 2
        CELL_H = 20
        PREV_S = 14
        # espaco total para as 3 celulas de frame
        frames_total = ew - DIR_W - GAP - FLIP_W - GAP
        CELL_W = max(10, frames_total // 3)

        dir_x   = ex
        col_x0  = dir_x + DIR_W + GAP
        flip_x0 = ex + ew - FLIP_W          # ancorado na borda direita

        # Cabecalho
        for fi, frame in enumerate(self.FRAMES):
            fx = col_x0 + fi * CELL_W + CELL_W // 2
            txt(surf, frame, fx, ey, font_xs, DIM, "center")
        txt(surf, "flip", flip_x0 + FLIP_W // 2, ey, font_xs, (180, 255, 180), "center")
        ey += 12

        self._preview_cells.clear()
        self._flip_btns.clear()

        for di, direcao in enumerate(self.DIRECOES):
            row_y  = ey + di * (CELL_H + 2)
            dc_    = self.DIR_CORES[direcao]
            is_dir = direcao == self._sel_dir
            dd_    = dados.get(direcao, {})
            flip_d = bool(dd_.get("flip", False))

            # Icone de direcao (seta)
            arrow  = self.DIR_ARROW[direcao]
            dir_bg = pygame.Rect(dir_x, row_y, DIR_W, CELL_H)
            pygame.draw.rect(surf,
                             (28, 32, 52) if is_dir else (14, 16, 26),
                             dir_bg, border_radius=2)
            if is_dir:
                pygame.draw.rect(surf, dc_, dir_bg, 1, border_radius=2)
            txt(surf, arrow, dir_bg.centerx, row_y + 4,
                font_xs, dc_ if is_dir else DIM, "center")

            # Celulas de frame
            for fi, frame in enumerate(self.FRAMES):
                cl, ln = self._get_tile(dd_, frame)
                cx_    = col_x0 + fi * CELL_W
                is_sel = is_dir and frame == self._sel_frame

                cell_r = pygame.Rect(cx_, row_y, CELL_W - 2, CELL_H)
                self._preview_cells[(direcao, frame)] = cell_r
                rrect(surf, (38, 58, 88) if is_sel else (18, 20, 34), cell_r, rad=2)
                if is_sel:
                    pygame.draw.rect(surf, dc_, cell_r, 1, border_radius=2)

                # Miniatura com flip aplicado visualmente
                if cur_sidx >= 0:
                    try:
                        raw = self.mgr.get_raw(cur_sidx, cl, ln)
                        if flip_d:
                            raw = pygame.transform.flip(raw, True, False)
                        prev = pygame.transform.scale(raw, (PREV_S, PREV_S))
                        surf.blit(prev, (cell_r.x + 1, cell_r.y + 3))
                    except Exception:
                        pass

                txt(surf, f"{cl},{ln}",
                    cell_r.x + PREV_S + 3, row_y + 5,
                    font_xs, dc_ if is_sel else DIM)

            # ── Botao FLIP ancorado na borda direita ───────────────────────────
            flip_r = pygame.Rect(flip_x0, row_y, FLIP_W, CELL_H)
            self._flip_btns[direcao] = flip_r
            if flip_d:
                rrect(surf, (40, 170, 70), flip_r, rad=3)
                txt(surf, "ON", flip_r.centerx, flip_r.y + 4,
                    font_xs, (220, 255, 220), "center")
            else:
                rrect(surf, (25, 28, 46), flip_r, rad=3, bw=1, bc=(50, 56, 82))
                txt(surf, "OFF", flip_r.centerx, flip_r.y + 4,
                    font_xs, DIM, "center")

        ey += len(self.DIRECOES) * (CELL_H + 2) + 4
        txt(surf, "LMB=selecionar tile  |  Ctrl+scroll=zoom  |  Shift+scroll=horizontal",
            ex, ey, font_xs, (42, 48, 72))

    # ── Handle Event ───────────────────────────────────────────────────────────
    def handle_event(self, event, mpos):
        in_panel = self._rect.collidepoint(mpos)

        # ── Scroll e zoom no viewer ────────────────────────────────────────────
        if event.type == pygame.MOUSEWHEEL and in_panel:
            nome, dados = self._npc()
            cur_sidx = -1
            if dados:
                spr = dados.get("sprite", "")
                cur_sidx = self.mgr.idx_of(spr) if spr else -1

            if self._viewer_rect.collidepoint(mpos) and cur_sidx >= 0:
                ctrl  = bool(pygame.key.get_mods() & pygame.KMOD_CTRL)
                shift = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                if ctrl:
                    new_sc = clamp(self._v_sc + event.y, self.SC_MIN, self.SC_MAX)
                    if new_sc != self._v_sc:
                        self._v_sc = new_sc
                        self._v_cache.clear()
                elif shift:
                    max_h = max(0, self._sheet_px_w(cur_sidx) - self._viewer_rect.w)
                    self._h_scroll = clamp(
                        self._h_scroll - event.y * TILE_SIZE, 0, max_h)
                else:
                    max_v = max(0, self._sheet_px_h(cur_sidx) - self._viewer_rect.h)
                    self._v_scroll = clamp(
                        self._v_scroll - event.y * TILE_SIZE, 0, max_v)
            else:
                self._list_scroll = max(0, self._list_scroll - event.y * 16)
            return True

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        if not in_panel:
            return False

        # Toolbar
        if self._btn_import and self._btn_import.collidepoint(mpos):
            print(f"[NPCPanel] {self.importar_npcs_de_itens()}")
            return True

        # Lista
        for i, ir in self._npc_rects.items():
            if ir.collidepoint(mpos):
                self._sel_npc  = i
                self._v_scroll = 0
                self._h_scroll = 0
                return True

        # Deletar sprites (limpa animacoes mas mantém o NPC na lista)
        if self._btn_del_npc and self._btn_del_npc.collidepoint(mpos):
            if 0 <= self._sel_npc < len(self._npc_names):
                nd = self._npc_names[self._sel_npc]
                self._dados[nd] = self._blank_npc()
                self._status = f"Sprites de {nd} limpos."
            return True

        nome, dados = self._npc()
        if not nome or not dados:
            return False

        # Sheet — setas < >
        for key, sbr in self._sheet_btns.items():
            if sbr.collidepoint(mpos):
                cur_spr2  = dados.get("sprite", "")
                cur_sidx2 = self.mgr.idx_of(cur_spr2) if cur_spr2 else -1
                n = self.mgr.count()
                if n > 0:
                    if key == "prev":
                        new_idx = (cur_sidx2 - 1) % n
                    else:
                        new_idx = (cur_sidx2 + 1) % n
                    dados["sprite"] = self.mgr.names[new_idx]
                self._v_cache.clear()
                self._v_scroll = 0
                self._h_scroll = 0
                return True

        # Grid de preview — seleciona dir+frame
        for (direcao, frame), cr_ in self._preview_cells.items():
            if cr_.collidepoint(mpos):
                self._sel_dir   = direcao
                self._sel_frame = frame
                return True

        # Flip
        for direcao, fr_ in self._flip_btns.items():
            if fr_.collidepoint(mpos):
                dd_ = dados.setdefault(direcao, {})
                dd_["flip"] = not bool(dd_.get("flip", False))
                return True

        # Viewer — clique atribui (col, lin) ao dir+frame ativo
        if self._viewer_rect.collidepoint(mpos):
            cur_spr  = dados.get("sprite", "")
            cur_sidx = self.mgr.idx_of(cur_spr) if cur_spr else -1
            if cur_sidx >= 0:
                ts  = TILE_SIZE * self._v_sc
                col = (mpos[0] - self._viewer_rect.x + self._h_scroll) // ts
                lin = (mpos[1] - self._viewer_rect.y + self._v_scroll) // ts
                nc  = self.mgr.ncols(cur_sidx)
                nr  = self.mgr.nrows(cur_sidx)
                col = clamp(col, 0, nc - 1)
                lin = clamp(lin, 0, nr - 1)
                dd_ = dados.setdefault(self._sel_dir, {})
                dd_[self._sel_frame] = (col, lin)
                # Avanca frame automaticamente
                idx = self.FRAMES.index(self._sel_frame)
                self._sel_frame = self.FRAMES[(idx + 1) % len(self.FRAMES)]
            return True

        return False


# ─── RightPanel ────────────────────────────────────────────────────────────────
class RightPanel:
    SC   = 2          # zoom padrão do viewer (começa em 2×, ajustável)
    SC_MIN = 1
    SC_MAX = 8
    TABS = ["Sheet", "Paleta", "Itens", "NPCs", "Sprites Itens"]

    def __init__(self, rect, mgr, registry):
        self.rect         = rect
        self.mgr          = mgr
        self.registry     = registry
        self.active_sheet = -1
        self.sel_col      = 0
        self.sel_lin      = 0
        self.sheet_scroll   = 0
        self.sheet_scroll_x = 0
        self.viewer_sc    = self.SC
        self.list_scroll  = 0
        self._ss_cache    = {}
        self.props_panel  = PropsPanel(registry, mgr)
        self.palette      = TilePalette(registry, mgr)
        self.items_panel        = ItemsPanel(mgr)
        self.npc_panel          = NPCPanel(mgr)
        self.item_sprites_panel = ItemSpritesPanel(mgr)
        self.active_tab   = 0
        self._rmb_sel_start = None
        self._rmb_sel_end   = None

    # ── Geometry ───────────────────────────────────────────────────────────────
    def _tab_rects(self):
        n  = len(self.TABS)
        tw = self.rect.w // n
        return [pygame.Rect(self.rect.x + i * tw, self.rect.y, tw, TAB_H)
                for i in range(n)]

    def _cr(self):  # content rect
        return pygame.Rect(self.rect.x, self.rect.y + TAB_H,
                           self.rect.w, self.rect.h - TAB_H)

    def _hdr_r(self):
        cr = self._cr()
        return pygame.Rect(cr.x, cr.y, cr.w, TOOLBAR_H)

    def _list_lbl_r(self):
        return pygame.Rect(self._hdr_r().x, self._hdr_r().bottom,
                           self._hdr_r().w, 20)

    def _list_r(self):
        ll = self._list_lbl_r()
        return pygame.Rect(ll.x, ll.bottom, ll.w, SHEET_LIST_H)

    def _addbtn_r(self):
        lr = self._list_r()
        return pygame.Rect(lr.right - 32, lr.y + 2, 28, 18)

    def _addfolder_r(self):
        lr = self._list_r()
        return pygame.Rect(lr.right - 66, lr.y + 2, 30, 18)

    def _viewer_r(self):
        lr = self._list_r()
        return pygame.Rect(lr.x + 4, lr.bottom + 20, lr.w - 8, SHEET_PREVIEW_H)

    def _info_r(self):
        vr = self._viewer_r()
        return pygame.Rect(vr.x - 4, vr.bottom + 4, self.rect.w, 68)

    def _props_r(self):
        ir = self._info_r()
        return pygame.Rect(self.rect.x, ir.bottom,
                           self.rect.w, self.rect.bottom - ir.bottom)

    # ── Sheet surface (cache) ──────────────────────────────────────────────────
    def _ss(self, idx):
        sc = self.viewer_sc
        key = (idx, sc)
        if key not in self._ss_cache:
            raw = self.mgr.surfs[idx]
            self._ss_cache[key] = pygame.transform.scale(
                raw, (raw.get_width()*sc, raw.get_height()*sc))
        return self._ss_cache[key]

    def _sheet_h(self):
        if self.active_sheet < 0: return 0
        return self._ss(self.active_sheet).get_height()

    def _sheet_w(self):
        if self.active_sheet < 0: return 0
        return self._ss(self.active_sheet).get_width()

    # ── API ────────────────────────────────────────────────────────────────────
    def selected_cell(self):
        if self.active_tab == 1:
            return self.palette.selected_cell()
        if self.active_sheet < 0: return None
        return make_cell(self.active_sheet, self.sel_col, self.sel_lin)

    def get_multi_sel_rect(self):
        """Retorna (c0,l0,c1,l1) normalizado da seleção RMB, ou None."""
        if self._rmb_sel_start is None or self._rmb_sel_end is None:
            return None
        c0 = min(self._rmb_sel_start[0], self._rmb_sel_end[0])
        l0 = min(self._rmb_sel_start[1], self._rmb_sel_end[1])
        c1 = max(self._rmb_sel_start[0], self._rmb_sel_end[0])
        l1 = max(self._rmb_sel_start[1], self._rmb_sel_end[1])
        return (c0, l0, c1, l1)

    def build_multi_cells(self):
        """Retorna lista de {s,c,l,dc,dl} para o bloco selecionado com RMB."""
        r = self.get_multi_sel_rect()
        if r is None or self.active_sheet < 0:
            return []
        c0, l0, c1, l1 = r
        result = []
        for l in range(l0, l1 + 1):
            for c in range(c0, c1 + 1):
                result.append({"s": self.active_sheet, "c": c, "l": l,
                                "dc": c - c0, "dl": l - l0})
        return result

    def open_sheet(self, idx):
        self.active_sheet = idx
        self.sheet_scroll = 0
        self._sync_props()

    def _sync_props(self):
        if self.active_sheet >= 0:
            self.props_panel.set_tile(
                self.mgr.names[self.active_sheet], self.sel_col, self.sel_lin)

    def _jump_to_sheet(self, sn, col, lin):
        """Pula o viewer de sheet para mostrar a variante escolhida no PropsPanel."""
        idx = self.mgr.idx_of(sn)
        if idx < 0: return
        self.active_sheet = idx
        self.sel_col      = col
        self.sel_lin      = lin
        vr = self._viewer_r()
        ts = TILE_SIZE * self.viewer_sc
        ty = lin * ts
        if ty < self.sheet_scroll or ty + ts > self.sheet_scroll + vr.h:
            self.sheet_scroll = max(0, ty - vr.h // 2)
        tx = col * ts
        if tx < self.sheet_scroll_x or tx + ts > self.sheet_scroll_x + vr.w:
            self.sheet_scroll_x = max(0, tx - vr.w // 2)
        self._ss_cache.clear()

    # ── Eventos ────────────────────────────────────────────────────────────────
    def handle_event(self, event, mpos, font_xs):
        # Abas
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, tr in enumerate(self._tab_rects()):
                if tr.collidepoint(mpos):
                    self.active_tab = i
                    return True

        # Aba Itens
        if self.active_tab == 2:
            cr     = self._cr()
            itens_r = pygame.Rect(cr.x, cr.y, cr.w, cr.h)
            self.items_panel._rect = itens_r
            return self.items_panel.handle_event(event, mpos)

        # Aba NPCs
        if self.active_tab == 3:
            cr    = self._cr()
            npc_r = pygame.Rect(cr.x, cr.y, cr.w, cr.h)
            self.npc_panel._rect = npc_r
            return self.npc_panel.handle_event(event, mpos)

        # Aba Sprites Itens
        if self.active_tab == 4:
            cr     = self._cr()
            isp_r  = pygame.Rect(cr.x, cr.y, cr.w, cr.h)
            self.item_sprites_panel._rect = isp_r
            return self.item_sprites_panel.handle_event(event, mpos)

        # Aba Paleta
        if self.active_tab == 1:
            cr    = self._cr()
            pal_r = pygame.Rect(cr.x, cr.y, cr.w, cr.h)
            self.palette._rect = pal_r
            return self.palette.handle_event(event, mpos)

        # ── Aba Sheet ──────────────────────────────────────────────────────────
        if self.props_panel._editing_field is not None:
            if event.type in (pygame.KEYDOWN, pygame.TEXTINPUT,
                              pygame.MOUSEBUTTONDOWN):
                if self.props_panel.handle_event(event, mpos):
                    return True

        if not self.rect.collidepoint(mpos) and event.type != pygame.KEYDOWN:
            return False

        lr   = self._list_r()
        vr   = self._viewer_r()
        ab   = self._addbtn_r()
        afb  = self._addfolder_r()
        pr   = self._props_r()

        if (pr.collidepoint(mpos)
                or (self.props_panel._editing_field
                    and event.type == pygame.MOUSEBUTTONDOWN)):
            if self.props_panel.handle_event(event, mpos):
                return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if afb.collidepoint(mpos):
                    self._add_folder_dialog()
                    return True
                if ab.collidepoint(mpos):
                    self._add_file_dialog()
                    return True
                if lr.collidepoint(mpos):
                    ry  = mpos[1] - lr.y + self.list_scroll
                    idx = ry // 28
                    if 0 <= idx < self.mgr.count():
                        self.open_sheet(idx)
                    return True
                if self.active_sheet >= 0 and vr.collidepoint(mpos):
                    ts  = TILE_SIZE * self.viewer_sc
                    col = (mpos[0] - vr.x + self.sheet_scroll_x) // ts
                    lin = (mpos[1] - vr.y + self.sheet_scroll) // ts
                    nc  = self.mgr.ncols(self.active_sheet)
                    nr  = self.mgr.nrows(self.active_sheet)
                    if 0 <= col < nc and 0 <= lin < nr:
                        self.sel_col = col
                        self.sel_lin = lin
                        self._rmb_sel_start = (col, lin)
                        self._rmb_sel_end   = (col, lin)
                        self._sync_props()
                    return True

            # RMB na lista → remover sheet
            if event.button == 3 and lr.collidepoint(mpos):
                ry  = mpos[1] - lr.y + self.list_scroll
                idx = ry // 28
                if 0 <= idx < self.mgr.count():
                    self._remove_sheet(idx)
                return True

            # RMB no viewer → iniciar multi-seleção
            if event.button == 3 and self.active_sheet >= 0 and vr.collidepoint(mpos):
                ts  = TILE_SIZE * self.viewer_sc
                col = (mpos[0] - vr.x + self.sheet_scroll_x) // ts
                lin = (mpos[1] - vr.y + self.sheet_scroll) // ts
                nc  = self.mgr.ncols(self.active_sheet)
                nr  = self.mgr.nrows(self.active_sheet)
                col = clamp(col, 0, nc - 1)
                lin = clamp(lin, 0, nr - 1)
                self._rmb_sel_start = (col, lin)
                self._rmb_sel_end   = (col, lin)
                return True

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 3 and self._rmb_sel_start is not None and vr.collidepoint(mpos):
                return True

        if event.type == pygame.MOUSEMOTION:
            if (pygame.mouse.get_pressed()[2]
                    and self._rmb_sel_start is not None
                    and self.active_sheet >= 0
                    and vr.collidepoint(mpos)):
                ts  = TILE_SIZE * self.viewer_sc
                col = (mpos[0] - vr.x + self.sheet_scroll_x) // ts
                lin = (mpos[1] - vr.y + self.sheet_scroll) // ts
                nc  = self.mgr.ncols(self.active_sheet)
                nr  = self.mgr.nrows(self.active_sheet)
                col = clamp(col, 0, nc - 1)
                lin = clamp(lin, 0, nr - 1)
                self._rmb_sel_end = (col, lin)
                return True

        if event.type == pygame.MOUSEWHEEL:
            ctrl = bool(pygame.key.get_mods() & pygame.KMOD_CTRL)
            if vr.collidepoint(mpos) and self.active_sheet >= 0:
                if ctrl:
                    # Ctrl+Scroll = zoom do viewer
                    new_sc = clamp(self.viewer_sc + event.y, self.SC_MIN, self.SC_MAX)
                    if new_sc != self.viewer_sc:
                        self.viewer_sc = new_sc
                        self._ss_cache.clear()
                        # Reposiciona scroll para manter tile selecionado visível
                        ts = TILE_SIZE * self.viewer_sc
                        ty = self.sel_lin * ts
                        if ty < self.sheet_scroll or ty + ts > self.sheet_scroll + vr.h:
                            self.sheet_scroll = max(0, ty - vr.h // 2)
                        tx = self.sel_col * ts
                        if tx < self.sheet_scroll_x or tx + ts > self.sheet_scroll_x + vr.w:
                            self.sheet_scroll_x = max(0, tx - vr.w // 2)
                    return True
                # Shift+Scroll = scroll horizontal
                shift = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                if shift:
                    max_sx = max(0, self._sheet_w() - vr.w)
                    self.sheet_scroll_x = clamp(
                        self.sheet_scroll_x - event.y * 20, 0, max_sx)
                else:
                    max_s = max(0, self._sheet_h() - vr.height)
                    self.sheet_scroll = clamp(
                        self.sheet_scroll - event.y * 20, 0, max_s)
                return True
            if lr.collidepoint(mpos):
                max_s = max(0, self.mgr.count() * 28 - SHEET_LIST_H)
                self.list_scroll = clamp(
                    self.list_scroll - event.y * 18, 0, max_s)
                return True

        # ── Atalhos de teclado para o viewer (Aba Sheet) ──────────────────────
        # Ctrl+Setas = scroll no PNG do viewer de tiles
        # Shift+← / Shift+→ = trocar de sheet (PNG)
        # Setas simples = mover tile selecionado
        if event.type == pygame.KEYDOWN and self.active_tab == 0:
            ctrl  = bool(pygame.key.get_mods() & pygame.KMOD_CTRL)
            shift = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)

            # Shift+← / Shift+→ = navegar entre sheets (PNGs)
            if shift and not ctrl and event.key == pygame.K_LEFT:
                if self.mgr.count() > 1:
                    new_idx = (self.active_sheet - 1) % self.mgr.count()
                    self.open_sheet(new_idx)
                return True
            if shift and not ctrl and event.key == pygame.K_RIGHT:
                if self.mgr.count() > 1:
                    new_idx = (self.active_sheet + 1) % self.mgr.count()
                    self.open_sheet(new_idx)
                return True

            # Ctrl+Setas = scroll do viewer
            if ctrl and not shift and event.key == pygame.K_LEFT:
                max_sx = max(0, self._sheet_w() - self._viewer_r().w)
                self.sheet_scroll_x = clamp(
                    self.sheet_scroll_x - TILE_SIZE * self.viewer_sc * 3, 0, max_sx)
                return True
            if ctrl and not shift and event.key == pygame.K_RIGHT:
                max_sx = max(0, self._sheet_w() - self._viewer_r().w)
                self.sheet_scroll_x = clamp(
                    self.sheet_scroll_x + TILE_SIZE * self.viewer_sc * 3, 0, max_sx)
                return True
            if ctrl and not shift and event.key == pygame.K_UP:
                max_sy = max(0, self._sheet_h() - self._viewer_r().h)
                self.sheet_scroll = clamp(
                    self.sheet_scroll - TILE_SIZE * self.viewer_sc * 3, 0, max_sy)
                return True
            if ctrl and not shift and event.key == pygame.K_DOWN:
                max_sy = max(0, self._sheet_h() - self._viewer_r().h)
                self.sheet_scroll = clamp(
                    self.sheet_scroll + TILE_SIZE * self.viewer_sc * 3, 0, max_sy)
                return True

            # Setas simples = mover tile selecionado dentro do sheet
            if not ctrl and not shift and self.active_sheet >= 0:
                nc = self.mgr.ncols(self.active_sheet)
                nr = self.mgr.nrows(self.active_sheet)
                moved = False
                if event.key == pygame.K_LEFT:
                    self.sel_col = (self.sel_col - 1) % nc
                    moved = True
                elif event.key == pygame.K_RIGHT:
                    self.sel_col = (self.sel_col + 1) % nc
                    moved = True
                elif event.key == pygame.K_UP:
                    self.sel_lin = (self.sel_lin - 1) % nr
                    moved = True
                elif event.key == pygame.K_DOWN:
                    self.sel_lin = (self.sel_lin + 1) % nr
                    moved = True
                if moved:
                    # Atualiza seleção RMB e props
                    self._rmb_sel_start = (self.sel_col, self.sel_lin)
                    self._rmb_sel_end   = (self.sel_col, self.sel_lin)
                    self._sync_props()
                    # Auto-scroll para manter o tile visível
                    vr = self._viewer_r()
                    ts = TILE_SIZE * self.viewer_sc
                    tx = self.sel_col * ts
                    ty = self.sel_lin * ts
                    if tx < self.sheet_scroll_x:
                        self.sheet_scroll_x = tx
                    elif tx + ts > self.sheet_scroll_x + vr.w:
                        self.sheet_scroll_x = tx + ts - vr.w
                    if ty < self.sheet_scroll:
                        self.sheet_scroll = ty
                    elif ty + ts > self.sheet_scroll + vr.h:
                        self.sheet_scroll = ty + ts - vr.h
                    return True

        return False

    def _add_file_dialog(self):
        root = tk.Tk(); root.withdraw()
        path = filedialog.askopenfilename(
            title="Carregar spritesheet PNG",
            filetypes=[("PNG", "*.png"), ("Imagens", "*.png *.jpg"),
                       ("Todos", "*.*")])
        root.destroy()
        if path:
            idx = self.mgr.add(path)
            self._ss_cache.pop(idx, None)
            self.open_sheet(idx)

    def _add_folder_dialog(self):
        editor = self.props_panel._editor
        if editor is None: return
        dlg   = AddTilesDialog(editor.screen, editor.font_sm,
                               editor.font_xs, self.mgr)
        paths = dlg.run()
        for path in paths:
            idx = self.mgr.add(path)
            self._ss_cache.pop(idx, None)
        if paths:
            self.open_sheet(self.mgr.count() - 1)
            editor.status_msg = f"{len(paths)} sheet(s) importada(s)."

    def _remove_sheet(self, idx):
        self.mgr.remove(idx)
        self._ss_cache.clear()
        self.active_sheet = min(self.active_sheet, self.mgr.count() - 1)
        if self.active_sheet >= 0:
            self._sync_props()

    # ── Desenho ────────────────────────────────────────────────────────────────
    def draw(self, surf, font, font_sm, font_xs, active_layer):
        pygame.draw.rect(surf, PANEL_BG, self.rect)
        pygame.draw.line(surf, PANEL_SEP,
                         self.rect.topleft, self.rect.bottomleft, 2)
        lc = LAYER_COLORS[active_layer]

        for i, (label, tr) in enumerate(zip(self.TABS, self._tab_rects())):
            is_act = i == self.active_tab
            pygame.draw.rect(surf, lc if is_act else BTN_BG, tr)
            pygame.draw.rect(surf, PANEL_SEP, tr, 1)
            txt(surf, label, tr.centerx, tr.y + 8, font_sm,
                BTN_ON_T if is_act else DIM, "center")

        cr = self._cr()

        if self.active_tab == 2:
            itens_r = pygame.Rect(cr.x, cr.y, cr.w, cr.h)
            self.items_panel.draw(surf, itens_r, font_sm, font_xs)
            return

            return

        if self.active_tab == 3:
            npc_r = pygame.Rect(cr.x, cr.y, cr.w, cr.h)
            self.npc_panel.draw(surf, npc_r, font_sm, font_xs)
            return

        if self.active_tab == 4:
            isp_r = pygame.Rect(cr.x, cr.y, cr.w, cr.h)
            self.item_sprites_panel.draw(surf, isp_r, font_sm, font_xs)
            return

        if self.active_tab == 1:
            pal_r = pygame.Rect(cr.x, cr.y, cr.w, cr.h)
            self.palette.draw(surf, pal_r, font_sm, font_xs, active_layer)
            return

        # ── Aba Sheet ──────────────────────────────────────────────────────────
        hdr = self._hdr_r()
        pygame.draw.rect(surf, HDR_BG, hdr)
        txt(surf, "SPRITESHEET PICKER", hdr.centerx, hdr.y + 5, font_sm,
            lc, "center")
        txt(surf, f"Camada ativa:  {LAYER_NAMES[active_layer]}",
            hdr.centerx, hdr.y + 22, font_xs, lc, "center")

        # Botões + e dir
        ab  = self._addbtn_r()
        afb = self._addfolder_r()
        ll  = self._list_lbl_r()
        txt(surf, "Sheets  (RMB=remover):", ll.x + 6, ll.y + 3, font_xs, DIM)
        rrect(surf, ACCENT,        ab,  rad=3)
        txt(surf, "+", ab.centerx,  ab.y + 3, font_xs, BTN_ON_T, "center")
        rrect(surf, (40, 110, 60), afb, rad=3)
        txt(surf, "dir", afb.centerx, afb.y + 3, font_xs, TEXT, "center")

        # Lista de sheets
        lr = self._list_r()
        pygame.draw.rect(surf, (14, 16, 26), lr)
        pygame.draw.rect(surf, PANEL_SEP, lr, 1)
        surf.set_clip(lr)
        for i in range(self.mgr.count()):
            iy     = lr.y + i * 28 - self.list_scroll
            if iy + 28 < lr.y or iy > lr.bottom: continue
            is_act = i == self.active_sheet
            rrect(surf, lc if is_act else BTN_BG,
                  pygame.Rect(lr.x + 3, iy + 2, lr.w - 6, 24), rad=4)
            tc = BTN_ON_T if is_act else TEXT
            surf.blit(self.mgr.get_scaled(i, 0, 0, 18), (lr.x + 6, iy + 5))
            txt(surf, self.mgr.names[i], lr.x + 28, iy + 7, font_xs, tc)
        if self.mgr.count() == 0:
            txt(surf, "Use + (arquivo) ou dir (pasta)",
                lr.centerx, lr.centery - 4, font_xs, DIM, "center")
        surf.set_clip(None)

        # Viewer label + surf
        vl_y = lr.bottom + 2
        if self.active_sheet >= 0:
            sheet_nav = (f"[{self.active_sheet+1}/{self.mgr.count()}] "
                         f"{self.mgr.names[self.active_sheet]}  "
                         f"Shift+←→=sheet  ←→↑↓=tile")
            txt(surf, sheet_nav, cr.x + 6, vl_y + 2, font_xs, ACCENT2)
        else:
            txt(surf, "Selecione uma sheet acima (ou Shift+←→)",
                cr.x + 6, vl_y + 2, font_xs, DIM)

        vr = self._viewer_r()
        pygame.draw.rect(surf, (12, 13, 22), vr)
        pygame.draw.rect(surf, PANEL_SEP, vr, 1)

        if self.active_sheet >= 0:
            ts   = TILE_SIZE * self.viewer_sc
            ssrf = self._ss(self.active_sheet)
            surf.set_clip(vr)
            surf.blit(ssrf, (vr.x - self.sheet_scroll_x,
                              vr.y - self.sheet_scroll))

            nc = self.mgr.ncols(self.active_sheet)
            nr = self.mgr.nrows(self.active_sheet)
            sn = self.mgr.names[self.active_sheet]
            for c in range(nc):
                for r in range(nr):
                    cx = vr.x + c * ts - self.sheet_scroll_x
                    cy = vr.y + r * ts - self.sheet_scroll
                    if self.registry.has(sn, c, r):
                        p   = self.registry.get(sn, c, r)
                        tid = p.get("id")
                        nvars = (len(self.registry.variants_of(tid))
                                 if tid is not None else 1)
                        if nvars > 1:
                            col = VAR_C
                        elif p.get("solid"):
                            col = WARN
                        else:
                            col = BTN_ON
                        pygame.draw.rect(surf, col, (cx, cy, ts, ts), 1)
                    else:
                        pygame.draw.rect(surf, (0,0,0), (cx, cy, ts, ts), 1)

            sx = vr.x + self.sel_col * ts - self.sheet_scroll_x
            sy = vr.y + self.sel_lin * ts - self.sheet_scroll
            pygame.draw.rect(surf, SEL_C, (sx, sy, ts, ts), 2)

            # Retângulo da multi-seleção RMB
            msr = self.get_multi_sel_rect()
            if msr is not None:
                mc0, ml0, mc1, ml1 = msr
                mw = (mc1 - mc0 + 1) * ts
                mh = (ml1 - ml0 + 1) * ts
                mx = vr.x + mc0 * ts - self.sheet_scroll_x
                my = vr.y + ml0 * ts - self.sheet_scroll
                sel_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
                sel_surf.fill((255, 200, 0, 45))
                surf.blit(sel_surf, (mx, my))
                pygame.draw.rect(surf, (255, 200, 0), (mx, my, mw, mh), 2)

            surf.set_clip(None)

            # Scrollbar vertical
            sh_h = self._sheet_h()
            if sh_h > vr.height:
                ratio = vr.height / sh_h
                bh = max(16, int(vr.height * ratio))
                by = vr.y + int(self.sheet_scroll / sh_h * vr.height)
                pygame.draw.rect(surf, ACCENT,
                                 (vr.right - 4, by, 4, bh), border_radius=2)
            # Scrollbar horizontal
            sw_w = self._sheet_w()
            if sw_w > vr.width:
                ratio = vr.width / sw_w
                bw = max(16, int(vr.width * ratio))
                bx = vr.x + int(self.sheet_scroll_x / sw_w * vr.width)
                pygame.draw.rect(surf, ACCENT2,
                                 (bx, vr.bottom - 4, bw, 4), border_radius=2)
        else:
            surf.set_clip(None)

        # Info do tile
        ir = self._info_r()
        if ir.height > 20 and self.active_sheet >= 0:
            pygame.draw.line(surf, PANEL_SEP, (ir.x, ir.y), (ir.right, ir.y), 1)
            px   = 44
            raw  = self.mgr.get_raw(self.active_sheet, self.sel_col, self.sel_lin)
            prev = pygame.transform.scale(raw, (px, px))
            cb   = make_checker(px // 2)
            bg2  = pygame.Surface((px, px))
            for ox, oy in [(0,0),(px//2,0),(0,px//2),(px//2,px//2)]:
                bg2.blit(cb, (ox, oy))
            surf.blit(bg2,  (ir.x + 8, ir.y + 6))
            surf.blit(prev, (ir.x + 8, ir.y + 6))
            pygame.draw.rect(surf, PANEL_SEP, (ir.x+8, ir.y+6, px, px), 1)

            ix = ir.x + px + 18
            txt(surf, self.mgr.names[self.active_sheet], ix, ir.y+8, font_xs, ACCENT2)
            txt(surf, f"col={self.sel_col}  lin={self.sel_lin}", ix, ir.y+22, font_xs, TEXT)
            sn    = self.mgr.names[self.active_sheet]
            props = self.registry.get(sn, self.sel_col, self.sel_lin)
            if props:
                tid   = props.get("id","?")
                nvars = len(self.registry.variants_of(tid)) if props.get("id") is not None else 0
                sol   = "SIM" if props.get("solid") else "NÃO"
                txt(surf, f"ID={tid}  solid={sol}  {nvars} visual(is)",
                    ix, ir.y+38, font_xs, ACCENT)
            else:
                txt(surf, "Não registrado", ix, ir.y+38, font_xs, DIM)
            txt(surf, "■verde=reg  ■vermelho=sólido  ■roxo=variante",
                ir.x+8, ir.y+56, font_xs, DIM)

        pr = self._props_r()
        if pr.height > 20:
            self.props_panel.draw(surf, pr, font, font_sm, font_xs)


# ─── NewMapDialog ──────────────────────────────────────────────────────────────
class NewMapDialog:
    def __init__(self, screen, font, font_sm, font_xs,
                 cur_cols, cur_rows, cur_name):
        self.screen  = screen
        self.font    = font
        self.font_sm = font_sm
        self.font_xs = font_xs
        self.fields  = {"cols": str(cur_cols), "rows": str(cur_rows),
                        "nome": cur_name}
        self.labels  = {"cols": "Colunas:", "rows": "Linhas:", "nome": "Nome:"}
        self.order   = ["cols", "rows", "nome"]
        self.active  = "cols"
        self._rects  = {}
        self._ok_r   = None
        self._ca_r   = None

    def run(self):
        clock = pygame.time.Clock()
        pygame.key.start_text_input()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.key.stop_text_input(); return None
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        idx = self.order.index(self.active)
                        if idx < len(self.order) - 1:
                            self.active = self.order[idx + 1]
                        else:
                            r = self._validate()
                            if r:
                                pygame.key.stop_text_input(); return r
                    if event.key == pygame.K_TAB:
                        idx = self.order.index(self.active)
                        self.active = self.order[(idx+1) % len(self.order)]
                    if event.key == pygame.K_BACKSPACE:
                        self.fields[self.active] = self.fields[self.active][:-1]
                if event.type == pygame.TEXTINPUT:
                    f = self.active
                    if f in ("cols", "rows") and not event.text.isdigit(): pass
                    else: self.fields[f] += event.text
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mp = pygame.mouse.get_pos()
                    for key, r in self._rects.items():
                        if r.collidepoint(mp): self.active = key
                    if self._ok_r and self._ok_r.collidepoint(mp):
                        r = self._validate()
                        if r: pygame.key.stop_text_input(); return r
                    if self._ca_r and self._ca_r.collidepoint(mp):
                        pygame.key.stop_text_input(); return None
            self._draw()
            clock.tick(60)

    def _validate(self):
        try:
            cols = int(self.fields["cols"])
            rows = int(self.fields["rows"])
        except: return None
        if not (4 <= cols <= 500 and 4 <= rows <= 500): return None
        return {"cols": cols, "rows": rows,
                "nome": self.fields["nome"].strip() or "novo_mapa"}

    def _draw(self):
        w, h  = self.screen.get_size()
        ov    = pygame.Surface((w, h), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160)); self.screen.blit(ov, (0, 0))
        DW, DH = 360, 260
        dx, dy = (w-DW)//2, (h-DH)//2
        pygame.draw.rect(self.screen, HDR_BG, (dx,dy,DW,DH), border_radius=10)
        pygame.draw.rect(self.screen, ACCENT,  (dx,dy,DW,DH), 2, border_radius=10)
        txt(self.screen, "NOVO MAPA", dx+DW//2, dy+12, self.font_sm, ACCENT, "center")
        self._rects.clear()
        fy = dy + 50
        for key in self.order:
            txt(self.screen, self.labels[key], dx+20, fy+5, self.font_xs, DIM)
            fr = pygame.Rect(dx+100, fy, DW-120, 28)
            self._rects[key] = fr
            ed = self.active == key
            rrect(self.screen, (25,28,45) if ed else BTN_BG, fr, rad=4,
                  bw=2, bc=ACCENT if ed else PANEL_SEP)
            txt(self.screen, self.fields[key] + ("|" if ed else ""),
                fr.x+8, fr.y+7, self.font_xs, SEL_C if ed else TEXT)
            fy += 44
        try:
            c, r = int(self.fields["cols"]), int(self.fields["rows"])
            ok   = 4 <= c <= 500 and 4 <= r <= 500
            info = f"{c}×{r} tiles  ({c*16}×{r*16} px)" if ok else "4–500"
            col  = BTN_ON if ok else WARN
        except:
            info = "Digite números"; col = WARN
        txt(self.screen, info, dx+DW//2, dy+DH-70, self.font_xs, col, "center")
        ok_r = pygame.Rect(dx+20, dy+DH-46, 140, 32)
        ca_r = pygame.Rect(dx+200, dy+DH-46, 140, 32)
        self._ok_r = ok_r; self._ca_r = ca_r
        rrect(self.screen, BTN_ON, ok_r, rad=6)
        txt(self.screen, "Criar Mapa", ok_r.centerx, ok_r.y+9,
            self.font_xs, BTN_ON_T, "center")
        rrect(self.screen, BTN_BG, ca_r, rad=6, bw=1, bc=WARN)
        txt(self.screen, "Cancelar",  ca_r.centerx, ca_r.y+9,
            self.font_xs, WARN, "center")
        pygame.display.flip()


# ─── MapEditor ─────────────────────────────────────────────────────────────────
class MapEditor:
    NUM_LAYERS = 3

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(
            (EDITOR_W, EDITOR_H), pygame.RESIZABLE)
        pygame.display.set_caption("Editor de Mapas v6.0")

        self.font    = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_sm = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_xs = pygame.font.SysFont("monospace", 11)

        self.map_name = "novo_mapa"
        self.map_cols = 35
        self.map_rows = 33
        self.layers   = [
            [[None]*self.map_cols for _ in range(self.map_rows)]
            for _ in range(self.NUM_LAYERS)
        ]
        self.active_layer = 0
        self.history      = []
        self.redo_stack   = []

        self.zoom      = float(ZOOM_DEFAULT)
        self.cam_x     = 0.0
        self.cam_y     = 0.0
        self.panning   = False
        self.pan_start = (0, 0)
        self.cam_start = (0.0, 0.0)

        self.tool         = "draw"
        self.drawing      = False
        self.erasing      = False
        self.last_painted = None
        self.show_grid    = True
        self._tb_btns     = {}      # toolbar buttons (rebuilt each frame)
        self._space_pan   = False   # pan via Espaço+drag
        self._sp_start    = (0, 0)
        self._sp_cam      = (0.0, 0.0)


        # Multi-seleção de tiles (RMB no sheet viewer → retângulo)
        # Cada elemento é um dict {"s":idx, "c":col, "l":lin, "dc":delta_col, "dl":delta_lin}
        self._multi_cells   = []   # lista de cells relativas ao canto superior-esq
        self._multi_w       = 1    # largura da seleção em tiles
        self._multi_h       = 1    # altura da seleção em tiles

        self.mgr            = SheetManager()
        self.registry       = TileRegistry()
        self._sem_conflicts = {}
        self._tcache        = {}

        self._auto_load()

        panel_rect = pygame.Rect(EDITOR_W - PANEL_W, 0, PANEL_W, EDITOR_H)
        self.panel = RightPanel(panel_rect, self.mgr, self.registry)
        self.panel.props_panel.set_editor(self)
        if self.mgr.count() > 0:
            self.panel.open_sheet(0)

        self.status_msg = (
            "v8  |  Atalhos: Ctrl+S/L/Z/Y/D/E/F/G/N/T/I  |  "
            "Ctrl+I = importar PNG  |  "
            "Viewer: Ctrl+Scroll=zoom  Shift+Scroll=horizontal  |  "
            "Nomes = estágios de planta separados por vírgula")

        aw = EDITOR_W - PANEL_W
        self.cam_x = (aw - self.map_cols*TILE_SIZE*self.zoom) / 2
        self.cam_y = (TOOLBAR_H
                      + (EDITOR_H - TOOLBAR_H
                         - self.map_rows*TILE_SIZE*self.zoom) / 2)

    # ── Auto-load ──────────────────────────────────────────────────────────────
    def _auto_load(self):
        here = os.path.dirname(os.path.abspath(__file__))
        for name in ["beteraba.png", "terras.png", "items.png",]:
            p = os.path.join(here, name)
            if os.path.exists(p): self.mgr.add(p)
        editor_dir = os.path.join(here, "editor")
        if os.path.isdir(editor_dir):
            for name in sorted(os.listdir(editor_dir)):
                if name.lower().endswith(".png"):
                    self.mgr.add(os.path.join(editor_dir, name))
        # tile_definitions.json automático
        for base in [here, editor_dir]:
            td = os.path.join(base, "tile_definitions.json")
            if os.path.exists(td):
                warns = self.registry.load_tile_definitions(td)
                n = len(self.registry._props)
                self.status_msg = f"tile_definitions carregado → {n} entradas."
                for w in warns: print("[WARN]", w)
                break

    # ── Helpers ────────────────────────────────────────────────────────────────
    @property
    def ts(self): return self.zoom * TILE_SIZE

    def _aw(self): return self.screen.get_width() - PANEL_W

    def _map_area(self):
        return pygame.Rect(0, TOOLBAR_H,
                           self._aw(), self.screen.get_height() - TOOLBAR_H)

    def _s2g(self, sx, sy):
        return int((sx - self.cam_x) / self.ts), int((sy - self.cam_y) / self.ts)

    def _g2s(self, gx, gy):
        return self.cam_x + gx*self.ts, self.cam_y + gy*self.ts

    def _inb(self, gx, gy):
        return 0 <= gx < self.map_cols and 0 <= gy < self.map_rows

    def _tile_surf(self, cell):
        if cell is None: return None
        px  = max(1, round(self.ts))
        key = (cell["s"], cell["c"], cell["l"], px)
        if key not in self._tcache:
            self._tcache[key] = self.mgr.get_scaled(
                cell["s"], cell["c"], cell["l"], px)
        return self._tcache[key]

    # ── Undo / Redo ────────────────────────────────────────────────────────────
    def _push(self):
        self.history.append(copy.deepcopy(self.layers))
        if len(self.history) > 80: self.history.pop(0)
        self.redo_stack.clear()

    def _undo(self):
        if self.history:
            self.redo_stack.append(copy.deepcopy(self.layers))
            self.layers = self.history.pop()

    def _redo(self):
        if self.redo_stack:
            self.history.append(copy.deepcopy(self.layers))
            self.layers = self.redo_stack.pop()

    # ── Edição ─────────────────────────────────────────────────────────────────
    def _paint(self, gx, gy, cell):
        if self._inb(gx, gy):
            self.layers[self.active_layer][gy][gx] = cell

    def _paint_multi(self, gx, gy):
        """Pinta o bloco multi-seleção com canto superior-esquerdo em (gx, gy)."""
        if not self._multi_cells:
            return
        for entry in self._multi_cells:
            tx = gx + entry["dc"]
            ty = gy + entry["dl"]
            cell = make_cell(entry["s"], entry["c"], entry["l"])
            if self._inb(tx, ty):
                self.layers[self.active_layer][ty][tx] = cell

    def _fill(self, gx, gy, new_cell):
        if not self._inb(gx, gy): return
        layer = self.layers[self.active_layer]
        old   = layer[gy][gx]
        if old == new_cell: return
        self._push()
        stack, visited = [(gx, gy)], set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited or not self._inb(cx, cy): continue
            if layer[cy][cx] != old: continue
            visited.add((cx, cy))
            layer[cy][cx] = new_cell
            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                stack.append((cx+dx, cy+dy))

    def _clear_layer(self, idx):
        self._push()
        self.layers[idx] = [[None]*self.map_cols for _ in range(self.map_rows)]

    def _clear_all(self):
        self._push()
        self.layers = [[[None]*self.map_cols for _ in range(self.map_rows)]
                       for _ in range(self.NUM_LAYERS)]

    def _resize(self, nc, nr):
        new_layers = []
        for layer in self.layers:
            nl = []
            for gy in range(nr):
                if gy < len(layer):
                    old = layer[gy]
                    nl.append([old[gx] if gx < len(old) else None
                               for gx in range(nc)])
                else:
                    nl.append([None] * nc)
            new_layers.append(nl)
        self.layers   = new_layers
        self.map_cols = nc
        self.map_rows = nr

    # ── Zoom ───────────────────────────────────────────────────────────────────
    def _apply_zoom(self, dy, mx, my):
        factor   = 1.0 + ZOOM_SPEED * dy
        new_zoom = clamp(self.zoom * factor, ZOOM_MIN, ZOOM_MAX)
        if abs(new_zoom - self.zoom) < 0.001: return
        ratio      = new_zoom / self.zoom
        self.cam_x = mx - ratio * (mx - self.cam_x)
        self.cam_y = my - ratio * (my - self.cam_y)
        self.zoom  = new_zoom
        self._tcache.clear()

    # ── Salvar / Carregar ──────────────────────────────────────────────────────
    def _dialog_new(self):
        dlg    = NewMapDialog(self.screen, self.font, self.font_sm,
                              self.font_xs, self.map_cols,
                              self.map_rows, self.map_name)
        result = dlg.run()
        if result:
            self._push()
            self.map_name = result["nome"]
            self._resize(result["cols"], result["rows"])
            self._tcache.clear()
            self.status_msg = (f"Mapa '{self.map_name}' "
                               f"{result['cols']}×{result['rows']} criado.")

    def _dialog_save(self):
        root = tk.Tk(); root.withdraw()
        name = simpledialog.askstring(
            "Salvar", "Nome do mapa:", initialvalue=self.map_name)
        slug = (name or self.map_name).lower().replace(" ", "_")
        path = filedialog.asksaveasfilename(
            title="Salvar mapa JSON",
            defaultextension=".json",
            filetypes=[("JSON","*.json")],
            initialfile=f"mapa_{slug}.json")
        root.destroy()
        if not path: return
        self.map_name = name or self.map_name
        self._save(path)

    def _save(self, path):
        # Detecta apenas conflitos semânticos reais (não visuais)
        self._sem_conflicts = self.registry.find_semantic_conflicts()
        if self._sem_conflicts:
            ids = list(self._sem_conflicts.keys())
            self.status_msg = (
                f"AVISO: {len(ids)} IDs com props inconsistentes: {ids[:5]}"
                " — corrija antes de usar no jogo.")
        else:
            self._sem_conflicts = {}

        data = {
            "nome":          self.map_name,
            "cols":          self.map_cols,
            "rows":          self.map_rows,
            "tile_size":     TILE_SIZE,
            "spritesheets":  self.mgr.names,
            "layers":        self.layers,
            "tile_registry": self.registry.to_dict(),
            "itens_custom":  self.panel.items_panel.to_dict(),
            "npc_sprites":   self.panel.npc_panel.to_dict(),
            "item_sprites":  self.panel.item_sprites_panel.to_dict(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Exporta tile_definitions.json ao lado do mapa
        base = os.path.splitext(path)[0]
        self.registry.export_tile_definitions(base + "_tile_definitions.json")

        if not self._sem_conflicts:
            self.status_msg = (
                f"Salvo: {os.path.basename(path)}"
                f"  +  {os.path.basename(base)}_tile_definitions.json")

    def _dialog_load(self):
        root = tk.Tk(); root.withdraw()
        path = filedialog.askopenfilename(
            title="Abrir mapa JSON",
            filetypes=[("JSON","*.json"),("Todos","*.*")])
        root.destroy()
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._push()
            self.map_name = data.get("nome", "mapa")
            self.map_cols = data["cols"]
            self.map_rows = data["rows"]

            base_dir   = os.path.dirname(path)
            here       = os.path.dirname(os.path.abspath(__file__))
            old_sheets = data.get("spritesheets", [])
            n2i        = {}
            for name in old_sheets:
                for d in [base_dir, here]:
                    full = os.path.join(d, name)
                    if os.path.exists(full):
                        n2i[name] = self.mgr.add(full); break

            self.layers = []
            for layer in data.get("layers", []):
                nl = []
                for row in layer:
                    nr_row = []
                    for cell in row:
                        if cell is None:
                            nr_row.append(None)
                        else:
                            old_name = (old_sheets[cell["s"]]
                                        if cell["s"] < len(old_sheets) else "")
                            nr_row.append({
                                "s": n2i.get(old_name, 0),
                                "c": cell["c"],
                                "l": cell["l"],
                            })
                    nl.append(nr_row)
                self.layers.append(nl)

            while len(self.layers) < self.NUM_LAYERS:
                self.layers.append(
                    [[None]*self.map_cols for _ in range(self.map_rows)])

            if "tile_registry" in data:
                self.registry.from_dict(data["tile_registry"])
                n = len(self.registry._props)
                self.status_msg = (
                    f"Carregado: {os.path.basename(path)}  ({n} entradas)")
            else:
                self.status_msg = (
                    f"Carregado: {os.path.basename(path)} (JSON antigo)")

            # ── Carrega Itens ─────────────────────────────────────────
            if "itens_custom" in data:
                self.panel.items_panel.from_dict(data["itens_custom"])

            # ── Carrega NPC Sprites ───────────────────────────────────
            if "npc_sprites" in data:
                self.panel.npc_panel.from_dict(data["npc_sprites"])
            if "item_sprites" in data:
                self.panel.item_sprites_panel.from_dict(data["item_sprites"])


            self._tcache.clear()
            self.panel._ss_cache.clear()
            if self.mgr.count() > 0:
                self.panel.open_sheet(0)

        except Exception as e:
            self.status_msg = f"Erro ao carregar: {e}"

    def _dialog_load_tiledefs(self):
        root = tk.Tk(); root.withdraw()
        path = filedialog.askopenfilename(
            title="Carregar tile_definitions.json",
            filetypes=[("JSON","*.json"),("Todos","*.*")])
        root.destroy()
        if not path: return
        warns = self.registry.load_tile_definitions(path)
        n = len(self.registry._props)
        self.status_msg = f"tile_definitions carregado → {n} entradas."
        for w in warns: print("[WARN]", w)

    # ── Render ─────────────────────────────────────────────────────────────────
    def _draw_bg(self):
        sh = self.screen.get_height()
        for gy in range(self.map_rows):
            sy = int(self.cam_y + gy*self.ts)
            if sy + self.ts < TOOLBAR_H or sy > sh: continue
            for gx in range(self.map_cols):
                sx = int(self.cam_x + gx*self.ts)
                if sx + self.ts < 0 or sx > self._aw(): continue
                c = GRID_A if (gx+gy)%2 == 0 else GRID_B
                pygame.draw.rect(self.screen, c,
                                 (sx, sy, round(self.ts), round(self.ts)))

    def _draw_layers(self):
        sh = self.screen.get_height()
        for li in range(self.NUM_LAYERS):
            layer     = self.layers[li]
            is_active = li == self.active_layer
            for gy in range(self.map_rows):
                sy = self.cam_y + gy*self.ts
                if sy + self.ts < TOOLBAR_H or sy > sh: continue
                for gx in range(self.map_cols):
                    sx = self.cam_x + gx*self.ts
                    if sx + self.ts < 0 or sx > self._aw(): continue
                    cell = layer[gy][gx]
                    if cell is None: continue
                    # ── Fundo automático para tiles de planta ─────────────────
                    # Tiles marcados como planta=True são transparentes no sprite;
                    # o jogo mostra terra_arada ou terra_molhada por baixo.
                    # No editor, desenhamos uma cor indicativa (marrom escuro) para
                    # que o tile de planta não apareça flutuando sobre o xadrez.
                    sn_cell = self.mgr.names[cell["s"]] if cell["s"] < len(self.mgr.names) else ""
                    cell_props = self.registry.get(sn_cell, cell["c"], cell["l"])
                    eh_planta = cell_props and cell_props.get("planta", False)
                    if eh_planta:
                        # Procura o tile de terra_arada no layer 0 (chão) da mesma posição,
                        # ou usa uma cor sólida marrom como indicativo visual.
                        chao_cell = self.layers[0][gy][gx] if li > 0 else None
                        fundo_surf = self._tile_surf(chao_cell) if chao_cell else None
                        if fundo_surf is None:
                            # Sem chão definido — pinta retângulo marrom (terra arada)
                            ts_px = round(self.ts)
                            fundo_surf = pygame.Surface((ts_px, ts_px), pygame.SRCALPHA)
                            fundo_surf.fill((101, 67, 33))   # marrom terra arada
                        if is_active:
                            self.screen.blit(fundo_surf, (int(sx), int(sy)))
                        else:
                            dim = fundo_surf.copy()
                            ov  = pygame.Surface(dim.get_size(), pygame.SRCALPHA)
                            ov.fill((0,0,0,130)); dim.blit(ov,(0,0))
                            self.screen.blit(dim, (int(sx), int(sy)))
                    # ─────────────────────────────────────────────────────────
                    ts_surf = self._tile_surf(cell)
                    if ts_surf is None: continue
                    if not is_active:
                        dim = ts_surf.copy()
                        ov  = pygame.Surface(dim.get_size(), pygame.SRCALPHA)
                        ov.fill((0,0,0,130)); dim.blit(ov,(0,0))
                        self.screen.blit(dim, (int(sx), int(sy)))
                    else:
                        self.screen.blit(ts_surf, (int(sx), int(sy)))
                        if self.show_grid:
                            sn    = self.mgr.names[cell["s"]]
                            props = self.registry.get(sn, cell["c"], cell["l"])
                            if props and props.get("solid"):
                                ov = pygame.Surface(
                                    (round(self.ts), round(self.ts)),
                                    pygame.SRCALPHA)
                                ov.fill((255,60,60,40))
                                self.screen.blit(ov, (int(sx), int(sy)))

    def _draw_grid(self):
        if not self.show_grid or self.zoom < 1.0: return
        aw = self._aw()
        sh = self.screen.get_height()
        for gy in range(self.map_rows + 1):
            y  = int(self.cam_y + gy*self.ts)
            x0 = max(0, int(self.cam_x))
            x1 = min(aw, int(self.cam_x + self.map_cols*self.ts))
            if TOOLBAR_H <= y <= sh:
                pygame.draw.line(self.screen, (28,32,52), (x0,y),(x1,y))
        for gx in range(self.map_cols + 1):
            x  = int(self.cam_x + gx*self.ts)
            y0 = max(TOOLBAR_H, int(self.cam_y))
            y1 = min(sh, int(self.cam_y + self.map_rows*self.ts))
            if 0 <= x <= aw:
                pygame.draw.line(self.screen, (28,32,52), (x,y0),(x,y1))
        pygame.draw.rect(
            self.screen, LAYER_COLORS[self.active_layer],
            (int(self.cam_x), int(self.cam_y),
             int(self.map_cols*self.ts), int(self.map_rows*self.ts)), 2)

    def _draw_cursor(self, mpos):
        mx, my = mpos
        ma = self._map_area()
        if not (0 <= mx < self._aw() and ma.y <= my < self.screen.get_height()):
            return
        gx, gy = self._s2g(mx, my)
        if not self._inb(gx, gy): return
        sx, sy = self._g2s(gx, gy)
        ts = round(self.ts)
        lc = LAYER_COLORS[self.active_layer]

        if self.tool == "erase":
            pygame.draw.rect(self.screen, SEL_C, (int(sx), int(sy), ts, ts), 2)
        elif self._multi_cells and self.tool not in ("erase", "fill", "pan"):
            # Mostra ghost de todos os tiles do bloco multi-seleção
            for entry in self._multi_cells:
                tx = gx + entry["dc"]
                ty = gy + entry["dl"]
                if not self._inb(tx, ty): continue
                esx, esy = self._g2s(tx, ty)
                cell = make_cell(entry["s"], entry["c"], entry["l"])
                ghost = self._tile_surf(cell)
                if ghost:
                    g2 = ghost.copy(); g2.set_alpha(140)
                    self.screen.blit(g2, (int(esx), int(esy)))
                pygame.draw.rect(self.screen, lc, (int(esx), int(esy), ts, ts), 1)
            # Borda externa do bloco
            multi_w = max((e["dc"] for e in self._multi_cells), default=0) + 1
            multi_h = max((e["dl"] for e in self._multi_cells), default=0) + 1
            pygame.draw.rect(self.screen, SEL_C,
                             (int(sx), int(sy), ts*multi_w, ts*multi_h), 2)
        else:
            cell = self.panel.selected_cell()
            if self.tool != "fill" and cell:
                ghost = self._tile_surf(cell)
                if ghost:
                    g2 = ghost.copy(); g2.set_alpha(150)
                    self.screen.blit(g2, (int(sx), int(sy)))
            pygame.draw.rect(self.screen, lc, (int(sx), int(sy), ts, ts), 2)

        cur = self.layers[self.active_layer][gy][gx]
        if cur:
            sn    = self.mgr.names[cur["s"]]
            props = self.registry.get(sn, cur["c"], cur["l"])
            tid   = props.get("id","?") if props else "?"
            nome  = props.get("nome","") if props else ""
            info  = (f"({gx},{gy}) {sn} c={cur['c']} l={cur['l']} id={tid}"
                     + (f' "{nome}"' if nome else ""))
        else:
            info = f"({gx},{gy}) vazio"
        txt(self.screen, info, mx + 14, my - 18, self.font_xs, ACCENT2)

    def _draw_toolbar(self):
        aw  = self._aw()
        pygame.draw.rect(self.screen, HDR_BG, (0, 0, aw, TOOLBAR_H))
        pygame.draw.line(self.screen, PANEL_SEP,
                         (0, TOOLBAR_H), (aw, TOOLBAR_H), 1)

        self._tb_btns = {}  # name → rect (rebuilt each frame)

        # ── Linha 1 (y=4): Ferramentas ────────────────────────────────────────
        tools = [("draw","Pintar"),("erase","Borracha"),("fill","Preencher"),("pan","Pan")]
        x = 8
        for name, lbl in tools:
            active = self.tool == name
            col    = LAYER_COLORS[self.active_layer] if active else BTN_BG
            btn    = pygame.Rect(x, 4, 66, 22)
            self._tb_btns[f"tool_{name}"] = btn
            rrect(self.screen, col, btn, rad=4)
            txt(self.screen, lbl, btn.centerx, btn.y+5,
                self.font_xs, BTN_ON_T if active else TEXT, "center")
            x += 70

        x += 6
        pygame.draw.line(self.screen, PANEL_SEP, (x, 5), (x, 26), 1)
        x += 8

        # ── Linha 1 (continuação): Ações ─────────────────────────────────────
        actions = [("undo","↩"), ("redo","↪"), ("grid","Grade"),
                   ("new","Novo"), ("save","Salvar"), ("load","Abrir"), ("tiledefs","TileDefs"),
                   ("importpng","+ PNG")]
        for name, lbl in actions:
            active = (name == "grid" and self.show_grid)
            col    = ACCENT if active else BTN_BG
            w_btn  = 54 if len(lbl) < 7 else 68
            btn    = pygame.Rect(x, 4, w_btn, 22)
            self._tb_btns[f"act_{name}"] = btn
            rrect(self.screen, col, btn, rad=4)
            txt(self.screen, lbl, btn.centerx, btn.y+5,
                self.font_xs, BTN_ON_T if active else TEXT, "center")
            x += w_btn + 4

        # ── Linha 2 (y=29): Camadas ───────────────────────────────────────────
        x2 = 8
        for i in range(3):
            lc     = LAYER_COLORS[i]
            active = i == self.active_layer
            btn    = pygame.Rect(x2, 29, 76, 20)
            self._tb_btns[f"layer_{i}"] = btn
            rrect(self.screen, lc if active else BTN_BG, btn, rad=3,
                  bw=0 if active else 1, bc=lc)
            txt(self.screen, LAYER_NAMES[i], btn.centerx, btn.y+4,
                self.font_xs, BTN_ON_T if active else lc, "center")
            x2 += 80
        # Info mapa
        reg_n  = len(self.registry._props)
        multi  = len(self._multi_cells)
        ms_str = f"  ■ {multi} tiles selecionados" if multi > 1 else ""
        txt(self.screen,
            f"  {self.map_name}  {self.map_cols}×{self.map_rows}"
            f"  zoom:{self.zoom:.1f}×  reg:{reg_n}{ms_str}",
            x2 + 4, 31, self.font_xs, DIM)

    def _draw_layer_indicator(self):
        sh  = self.screen.get_height()
        lc  = LAYER_COLORS[self.active_layer]
        box = pygame.Rect(8, sh - 54, 180, 24)
        rrect(self.screen, (16,18,30), box, rad=5, bw=2, bc=lc)
        txt(self.screen, f"Camada  {LAYER_NAMES[self.active_layer]}",
            box.x+8, box.y+6, self.font_xs, lc)
        for i in range(3):
            bx, by = 8 + i*62, sh - 26
            ac = i == self.active_layer
            rrect(self.screen,
                  LAYER_COLORS[i] if ac else BTN_BG,
                  pygame.Rect(bx, by, 56, 18), rad=3)
            txt(self.screen, LAYER_NAMES[i], bx+4, by+4,
                self.font_xs, BTN_ON_T if ac else LAYER_COLORS[i])

    def _draw_statusbar(self):
        aw = self._aw()
        sh = self.screen.get_height()
        y  = sh - 26
        pygame.draw.rect(self.screen, HDR_BG, (0, y, aw, 26))
        pygame.draw.line(self.screen, PANEL_SEP, (0,y),(aw,y),1)
        txt(self.screen, self.status_msg, 196, y+6, self.font_xs, DIM)
        txt(self.screen,
            f"Undo:{len(self.history)}  Redo:{len(self.redo_stack)}",
            aw-8, y+6, self.font_xs, DIM, "right")

    # ── Loop principal ─────────────────────────────────────────────────────────
    def run(self):
        clock  = pygame.time.Clock()

        while True:
            mpos = pygame.mouse.get_pos()
            mods = pygame.key.get_mods()
            ma   = self._map_area()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

                consumed = self.panel.handle_event(event, mpos, self.font_xs)

                # ── Toolbar: clique nos botões ─────────────────────────────────
                if (event.type == pygame.MOUSEBUTTONDOWN
                        and event.button == 1
                        and not consumed):
                    tb_btn = None
                    for k, r in self._tb_btns.items():
                        if r.collidepoint(mpos):
                            tb_btn = k; break
                    if tb_btn:
                        consumed = True
                        if tb_btn.startswith("tool_"):
                            self.tool = tb_btn[5:]
                            self.status_msg = f"Ferramenta: {self.tool}"
                        elif tb_btn == "act_undo":
                            self._undo(); self.status_msg = "Desfeito."
                        elif tb_btn == "act_redo":
                            self._redo(); self.status_msg = "Refeito."
                        elif tb_btn == "act_grid":
                            self.show_grid = not self.show_grid
                        elif tb_btn == "act_new":
                            self._dialog_new()
                        elif tb_btn == "act_save":
                            self._dialog_save()
                        elif tb_btn == "act_load":
                            self._dialog_load()
                        elif tb_btn == "act_tiledefs":
                            self._dialog_load_tiledefs()
                        elif tb_btn == "act_importpng":
                            self.panel._add_file_dialog()
                            self.status_msg = "PNG importado."
                        elif tb_btn.startswith("layer_"):
                            self.active_layer = int(tb_btn[6:])
                # ── Teclado  (atalhos globais todos com Ctrl) ─────────────────
                if event.type == pygame.KEYDOWN and not consumed:
                    ctrl = bool(mods & pygame.KMOD_CTRL)
                    if ctrl and event.key == pygame.K_z:
                        self._undo(); self.status_msg = "Desfeito."
                    elif ctrl and event.key == pygame.K_y:
                        self._redo(); self.status_msg = "Refeito."
                    elif ctrl and event.key == pygame.K_s:
                        self._dialog_save()
                    elif ctrl and event.key == pygame.K_l:
                        self._dialog_load()
                    elif ctrl and event.key == pygame.K_n:
                        self._dialog_new()
                    elif ctrl and event.key == pygame.K_t:
                        self._dialog_load_tiledefs()
                    elif ctrl and event.key == pygame.K_i:
                        self.panel._add_file_dialog()
                        self.status_msg = "PNG importado via Ctrl+I."
                    elif ctrl and event.key == pygame.K_f:
                        self.tool = "fill";  self.status_msg = "Fill."
                    elif ctrl and event.key == pygame.K_e:
                        self.tool = "erase"; self.status_msg = "Borracha."
                    elif ctrl and event.key == pygame.K_d:
                        self.tool = "draw";  self.status_msg = "Desenhar."
                    elif ctrl and event.key == pygame.K_g:
                        self.show_grid = not self.show_grid
                    elif ctrl and event.key == pygame.K_TAB:
                        n_tabs = len(self.panel.TABS)
                        self.panel.active_tab = (self.panel.active_tab + 1) % n_tabs
                        # Fecha edição de campo ao trocar de aba
                        self.panel.items_panel._commit()
                    elif event.key == pygame.K_DELETE:
                        if ctrl:
                            self._clear_all()
                            self.status_msg = "Tudo limpo."
                        else:
                            self._clear_layer(self.active_layer)
                            self.status_msg = f"Camada {self.active_layer} limpa."
                    elif ctrl and event.key == pygame.K_COMMA:
                        self.active_layer = (self.active_layer-1) % self.NUM_LAYERS
                    elif ctrl and event.key == pygame.K_PERIOD:
                        self.active_layer = (self.active_layer+1) % self.NUM_LAYERS
                    elif ctrl and event.key == pygame.K_1: self.active_layer = 0
                    elif ctrl and event.key == pygame.K_2: self.active_layer = 1
                    elif ctrl and event.key == pygame.K_3: self.active_layer = 2
                    elif ctrl and event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                        shift = bool(mods & pygame.KMOD_SHIFT)
                        if shift:
                            sw2 = self.screen.get_width()  // 2
                            sh2 = self.screen.get_height() // 2
                            self._apply_zoom(4, sw2, sh2)
                            self.status_msg = f"Zoom +  ({self.zoom:.1f}×)"
                    elif ctrl and event.key == pygame.K_MINUS:
                        shift = bool(mods & pygame.KMOD_SHIFT)
                        if shift:
                            sw2 = self.screen.get_width()  // 2
                            sh2 = self.screen.get_height() // 2
                            self._apply_zoom(-4, sw2, sh2)
                            self.status_msg = f"Zoom -  ({self.zoom:.1f}×)"
                    # Ctrl+Setas = pan da câmera do mapa
                    # (quando aba Sheet estiver ativa, o RightPanel consome
                    #  esses atalhos para mover o viewer — consumed será True)
                    elif ctrl and event.key == pygame.K_LEFT:
                        self.cam_x += max(16, int(TILE_SIZE * self.zoom * 3))
                        self.status_msg = "Pan ←"
                    elif ctrl and event.key == pygame.K_RIGHT:
                        self.cam_x -= max(16, int(TILE_SIZE * self.zoom * 3))
                        self.status_msg = "Pan →"
                    elif ctrl and event.key == pygame.K_UP:
                        self.cam_y += max(16, int(TILE_SIZE * self.zoom * 3))
                        self.status_msg = "Pan ↑"
                    elif ctrl and event.key == pygame.K_DOWN:
                        self.cam_y -= max(16, int(TILE_SIZE * self.zoom * 3))
                        self.status_msg = "Pan ↓"
                    elif event.key == pygame.K_SPACE:
                        # Espaço sozinho (sem Ctrl) = pan
                        self._space_pan = True
                        self._sp_start  = mpos
                        self._sp_cam    = (self.cam_x, self.cam_y)

                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_SPACE:
                        self._space_pan = False

                if not consumed:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        in_map = (ma.collidepoint(mpos)
                                  and mpos[0] < self._aw())
                        if in_map:
                            if event.button == 1:
                                gx, gy = self._s2g(*mpos)
                                if self.tool == "fill":
                                    cell = self.panel.selected_cell()
                                    if cell and self._inb(gx, gy):
                                        self._fill(gx, gy, cell)
                                elif self.tool == "erase":
                                    self._push(); self.drawing = True
                                    self._paint(gx, gy, None)
                                    self.last_painted = (gx, gy)
                                else:
                                    self._push(); self.drawing = True
                                    if self._multi_cells:
                                        self._paint_multi(gx, gy)
                                    else:
                                        self._paint(gx, gy, self.panel.selected_cell())
                                    self.last_painted = (gx, gy)

                            elif event.button == 3:
                                # RMB no mapa = apagar tile específico
                                self._push(); self.erasing = True
                                gx, gy = self._s2g(*mpos)
                                self._paint(gx, gy, None)
                                self.last_painted = (gx, gy)
                            elif event.button == 2:
                                self.panning   = True
                                self.pan_start = mpos
                                self.cam_start = (self.cam_x, self.cam_y)

                    if event.type == pygame.MOUSEBUTTONUP:
                        self.drawing = self.erasing = self.panning = False
                        self.last_painted = None

                    if event.type == pygame.MOUSEMOTION:
                        # Pan via Espaço
                        if self._space_pan:
                            self.cam_x = self._sp_cam[0] + mpos[0] - self._sp_start[0]
                            self.cam_y = self._sp_cam[1] + mpos[1] - self._sp_start[1]

                        in_map = (ma.collidepoint(mpos)
                                  and mpos[0] < self._aw())
                        if in_map and (self.drawing or self.erasing):
                            gx, gy = self._s2g(*mpos)
                            if (gx, gy) != self.last_painted:
                                if self.erasing or self.tool == "erase":
                                    self._paint(gx, gy, None)
                                elif self._multi_cells:
                                    self._paint_multi(gx, gy)
                                else:
                                    self._paint(gx, gy,
                                                self.panel.selected_cell())
                                self.last_painted = (gx, gy)
                        if self.panning:
                            self.cam_x = (self.cam_start[0]
                                          + mpos[0] - self.pan_start[0])
                            self.cam_y = (self.cam_start[1]
                                          + mpos[1] - self.pan_start[1])

                    if event.type == pygame.MOUSEWHEEL:
                        if (ma.collidepoint(mpos)
                                and mpos[0] < self._aw()):
                            self._apply_zoom(event.y, mpos[0], mpos[1])

                if event.type == pygame.VIDEORESIZE:
                    sw, sh = event.w, event.h
                    self.panel.rect = pygame.Rect(sw-PANEL_W, 0, PANEL_W, sh)

            # ── Render ────────────────────────────────────────────────────────
            sw = self.screen.get_width()
            sh = self.screen.get_height()
            self.panel.rect = pygame.Rect(sw-PANEL_W, 0, PANEL_W, sh)

            self.screen.fill(BG)
            clip = pygame.Rect(0, TOOLBAR_H, self._aw(), sh-TOOLBAR_H)
            self.screen.set_clip(clip)
            self._draw_bg()
            self._draw_layers()
            self._draw_grid()
            self._draw_cursor(mpos)
            self.screen.set_clip(None)
            self._draw_toolbar()
            self._draw_layer_indicator()
            self._draw_statusbar()
            self.panel.draw(self.screen, self.font, self.font_sm,
                            self.font_xs, self.active_layer)

            pygame.display.flip()
            clock.tick(60)


if __name__ == "__main__":
    MapEditor().run()