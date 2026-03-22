from setuptools import setup, Extension
from Cython.Build import cythonize

engine_ext = Extension(
    name="engine",
    sources=[
        "engine.pyx",   # wrapper Cython
        "Engine.c",     # implementação C
    ],
    include_dirs=["."],          # encontra Engine.h no mesmo diretório
    libraries=[
        "GL",    # OpenGL (glXDestroyContext, glXSwapBuffers, etc.)
        "X11",   # XOpenDisplay, XCreateWindow, etc.
        "png",   # libpng (carregamento de sprites)
        "m",     # libm (math.h)
    ],
    extra_compile_args=["-O2"],
)

setup(
    name="engine",
    ext_modules=cythonize(
        [engine_ext],
        compiler_directives={"language_level": "3"},
    ),
)
