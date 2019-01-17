.. third party requirements

.. role:: python(code)
    :language: python


==================================
Third Party Developer Requirements
==================================
This document provides policy and guidelines for all third-party developers who make cogs for Red Discord Bot. The standards within, are designed to provide a better experience for the community. While every cog may be different, it is important to have a level of predictability on how each is used and operated. Meeting these requirements ensures that your repository is safe, working, and intuitive. Questions regarding these policies and guidelines should be directed to QA.

*******************
Repository Template
*******************

We have standardized what a repository's structure should look like to better assist our downloader system and provide essential information to the Red portal.

The main repository should contain at a minimum:
 
 - A readme file (can be either .MD or .rst)
 - A info.json file (`examples <tpd_requirements.html#info-jsons>`_)
 - One folder for each cog package in the repository
 - A license (Not required, but recommended)

For a simple example of what this might look like when finished, take a look at our example template.

README
======
The readme file can be either an .MD or a .rst. However, it should contain, at a minimum the following: 

  **Repository Name** - Examples: Snuffy's Cogs, Bobo's Plugins, Cat-Toys, etc

  **Installation Instructions** - Tell the user how to download your repo and access your cogs. Any additional hurdles to using your 
  creations should be added here as well.

  **Requirements** - Any third party libraries or other requirements you feel necessary for the use of your cogs.

  **Credits** - You must credit anyone whose code you might have used or whom you received a substantial amount of help from.

  **Contact** - How to contact you about bugs, issues, or suggestions. 

  **License** - This is not required, but we do recommend having one.


Info Jsons
==========
There are two info.json files. One that goes into each cog folder and one at the main level of your repository. Each have similar keys, but serve a different purpose. The following keys are required:

**Repository Level**

 - author
 - install_msg
 - name
 - short
 - requirements
 - description
 - tags

**Cog Level**

 - author
 - install_msg
 - name
 - short
 - requirements
 - description
 - tags
 - min_python_version
 - permissions (Senior Only)

You may include as many optional keys as you wish. For more information these keys and their meaning, `read about it here <framework_downloader.html#info-json>`_

.. note::

    If your cog comes bundled with data, or creates any folder or files (outside of config), then this must be disclosed in your 
    installation message.

Cog Package Folder
^^^^^^^^^^^^^^^^^^
The cog folder has the following requirements:

- The folder name, must match the cog.py name. It should be in all lowercase letters
- The folder should contain an info.json file. Read above for more details on the specific keys needed
- An __init__.py for the cog
- The .py file for the cog. (in all lowercase letters)
- Any helper files or bundled data should be here as well

.. important::

    If your cog comes bundled with data, you are required to put it all into a folder named **data**. You may name any sub-directories 
    of this folder however you wish. 

********************
General Requirements
********************
These are general requirements that everyone should follow:

- No cog contains malicious code.
- No stolen or copied code found without proper credits.
- Disclose if a cog has heavy memory or I/O usage.
- Disclose if your cog collects any data.
- Disclose if your cog contains any NSFW material.
- Disclose if your cog creates or comes bundled with data outside of using Config.
- Your code is async compatible (not blocking).
- Does not break the Discord TOS.
- Does not conflict with core cogs. (E.G., it does not cause a core cog to fail to load).
- Contains at least three cogs. (See `ctx.send_filtered <tpd_requirements.html#quality-vs-quantity>`__)
- Does not over-saturate the current list of cogs.
- Unusable commands are hidden.
- Default locale must be English.
- Credited other authors when applicable.

*******************
Coding Requirements
*******************

- Class names must be CamelCase.
- The main cog class and every command must have a doc-string.
- Sanitize outputs when sending a user specified text. We recommend using `ctx.send_filtered <framework_bot.html#redbot.core.bot.RedBase.send_filtered>`__
- Respect the role hierarchy. Don't let a lower role have a way to grant a higher role.
- Don't write your own path to your included data. Use bundled data_path when possible.
- Your main class should inherit from commands.Cog.
- Use instance variables over globals whenever possible.
- f-strings are incompatible with translation, so choose one or the other.
- For most use-cases you should be using config for your I/O.
- Use converters in command arguments instead of strings when applicable. 

We have created a lot of tools to help eliminate boilerplate code. We may, at times, ask that you use some of these tools instead of writing your own, when appropriate. For example, ctx.send_filtered vs your own sanitized output.

*******************************
Senior Cog Creator Requirements
*******************************

Senior cog creators will have the following additional requirements:

- Code conforms to a style (PEP8 or Black recommended)
- Code gracefully handles errors
- Declared supported platforms
- Applicant has a positive attitude
- Responds well to feedback and criticism
- Regularly active
- In good standing with the community
- Cogs are designed maintain-ably
- Displays leadership qualities
- Repository adds something unique to the community


*********************
Quality vs. Quantity
*********************


QA will not reject an application solely on the repository not having three cogs. This rule is loosely in-place for developers who are very new to programming. We would rather these developers focus on honing their craft into three strong examples that represent their repository. In the same token, QA reserves the right to reject a repository that has several really tiny cogs, whose sum could be a simple custom command.

When looking at a repository with less than three cogs, we look for the following qualities to be demonstrated in the work:
 
- How unique is this cog? (Are there any others like it on cogs.red?)
- How creative is the cog? (Is it fun or solve a common problem?)
- How complex is it? (Does the size, feature-set, or utility dwarf most cogs?)

***************
Over Saturation
***************
QA will not deny a repository, simple because another repository has a cog that fulfills a similar function. We believe that the community has the right to choose which cog is best suited to their needs. Competition can also be a fantastic motivator, and only has positive benefits for the user-base. However, unlike javascript, we don't think that every problem requires a new framework. QA may reject an application if the repository has a limited number of cogs, and one or more is too similar in function to everything else on the market.
