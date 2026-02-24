# engine.pyx — Mini Engine 2D para Linux (X11 + libpng)
# Compile com: python setup.py build_ext --inplace
from libc.stdlib cimport malloc, free, calloc
from libc.string cimport memset, memcpy

# =============================================================================
# DECLARAÇÕES X11
# =============================================================================
cdef extern from "<X11/Xlib.h>":
    ctypedef struct Display
    ctypedef unsigned long Window
    ctypedef unsigned long Colormap
    ctypedef unsigned long Pixmap
    ctypedef unsigned long GC

    ctypedef struct XImage:
        int width
        int height
        int bytes_per_line
        char* data

    ctypedef struct XGCValues:
        pass

    ctypedef struct XEvent:
        int type

    ctypedef struct XKeyEvent:
        int          type
        unsigned int keycode
        unsigned int state

    Display* XOpenDisplay(char* display_name)
    int      XCloseDisplay(Display* display)
    int      DefaultScreen(Display* display)
    int      DefaultDepth(Display* display, int screen)
    Window   RootWindow(Display* display, int screen)
    unsigned long BlackPixel(Display* display, int screen)
    unsigned long WhitePixel(Display* display, int screen)
    Colormap DefaultColormap(Display* display, int screen)

    Window XCreateSimpleWindow(Display* d, Window parent,
                               int x, int y,
                               unsigned int w, unsigned int h,
                               unsigned int border_w,
                               unsigned long border,
                               unsigned long bg)
    int XSelectInput(Display* d, Window w, long mask)
    int XMapWindow(Display* d, Window w)
    int XFlush(Display* d)
    int XPending(Display* d)
    int XNextEvent(Display* d, XEvent* ev)
    int XStoreName(Display* d, Window w, char* name)

    GC  XCreateGC(Display* d, Window w, unsigned long mask, XGCValues* vals)
    int XFreeGC(Display* d, GC gc)
    int XSetForeground(Display* d, GC gc, unsigned long color)
    int XFillRectangle(Display* d, Window w, GC gc,
                       int x, int y,
                       unsigned int width, unsigned int height)
    int XCopyArea(Display* d, Pixmap src, Window dst, GC gc,
                  int src_x, int src_y,
                  unsigned int w, unsigned int h,
                  int dst_x, int dst_y)

    Pixmap XCreatePixmap(Display* d, Window w,
                         unsigned int width, unsigned int height, unsigned int depth)
    int    XFreePixmap(Display* d, Pixmap p)

    XImage* XCreateImage(Display* d, void* visual, unsigned int depth,
                         int fmt, int offset, char* data,
                         unsigned int w, unsigned int h,
                         int bitmap_pad, int bytes_per_line)
    int XPutImage(Display* d, Pixmap px, GC gc, XImage* img,
                  int src_x, int src_y, int dst_x, int dst_y,
                  unsigned int w, unsigned int h)

    void* XDefaultVisual(Display* d, int screen)

    long ExposureMask
    long KeyPressMask
    long KeyReleaseMask
    int  Expose
    int  KeyPress
    int  KeyRelease
    int  ZPixmap

    unsigned int XLookupKeysym(XKeyEvent* ev, int index)
    XImage* XGetImage(Display* d, Pixmap px, int x, int y,
                      unsigned int width, unsigned int height,
                      unsigned long plane_mask, int format)
    Pixmap XCreateBitmapFromData(Display* display, Window d, char* data, unsigned int width, unsigned int height)
    int XSetClipMask(Display* d, GC gc, Pixmap pixmap)
    int XSetClipOrigin(Display* d, GC gc, int clip_x_origin, int clip_y_origin)

# XDestroyImage e' uma MACRO em X11 — wrapper C inline
cdef extern from *:
    """
    #include <X11/Xlib.h>
    #include <X11/Xlibint.h>
    static inline int _engine_destroy_image(XImage* xi) {
        if (xi->obdata != NULL) XFree(xi->obdata);
        if (xi->data != NULL) XFree(xi->data);
        XFree(xi);
        return 1;
    }
    """
    int _engine_destroy_image(XImage* xi)

cdef extern from "<X11/keysym.h>":
    unsigned int XK_Escape
    unsigned int XK_Left
    unsigned int XK_Right
    unsigned int XK_Up
    unsigned int XK_Down
    unsigned int XK_space
    unsigned int XK_Return
    unsigned int XK_a
    unsigned int XK_d
    unsigned int XK_w
    unsigned int XK_s

# =============================================================================
# DECLARAÇÕES LIBPNG
# =============================================================================
cdef extern from "<png.h>":
    ctypedef struct png_struct
    ctypedef struct png_info
    ctypedef unsigned char  png_byte
    ctypedef unsigned char* png_bytep
    ctypedef unsigned char** png_bytepp

    png_struct* png_create_read_struct(char* ver, void* ep, void* eh, void* wh)
    png_info*   png_create_info_struct(png_struct* ps)
    void        png_destroy_read_struct(png_struct** ps, png_info** pi, png_info** ei)
    void        png_init_io(png_struct* ps, void* fp)
    void        png_read_info(png_struct* ps, png_info* pi)
    unsigned int  png_get_image_width(png_struct* ps, png_info* pi)
    unsigned int  png_get_image_height(png_struct* ps, png_info* pi)
    unsigned char png_get_bit_depth(png_struct* ps, png_info* pi)
    unsigned char png_get_color_type(png_struct* ps, png_info* pi)
    void        png_set_strip_16(png_struct* ps)
    void        png_set_palette_to_rgb(png_struct* ps)
    void        png_set_expand_gray_1_2_4_to_8(png_struct* ps)
    void        png_set_tRNS_to_alpha(png_struct* ps)
    void        png_set_filler(png_struct* ps, unsigned int filler, int flags)
    void        png_set_gray_to_rgb(png_struct* ps)
    void        png_set_bgr(png_struct* ps)
    void        png_read_update_info(png_struct* ps, png_info* pi)
    void        png_read_image(png_struct* ps, png_bytepp row_ptrs)
    char* PNG_LIBPNG_VER_STRING

    int PNG_COLOR_TYPE_PALETTE
    int PNG_COLOR_TYPE_GRAY
    int PNG_COLOR_TYPE_GRAY_ALPHA
    int PNG_FILLER_AFTER

cdef extern from "<stdio.h>":
    ctypedef struct FILE
    FILE* fopen(char* path, char* mode)
    int   fclose(FILE* fp)

# =============================================================================
# ESTRUTURAS INTERNAS
# =============================================================================
cdef struct SpriteData:
    Pixmap pixmap
    Pixmap mask
    int    width
    int    height
    int    loaded

cdef struct GameObject:
    int           x
    int           y
    int           sprite_id
    unsigned long color
    int           width
    int           height
    int           active
    int           tile_x
    int           tile_y
    int           tile_w
    int           tile_h
    int           use_tile
    int           flip_h
    int           flip_v

DEF MAX_SPRITES = 64
DEF MAX_OBJECTS = 512
DEF MAX_KEYS    = 256

# =============================================================================
# CLASSE VIDEO
# =============================================================================
cdef class Video:
    cdef Display* display
    cdef int      screen
    cdef Window   window
    cdef GC       gc
    cdef Pixmap   backbuffer
    cdef int      win_w
    cdef int      win_h
    cdef int      depth
    cdef int      scale
    cdef int      render_w
    cdef int      render_h

    cdef SpriteData sprites[MAX_SPRITES]
    cdef int        sprite_count

    cdef GameObject objects[MAX_OBJECTS]
    cdef int        object_count

    cdef int keys[MAX_KEYS]
    cdef int keys_prev[MAX_KEYS]

    cdef public int    running
    cdef unsigned long _bg_color

    def __cinit__(self, int width, int height, bytes title=b"Engine", int scale=1):
        cdef Window root
        cdef XGCValues gcv

        if scale < 1: scale = 1
        if scale > 8: scale = 8

        self.render_w  = width
        self.render_h  = height
        self.scale     = scale
        self.win_w     = width * scale
        self.win_h     = height * scale
        self.running   = 1
        self._bg_color = 0

        memset(self.sprites,   0, sizeof(self.sprites))
        memset(self.objects,   0, sizeof(self.objects))
        memset(self.keys,      0, sizeof(self.keys))
        memset(self.keys_prev, 0, sizeof(self.keys_prev))
        self.sprite_count = 0
        self.object_count = 0

        self.display = XOpenDisplay(NULL)
        if self.display == NULL:
            raise RuntimeError("Nao foi possivel abrir o display X11.")

        self.screen = DefaultScreen(self.display)
        self.depth  = DefaultDepth(self.display, self.screen)
        root = RootWindow(self.display, self.screen)

        self.window = XCreateSimpleWindow(
            self.display, root, 0, 0, self.win_w, self.win_h, 0,
            BlackPixel(self.display, self.screen),
            BlackPixel(self.display, self.screen))

        XStoreName(self.display, self.window, title)
        XSelectInput(self.display, self.window,
                     ExposureMask | KeyPressMask | KeyReleaseMask)
        XMapWindow(self.display, self.window)

        self.gc = XCreateGC(self.display, self.window, 0, &gcv)

        self.backbuffer = XCreatePixmap(
            self.display, self.window, self.render_w, self.render_h, self.depth)

        XFlush(self.display)

    # --- Configuracao ---
    def set_background(self, int r, int g, int b):
        self._bg_color = ((r & 0xFF) << 16) | ((g & 0xFF) << 8) | (b & 0xFF)

    # --- Sprites ---
    def load_sprite(self, bytes path) -> int:
        cdef int sid, mask_bpl, mx, my, m_idx, bit, row_bytes
        cdef unsigned int img_w, img_h, row
        cdef unsigned char bdepth, ctype, alpha
        cdef FILE* fp
        cdef png_struct* ps
        cdef png_info* pi
        cdef char* img_data
        cdef char* mask_data
        cdef png_bytepp rows
        cdef Pixmap mask_pxm, pxm
        cdef XImage* xi
        cdef SpriteData* sp

        if self.sprite_count >= MAX_SPRITES:
            return -1

        sid = self.sprite_count
        sp  = &self.sprites[sid]

        fp = fopen(path, b"rb")
        if fp == NULL:
            import os
            script_dir = os.path.dirname(os.path.abspath(__file__))
            alt_path = os.path.join(script_dir, path.decode()).encode()
            fp = fopen(alt_path, b"rb")
        if fp == NULL:
            return -1

        ps = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL)
        pi = png_create_info_struct(ps)
        png_init_io(ps, fp)
        png_read_info(ps, pi)

        img_w  = png_get_image_width(ps, pi)
        img_h  = png_get_image_height(ps, pi)
        bdepth = png_get_bit_depth(ps, pi)
        ctype  = png_get_color_type(ps, pi)

        if bdepth == 16: png_set_strip_16(ps)
        if ctype == PNG_COLOR_TYPE_PALETTE: png_set_palette_to_rgb(ps)
        if ctype == PNG_COLOR_TYPE_GRAY and bdepth < 8: png_set_expand_gray_1_2_4_to_8(ps)
        if ctype == PNG_COLOR_TYPE_GRAY or ctype == PNG_COLOR_TYPE_GRAY_ALPHA: png_set_gray_to_rgb(ps)
        png_set_tRNS_to_alpha(ps)
        png_set_filler(ps, 0xFF, PNG_FILLER_AFTER)
        png_set_bgr(ps)
        png_read_update_info(ps, pi)

        row_bytes = img_w * 4
        img_data  = <char*>malloc(img_h * row_bytes)
        rows      = <png_bytepp>malloc(img_h * sizeof(png_bytep))
        for row in range(img_h):
            rows[row] = <png_bytep>(img_data + row * row_bytes)

        png_read_image(ps, rows)
        png_destroy_read_struct(&ps, &pi, NULL)
        fclose(fp)
        free(rows)

        # Mascara de transparencia
        mask_bpl  = (img_w + 7) // 8
        mask_data = <char*>calloc(img_h, mask_bpl)
        for my in range(img_h):
            for mx in range(img_w):
                alpha = img_data[(my * img_w + mx) * 4 + 3]
                if alpha > 127:
                    m_idx = my * mask_bpl + (mx // 8)
                    bit   = mx % 8
                    mask_data[m_idx] = mask_data[m_idx] | (1 << bit)

        mask_pxm = XCreateBitmapFromData(self.display, self.window, mask_data, img_w, img_h)
        free(mask_data)

        xi  = XCreateImage(self.display, XDefaultVisual(self.display, self.screen),
                           self.depth, ZPixmap, 0, img_data, img_w, img_h, 32, 0)
        pxm = XCreatePixmap(self.display, self.window, img_w, img_h, self.depth)
        XPutImage(self.display, pxm, self.gc, xi, 0, 0, 0, 0, img_w, img_h)
        _engine_destroy_image(xi)

        sp.pixmap = pxm
        sp.mask   = mask_pxm
        sp.width  = img_w
        sp.height = img_h
        sp.loaded = 1
        self.sprite_count += 1
        return sid

    def load_sprite_region(self, bytes path, int x, int y, int w, int h) -> int:
        """
        Carrega uma regiao especifica de uma imagem PNG como sprite.
        """
        cdef int sid, mask_bpl, mx, my, m_idx, bit
        cdef int row_bytes, region_row_bytes, dest_y, src_y2
        cdef unsigned int img_w, img_h, row
        cdef unsigned char bdepth, ctype, alpha
        cdef FILE* fp
        cdef png_struct* ps
        cdef png_info* pi
        cdef char* img_data
        cdef char* region_data
        cdef char* mask_data
        cdef png_bytepp rows
        cdef Pixmap mask_pxm, pxm
        cdef XImage* xi
        cdef SpriteData* sp

        if self.sprite_count >= MAX_SPRITES:
            return -1

        fp = fopen(path, b"rb")
        if fp == NULL:
            import os
            script_dir = os.path.dirname(os.path.abspath(__file__))
            alt_path = os.path.join(script_dir, path.decode()).encode()
            fp = fopen(alt_path, b"rb")
        if fp == NULL:
            print(f"[Engine] Erro: nao abriu {path}")
            return -1

        ps = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL)
        pi = png_create_info_struct(ps)
        png_init_io(ps, fp)
        png_read_info(ps, pi)

        img_w  = png_get_image_width(ps, pi)
        img_h  = png_get_image_height(ps, pi)
        bdepth = png_get_bit_depth(ps, pi)
        ctype  = png_get_color_type(ps, pi)

        if x < 0 or y < 0 or w <= 0 or h <= 0:
            print(f"[Engine] Erro: parametros invalidos (x={x}, y={y}, w={w}, h={h})")
            png_destroy_read_struct(&ps, &pi, NULL)
            fclose(fp)
            return -1

        if x + w > img_w or y + h > img_h:
            print(f"[Engine] Erro: regiao fora dos limites ({x}+{w}>{img_w} ou {y}+{h}>{img_h})")
            png_destroy_read_struct(&ps, &pi, NULL)
            fclose(fp)
            return -1

        if bdepth == 16: png_set_strip_16(ps)
        if ctype == PNG_COLOR_TYPE_PALETTE: png_set_palette_to_rgb(ps)
        if ctype == PNG_COLOR_TYPE_GRAY and bdepth < 8: png_set_expand_gray_1_2_4_to_8(ps)
        if ctype == PNG_COLOR_TYPE_GRAY or ctype == PNG_COLOR_TYPE_GRAY_ALPHA: png_set_gray_to_rgb(ps)
        png_set_tRNS_to_alpha(ps)
        png_set_filler(ps, 0xFF, PNG_FILLER_AFTER)
        png_set_bgr(ps)
        png_read_update_info(ps, pi)

        row_bytes = img_w * 4
        img_data  = <char*>malloc(img_h * row_bytes)
        rows      = <png_bytepp>malloc(img_h * sizeof(png_bytep))
        for row in range(img_h):
            rows[row] = <png_bytep>(img_data + row * row_bytes)

        png_read_image(ps, rows)
        png_destroy_read_struct(&ps, &pi, NULL)
        fclose(fp)
        free(rows)

        # Extrai a regiao desejada
        region_row_bytes = w * 4
        region_data      = <char*>malloc(h * region_row_bytes)
        for dest_y in range(h):
            src_y2 = y + dest_y
            memcpy(
                region_data + (dest_y * region_row_bytes),
                img_data + (src_y2 * row_bytes) + (x * 4),
                region_row_bytes
            )
        free(img_data)

        # Mascara da regiao
        mask_bpl  = (w + 7) // 8
        mask_data = <char*>calloc(h, mask_bpl)
        for my in range(h):
            for mx in range(w):
                alpha = region_data[(my * w + mx) * 4 + 3]
                if alpha > 127:
                    m_idx = my * mask_bpl + (mx // 8)
                    bit   = mx % 8
                    mask_data[m_idx] = mask_data[m_idx] | (1 << bit)

        mask_pxm = XCreateBitmapFromData(self.display, self.window, mask_data, w, h)
        free(mask_data)

        xi  = XCreateImage(self.display, XDefaultVisual(self.display, self.screen),
                           self.depth, ZPixmap, 0, region_data, w, h, 32, 0)
        pxm = XCreatePixmap(self.display, self.window, w, h, self.depth)
        XPutImage(self.display, pxm, self.gc, xi, 0, 0, 0, 0, w, h)
        _engine_destroy_image(xi)

        sid = self.sprite_count
        sp  = &self.sprites[sid]
        sp.pixmap = pxm
        sp.mask   = mask_pxm
        sp.width  = w
        sp.height = h
        sp.loaded = 1
        self.sprite_count += 1
        return sid

    # --- Objetos ---
    def add_object(self, int x, int y, int sprite_id=-1,
                   int width=32, int height=32,
                   int r=255, int g=255, int b=255) -> int:
        cdef int oid
        cdef GameObject* obj
        if self.object_count >= MAX_OBJECTS:
            return -1
        oid           = self.object_count
        obj           = &self.objects[oid]
        obj.x         = x
        obj.y         = y
        obj.sprite_id = sprite_id
        obj.width     = width
        obj.height    = height
        obj.color     = ((r & 0xFF) << 16) | ((g & 0xFF) << 8) | (b & 0xFF)
        obj.active    = 1
        obj.use_tile  = 0
        obj.flip_h    = 0
        obj.flip_v    = 0
        self.object_count += 1
        return oid

    def add_tile_object(self, int x, int y, int sprite_id,
                        int tile_x, int tile_y,
                        int tile_w, int tile_h) -> int:
        cdef int oid
        cdef GameObject* obj
        oid = self.add_object(x, y, sprite_id, tile_w, tile_h)
        if oid < 0:
            return -1
        obj          = &self.objects[oid]
        obj.use_tile = 1
        obj.tile_x   = tile_x
        obj.tile_y   = tile_y
        obj.tile_w   = tile_w
        obj.tile_h   = tile_h
        obj.flip_h   = 0
        obj.flip_v   = 0
        return oid

    def move_object(self, int oid, int dx, int dy):
        if 0 <= oid < self.object_count:
            self.objects[oid].x += dx
            self.objects[oid].y += dy

    def set_object_pos(self, int oid, int x, int y):
        if 0 <= oid < self.object_count:
            self.objects[oid].x = x
            self.objects[oid].y = y

    def set_object_sprite(self, int oid, int sprite_id):
        if 0 <= oid < self.object_count:
            self.objects[oid].sprite_id = sprite_id

    def get_object_pos(self, int oid):
        if 0 <= oid < self.object_count:
            return (self.objects[oid].x, self.objects[oid].y)
        return (0, 0)

    def set_object_tile(self, int oid, int tile_x, int tile_y):
        if 0 <= oid < self.object_count:
            self.objects[oid].tile_x = tile_x
            self.objects[oid].tile_y = tile_y

    def set_object_flip(self, int oid, int flip_h=0, int flip_v=0):
        if 0 <= oid < self.object_count:
            self.objects[oid].flip_h = flip_h
            self.objects[oid].flip_v = flip_v

    def remove_object(self, int oid):
        if 0 <= oid < self.object_count:
            self.objects[oid].active = 0

    # --- Renderizacao ---
    def clear(self):
        XSetForeground(self.display, self.gc, self._bg_color)
        XFillRectangle(self.display, self.backbuffer, self.gc,
                       0, 0, self.render_w, self.render_h)

    # ==========================================================================
    # _draw_with_flip — todos os cdef no topo da funcao (regra do Cython)
    # ==========================================================================
    cdef void _draw_with_flip(self,
                               Pixmap src_pixmap, Pixmap src_mask,
                               int src_x, int src_y,
                               int src_w, int src_h,
                               int dst_x, int dst_y,
                               int flip_h, int flip_v):
        # Todas as declaracoes obrigatoriamente aqui no topo
        cdef XImage* xi
        cdef XImage* mask_xi
        cdef XImage* flipped_xi
        cdef int row_bytes
        cdef char* flipped_data
        cdef Pixmap flipped_mask
        cdef int x, y
        cdef int src_idx, dst_idx, dst_x_pixel, dst_y_pixel
        cdef int fmask_bpl, mbpl
        cdef char* fmask_data
        cdef int orig_bidx, orig_bbit, orig_bit
        cdef int dst_mx, dst_my, dst_bidx, dst_bbit

        # Sem flip: caminho rapido
        if not flip_h and not flip_v:
            if src_mask:
                XSetClipMask(self.display, self.gc, src_mask)
                XSetClipOrigin(self.display, self.gc, dst_x - src_x, dst_y - src_y)
            XCopyArea(self.display, src_pixmap, self.backbuffer, self.gc,
                      src_x, src_y, src_w, src_h, dst_x, dst_y)
            if src_mask:
                XSetClipMask(self.display, self.gc, 0)
            return

        # Com flip: inverte pixels
        xi = XGetImage(self.display, src_pixmap,
                       src_x, src_y, src_w, src_h,
                       0xFFFFFFFF, ZPixmap)
        if xi == NULL:
            return

        row_bytes    = src_w * 4
        flipped_data = <char*>malloc(src_h * row_bytes)

        for y in range(src_h):
            for x in range(src_w):
                src_idx     = (y * src_w + x) * 4
                dst_x_pixel = (src_w - 1 - x) if flip_h else x
                dst_y_pixel = (src_h - 1 - y) if flip_v else y
                dst_idx     = (dst_y_pixel * src_w + dst_x_pixel) * 4
                flipped_data[dst_idx + 0] = xi.data[src_idx + 0]
                flipped_data[dst_idx + 1] = xi.data[src_idx + 1]
                flipped_data[dst_idx + 2] = xi.data[src_idx + 2]
                flipped_data[dst_idx + 3] = xi.data[src_idx + 3]

        _engine_destroy_image(xi)

        # Gera mascara invertida
        flipped_mask = 0
        if src_mask:
            mask_xi = XGetImage(self.display, src_mask,
                                src_x, src_y, src_w, src_h,
                                0xFFFFFFFF, ZPixmap)
            if mask_xi != NULL:
                fmask_bpl  = (src_w + 7) // 8
                mbpl       = mask_xi.bytes_per_line
                fmask_data = <char*>calloc(src_h, fmask_bpl)

                for y in range(src_h):
                    for x in range(src_w):
                        orig_bidx = y * mbpl + (x // 8)
                        orig_bbit = x % 8
                        orig_bit  = (mask_xi.data[orig_bidx] >> orig_bbit) & 1
                        if orig_bit:
                            dst_mx   = (src_w - 1 - x) if flip_h else x
                            dst_my   = (src_h - 1 - y) if flip_v else y
                            dst_bidx = dst_my * fmask_bpl + (dst_mx // 8)
                            dst_bbit = dst_mx % 8
                            fmask_data[dst_bidx] = fmask_data[dst_bidx] | (1 << dst_bbit)

                flipped_mask = XCreateBitmapFromData(
                    self.display, self.window, fmask_data, src_w, src_h)
                free(fmask_data)
                _engine_destroy_image(mask_xi)

        # Aplica mascara invertida e desenha
        if flipped_mask:
            XSetClipMask(self.display, self.gc, flipped_mask)
            XSetClipOrigin(self.display, self.gc, dst_x, dst_y)

        flipped_xi = XCreateImage(
            self.display,
            XDefaultVisual(self.display, self.screen),
            self.depth, ZPixmap, 0,
            flipped_data, src_w, src_h, 32, 0)

        XPutImage(self.display, self.backbuffer, self.gc,
                  flipped_xi, 0, 0, dst_x, dst_y, src_w, src_h)

        _engine_destroy_image(flipped_xi)

        if flipped_mask:
            XSetClipMask(self.display, self.gc, 0)
            XFreePixmap(self.display, flipped_mask)

    # ==========================================================================
    # draw
    # ==========================================================================
    def draw(self):
        cdef int i
        cdef GameObject* obj
        cdef SpriteData* sp
        for i in range(self.object_count):
            obj = &self.objects[i]
            if not obj.active:
                continue
            if obj.sprite_id >= 0 and obj.sprite_id < self.sprite_count:
                sp = &self.sprites[obj.sprite_id]
                if sp.loaded:
                    if obj.use_tile:
                        self._draw_with_flip(
                            sp.pixmap, sp.mask,
                            obj.tile_x * obj.tile_w,
                            obj.tile_y * obj.tile_h,
                            obj.tile_w, obj.tile_h,
                            obj.x, obj.y,
                            obj.flip_h, obj.flip_v)
                    else:
                        self._draw_with_flip(
                            sp.pixmap, sp.mask,
                            0, 0,
                            sp.width, sp.height,
                            obj.x, obj.y,
                            obj.flip_h, obj.flip_v)
            else:
                XSetForeground(self.display, self.gc, obj.color)
                XFillRectangle(self.display, self.backbuffer, self.gc,
                               obj.x, obj.y, obj.width, obj.height)

    def draw_rect(self, int x, int y, int w, int h,
                  int r=255, int g=255, int b=255):
        cdef unsigned long color
        color = ((r & 0xFF) << 16) | ((g & 0xFF) << 8) | (b & 0xFF)
        XSetForeground(self.display, self.gc, color)
        XFillRectangle(self.display, self.backbuffer, self.gc, x, y, w, h)

    def draw_overlay(self, int x, int y, int w, int h,
                     int r, int g, int b, float alpha):
        """
        Desenha um retângulo colorido com alpha real sobre o backbuffer.
        alpha: 0.0 = totalmente transparente, 1.0 = totalmente opaco.
        Lê os pixels atuais do backbuffer, blenda e escreve de volta.
        Sem pontilhado, sem linhas — blend matemático pixel a pixel.
        """
        cdef XImage* xi
        cdef char*   blended
        cdef int     px, py, idx
        cdef int     src_r, src_g, src_b
        cdef int     ia   # alpha em inteiro 0..256 (evita float no loop)
        cdef int     bw, bh

        # Clamp da área ao backbuffer
        if x < 0: x = 0
        if y < 0: y = 0
        bw = w if x + w <= self.render_w else self.render_w - x
        bh = h if y + h <= self.render_h else self.render_h - y
        if bw <= 0 or bh <= 0:
            return

        # Lê os pixels do backbuffer na região pedida
        xi = XGetImage(self.display, self.backbuffer,
                       x, y, bw, bh, 0xFFFFFFFF, ZPixmap)
        if xi == NULL:
            return

        ia = <int>(alpha * 256.0)   # 0..256  (usa shift depois)
        if ia > 256: ia = 256
        if ia < 0:   ia = 0

        blended = <char*>malloc(bh * bw * 4)
        if blended == NULL:
            _engine_destroy_image(xi)
            return

        for py in range(bh):
            for px in range(bw):
                idx = (py * bw + px) * 4
                # X11 armazena BGR no ZPixmap
                src_b = <unsigned char>xi.data[idx + 0]
                src_g = <unsigned char>xi.data[idx + 1]
                src_r = <unsigned char>xi.data[idx + 2]

                # blend = src * (1-alpha) + dst * alpha
                blended[idx + 0] = <char>(((b * ia) + (src_b * (256 - ia))) >> 8)
                blended[idx + 1] = <char>(((g * ia) + (src_g * (256 - ia))) >> 8)
                blended[idx + 2] = <char>(((r * ia) + (src_r * (256 - ia))) >> 8)
                blended[idx + 3] = xi.data[idx + 3]

        _engine_destroy_image(xi)

        xi = XCreateImage(self.display,
                          XDefaultVisual(self.display, self.screen),
                          self.depth, ZPixmap, 0,
                          blended, bw, bh, 32, 0)
        if xi != NULL:
            XPutImage(self.display, self.backbuffer, self.gc,
                      xi, 0, 0, x, y, bw, bh)
            _engine_destroy_image(xi)
        else:
            free(blended)

    def present(self):
        cdef XImage* small_img
        cdef XImage* scaled_img
        cdef int scaled_row_bytes
        cdef char* scaled_data
        cdef int x, y, sx, sy, src_idx, dst_idx

        if self.scale == 1:
            XCopyArea(self.display, self.backbuffer, self.window, self.gc,
                      0, 0, self.render_w, self.render_h, 0, 0)
        else:
            small_img = XGetImage(
                self.display, self.backbuffer,
                0, 0, self.render_w, self.render_h,
                0xFFFFFFFF, ZPixmap)

            if small_img != NULL:
                scaled_row_bytes = self.win_w * 4
                scaled_data      = <char*>malloc(self.win_h * scaled_row_bytes)

                for y in range(self.win_h):
                    sy = y // self.scale
                    for x in range(self.win_w):
                        sx      = x // self.scale
                        src_idx = (sy * self.render_w + sx) * 4
                        dst_idx = (y * self.win_w + x) * 4
                        scaled_data[dst_idx + 0] = small_img.data[src_idx + 0]
                        scaled_data[dst_idx + 1] = small_img.data[src_idx + 1]
                        scaled_data[dst_idx + 2] = small_img.data[src_idx + 2]
                        scaled_data[dst_idx + 3] = small_img.data[src_idx + 3]

                scaled_img = XCreateImage(
                    self.display,
                    XDefaultVisual(self.display, self.screen),
                    self.depth, ZPixmap, 0,
                    scaled_data, self.win_w, self.win_h, 32, 0)

                XPutImage(self.display, self.window, self.gc,
                          scaled_img, 0, 0, 0, 0, self.win_w, self.win_h)

                _engine_destroy_image(small_img)
                _engine_destroy_image(scaled_img)

        XFlush(self.display)

    # --- Tilemap ---
    def draw_tilemap(self, list tilemap, int sprite_id,
                     int tile_w=32, int tile_h=32,
                     int offset_x=0, int offset_y=0):
        cdef SpriteData* sp
        cdef int tiles_per_row, row_idx, col_idx, tile_id, src_x, src_y, dst_x, dst_y

        if sprite_id < 0 or sprite_id >= self.sprite_count:
            return
        sp = &self.sprites[sprite_id]
        if not sp.loaded:
            return

        tiles_per_row = sp.width // tile_w
        for row_idx, row in enumerate(tilemap):
            for col_idx, tile_id in enumerate(row):
                if tile_id < 0:
                    continue
                src_x = (tile_id % tiles_per_row) * tile_w
                src_y = (tile_id // tiles_per_row) * tile_h
                dst_x = col_idx * tile_w + offset_x
                dst_y = row_idx * tile_h + offset_y
                XCopyArea(self.display, sp.pixmap, self.backbuffer, self.gc,
                          src_x, src_y, tile_w, tile_h, dst_x, dst_y)

    cpdef draw_sprite_part(self, int sprite_id, int x, int y,
                           int src_x, int src_y, int src_w, int src_h):
        cdef SpriteData* sp
        if sprite_id < 0 or sprite_id >= self.sprite_count:
            return
        sp = &self.sprites[sprite_id]
        if not sp.loaded:
            return
        XSetClipMask(self.display, self.gc, sp.mask)
        XSetClipOrigin(self.display, self.gc, x - src_x, y - src_y)
        XCopyArea(self.display, sp.pixmap, self.backbuffer, self.gc,
                  src_x, src_y, src_w, src_h, x, y)
        XSetClipMask(self.display, self.gc, 0)

    # --- Input ---
    def poll_events(self):
        cdef XEvent     ev
        cdef XKeyEvent* kev
        cdef unsigned int ksym
        cdef int idx

        memcpy(self.keys_prev, self.keys, sizeof(self.keys))

        while XPending(self.display) > 0:
            XNextEvent(self.display, &ev)
            if ev.type == KeyPress or ev.type == KeyRelease:
                kev  = <XKeyEvent*>(&ev)
                ksym = XLookupKeysym(kev, 0)
                idx  = ksym & (MAX_KEYS - 1)
                if ev.type == KeyPress:
                    self.keys[idx] = 1
                    if ksym == XK_Escape:
                        self.running = 0
                else:
                    self.keys[idx] = 0

    cdef unsigned int _name_to_keysym(self, bytes key):
        if key == b"left":   return XK_Left
        if key == b"right":  return XK_Right
        if key == b"up":     return XK_Up
        if key == b"down":   return XK_Down
        if key == b"space":  return XK_space
        if key == b"return": return XK_Return
        if key == b"escape": return XK_Escape
        if key == b"a":      return XK_a
        if key == b"d":      return XK_d
        if key == b"w":      return XK_w
        if key == b"s":      return XK_s
        if len(key) == 1:    return <unsigned int>key[0]
        return 0

    def key_down(self, bytes key) -> bool:
        cdef unsigned int ksym
        ksym = self._name_to_keysym(key)
        return self.keys[ksym & (MAX_KEYS - 1)] == 1

    def key_pressed(self, bytes key) -> bool:
        cdef unsigned int ksym
        cdef int idx
        ksym = self._name_to_keysym(key)
        idx  = ksym & (MAX_KEYS - 1)
        return self.keys[idx] == 1 and self.keys_prev[idx] == 0

    def key_released(self, bytes key) -> bool:
        cdef unsigned int ksym
        cdef int idx
        ksym = self._name_to_keysym(key)
        idx  = ksym & (MAX_KEYS - 1)
        return self.keys[idx] == 0 and self.keys_prev[idx] == 1

    # --- Colisao AABB ---
    def check_collision(self, int oid1, int oid2) -> bool:
        cdef GameObject* a
        cdef GameObject* b
        cdef int aw, ah, bw, bh

        if oid1 < 0 or oid2 < 0:
            return False
        if oid1 >= self.object_count or oid2 >= self.object_count:
            return False
        if not self.objects[oid1].active or not self.objects[oid2].active:
            return False

        a = &self.objects[oid1]
        b = &self.objects[oid2]

        if a.use_tile:
            aw = a.tile_w; ah = a.tile_h
        elif a.sprite_id >= 0:
            aw = self.sprites[a.sprite_id].width
            ah = self.sprites[a.sprite_id].height
        else:
            aw = a.width; ah = a.height

        if b.use_tile:
            bw = b.tile_w; bh = b.tile_h
        elif b.sprite_id >= 0:
            bw = self.sprites[b.sprite_id].width
            bh = self.sprites[b.sprite_id].height
        else:
            bw = b.width; bh = b.height

        return (a.x < b.x + bw and a.x + aw > b.x and
                a.y < b.y + bh and a.y + ah > b.y)

    def __dealloc__(self):
        cdef int i
        for i in range(self.sprite_count):
            if self.sprites[i].loaded:
                XFreePixmap(self.display, self.sprites[i].pixmap)
                if self.sprites[i].mask:
                    XFreePixmap(self.display, self.sprites[i].mask)
        if self.display != NULL:
            XFreePixmap(self.display, self.backbuffer)
            XFreeGC(self.display, self.gc)
            XCloseDisplay(self.display)

    # --- Texto e Caixas Graficas ---

    def draw_text(self, int x, int y, str text,
                  int font_sid, int font_w, int font_h,
                  int chars_per_row=16, int ascii_offset=32, int line_spacing=0):
        cdef SpriteData* sp
        cdef int cx, cy, tile_x, tile_y, cp

        if font_sid < 0 or font_sid >= self.sprite_count:
            return
        sp = &self.sprites[font_sid]
        if not sp.loaded:
            return

        cx = x
        cy = y
        for ch in text:
            if ch == '\n':
                cy += font_h + line_spacing
                cx = x
                continue
            cp = ord(ch) - ascii_offset
            if cp < 0:
                cp = 0
            tile_x = (cp % chars_per_row) * font_w
            tile_y = (cp // chars_per_row) * font_h
            XCopyArea(self.display, sp.pixmap, self.backbuffer, self.gc,
                      tile_x, tile_y, font_w, font_h, cx, cy)
            cx += font_w

    def draw_box(self, int x, int y, int box_w, int box_h,
                 int box_sid, int tile_w, int tile_h):
        cdef SpriteData* sp
        cdef Display* d
        cdef Pixmap src, dst
        cdef GC gc
        cdef int cx, cy, copy_w, copy_h

        if box_sid < 0 or box_sid >= self.sprite_count: return
        sp = &self.sprites[box_sid]
        if not sp.loaded: return

        if box_w < tile_w * 2: box_w = tile_w * 2
        if box_h < tile_h * 2: box_h = tile_h * 2

        d   = self.display
        src = sp.pixmap
        dst = self.backbuffer
        gc  = self.gc

        # Centro
        cy = y + tile_h
        while cy < y + box_h - tile_h:
            copy_h = tile_h
            if cy + copy_h > y + box_h - tile_h: copy_h = (y + box_h - tile_h) - cy
            cx = x + tile_w
            while cx < x + box_w - tile_w:
                copy_w = tile_w
                if cx + copy_w > x + box_w - tile_w: copy_w = (x + box_w - tile_w) - cx
                XCopyArea(d, src, dst, gc, tile_w, tile_h, copy_w, copy_h, cx, cy)
                cx += copy_w
            cy += copy_h

        # Bordas Superior e Inferior
        cx = x + tile_w
        while cx < x + box_w - tile_w:
            copy_w = tile_w
            if cx + copy_w > x + box_w - tile_w: copy_w = (x + box_w - tile_w) - cx
            XCopyArea(d, src, dst, gc, tile_w, 0,        copy_w, tile_h, cx, y)
            XCopyArea(d, src, dst, gc, tile_w, tile_h*2, copy_w, tile_h, cx, y + box_h - tile_h)
            cx += copy_w

        # Bordas Esquerda e Direita
        cy = y + tile_h
        while cy < y + box_h - tile_h:
            copy_h = tile_h
            if cy + copy_h > y + box_h - tile_h: copy_h = (y + box_h - tile_h) - cy
            XCopyArea(d, src, dst, gc, 0,        tile_h, tile_w, copy_h, x,                  cy)
            XCopyArea(d, src, dst, gc, tile_w*2, tile_h, tile_w, copy_h, x + box_w - tile_w, cy)
            cy += copy_h

        # Quatro Cantos
        XCopyArea(d, src, dst, gc, 0,        0,        tile_w, tile_h, x,                  y)
        XCopyArea(d, src, dst, gc, tile_w*2, 0,        tile_w, tile_h, x + box_w - tile_w, y)
        XCopyArea(d, src, dst, gc, 0,        tile_h*2, tile_w, tile_h, x,                  y + box_h - tile_h)
        XCopyArea(d, src, dst, gc, tile_w*2, tile_h*2, tile_w, tile_h, x + box_w - tile_w, y + box_h - tile_h)

    def draw_text_box(self, int x, int y, int box_w, int box_h,
                      str title, str content,
                      int box_sid, int box_tw, int box_th,
                      int font_sid, int font_w, int font_h,
                      int chars_per_row=16, int ascii_offset=32, int line_spacing=4):
        cdef int inner_x, inner_y, max_chars, line_y
        cdef str current_line

        self.draw_box(x, y, box_w, box_h, box_sid, box_tw, box_th)

        inner_x   = x + box_tw
        inner_y   = y + box_th
        max_chars = (box_w - (box_tw * 2)) // font_w

        if max_chars <= 0:
            return

        if title:
            self.draw_text(inner_x, inner_y, title, font_sid, font_w, font_h,
                           chars_per_row, ascii_offset, line_spacing)
            inner_y += font_h + line_spacing + 8

        line_y       = inner_y
        current_line = ""

        for paragraph in content.split('\n'):
            words = paragraph.split(' ')
            for word in words:
                if len(current_line) + len(word) <= max_chars:
                    current_line += word + " "
                else:
                    self.draw_text(inner_x, line_y, current_line.strip(),
                                   font_sid, font_w, font_h,
                                   chars_per_row, ascii_offset, line_spacing)
                    line_y += font_h + line_spacing
                    current_line = word + " "

            if current_line:
                self.draw_text(inner_x, line_y, current_line.strip(),
                               font_sid, font_w, font_h,
                               chars_per_row, ascii_offset, line_spacing)
                line_y += font_h + line_spacing
                current_line = ""
