#python3 setup.py build_ext --inplace
#cp engine*.so /home/joao/Documentos/hervest-moon/game/

from libc.stdlib cimport malloc, free
from libc.string cimport memset

cdef extern from "Engine.h":

    int ENGINE_MAX_SPRITES
    int ENGINE_MAX_OBJECTS
    int ENGINE_MAX_KEYS

    ctypedef struct SpriteData:
        int width
        int height
        int loaded

    ctypedef struct GameObject:
        int x, y
        int sprite_id
        unsigned long color
        int width, height
        int active
        int tile_x, tile_y
        int tile_w, tile_h
        int use_tile
        int flip_h, flip_v

    ctypedef struct Engine:
        int win_w, win_h
        int depth
        int scale
        int render_w, render_h
        int sprite_count
        int object_count
        int running
        unsigned long bg_color
        int fullscreen
        int saved_win_w, saved_win_h
        int saved_render_w, saved_render_h

    int  engine_init(Engine *e, int width, int height,
                     const char *title, int scale)
    void engine_destroy(Engine *e)
    void engine_set_background(Engine *e, int r, int g, int b)
    void engine_toggle_fullscreen(Engine *e)

    int engine_load_sprite(Engine *e, const char *path)
    int engine_load_sprite_region(Engine *e, const char *path,
                                  int x, int y, int w, int h)

    int  engine_add_object(Engine *e, int x, int y, int sprite_id,
                           int width, int height, int r, int g, int b)
    int  engine_add_tile_object(Engine *e, int x, int y, int sprite_id,
                                int tile_x, int tile_y,
                                int tile_w, int tile_h)
    void engine_move_object(Engine *e, int oid, int dx, int dy)
    void engine_set_object_pos(Engine *e, int oid, int x, int y)
    void engine_set_object_sprite(Engine *e, int oid, int sprite_id)
    void engine_get_object_pos(Engine *e, int oid, int *out_x, int *out_y)
    void engine_set_object_tile(Engine *e, int oid, int tile_x, int tile_y)
    void engine_set_object_flip(Engine *e, int oid, int flip_h, int flip_v)
    void engine_remove_object(Engine *e, int oid)

    void engine_clear(Engine *e)
    void engine_draw(Engine *e)
    void engine_draw_rect(Engine *e, int x, int y, int w, int h,
                          int r, int g, int b)
    void engine_draw_overlay(Engine *e, int x, int y, int w, int h,
                             int r, int g, int b, float alpha)
    void engine_flush(Engine *e)
    void engine_draw_rain(Engine *e,
                          int screen_w, int screen_h,
                          int frame,
                          const int *gotas_x, const int *gotas_y, int n_gotas,
                          int gota_w, int gota_h)
    void engine_draw_night(Engine *e,
                           int screen_w, int screen_h,
                           float intensidade, int offset)
    void engine_present(Engine *e)

    void engine_draw_tilemap(Engine *e,
                             const int *tilemap,
                             int tile_rows, int tile_cols,
                             int sprite_id,
                             int tile_w, int tile_h,
                             int offset_x, int offset_y)
    void engine_draw_sprite_part(Engine *e, int sprite_id,
                                 int x, int y,
                                 int src_x, int src_y,
                                 int src_w, int src_h)
    void engine_draw_sprite_part_inverted(Engine *e, int sprite_id,
                                          int x, int y,
                                          int src_x, int src_y,
                                          int src_w, int src_h)

    void engine_draw_text(Engine *e, int x, int y, const char *text,
                          int font_sid, int font_w, int font_h,
                          int chars_per_row, int ascii_offset,
                          int line_spacing)
    void engine_draw_box(Engine *e, int x, int y, int box_w, int box_h,
                         int box_sid, int tile_w, int tile_h)
    void engine_draw_text_box(Engine *e,
                              int x, int y, int box_w, int box_h,
                              const char *title, const char *content,
                              int box_sid, int box_tw, int box_th,
                              int font_sid, int font_w, int font_h,
                              int chars_per_row, int ascii_offset,
                              int line_spacing)

    void engine_poll_events(Engine *e)
    int  engine_key_down(Engine *e, const char *key)
    int  engine_key_pressed(Engine *e, const char *key)
    int  engine_key_released(Engine *e, const char *key)

    int  engine_check_collision(Engine *e, int oid1, int oid2)

    void engine_cap_fps(Engine *e, int fps_target)


cdef class Video:
    """
    Wrapper Python para o Engine C (Engine.h / Engine.c).

    Uso:
        v = Video(320, 180, b"RPG Classico", scale=3)
    """

    cdef Engine _eng

    @property
    def running(self):
        return bool(self._eng.running)

    def __cinit__(self, int width, int height, title, int scale=1):
        cdef bytes btitle
        if isinstance(title, str):
            btitle = title.encode('utf-8')
        else:
            btitle = title
        memset(&self._eng, 0, sizeof(Engine))
        if not engine_init(&self._eng, width, height, btitle, scale):
            raise RuntimeError("engine_init() falhou – verifique display X11 e libpng")

    def __dealloc__(self):
        engine_destroy(&self._eng)

    def set_background(self, int r, int g, int b):
        engine_set_background(&self._eng, r, g, b)

    def toggle_fullscreen(self):
        """Alterna entre janela e tela cheia pixel-perfect.

        Em tela cheia, calcula o maior scale inteiro que cabe no monitor
        e centraliza com letterbox preto — sprites sempre nítidos (GL_NEAREST).
        Tecla sugerida: F (mapeada em game.py via key_pressed(b"f")).
        """
        engine_toggle_fullscreen(&self._eng)

    @property
    def fullscreen(self):
        return bool(self._eng.fullscreen)

    @property
    def render_w(self):
        return self._eng.render_w

    @property
    def render_h(self):
        return self._eng.render_h

    def load_sprite(self, path) -> int:
        cdef bytes bpath = path if isinstance(path, bytes) else path.encode('utf-8')
        cdef int sid = engine_load_sprite(&self._eng, bpath)
        if sid < 0:
            raise RuntimeError(f"Falha ao carregar sprite: {path}")
        return sid

    def load_sprite_region(self, path, int x, int y, int w, int h) -> int:
        cdef bytes bpath = path if isinstance(path, bytes) else path.encode('utf-8')
        cdef int sid = engine_load_sprite_region(&self._eng, bpath, x, y, w, h)
        if sid < 0:
            raise RuntimeError(f"Falha ao carregar região de sprite: {path}")
        return sid

    def add_object(self, int x, int y, int sprite_id=-1,
                   int width=0, int height=0,
                   int r=255, int g=255, int b=255) -> int:
        cdef int oid = engine_add_object(&self._eng, x, y, sprite_id,
                                         width, height, r, g, b)
        if oid < 0:
            raise RuntimeError("engine_add_object() falhou – limite de objetos atingido?")
        return oid

    def add_tile_object(self, int x, int y, int sprite_id,
                        int tile_x, int tile_y,
                        int tile_w, int tile_h) -> int:
        cdef int oid = engine_add_tile_object(&self._eng, x, y, sprite_id,
                                               tile_x, tile_y, tile_w, tile_h)
        if oid < 0:
            raise RuntimeError("engine_add_tile_object() falhou")
        return oid

    def move_object(self, int oid, int dx, int dy):
        engine_move_object(&self._eng, oid, dx, dy)

    def set_object_pos(self, int oid, int x, int y):
        engine_set_object_pos(&self._eng, oid, x, y)

    def set_object_sprite(self, int oid, int sprite_id):
        engine_set_object_sprite(&self._eng, oid, sprite_id)

    def get_object_pos(self, int oid):
        cdef int ox = 0, oy = 0
        engine_get_object_pos(&self._eng, oid, &ox, &oy)
        return (ox, oy)

    def set_object_tile(self, int oid, int tile_x, int tile_y):
        engine_set_object_tile(&self._eng, oid, tile_x, tile_y)

    def set_object_flip(self, int oid, int flip_h, int flip_v):
        engine_set_object_flip(&self._eng, oid, flip_h, flip_v)

    def remove_object(self, int oid):
        engine_remove_object(&self._eng, oid)

    def clear(self):
        engine_clear(&self._eng)

    def draw(self):
        engine_draw(&self._eng)

    def draw_rect(self, int x, int y, int w, int h,
                  int r=255, int g=255, int b=255):
        engine_draw_rect(&self._eng, x, y, w, h, r, g, b)

    def draw_overlay(self, int x, int y, int w, int h,
                     int r, int g, int b, float alpha):
        engine_draw_overlay(&self._eng, x, y, w, h, r, g, b, alpha)

    def flush(self):
        """Força o flush do batch acumulado."""
        engine_flush(&self._eng)

    def draw_rain(self, int screen_w, int screen_h,
                  int frame,
                  gotas_x_list, gotas_y_list,
                  int gota_w, int gota_h):
        """Desenha chuva completa em C puro — pontilhado + gotas."""
        cdef int n = len(gotas_x_list)
        cdef int *gx = <int *>malloc(n * sizeof(int))
        cdef int *gy = <int *>malloc(n * sizeof(int))
        if not gx or not gy:
            free(gx); free(gy)
            raise MemoryError("draw_rain: malloc falhou")
        try:
            for i in range(n):
                gx[i] = gotas_x_list[i]
                gy[i] = gotas_y_list[i]
            engine_draw_rain(&self._eng, screen_w, screen_h,
                             frame, gx, gy, n, gota_w, gota_h)
        finally:
            free(gx)
            free(gy)

    def draw_night(self, int screen_w, int screen_h,
                   float intensidade, int offset):
        """Escurece a tela em C puro — zero loop Python."""
        engine_draw_night(&self._eng, screen_w, screen_h, intensidade, offset)

    def present(self):
        engine_present(&self._eng)

    def draw_tilemap(self, tilemap_list,
                     int tile_rows, int tile_cols,
                     int sprite_id,
                     int tile_w, int tile_h,
                     int offset_x=0, int offset_y=0):
        cdef int n = tile_rows * tile_cols
        cdef int *buf = <int *>malloc(n * sizeof(int))
        if not buf:
            raise MemoryError("draw_tilemap: malloc falhou")
        try:
            for i in range(n):
                buf[i] = tilemap_list[i]
            engine_draw_tilemap(&self._eng, buf,
                                tile_rows, tile_cols,
                                sprite_id,
                                tile_w, tile_h,
                                offset_x, offset_y)
        finally:
            free(buf)

    def draw_sprite_part(self, int sprite_id,
                         int x, int y,
                         int src_x, int src_y,
                         int src_w, int src_h):
        engine_draw_sprite_part(&self._eng, sprite_id,
                                x, y, src_x, src_y, src_w, src_h)

    def draw_sprite_part_inverted(self, int sprite_id,
                                   int x, int y,
                                   int src_x, int src_y,
                                   int src_w, int src_h):
        """Desenha a região do sprite com cores RGB invertidas (preto↔branco).
        Usado para plantas em terra molhada no sistema P&B."""
        engine_draw_sprite_part_inverted(&self._eng, sprite_id,
                                          x, y, src_x, src_y, src_w, src_h)

    def draw_text(self, int x, int y, text,
                  int font_sid, int font_w=8, int font_h=8,
                  int chars_per_row=16, int ascii_offset=32,
                  int line_spacing=0):
        cdef bytes bt = text if isinstance(text, bytes) else text.encode('latin-1', errors='replace')
        engine_draw_text(&self._eng, x, y, bt,
                         font_sid, font_w, font_h,
                         chars_per_row, ascii_offset, line_spacing)

    def draw_box(self, int x, int y, int box_w, int box_h,
                 int box_sid, int tile_w=8, int tile_h=8):
        engine_draw_box(&self._eng, x, y, box_w, box_h,
                        box_sid, tile_w, tile_h)

    def draw_text_box(self, int x, int y, int box_w, int box_h,
                      title, content,
                      int box_sid, int box_tw=8, int box_th=8,
                      int font_sid=-1, int font_w=8, int font_h=8,
                      int chars_per_row=16, int ascii_offset=32,
                      int line_spacing=0):
        cdef bytes bt = title   if isinstance(title,   bytes) else title.encode('latin-1', errors='replace')
        cdef bytes bc = content if isinstance(content, bytes) else content.encode('latin-1', errors='replace')
        engine_draw_text_box(&self._eng,
                             x, y, box_w, box_h,
                             bt, bc,
                             box_sid, box_tw, box_th,
                             font_sid, font_w, font_h,
                             chars_per_row, ascii_offset, line_spacing)

    def poll_events(self):
        engine_poll_events(&self._eng)

    def key_down(self, key) -> bool:
        cdef bytes bk = key if isinstance(key, bytes) else key.encode('utf-8')
        return bool(engine_key_down(&self._eng, bk))

    def key_pressed(self, key) -> bool:
        cdef bytes bk = key if isinstance(key, bytes) else key.encode('utf-8')
        return bool(engine_key_pressed(&self._eng, bk))

    def key_released(self, key) -> bool:
        cdef bytes bk = key if isinstance(key, bytes) else key.encode('utf-8')
        return bool(engine_key_released(&self._eng, bk))

    def check_collision(self, int oid1, int oid2) -> bool:
        return bool(engine_check_collision(&self._eng, oid1, oid2))

    def cap_fps(self, int fps_target=60):
        """
        Limita o framerate. Chame no fim de cada frame após present().
        Usa nanosleep internamente — não desperdiça CPU.
        """
        engine_cap_fps(&self._eng, fps_target)
