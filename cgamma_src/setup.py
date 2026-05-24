from setuptools import setup, Extension

module = Extension(
    "cgamma",
    sources=["gamma.c"],
)

setup(
    name="cgamma",
    version="0.1",
    ext_modules=[module],
)