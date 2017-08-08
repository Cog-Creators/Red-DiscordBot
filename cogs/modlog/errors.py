class ModError(Exception):
    pass


class UnauthorizedCaseEdit(ModError):
    pass


class CaseMessageNotFound(ModError):
    pass


class NoModLogChannel(ModError):
    pass


class NoModLogAccess(ModError):
    pass


class CaseTypeNotEnabled(ModError):
    pass


class InvalidCaseType(ModError):
    pass
