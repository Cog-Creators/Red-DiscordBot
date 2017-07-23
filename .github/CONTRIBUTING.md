# Introduction
### Welcome!
First off, thank you for contributing to the further development of Red. We're always looking for new ways to improve our project and we appreciate any help you can give us.

### Why do these guidelines exist?
Red is an open source project. This means that each and every one of the developers and contributors who have helped make Red what it is today have done so by volunteering their time and effort. It takes a lot of time to coordinate and organize issues and new features and to review and test pull requests. By following these guidelines you will help the developers streamline the contribution process and save them time. In doing so we hope to get back to each and every issue and pull request in a timely manner.

### What kinds of contributions are we looking for?
We love receiving contributions from our community. Any assistance you can provide with regards to bug fixes, feature enhancements, and documentation is more than welcome.

However, please do **NOT** use the issue tracker for support questions. Any questions or comments of that nature can be answered on our support server located [here](https://discord.gg/red).

# Ground Rules
We've made a point to use [ZenHub](https://www.zenhub.com/) (a plugin for GitHub) as our main source of collaboration and coordination. Your experience contributing to Red will be greatly improved if you go get that plugin.
1. Ensure cross compatibility for Windows, Mac OS and Linux.
2. Ensure all Python features used in contributions exist and work in Python 3.5 and above.
3. Create new tests for code you add or bugs you fix. It helps us help you by making sure we don't accidentally break anything :grinning:
4. Create any issues for new features you'd like to implement and explain why this feature is useful to everyone and not just you personally.
5. Don't add new cogs unless specifically given approval in an issue discussing said cog idea.
6. Be welcoming to newcomers and encourage diverse new contributors from all backgrounds. See [Python Community Code of Conduct](https://www.python.org/psf/codeofconduct/).

# Your First Contribution
Unsure of how to get started contributing to Red? Please take a look at the Issues section of this repo and sort by the following labels:

* beginner - issues that can normally be fixed in just a few lines of code and maybe a test or two.
* help-wanted - issues that are currently unassigned to anyone and may be a bit more involved/complex than issues tagged with beginner.

**Working on your first Pull Request?** You can learn how from this *free* series [How to Contribute to an Open Source Project on GitHub](https://egghead.io/series/how-to-contribute-to-an-open-source-project-on-github)

At this point you're ready to start making changes. Feel free to ask for help; everyone was a beginner at some point!

# Getting Started
### Testing
We've recently started adding unit-testing into Red. All current tests can be found in the `tests/` directory at the root level of the repository. You will need `py.test` installed in order to run them (which is already in `requirement.txt`). Tests can be run by simply calling `pytest` once you've `cd`'d into the Red repository folder.

### To contribute changes
1. Create your own fork of the Red repository.
2. Make the changes in your own fork.
3. If you like the changes and think the main Red project could use it:
    * Ensure your code follows (generally) the PEP8 Python style guide
    * Create a Pull Request on GitHub with your changes

### How To Report A Bug
Please see our **ISSUES.MD** for more information.

### How To Suggest A Feature Or Enhancement
The goal of Red is to be as useful to as many people as possible, this means that all features must be useful to anyone and any server that uses Red.

If you find yourself wanting a feature that Red does not already have, you're probably not alone. There's bound to be a great number of users out there needing the same thing and a lot of the features that Red has today have been added because of the needs of our users. Open an issue on our issues list and describe the feature you would like to see, how you would use it, how it should work, and why it would be useful to the Red community as a whole.

# Code Review Process

We have a core team working tirelessly to implement new features and fix bugs for the Red community. This core team looks at and evaluates new issues and PRs on a daily basis.

The decisions we make are based on a simple majority of that team or by decree of the project owner.

### Issues
Any new issues will be looked at and evaluated for validity of a bug or for the usefulness of a suggested feature. If we have questions about your issue we will get back as soon as we can (usually in a day or two) and will try to make a decision within a week.

### Pull Requests
Pull requests are evaluated by their quality and how effectively they solve their corresponding issue. The process for reviewing pull requests is as follows:

1. A pull request is submitted
2. Core team members will review and test the pull request (usually within a week)
3. After a majority of the core team approves your pull request:
    * If your pull request is considered an improvement or enhancement the project owner will have 1 day to veto or approve your pull request.
    * If your pull request is considered a new feature the project owner will have 1 week to veto or approve your pull request.
4. If any feedback is given we expect a response within 1 week or we may decide to close the PR.
5. If your pull request is not vetoed and no core member requests changes then it will be approved and merged into the project.

### Differences between "new features" and "improvements"
The difference between a new feature and improvement can be quite fuzzy and the project owner reserves all rights to decide under which category your PR falls.

At a very basic level a PR is a new feature if it changes the intended way any part of the Red project currently works or if it modifies the user experience (UX) in any significant way. Otherwise, it is likely to be considered an improvement.

# Community
You can chat with the core team and other community members about issues or pull requests in the #coding channel of the Red support server located [here](https://discord.gg/red).
