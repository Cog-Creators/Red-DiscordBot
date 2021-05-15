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
* [5. Code Review Process](#5-code-review-process)
  * [5.1 Issues](#51-issues)
  * [5.2 Pull Requests](#52-pull-requests)
  * [5.3 Differences between "new features" and "improvements"](#53-differences-between-new-features-and-improvements)
* [6. Community](#6-community)

# 1. Introduction
**Welcome!** First off, thank you for contributing to the further development of Red. We're always looking for new ways to improve our project and we appreciate any help you can give us.

### 1.1 Why do these guidelines exist?
Red is an open source project. This means that each and every one of the developers and contributors who have helped make Red what it is today have done so by volunteering their time and effort. It takes a lot of time to coordinate and organize issues and new features and to review and test pull requests. By following these guidelines you will help the developers streamline the contribution process and save them time. In doing so we hope to get back to each and every issue and pull request in a timely manner.

### 1.2 What kinds of contributions are we looking for?
We love receiving contributions from our community. Any assistance you can provide with regards to bug fixes, feature enhancements, and documentation is more than welcome.

# 2. Ground Rules
1. Ensure cross compatibility for Windows, Mac OS and Linux.
2. Ensure all Python features used in contributions exist and work in Python 3.8.1 and above.
3. Create new tests for code you add or bugs you fix. It helps us help you by making sure we don't accidentally break anything :grinning:
4. Create any issues for new features you'd like to implement and explain why this feature is useful to everyone and not just you personally.
5. Don't add new cogs unless specifically given approval in an issue discussing said cog idea.
6. Be welcoming to newcomers and encourage diverse new contributors from all backgrounds. See [Python Community Code of Conduct](https://www.python.org/psf/codeofconduct/).

# 3. Your First Contribution
Unsure of how to get started contributing to Red? Please take a look at the Issues section of this repo and sort by the following labels:

* beginner - issues that can normally be fixed in just a few lines of code and maybe a test or two.
* help-wanted - issues that are currently unassigned to anyone and may be a bit more involved/complex than issues tagged with beginner.

**Working on your first Pull Request?** You can learn how from this *free* series [How to Contribute to an Open Source Project on GitHub](https://app.egghead.io/playlists/how-to-contribute-to-an-open-source-project-on-github)

At this point you're ready to start making changes. Feel free to ask for help; everyone was a beginner at some point!

# 4. Getting Started

Red's repository is configured to follow a particular development workflow, using various reputable tools. We kindly ask that you stick to this workflow when contributing to Red, by following the guides below. This will help you to easily produce quality code, identify errors early, and streamline the code review process.

### 4.1 Setting up your development environment
The following requirements must be installed prior to setting up:
 - Python 3.8.1 or greater
 - git
 - pip
 
If you're not on Windows, you should also have GNU make installed, and you can optionally install [pyenv](https://github.com/pyenv/pyenv), which can help you run tests for different python versions.

1. Fork and clone the repository to a directory on your local machine.
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
 
**Note:** If you're comfortable with setting up virtual environments yourself and would rather do it manually, just run `pip install -Ur tools/dev-requirements.txt` after setting it up.

### 4.2 Testing
We're using [tox](https://github.com/tox-dev/tox) to run all of our tests. It's extremely simple to use, and if you followed the previous section correctly, it is already installed to your virtual environment.

Currently, tox does the following, creating its own virtual environments for each stage:
- Runs all of our unit tests with [pytest](https://github.com/pytest-dev/pytest) on python 3.8 (test environment `py38`)
- Ensures documentation builds without warnings, and all hyperlinks have a valid destination (test environment `docs`)
- Ensures that the code meets our style guide with [black](https://github.com/psf/black) (test environment `style`)

To run all of these tests, just run the command `tox` in the project directory.

To run a subset of these tests, use the command `tox -e <env>`, where `<env>` is the test environment you want tox to run. The test environments are noted in the dot points above.

Your PR will not be merged until all of these tests pass.

### 4.3 Style
Our style checker of choice, [black](https://github.com/psf/black), actually happens to be an auto-formatter. The checking functionality simply detects whether or not it would try to reformat something in your code, should you run the formatter on it. For this reason, we recommend using this tool as a formatter, regardless of any disagreements you might have with the style it enforces.

Use the command `black --help` to see how to use this tool. The full style guide is explained in detail on [black's GitHub repository](https://github.com/psf/black). **There is one exception to this**, however, which is that we set the line length to 99, instead of black's default 88. This is already set in `pyproject.toml` configuration file in the repo so you can simply format code with Black like so: `black <src>`.

### 4.4 Make
You may have noticed we have a `Makefile` and a `make.bat` in the top-level directory. For now, you can do a few things with them:
1. `make reformat`: Reformat all python files in the project with Black
2. `make stylecheck`: Check if any `.py` files in the project need reformatting
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
    * Run tests with `tox` to ensure your code is up to scratch
    * Create a Pull Request on GitHub with your changes
      - If you are contributing a behavior change, please keep in mind that behavior changes
        are conditional on them being appropriate for the project's current goals.
        If you would like to reduce the risk of putting in effort for something we aren't
        going to use, open an issue discussing it first.

### 4.7 How To Report A Bug
Please see our **ISSUES.MD** for more information.

### 4.8 How To Suggest A Feature Or Enhancement
The goal of Red is to be as useful to as many people as possible, this means that all features must be useful to anyone and any server that uses Red.

If you find yourself wanting a feature that Red does not already have, you're probably not alone. There's bound to be a great number of users out there needing the same thing and a lot of the features that Red has today have been added because of the needs of our users. Open an issue on our issues list and describe the feature you would like to see, how you would use it, how it should work, and why it would be useful to the Red community as a whole.

# 5. Code Review Process

We have a core team working tirelessly to implement new features and fix bugs for the Red community. This core team looks at and evaluates new issues and PRs on a daily basis.

The decisions we make are based on a simple majority of that team or by decree of the project owner.

### 5.1 Issues
Any new issues will be looked at and evaluated for validity of a bug or for the usefulness of a suggested feature. If we have questions about your issue we will get back as soon as we can (usually in a day or two) and will try to make a decision within a week.

### 5.2 Pull Requests
Pull requests are evaluated by their quality and how effectively they solve their corresponding issue. The process for reviewing pull requests is as follows:

1. A pull request is submitted
2. Core team members will review and test the pull request (usually within a week)
3. After a member of the core team approves your pull request:
    * If your pull request is considered an improvement or enhancement the project owner will have 1 day to veto or approve your pull request.
    * If your pull request is considered a new feature the project owner will have 1 week to veto or approve your pull request.
4. If any feedback is given we expect a response within 1 week or we may decide to close the PR.
5. If your pull request is not vetoed and no core member requests changes then it will be approved and merged into the project.

### 5.3 Differences between "new features" and "improvements"
The difference between a new feature and improvement can be quite fuzzy and the project owner reserves all rights to decide under which category your PR falls.

At a very basic level a PR is a new feature if it changes the intended way any part of the Red project currently works or if it modifies the user experience (UX) in any significant way. Otherwise, it is likely to be considered an improvement.

# 6. Community
You can chat with the core team and other community members about issues or pull requests in the #coding channel of the Red support server located [here](https://discord.gg/red).
