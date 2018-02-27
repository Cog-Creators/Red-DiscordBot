from distutils.core import setup
from pathlib import Path
from subprocess import run, PIPE

import os
import sys

from setuptools import find_packages

IS_TRAVIS = 'TRAVIS' in os.environ
IS_DEPLOYING = 'DEPLOYING' in os.environ

dep_links = ['https://github.com/Rapptz/discord.py/tarball/rewrite#egg=discord.py-1.0']
if IS_TRAVIS:
    dep_links = []


def get_package_list():
    core = find_packages(include=['redbot', 'redbot.*'])
    return core


def get_requirements():
    with open('requirements.txt') as f:
        requirements = f.read().splitlines()
    if IS_TRAVIS and not IS_DEPLOYING:
        requirements.remove('git+https://github.com/Rapptz/discord.py.git@rewrite#egg=discord.py[voice]')
    else:
        requirements.append('discord.py>=1.0.0a0')  # Because RTD
    if sys.platform.startswith("linux"):
        requirements.append("distro")
    return requirements


def get_version():
    try:
        p = run(
            "git describe --abbrev=0 --tags".split(),
            stdout=PIPE
        )
    except FileNotFoundError:
        # No git
        return 3, 0, 0

    if p.returncode != 0:
        return 3, 0, 0

    stdout = p.stdout.strip().decode()
    if stdout.startswith("v"):
        numbers = stdout[1:].split('.')
        args = [0, 0, 0]
        for i in range(3):
            try:
                args[i] = int(numbers[i])
            except (IndexError, ValueError):
                args[i] = 0
        return args
    return 3, 0, 0


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

    ret = {
        'redbot.core': glob_locale_files(Path('redbot/core/locales'))
    }

    cogs_path = Path('redbot/cogs')

    for cog_folder in cogs_path.iterdir():
        locales_folder = cog_folder / 'locales'
        if not locales_folder.is_dir():
            continue

        pkg_name = str(cog_folder).replace('/', '.')
        ret[pkg_name] = glob_locale_files(locales_folder)

    return ret


setup(
    name='Red-DiscordBot',
    version="{}.{}.{}b9".format(*get_version()),
    packages=get_package_list(),
    package_data=find_locale_folders(),
    url='https://github.com/Cog-Creators/Red-DiscordBot',
    license='GPLv3',
    author='Cog-Creators',
    author_email='',
    description='A highly customizable Discord bot',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: AsyncIO',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Communications :: Chat',
        'Topic :: Documentation :: Sphinx'
    ],
    entry_points={
        'console_scripts': [
            'redbot=redbot.__main__:main',
            'redbot-setup=redbot.setup:main',
            'redbot-launcher=redbot.launcher:main'
        ]
    },
    python_requires='>=3.5',
    setup_requires=get_requirements(),
    install_requires=get_requirements(),
    dependency_links=dep_links,
    extras_require={
        'test': [
            'pytest>=3', 'pytest-asyncio'
        ],
        'mongo': ['motor'],
        'docs': ['sphinx', 'sphinxcontrib-asyncio', 'sphinx_rtd_theme'],
        'voice': ['PyNaCl']
    }
)
