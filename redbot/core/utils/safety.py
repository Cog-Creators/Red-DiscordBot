import warnings
import functools


def unsafe(f, message=None):
    """
    Decorator form for marking a function as unsafe.

    This form may not get used much, but there are a few cases
    we may want to add something unsafe generally, but safe in specific uses.

    The warning can be supressed in the safe context with warnings.catch_warnings
    This should be used sparingly at most.
    """

    def wrapper(func):
        @functools.wraps(func)
        def get_wrapped(*args, **kwargs):
            actual_message = message or f"{func.__name__} is unsafe for use"
            warnings.warn(actual_message, stacklevel=3, category=RuntimeWarning)
            return func(*args, **kwargs)

        return get_wrapped

    return wrapper


def warn_unsafe(f, message=None):
    """
    Function to mark function from dependencies as unsafe for use.

    Warning: There is no check that a function has already been modified.
    This form should only be used in init, if you want to mark an internal function
    as unsafe, use the decorator form above.

    The warning can be suppressed in safe contexts with warnings.catch_warnings
    This should be used sparingly at most.
    """

    def wrapper(func):
        @functools.wraps(func)
        def get_wrapped(*args, **kwargs):
            actual_message = message or f"{func.__name__} is unsafe for use"
            warnings.warn(actual_message, stacklevel=3, category=RuntimeWarning)
            return func(*args, **kwargs)

        return get_wrapped

    return wrapper(f)
