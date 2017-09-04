from distutils.core import setup
from pathlib import Path

import os
from setuptools import find_packages

from redbot.core import __version__


def get_package_list():
    core = find_packages(include=['redbot', 'redbot.*'])
    return core


def get_version():
    return "{}.{}.{}".format(*__version__)


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
    version=get_version(),
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
        'Topic :: Communications :: Chat :: Discord',
        'Topic :: Documentation :: Sphinx'
    ],
    entry_points={
        'console_scripts': [
            'redbot=redbot.__main__:main',
            'redbot-setup=redbot.setup:basic_setup']
    },
    python_requires='>=3.5',
    install_requires=[
        'discord.py>=1.0[voice]',
        'appdirs',
        'youtube_dl',
        'raven'
    ],
    dependency_links=[
        'git+https://github.com/Rapptz/discord.py@rewrite#egg=discord.py-1.0',
        'git+https://github.com/pytest-dev/pytest-asyncio#egg=pytest-asyncio'
    ],
    extras_require={
        'test': ['pytest>=3', 'pytest-asyncio'],
        'mongo': ['pymongo', 'motor'],
        'docs': ['sphinx', 'sphinxcontrib-asyncio', 'sphinx_rtd_theme']
    }
)
