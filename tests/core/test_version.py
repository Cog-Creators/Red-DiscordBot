from redbot import core


def test_version_working():
    assert hasattr(core, '__version__')
    assert core.__version__ >= (3, 0, 0)
