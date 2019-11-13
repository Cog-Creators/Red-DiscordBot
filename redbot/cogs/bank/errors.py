class BankError(Exception):
    pass


class BankNotGlobal(BankError):
    pass


class BankIsGlobal(BankError):
    pass


class AccountAlreadyExists(BankError):
    pass


class NoAccount(BankError):
    pass


class NoSenderAccount(NoAccount):
    pass


class NoReceiverAccount(NoAccount):
    pass


class InsufficientBalance(BankError):
    pass


class NegativeValue(BankError):
    pass


class SameSenderAndReceiver(BankError):
    pass
