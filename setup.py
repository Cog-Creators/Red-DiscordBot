import distutils.ccompiler as ccompiler
import os
import re
import tempfile
from distutils.errors import CCompilerError, DistutilsPlatformError
from setuptools import setup, find_packages

requirements = [
    "aiohttp-json-rpc==0.11.1",
    "aiohttp==3.3.2",
    "appdirs==1.4.3",
    "async-timeout==3.0.0",
    "attrs==18.2.0",
    "chardet==3.0.4",
    "colorama==0.3.9",
    "discord.py>=1.0.0a0",
    "distro==1.3.0; sys_platform == 'linux'",
    "fuzzywuzzy==0.17.0",
    "idna-ssl==1.1.0",
    "idna==2.7",
    "multidict==4.4.2",
    "python-levenshtein==0.12.0",
    "pyyaml==3.13",
    "raven==6.9.0",
    "raven-aiohttp==0.7.0",
    "websockets==6.0",
    "yarl==1.2.6",
]

python_requires = ">=3.6.2,<3.8"
if os.name == "nt":
    # Due to issues with ProactorEventLoop prior to 3.6.6 (bpo-26819)
    python_requires = ">=3.6.6,<3.8"


def get_dependency_links():
    with open("dependency_links.txt") as file:
        return file.read().splitlines()


def check_compiler_available():
    m = ccompiler.new_compiler()

    with tempfile.TemporaryDirectory() as tdir:
        with open(os.path.join(tdir, "dummy.c"), "w") as tfile:
            tfile.write("int main(int argc, char** argv) {return 0;}")
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


if __name__ == "__main__":
    if not check_compiler_available():
        requirements.remove(
            next(r for r in requirements if r.lower().startswith("python-levenshtein"))
        )

    if "READTHEDOCS" in os.environ:
        requirements.remove(next(r for r in requirements if r.lower().startswith("discord.py")))

    setup(
        name="Red-DiscordBot",
        version=get_version(),
        packages=find_packages(include=["redbot", "redbot.*"]),
        package_data={"": ["locales/*.po", "data/*", "data/**/*"]},
        url="https://github.com/Cog-Creators/Red-DiscordBot",
        license="GPLv3",
        author="Cog-Creators",
        author_email="",
        description="A highly customizable Discord bot",
        classifiers=[
            "Development Status :: 4 - Beta",
            "Framework :: AsyncIO",
            "Framework :: Pytest",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Topic :: Communications :: Chat",
            "Topic :: Documentation :: Sphinx",
        ],
        entry_points={
            "console_scripts": [
                "redbot=redbot.__main__:main",
                "redbot-setup=redbot.setup:main",
                "redbot-launcher=redbot.launcher:main",
            ],
            "pytest11": ["red-discordbot = redbot.pytest"],
        },
        python_requires=python_requires,
        install_requires=requirements,
        dependency_links=get_dependency_links(),
        extras_require={
            "test": [
                "atomicwrites==1.2.1",
                "more-itertools==4.3.0",
                "pluggy==0.7.1",
                "py==1.6.0",
                "pytest==3.8.1",
                "pytest-asyncio==0.9.0",
                "six==1.11.0",
            ],
            "mongo": ["motor==2.0.0", "pymongo==3.7.1"],
            "docs": [
                "alabaster==0.7.11",
                "babel==2.6.0",
                "certifi==2018.8.24",
                "docutils==0.14",
                "imagesize==1.1.0",
                "Jinja2==2.10",
                "MarkupSafe==1.0",
                "packaging==17.1",
                "pyparsing==2.2.1",
                "six==1.11.0",
                "Pygments==2.2.0",
                "pytz==2018.5",
                "requests==2.19.1",
                "urllib3==1.23",
                "six==1.11.0",
                "snowballstemmer==1.2.1",
                "sphinx==1.7.9",
                "sphinx_rtd_theme==0.4.1",
                "sphinxcontrib-asyncio==0.2.0",
                "sphinxcontrib-websupport==1.1.0",
            ],
            "voice": ["red-lavalink==0.1.2"],
            "style": ["black==18.6b4", "click==6.7", "toml==0.9.6"],
        },
    )
