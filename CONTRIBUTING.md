# Contents
* [1. Introduction](#1-introduction)
  * [1.1 Why do these guidelines exist?](#11-why-do-these-guidelines-exist)
  * [1.2 What kinds of contributions are we looking for?](#12-what-kinds-of-contributions-are-we-looking-for)
* [2. Ground Rules](#2-ground-rules)
* [3. Your First Contribution](#3-your-first-contribution)
* [4. Getting Started](#4-getting-started)
  * [4.1 Setting up your development environment](#41-setting-up-your-development-environment)
  * [4.2 Testing](#42-testing)
  * [4.3 Style](#43-style)
  * [4.4 Make](#44-make)
  * [4.5 Keeping your dependencies up to date](#45-keeping-your-dependencies-up-to-date)
  * [4.6 To contribute changes](#46-to-contribute-changes)
  * [4.7 How To Report A Bug](#47-how-to-report-a-bug)
  * [4.8 How To Suggest A Feature Or Enhancement](#48-how-to-suggest-a-feature-or-enhancement)
* [5. Community](#5-community)

# 1. Introduction
**Welcome!** First off, thank you for contributing to the further development of Red. We're always looking for new ways to improve our project and we appreciate any help you can give us.

### 1.1 Why do these guidelines exist?
Red is an open source project. This means that each and every one of the developers and contributors who have helped make Red what it is today have done so by volunteering their time and effort. It takes a lot of time to coordinate and organize issues and new features and to review and test pull requests. By following these guidelines you will help the developers streamline the contribution process and save them time. In doing so we hope to get back to each and every issue and pull request in a timely manner.

### 1.2 What kinds of contributions are we looking for?
We love receiving contributions from our community. Any assistance you can provide with regards to bug fixes, feature enhancements, and documentation is more than welcome.

# 2. Ground Rules
1. Ensure cross compatibility for Windows, macOS and Linux.
2. Ensure all Python features used in contributions exist and work in Python 3.8.1 and above.
3. If you're working on code that's covered by tests, create new tests for code you add or bugs you fix.
   It helps us help you by making sure we don't accidentally break anything :grinning:
4. Create any issues for new features you'd like to implement and explain why this feature is useful to everyone and not just you personally.
5. Don't make Pull Requests adding new functionality if there is no accepted issue discussing said functionality.
6. Be welcoming to newcomers and encourage diverse new contributors from all backgrounds. See [Python Community Code of Conduct](https://www.python.org/psf/codeofconduct/).

# 3. Your First Contribution
Unsure of how to get started contributing to Red? Please take a look at the Issues section of this repo and sort by the following labels:

* Good First Issue - issues that can normally be fixed in just a few lines of code.
* Help Wanted - issues that are currently unassigned to anyone and may be a bit more involved/complex than issues tagged with Good First Issue.

**Working on your first Pull Request?** You can learn how from this *free* series [How to Contribute to an Open Source Project on GitHub](https://app.egghead.io/playlists/how-to-contribute-to-an-open-source-project-on-github)

At this point you're ready to start making changes. Feel free to ask for help (see information about [Community](#5-community) below); everyone was a beginner at some point!

# 4. Getting Started
Red's repository is configured to follow a particular development workflow, using various reputable tools. We kindly ask that you stick to this workflow when contributing to Red, by following the guides below. This will help you to easily produce quality code, identify errors early, and streamline the code review process.

### 4.1 Setting up your development environment
The following requirements must be installed prior to setting up:
 - Python 3.8.1 or greater
 - git
 - pip
 
If you're not on Windows, you should also have GNU make installed, and you can optionally install [pyenv](https://github.com/pyenv/pyenv), which can help you run tests for different python versions.

1. Fork and clone the repository to a directory on your local machine.
    ```bash
    git clone https://github.com/Cog-Creators/Red-DiscordBot
    cd Red-DiscordBot
    ```
2. Open a command line in that directory and execute the following command:
    ```bash
    make newenv
    ```
    Red, its dependencies, and all required development tools, are now installed to a virtual environment located in the `.venv` subdirectory. Red is installed in editable mode, meaning that edits you make to the source code in the repository will be reflected when you run Red.
3. Activate the new virtual environment with one of the following commands:
    - Posix:
        ```bash
        source .venv/bin/activate
        ```
    - Windows:
        ```powershell
        .venv\Scripts\activate
        ```
    Each time you open a new command line, you should execute this command first. From here onwards, we will assume you are executing commands from within this activated virtual environment.
4. (optional but recommended) Install pre-commit hook which automatically ensures that you meet our style guide when you make a commit:
    ```bash
    pre-commit install
    ```

**Note:** If you're comfortable with setting up virtual environments yourself and would rather do it manually, just run `pip install -Ur tools/dev-requirements.txt` after setting it up and optionally install a pre-commit hook with `pre-commit install`.

### 4.2 Testing
We're using [tox](https://github.com/tox-dev/tox) to run all of our tests. It's extremely simple to use, and if you followed the previous section correctly, it is already installed to your virtual environment.

Currently, tox does the following, creating its own virtual environments for each stage:
- Runs all of our unit tests with [pytest](https://github.com/pytest-dev/pytest) on python 3.8 (test environment `py38`)
- Ensures documentation builds without warnings, and all hyperlinks have a valid destination (test environment `docs`)
- Ensures that the code meets our style guide (test environment `pre-commit`, does not run by default because it changes state of project folder and it is already checked by `pre-commit`)

To run all of these tests, just run the command `tox` in the project directory.

To run a subset of these tests, use the command `tox -e <env>`, where `<env>` is the test environment you want tox to run. The test environments are noted in the dot points above.

Your PR will not be merged until all of these tests pass.

### 4.3 Style
This project uses a bunch of style checks to ensure that all of the code is formatted consistently.
We use [pre-commit](https://pre-commit.com/) to ensure that all of these are fulfilled by all PRs made on our repositories.

If you've done the optional step of installing a pre-commit hook [4.1 Setting up your development environment](#41-setting-up-your-development-environment) section,
you actually don't have to worry about anything as all of these style checks are ran automatically whenever you make a commit. However, if you chose not to, you can:
- run all hooks on currently **staged** (`git add`ed) files with:
```bash
pre-commit
```
- or run all hooks on all files with:
```bash
pre-commit run --all-files
```

Now let's get into the specifics of the checks that we have.

Primarily, we use [Black](https://github.com/psf/black) and [ruff's import sorting](https://github.com/charliermarsh/ruff) which both are actually auto-formatters.
This means that the checking functionality simply detects whether or not it would try to reformat something in your code, should you run the formatter on it.
For this reason, we recommend using these tools as formatters, regardless of any disagreements you might have with the style they enforce.

The full style guide is explained in detail in [Black's documentation](https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html).

**There are two exceptions to this**.
Firstly, we set the line length to 99, instead of Black's default 88. This is already set in `pyproject.toml` configuration file in the repo so you do not need to specify this when running Black.
Secondly, we do not allow the usage of `# fmt: skip` and `# fmt: on/off` comments for excluding parts of code from being reformatted. **All** of the code should be formatted with Black in full.

The other auto-formatter that we use - [ruff's import sorting](https://github.com/charliermarsh/ruff) - only focuses on sorting imports alphabetically, and automatically separated into sections and by type.

Imports are sectioned based on where they import from in order:
- future imports (`from __future__ import ...`)
- imports from Python's standard library (e.g. `import collections` or `from typing import Any`)
- imports from third-party libraries (e.g. `import aiohttp` or `from discord.ext import commands`)
- imports from first-party libraries (imports from `redbot`)
- relative imports (e.g. `from .submodule import ...`)

Within a section, `from ... import ...` statements are placed *after* `import ...` statements and the imports are sorted alphabetically.

Other checks and formatters that we are using:
- [ruff](https://github.com/charliermarsh/ruff):
  This linter (check) is primarily used to prevent some common errors and bad practices.
  It might also report on some style issues though that should happen rarely when using Black formatter.

  When necessary, specific errors can be ignored with a `# noqa: CODE` annotation written above or at the end of the relevant line.
  The explanation of how this annotation works can be found in
  [ruff's documentation](https://github.com/charliermarsh/ruff#ignoring-errors).
- [end-of-file-fixer](https://github.com/pre-commit/pre-commit-hooks#end-of-file-fixer):
  This ensures that all text files have exactly one empty line at the end. This is a common practice and is often required by Unix tools.

  References:
  - [why you should end a file in a newline (beginner) anthony explains #083 on YouTube](https://www.youtube.com/watch?v=r5nWtfwK_dk)
  - [Why should text files end with a newline? on Stack Overflow](https://stackoverflow.com/questions/729692/why-should-text-files-end-with-a-newline)
- [mixed-line-ending](https://github.com/pre-commit/pre-commit-hooks#mixed-line-ending):
  This replaces usage of `CRLF` (`\r\n`) as the line ending with `LF` (`\n`). This improves consistency, minimizes git diffs
  and generally causes less problems than using `CRLF` as the line ending.
- [trailing-whitespace](https://github.com/pre-commit/pre-commit-hooks#trailing-whitespace):
  This formatter removes trailing whitespace from all lines in text files. Trailing whitespace can be somewhat annoying when working on a file
  and it can also introduce subtle bugs with multi-line string literals in Python.

  References:
  - [Why is trailing whitespace a big deal?](https://softwareengineering.stackexchange.com/questions/121555/why-is-trailing-whitespace-a-big-deal)
- [check-ast](https://github.com/pre-commit/pre-commit-hooks#check-ast),
  [check-json](https://github.com/pre-commit/pre-commit-hooks#check-json),
  [check-toml](https://github.com/pre-commit/pre-commit-hooks#check-toml),
  [check-yaml](https://github.com/pre-commit/pre-commit-hooks#check-yaml):
  These checks just verify that `.py`, `.json`, `.toml`, and `.yaml` files are using valid syntax.
- [pretty-format-json](https://github.com/pre-commit/pre-commit-hooks#pretty-format-json):
  This is an auto-formatter ensuring consistent indentation across all JSON files in the repository.
- [check-case-conflict](https://github.com/pre-commit/pre-commit-hooks#check-case-conflict):
  This checks that the repository does not contain two or more files with names that only differ in their casing (i.e. `file` and `File`).
  This is done to ensure that the repository can actually be checked out on a case-insensitive filesystem that are commonly used on
  macOS (e.g. HFS+) and Windows (e.g. NTFS and FAT).
- [check-merge-conflict](https://github.com/pre-commit/pre-commit-hooks#check-merge-conflict):
  This checks that the files do not contain merge conflict strings which can sometimes accidentally happen when resolving conflicts with git.
- [no-commit-to-branch](https://github.com/pre-commit/pre-commit-hooks#no-commit-to-branch):
  This ensures that you don't accidentally commit changes to `V3/develop` branch directly. `V3/develop` branch should never be committed
  and pushed to directly, it should only ever be modified through Pull Requests.
- [python-check-blanket-noqa](https://github.com/pre-commit/pygrep-hooks#provided-hooks):
  This checks that `noqa` annotations added to ignore errors from ruff always specify specific codes to ignore.
- [rst-directive-colons](https://github.com/pre-commit/pygrep-hooks#provided-hooks),
  [rst-inline-touching-normal](https://github.com/pre-commit/pygrep-hooks#provided-hooks):
  These check for two common issues with RST documents.
- [codespell](https://github.com/codespell-project/codespell):
  This checks for common misspellings in text files.

  When necessary, specific lines can be ignored with `.codespell-ignore-lines` file and specific words can be ignored with `.codespell-ignore-words` file.
  Usage of `.codespell-ignore-words` is generally discouraged.

### 4.4 Make
You may have noticed we have a `Makefile` and a `make.bat` in the top-level directory. For now, you can do a few things with them:
1. `make reformat`: Reformat all python files in the project with Black and ruff
2. `make stylecheck`: Check if any `.py` files in the project need reformatting with Black or ruff
3. `make newenv`: Set up a new virtual environment in the `.venv` subdirectory, and install Red and its dependencies. If one already exists, it is cleared out and replaced.
4. `make syncenv`: Sync your environment with Red's latest dependencies.

The other make recipes are most likely for project maintainers rather than contributors.

You can specify the Python executable used in the make recipes with the `PYTHON` environment variable, e.g. `make PYTHON=/usr/bin/python3.8 newenv`.

### 4.5 Keeping your dependencies up to date
Whenever you pull from upstream (V3/develop on the main repository) and you notice either of the files `setup.cfg` or `tools/dev-requirements.txt` have been changed, it can often mean some package dependencies have been updated, added or removed. To make sure you're testing and formatting with the most up-to-date versions of our dependencies, run `make syncenv`. You could also simply do `make newenv` to install them to a clean new virtual environment.

### 4.6 To contribute changes

1. Create a new branch on your fork
2. Make the changes
3. If you like the changes and think the main Red project could use it:
    * Run style checks with `pre-commit`.
    * (optional, advised if it's your first non-trivial PR to this project) Run tests with `tox` to ensure your code is up to scratch
    * Create a Pull Request on GitHub with your changes
      - If you are contributing a behavior change, please keep in mind that behavior changes
        are conditional on them being appropriate for the project's current goals.
        If you would like to reduce the risk of putting in effort for something we aren't
        going to use, open an issue discussing it first.

### 4.7 How To Report A Bug
After checking that the bug has not already been reported by someone else on our issue tracker, you should create a new issue
by choosing appropriate type of issue and **carefully** filling out the issue form. Please make sure that you include reproduction steps
and describe the issue as precisely as you can.

### 4.8 How To Suggest A Feature Or Enhancement
The goal of Red is to be as useful to as many people as possible, this means that all features must be useful to anyone and any server that uses Red.

If you find yourself wanting a feature that Red does not already have, you're probably not alone. There's bound to be a great number of users out there needing the same thing and a lot of the features that Red has today have been added because of the needs of our users. Open an issue on our issues list and describe the feature you would like to see, how you would use it, how it should work, and why it would be useful to the Red community as a whole.

# 5. Community
You can chat with the core team and other community members about issues or pull requests in the #coding channel of the Red support server located [here](https://discord.gg/red).
