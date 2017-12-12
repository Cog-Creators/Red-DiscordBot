This is a faithful port of the “Adventure” game to Python 3 from the
original 1977 FORTRAN code by Crowther and Woods (it is driven by the
same ``advent.dat`` file!) that lets you explore Colossal Cave, where
others have found fortunes in treasure and gold, though it is rumored
that some who enter are never seen again.  To encourage the use of
Python 3, the game is designed to be played right at the Python prompt.
Single-word commands can be typed by themselves, but two-word commands
should be written as a function call (since a two-word command would not
be valid Python)::

    >>> import adventure
    >>> adventure.play()
    WELCOME TO ADVENTURE!!  WOULD YOU LIKE INSTRUCTIONS?

    >>> no
    YOU ARE STANDING AT THE END OF A ROAD BEFORE A SMALL BRICK BUILDING.
    AROUND YOU IS A FOREST.  A SMALL STREAM FLOWS OUT OF THE BUILDING AND
    DOWN A GULLY.

    >>> east
    YOU ARE INSIDE A BUILDING, A WELL HOUSE FOR A LARGE SPRING.
    THERE ARE SOME KEYS ON THE GROUND HERE.
    THERE IS A SHINY BRASS LAMP NEARBY.
    THERE IS FOOD HERE.
    THERE IS A BOTTLE OF WATER HERE.

    >>> get(lamp)
    OK

    >>> leave
    YOU'RE AT END OF ROAD AGAIN.

    >>> south
    YOU ARE IN A VALLEY IN THE FOREST BESIDE A STREAM TUMBLING ALONG A
    ROCKY BED.

The original Adventure paid attention to only the first five letters of
each command, so a long command like ``inventory`` could simply be typed
as ``inven``.  This package defines a symbol for both versions of every
long word, so you can type the long or short version as you please.

You can save your game at any time by calling the ``save()`` command
with a filename, and then can resume it later::

    >>> save('advent.save')
    GAME SAVED

    >>> adventure.resume('advent.save')
    GAME RESTORED
    >>> look
    SORRY, BUT I AM NOT ALLOWED TO GIVE MORE DETAIL.  I WILL REPEAT THE
    LONG DESCRIPTION OF YOUR LOCATION.
    YOU ARE IN A VALLEY IN THE FOREST BESIDE A STREAM TUMBLING ALONG A
    ROCKY BED.

You can find two complete, working walkthroughs of the game in its
``tests`` directory, which you can run using the ``discover`` module that
comes built-in with Python 3::

    $ python3 -m unittest discover adventure

I wrote most of this package over Christmas vacation 2010, to learn more
about the workings of the game that so enthralled me as a child; the
project also gave me practice writing Python 3.  I still forget the
parentheses when writing ``print()`` if I am not paying attention.

Traditional Mode
================

You can also use this package to play Adventure at a traditional prompt
that does not require its input to be valid Python.  Use your operating
system command line to run the package::

    $ python3 -m adventure
    WELCOME TO ADVENTURE!!  WOULD YOU LIKE INSTRUCTIONS?

    >

At the prompt that will appear, two-word commands can simply be
separated by a space::

    > get lamp
    OK

For extra authenticity, the output of the Adventure game in this mode is
typed to your screen at 1200 baud.  You will note that although this
prints the text faster than you can read it anyway, your experience of
the game will improve considerably, especially when a move results in a
surprise.

Why is the game better at 1200 baud?  When a paragraph of text is
allowed to appear on the screen all at once, your eyes scan the entire
paragraph for important information, often ruining any surprises before
you can then settle down and read it from the beginning.  But at 1200
baud, you wind up reading the text in order as it appears, which unfolds
the narrative sequentially as the author of Adventure intended.

If you created a file with the in-game ``save`` command, you can restore
it later by naming it on the command line::

    > save mygame
    GAME SAVED
    > quit
    DO YOU REALLY WANT TO QUIT NOW?
    > y
    OK

    $ python3 -m adventure mygame
    GAME RESTORED
    >

Notes
=====

* Several Adventure commands conflict with standard Python built-in
  functions.  If you want to run the normal Python function ``exit()``,
  ``open()``, ``quit()``, or ``help()``, then import the ``builtin``
  module and run the copy of the function stored there.

* The word “break” is a Python keyword, so there was no possibility of
  using it in the game.  Instead, use one of the two synonyms defined by
  the PDP version of Adventure: “shatter” or “smash.”

Copyright
=========

The ``advent.dat`` game data file distributed with this Python package,
like the rest of the original source code for Adventure, is a public
domain work.  Phrases from the original work that have been copied into
my source code from the FORTRAN source (the famous phrase “You have
gotten yourself killed” and so forth) remain public domain and can be
used without attribution.

My own Python code that re-implements the game engine is:

Copyright 2010–2015 Brandon Rhodes

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Changelog
=========

| 1.4 — 2016 January 31 — readline editing; added license; bug fix; test fix.
| 1.3 — 2012 April 27 — installs on Windows; fixed undefined commands
| 1.2 — 2012 April 5 — restoring saves from command line; 5-letter commands
| 1.1 — 2011 March 12 — traditional mode; more flexible Python syntax
| 1.0 — 2011 February 15 — 100% test coverage, feature-complete
| 0.3 — 2011 January 31 — first public release