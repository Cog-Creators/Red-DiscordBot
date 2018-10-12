from redbot.core.utils.mod import is_mod_or_superior as ims, is_allowed_by_hierarchy as iah , get_audit_reason as gar
from .log import log as mlog

class UtilsMixin:
    """
    This is really just a laziness issue for this one
    """

    @property
    def is_mod_or_superior(self):
        return ims

    @property
    def is_allowed_by_hierarchy(self):
        return iah

    @property
    def get_audit_reason(self):
        return gar
    
    @property
    def log(self):
        return mlog