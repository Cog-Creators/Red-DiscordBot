import os
import re
from setuptools import setup, find_packages

install_requires = [
    "aiohttp-json-rpc==0.12",
    "aiohttp==3.5.4",
    "appdirs==1.4.3",
    "async-timeout==3.0.1",
    "attrs==18.2.0",
    "chardet==3.0.4",
    "colorama==0.4.1",
    "distro==1.4.0; sys_platform == 'linux'",
    "fuzzywuzzy==0.17.0",
    "idna-ssl==1.1.0",
    "idna==2.8",
    "multidict==4.5.2",
    "python-levenshtein-wheels==0.13.1",
    "pyyaml==3.13",
    "raven==6.10.0",
    "raven-aiohttp==0.7.0",
    "red-lavalink==0.2.3",
    "schema==0.6.8",
    "websockets==7.0",
    "yarl==1.3.0",
]

extras_require = {
    "test": [
        "atomicwrites==1.3.0",
        "more-itertools==6.0.0",
        "pluggy==0.8.1",
        "py==1.7.0",
        "pytest==4.2.0",
        "pytest-asyncio==0.10.0",
        "six==1.12.0",
    ],
    "mongo": ["motor==2.0.0", "pymongo==3.7.2", "dnspython==1.16.0"],
    "docs": [
        "alabaster==0.7.12",
        "babel==2.6.0",
        "certifi==2018.11.29",
        "docutils==0.14",
        "imagesize==1.1.0",
        "Jinja2==2.10",
        "MarkupSafe==1.1.0",
        "packaging==19.0",
        "pyparsing==2.3.1",
        "Pygments==2.3.1",
        "pytz==2018.9",
        "requests==2.21.0",
        "six==1.12.0",
        "snowballstemmer==1.2.1",
        "sphinx==1.8.4",
        "sphinx_rtd_theme==0.4.3",
        "sphinxcontrib-asyncio==0.2.0",
        "sphinxcontrib-websupport==1.1.0",
        "urllib3==1.24.1",
    ],
    "voice": [],
    "style": ["black==18.9b0", "click==7.0", "toml==0.10.0"],
}

python_requires = ">=3.6.2,<3.8"
if os.name == "nt":
    # Due to issues with ProactorEventLoop prior to 3.6.6 (bpo-26819)
    python_requires = ">=3.6.6,<3.8"


def get_version():
    with open("redbot/core/__init__.py") as f:
        version = re.search(
            r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE
        ).group(1)
    return version


if __name__ == "__main__":
    setup(
        name="Red-DiscordBot",
        version=get_version(),
        packages=(
            find_packages(include=("redbot", "redbot.*")) + ["discord", "discord.ext.commands"]
        ),
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
        install_requires=install_requires,
        extras_require=extras_require,
    )
