from distutils.core import setup
from setuptools import find_packages

from core import __version__


def get_package_list():
    core = find_packages(include=['core', 'core.*'])
    cogs = find_packages(include=['cogs', 'cogs.*'])

    return core + cogs


def get_version():
    return "{}.{}.{}".format(*__version__)


setup(
    name='Red-DiscordBot',
    version=get_version(),
    packages=get_package_list(),
    package_dir={
        'redbot': 'core',
        'redbot.cogs': 'cogs'
    },
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
    scripts=[
        'scripts/redbot-setup.py'
    ]
)
