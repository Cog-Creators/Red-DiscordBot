import distutils.ccompiler as ccompiler
import re
import tempfile
from distutils.errors import CCompilerError, DistutilsPlatformError
from pathlib import Path
from setuptools import setup, find_packages

dep_links = [
    (
        "https://github.com/Rapptz/discord.py/tarball/"
        "7eb918b19e3e60b56eb9039eb267f8f3477c5e17#egg=discord.py-1.0"
    )
]

requirements = [
    "aiohttp-json-rpc==0.8.7",
    "aiohttp==2.2.5",
    "appdirs==1.4.3",
    "async-timeout==2.0.1",
    "chardet==3.0.4",
    "colorama==0.3.9",
    "distro==1.3.0; sys_platform == 'linux'",
    "fuzzywuzzy==0.16.0",
    "idna==2.7",
    "multidict==4.3.1",
    "python-levenshtein==0.12.0",
    "pyyaml==3.12",
    "raven==6.5.0",
    "red-trivia==1.1.1",
    "websockets==3.4",
    "yarl==0.18.0",
]


def get_package_list():
    core = find_packages(include=["redbot", "redbot.*"])
    return core


def check_compiler_available():
    m = ccompiler.new_compiler()

    with tempfile.TemporaryDirectory() as tdir:
        with tempfile.NamedTemporaryFile(prefix="dummy", suffix=".c", dir=tdir) as tfile:
            tfile.write(b"int main(int argc, char** argv) {return 0;}")
            tfile.seek(0)
            try:
                m.compile([tfile.name], output_dir=tdir)
            except (CCompilerError, DistutilsPlatformError):
                return False
    return True


def get_version():
    with open("redbot/core/__init__.py") as f:
        version = re.search(
            r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE
        ).group(1)
    return version


def find_locale_folders():
    """
    Ignore this tomfoolery in the desire for automation. It works, that's
    all you gotta know. Don't fuck with this unless you really know what
    you're doing, otherwise we lose all translations.
    """

    def glob_locale_files(path: Path):
        msgs = path.glob("*.po")

        parents = path.parents

        return [str(m.relative_to(parents[0])) for m in msgs]

    ret = {"redbot.core": glob_locale_files(Path("redbot/core/locales"))}

    cogs_path = Path("redbot/cogs")

    for cog_folder in cogs_path.iterdir():
        locales_folder = cog_folder / "locales"
        if not locales_folder.is_dir():
            continue

        pkg_name = str(cog_folder).replace("/", ".")
        ret[pkg_name] = glob_locale_files(locales_folder)

    return ret


if __name__ == "__main__":
    if not check_compiler_available():
        requirements.remove(
            next(r for r in requirements if r.lower().startswith("python-levenshtein"))
        )

    setup(
        name="Red-DiscordBot",
        version=get_version(),
        packages=get_package_list(),
        package_data=find_locale_folders(),
        include_package_data=True,
        url="https://github.com/Cog-Creators/Red-DiscordBot",
        license="GPLv3",
        author="Cog-Creators",
        author_email="",
        description="A highly customizable Discord bot",
        classifiers=[
            "Development Status :: 4 - Beta",
            "Framework :: AsyncIO",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Topic :: Communications :: Chat",
            "Topic :: Documentation :: Sphinx",
        ],
        entry_points={
            "console_scripts": [
                "redbot=redbot.__main__:main",
                "redbot-setup=redbot.setup:main",
                "redbot-launcher=redbot.launcher:main",
            ]
        },
        python_requires=">=3.6,<3.7",
        install_requires=requirements,
        dependency_links=dep_links,
        extras_require={
            "test": ["pytest>3", "pytest-asyncio"],
            "mongo": ["motor"],
            "docs": ["sphinx>=1.7", "sphinxcontrib-asyncio", "sphinx_rtd_theme"],
            "voice": ["red-lavalink>=0.0.4"],
            "style": ["black==18.5b1"],
        },
    )
