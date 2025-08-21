from setuptools import setup, Extension
from Cython.Build import cythonize
from Cython.Distutils import build_ext
import os

# Look for each .py file inside src tree
py_modules = []
for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".py"):
            module_path = os.path.join(root, file)
            module_name = module_path[:-3].replace(os.sep, ".")
            py_modules.append(Extension(module_name, [module_path]))



setup(
    name="ecw_designer",
    version='0.0.0',
    ext_modules=cythonize(
        py_modules,
        build_dir="build_cythonize",
        compiler_directives={
            'language_level': "3",
            'always_allow_keywords': True,
        }
    ),
    cmdclass=dict(
        build_ext=build_ext
    ),
)