from __future__ import annotations

import os
import pathlib
import subprocess
import sys
from typing import List

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext

here = pathlib.Path(__file__).resolve().parent


class CMakeExtension(Extension):
    def __init__(self, name: str, sourcedir: str = "") -> None:
        super().__init__(name, sources=[])
        self.sourcedir = os.fspath(pathlib.Path(sourcedir).resolve())


class CMakeBuild(build_ext):
    def build_extension(self, ext: Extension) -> None:
        extdir = pathlib.Path(self.get_ext_fullpath(ext.name)).parent.resolve()
        cfg = os.environ.get("CMAKE_BUILD_TYPE", "Release")

        cmake_args: List[str] = [
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={extdir}",
            f"-DPYTHON_EXECUTABLE={sys.executable}",
            f"-DCMAKE_BUILD_TYPE={cfg}",
        ]

        build_temp = pathlib.Path(self.build_temp)
        build_temp.mkdir(parents=True, exist_ok=True)

        subprocess.check_call([
            "cmake",
            here.as_posix(),
            *cmake_args,
        ], cwd=build_temp)

        subprocess.check_call([
            "cmake",
            "--build",
            ".",
            "--target",
            "cpp_event_processor",
            "--target",
            "cpp_leaderboard",
            "--config",
            cfg,
        ], cwd=build_temp)


setup(
    name="engagehub-cpp-extensions",
    version="0.1.0",
    author="EngageHub",
    description="High-performance C++ extensions for EngageHub backend",
    long_description=(here / "README.md").read_text(encoding="utf8") if (here / "README.md").exists() else "",
    packages=[],
    ext_modules=[CMakeExtension("cpp_event_processor"), CMakeExtension("cpp_leaderboard")],
    cmdclass={"build_ext": CMakeBuild},
    zip_safe=False,
)
