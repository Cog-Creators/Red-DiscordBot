.. _version-guarantees:

==========
Versioning
==========

Red uses semantic versioning.

==========
Guarantees
==========

Anything in the ``redbot.core`` module or any of it's submodules 
which is not private (even if not documented) should not break without notice.

Anything in the ``redbot.cogs`` module or any of it's submodules is specifically
excluded from being guaranteed.

If you would like something in here to be guaranteed,
open an issue making a case for it to be moved.

=======================
Breaking Change Notices
=======================

Breaking changes in Red will be noted in the changelog with a special section.

Breaking changes may only occur on a minor or major version bump.

A change not covered by our guarantees may not be considered breaking for these purposes, 
while still being documented as a breaking change in internal documentation
for the purposes of other internal APIs
