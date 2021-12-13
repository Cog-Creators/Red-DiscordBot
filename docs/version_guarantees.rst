.. _version-guarantees:

==========
Versioning
==========

Red is versioned as ``major.minor.micro``

While this is very similar to SemVer, we have our own set of guarantees.

Major versions are for project wide rewrites and are not expected in the foreseeable future.

===================
End-user Guarantees
===================

Red `provides support for wide variety of operating systems <install_guides/index>`.

Support for an entire operating system may only be dropped in a minor or major version bump.

Red will continue to, at the very least, support current latest stable version of
each operating system that was supported by previous micro versions.

In addition to that, we strive (but do not guarantee) to provide support for all versions that
are currently supported by operating system's developers per the table below.
We generally drop support for no longer supported OS versions as soon as they reached
their end-of-life date.

.. note::

    We recommend to always use the latest OS version supported by Red.

================================   ============================================================
Operating system version           Ideally supported until
================================   ============================================================
Windows 10                         `End/Retirement Date <https://docs.microsoft.com/en-us/lifecycle/products/windows-10-home-and-pro>`__
Windows 11                         `Retirement Date <https://docs.microsoft.com/en-us/lifecycle/products/windows-11-home-and-pro-version-21h2>`__
macOS 10.15 (Catalina)             ~2022-10
macOS 11 (Big Sur)                 ~2023-10
macOS 12 (Monterey)                ~2024-10
Alma Linux 8                       2029-05-31 (`How long will CloudLinux support AlmaLinux? <https://wiki.almalinux.org/FAQ.html#how-long-will-cloudlinux-support-almalinux>`__)
Arch Linux                         forever (support is only provided for an up-to-date system)
CentOS 7                           2024-06-30 (`end of Maintenance Updates <https://wiki.centos.org/About/Product>`__)
CentOS Stream 8                    2024-05-31 (`end of Maintenance Updates <https://wiki.centos.org/About/Product>`__)
Debian 10 Buster                   2022-08-14 (`End of life <https://wiki.debian.org/DebianReleases#Production_Releases>`__)
Debian 11 Bullseye                 ~2024-09 (`End of life <https://wiki.debian.org/DebianReleases#Production_Releases>`__)
Fedora Linux 34                    2022-05-17 (`End of Life <https://fedoraproject.org/wiki/Fedora_Release_Life_Cycle#Maintenance_Schedule>`__)
Fedora Linux 35                    ~2022-11 (`End of Life <https://fedoraproject.org/wiki/Fedora_Release_Life_Cycle#Maintenance_Schedule>`__)
openSUSE Leap 15.2                 2021-12-31 (`end of maintenance life cycle <https://en.opensuse.org/Lifetime#openSUSE_Leap>`__)
openSUSE Leap 15.3                 2022-11-30 (`end of maintenance life cycle <https://en.opensuse.org/Lifetime#openSUSE_Leap>`__)
openSUSE Tumbleweed                forever (support is only provided for an up-to-date system)
Oracle Linux 8                     2029-07-31 (`End of Premier Support <https://www.oracle.com/us/support/library/elsp-lifetime-069338.pdf>`__)
Raspberry Pi OS (Legacy) 10        2022-08-14 (`End of life for Debian 10 <https://wiki.debian.org/DebianReleases#Production_Releases>`__)
Raspberry Pi OS 11                 ~2023-12 (approximate date of release of Raspberry Pi OS 12)
RHEL 8 (latest)                    2029-05-31 (`End of Maintenance Support <https://access.redhat.com/support/policy/updates/errata#Life_Cycle_Dates>`__)
RHEL 8.4                           2023-05-30 (`End of Extended Update Support <https://access.redhat.com/support/policy/updates/errata#Extended_Update_Support>`__)
Rocky Linux 8                      2029-05-31 (`end-of-life <https://rockylinux.org/download/>`__)
Ubuntu 18.04 LTS                   2023-04-30 (`End of Standard Support <https://wiki.ubuntu.com/Releases#Current>`__)
Ubuntu 20.04 LTS                   2025-04-30 (`End of Standard Support <https://wiki.ubuntu.com/Releases#Current>`__)
Ubuntu 21.10                       2022-07-31 (`End of Standard Support <https://wiki.ubuntu.com/Releases#Current>`__)
================================   ============================================================

====================
Developer Guarantees
====================

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
