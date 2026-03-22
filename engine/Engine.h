#ifndef ENGINE_H
#define ENGINE_H

/* ============================================================
 * Engine.h — Mini Engine 2D para Linux (OpenGL 2.1 + GLX + libpng)
 *
 * BACKEND OpenGL:
 *   - Sprites como texturas RGBA em VRAM (glTexImage2D)
 *   - Rendering via VBO + batching por textura (1 draw call por textura/frame)
 *   - Projeção ortográfica em pixel-space (0,0 = canto superior esquerdo)
 *   - Alpha blending via GL_SRC_ALPHA / GL_ONE_MINUS_SRC_ALPHA
 *   - Escala feita pela projeção — sem loops de pixel
 *   - engine_draw_overlay: quad semitransparente puro (zero CPU)
 *   - engine_draw_sprite_part_inverted: fragment via glLogicOp XOR
 *   - VSync via glXSwapIntervalEXT (zero CPU no frame sleep)
 *   - Cache de PNG para múltiplos load_sprite_region do mesmo arquivo
 *   - Texture bind tracking: glBindTexture só quando realmente muda
 *   - keys / keys_prev como ponteiros (swap O(1) ao invés de memcpy)
 *
 * Compilar com:
 *   gcc -O2 -o game main.c Engine.c -lX11 -lGL -lpng -lm
 *
 * API 100% compatível com a versão anterior.
 * O engine.pyx NÃO precisa de nenhuma alteração.
 * ============================================================ */

#include <X11/Xlib.h>
#include <X11/keysym.h>
#include <GL/gl.h>
#include <GL/glx.h>
#include <stdint.h>

/* ---- Limites ------------------------------------------------ */
#define ENGINE_MAX_SPRITES   64
#define ENGINE_MAX_OBJECTS   512
#define ENGINE_MAX_KEYS      256

/* ---- Estrutura de sprite (OpenGL) -------------------------- */
typedef struct {
    GLuint texture;   /* ID da textura OpenGL */
    int    width;
    int    height;
    int    loaded;
} SpriteData;

/* ---- Objeto de jogo ---------------------------------------- */
typedef struct {
    int           x, y;
    int           sprite_id;
    unsigned long color;      /* 0x00RRGGBB packed */
    int           width, height;
    int           active;
    int           tile_x, tile_y;
    int           tile_w, tile_h;
    int           use_tile;
    int           flip_h, flip_v;
} GameObject;

/* ---- Contexto principal ------------------------------------ */
typedef struct {
    /* X11 / GLX */
    Display    *display;
    int         screen;
    Window      window;
    GLXContext  glx_ctx;

    int         win_w, win_h;
    int         depth;          /* sempre 24; mantido por compatibilidade */
    int         scale;
    int         render_w, render_h;

    /* Textura branca 1×1 (desenho de rects sólidos e overlay) */
    GLuint      white_tex;

    /* Sprites */
    SpriteData  sprites[ENGINE_MAX_SPRITES];
    int         sprite_count;

    /* Objetos */
    GameObject  objects[ENGINE_MAX_OBJECTS];
    int         object_count;

    /*
     * OTIMIZAÇÃO 5 — keys / keys_prev como ponteiros (swap O(1)).
     * Engine.c mantém dois arrays estáticos e apenas troca os ponteiros
     * a cada frame, evitando o memcpy de 1024 bytes anterior.
     * Para código externo (Cython, main.c), o acesso via e->keys[idx]
     * continua funcionando identicamente.
     */
    int        *keys;
    int        *keys_prev;

    int         running;
    unsigned long bg_color;  /* 0x00RRGGBB packed */

    /* Fullscreen pixel-perfect */
    int         fullscreen;
    int         saved_win_w, saved_win_h;
    int         saved_render_w, saved_render_h;
} Engine;

/* ==============================================================
 * API pública — nomes, argumentos e semântica idênticos à versão anterior
 * ============================================================== */

int  engine_init(Engine *e, int width, int height,
                 const char *title, int scale);
void engine_destroy(Engine *e);

void engine_set_background(Engine *e, int r, int g, int b);

int  engine_load_sprite(Engine *e, const char *path);
int  engine_load_sprite_region(Engine *e, const char *path,
                                int x, int y, int w, int h);

int  engine_add_object(Engine *e, int x, int y, int sprite_id,
                       int width, int height, int r, int g, int b);
int  engine_add_tile_object(Engine *e, int x, int y, int sprite_id,
                             int tile_x, int tile_y,
                             int tile_w, int tile_h);
void engine_move_object(Engine *e, int oid, int dx, int dy);
void engine_set_object_pos(Engine *e, int oid, int x, int y);
void engine_set_object_sprite(Engine *e, int oid, int sprite_id);
void engine_get_object_pos(Engine *e, int oid, int *out_x, int *out_y);
void engine_set_object_tile(Engine *e, int oid, int tile_x, int tile_y);
void engine_set_object_flip(Engine *e, int oid, int flip_h, int flip_v);
void engine_remove_object(Engine *e, int oid);

void engine_clear(Engine *e);
void engine_draw(Engine *e);
void engine_draw_rect(Engine *e, int x, int y, int w, int h,
                      int r, int g, int b);
void engine_draw_overlay(Engine *e, int x, int y, int w, int h,
                          int r, int g, int b, float alpha);
void engine_flush(Engine *e);
void engine_draw_rain(Engine *e,
                      int screen_w, int screen_h,
                      int frame,
                      const int *gotas_x, const int *gotas_y, int n_gotas,
                      int gota_w, int gota_h);
void engine_draw_night(Engine *e,
                       int screen_w, int screen_h,
                       float intensidade, int offset);
void engine_present(Engine *e);

void engine_draw_tilemap(Engine *e,
                          const int *tilemap,
                          int tile_rows, int tile_cols,
                          int sprite_id,
                          int tile_w, int tile_h,
                          int offset_x, int offset_y);
void engine_draw_sprite_part(Engine *e, int sprite_id,
                              int x, int y,
                              int src_x, int src_y,
                              int src_w, int src_h);
void engine_draw_sprite_part_inverted(Engine *e, int sprite_id,
                                       int x, int y,
                                       int src_x, int src_y,
                                       int src_w, int src_h);

void engine_draw_text(Engine *e, int x, int y, const char *text,
                      int font_sid, int font_w, int font_h,
                      int chars_per_row, int ascii_offset,
                      int line_spacing);
void engine_draw_box(Engine *e, int x, int y, int box_w, int box_h,
                     int box_sid, int tile_w, int tile_h);
void engine_draw_text_box(Engine *e,
                           int x, int y, int box_w, int box_h,
                           const char *title, const char *content,
                           int box_sid, int box_tw, int box_th,
                           int font_sid, int font_w, int font_h,
                           int chars_per_row, int ascii_offset,
                           int line_spacing);

void engine_poll_events(Engine *e);
int  engine_key_down(Engine *e, const char *key);
int  engine_key_pressed(Engine *e, const char *key);
int  engine_key_released(Engine *e, const char *key);

int  engine_check_collision(Engine *e, int oid1, int oid2);

void engine_cap_fps(Engine *e, int fps_target);

void engine_toggle_fullscreen(Engine *e);

#endif /* ENGINE_H */