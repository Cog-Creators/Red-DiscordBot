=========
multidict
=========

.. image:: https://img.shields.io/pypi/v/multidict.svg
   :target: https://pypi.org/project/multidict

.. image:: https://readthedocs.org/projects/multidict/badge/?version=latest
   :target: http://multidict.readthedocs.org/en/latest/?badge=latest

.. image:: https://img.shields.io/travis/aio-libs/multidict/master.svg?label=Linux%20build%20%40%20Travis%20CI
   :align: right
   :target: http://travis-ci.org/aio-libs/multidict

.. image:: https://img.shields.io/appveyor/ci/asvetlov/multidict/master.svg?label=Windows%20build%20%40%20Appveyor
   :align: right
   :target: https://ci.appveyor.com/project/asvetlov/multidict/branch/master

.. image:: https://img.shields.io/pypi/pyversions/multidict.svg
   :target: https://pypi.org/project/multidict

.. image:: https://codecov.io/gh/aio-libs/multidict/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/aio-libs/multidict
   :alt: Coverage metrics

.. image:: https://badges.gitter.im/Join%20Chat.svg
   :target: https://gitter.im/aio-libs/Lobby
   :alt: Chat on Gitter

Multidict is dict-like collection of *key-value pairs* where key
might be occurred more than once in the container.

Introduction
------------

*HTTP Headers* and *URL query string* require specific data structure:
*multidict*. It behaves mostly like a regular ``dict`` but it may have
several *values* for the same *key* and *preserves insertion ordering*.

The *key* is ``str`` (or ``istr`` for case-insensitive dictionaries).

``multidict`` has four multidict classes:
``MultiDict``, ``MultiDictProxy``, ``CIMultiDict``
and ``CIMultiDictProxy``.

Immutable proxies (``MultiDictProxy`` and
``CIMultiDictProxy``) provide a dynamic view for the
proxied multidict, the view reflects underlying collection changes. They
implement the ``collections.abc.Mapping`` interface.

Regular mutable (``MultiDict`` and ``CIMultiDict``) classes
implement ``collections.abc.MutableMapping`` and allows to change
their own content.


*Case insensitive* (``CIMultiDict`` and
``CIMultiDictProxy``) ones assume the *keys* are case
insensitive, e.g.::

   >>> dct = CIMultiDict(key='val')
   >>> 'Key' in dct
   True
   >>> dct['Key']
   'val'

*Keys* should be ``str`` or ``istr`` instances.

The library has optional Cython_ optimization for sake of speed.


License
-------

Apache 2


.. _aiohttp: https://github.com/KeepSafe/aiohttp
.. _Cython: http://cython.org/

3.3.2 (2017-11-02)
------------------

* Fix tarball (again)


3.3.1 (2017-11-01)
------------------

* Include .c files in tarball (#181)


3.3.0 (2017-10-15)
------------------

* Introduce abstract base classes (#102)

* Publish OSX binary wheels (#153)


3.2.0 (2017-09-17)
------------------

* Fix pickling (#134)

* Fix equality check when other contains more keys (#124)

* Fix `CIMultiDict` copy (#107)

3.1.3 (2017-07-14)
------------------

* Fix build

3.1.2 (2017-07-14)
------------------

* Fix type annotations

3.1.1 (2017-07-09)
------------------

* Remove memory leak in `istr` implementation (#105)

3.1.0 (2017-06-25)
------------------

* Raise `RuntimeError` on dict iterations if the dict was changed (#99)

* Update `__init__.pyi` signatures

3.0.0 (2017-06-21)
------------------

* Refactor internal data structures: main dict operations are about
  100% faster now.

* Preserve order on multidict updates (#68)

  Updates are `md[key] = val` and `md.update(...)` calls.

  Now **the last** entry is replaced with new key/value pair, all
  previous occurrences are removed.

  If key is not present in dictionary the pair is added to the end

* Force keys to `str` instances (#88)

* Implement `.popall(key[, default])` (#84)

* `.pop()` removes only first occurence, `.popone()` added (#92)

* Implement dict's version (#86)

* Proxies are not pickable anymore (#77)

2.1.7 (2017-05-29)
------------------

* Fix import warning on Python 3.6 (#79)

2.1.6 (2017-05-27)
------------------

* Rebuild the library for fixning missing `__spec__` attribute (#79)

2.1.5 (2017-05-13)
------------------

* Build Python 3.6 binary wheels

2.1.4 (2016-12-1)
------------------

* Remove LICENSE filename extension @ MANIFEST.in file (#31)

2.1.3 (2016-11-26)
------------------

* Add a fastpath for multidict extending by multidict


2.1.2 (2016-09-25)
------------------

* Fix `CIMultiDict.update()` for case of accepting `istr`


2.1.1 (2016-09-22)
------------------

* Fix `CIMultiDict` constructor for case of accepting `istr` (#11)


2.1.0 (2016-09-18)
------------------

* Allow to create proxy from proxy

* Add type hints (PEP-484)


2.0.1 (2016-08-02)
------------------

* Don't crash on `{} - MultiDict().keys()` and similar operations (#6)


2.0.0 (2016-07-28)
------------------

* Switch from uppercase approach for case-insensitive string to
  `str.title()` (#5)

* Deprecase `upstr` class in favor of `istr` alias.

1.2.2 (2016-08-02)
------------------

* Don't crash on `{} - MultiDict().keys()` and similar operations (#6)

1.2.1 (2016-07-21)
------------------

* Don't expose `multidict.__version__`


1.2.0 (2016-07-16)
------------------

* Make `upstr(upstr('abc'))` much faster


1.1.0 (2016-07-06)
------------------

* Don't double-iterate during MultiDict initialization (#3)

* Fix CIMultiDict.pop: it is case insensitive now (#1)

* Provide manylinux wheels as well as Windows ones

1.0.3 (2016-03-24)
------------------

* Add missing MANIFEST.in

1.0.2 (2016-03-24)
------------------

* Fix setup build


1.0.0 (2016-02-19)
------------------

* Initial implementation

