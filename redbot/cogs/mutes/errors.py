class ControlFlowException(Exception):
    """ 
    The base exception for any exceptions used solely for control flow 
    If this or any subclass of this ever propogates, something has gone wrong.
    """

    pass


class NoChangeError(ControlFlowException):
    pass


class PermError(ControlFlowException):
    """
    An error to be raised when a permission issue is detected prior to an api call being made
    """

    def __init__(self, friendly_error=None, *args):
        self.friendly_error = friendly_error
        super().__init__(*args)
