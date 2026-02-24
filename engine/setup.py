from setuptools import setup, Extension
from Cython.Build import cythonize

ext = Extension(
    name="engine",
    sources=["engine.pyx"],
    libraries=["X11", "png"],          # X11 + libpng
    library_dirs=["/usr/lib", "/usr/lib/x86_64-linux-gnu"],
    include_dirs=["/usr/include"],
)

setup(
    ext_modules=cythonize(ext, compiler_directives={"language_level": "3"})
)
