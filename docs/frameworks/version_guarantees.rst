.. _version-guarantees:

==========
Versioning
==========

Red is versioned as ``major.minor.micro``

While this is very similar to SemVer, we have our own set of guarantees.

Major versions are for project wide rewrites and are not expected in the foreseeable future.

==========
Guarantees
==========

Anything in the ``redbot.core`` module or any of its submodules 
which is not private (even if not documented) should not break without notice.

Anything in the ``redbot.cogs`` and ``redbot.vendored`` modules or any of their submodules is specifically
excluded from being guaranteed.

Method names and names of attributes of classes, functions, extensions, and modules
provided by or provided to the bot should not begin with 
``red_`` or be of the form ``__red_*__`` except as documented.
This allows us to add certain optional features non-breakingly without a name conflict.

Any RPC method exposed by Red may break without notice.

If you would like something in here to be guaranteed,
open an issue making a case for it to be moved.

=======================
Breaking Change Notices
=======================

Breaking changes in Red will be noted in the changelog with a special section.

Breaking changes may only occur on a minor or major version bump.

A change not covered by our guarantees may not be considered breaking for these purposes, 
while still being documented as a breaking change in internal documentation
for the purposes of other internal APIs.
