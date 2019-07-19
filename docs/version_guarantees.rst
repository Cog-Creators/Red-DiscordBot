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
