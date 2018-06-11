from .config import Config

__all__ = ["Config", "__version__"]


class VersionInfo:
    def __init__(self, major, minor, micro, releaselevel, serial):
        self._levels = ["alpha", "beta", "final"]
        self.major = major
        self.minor = minor
        self.micro = micro

        if releaselevel not in self._levels:
            raise TypeError("'releaselevel' must be one of: {}".format(", ".join(self._levels)))

        self.releaselevel = releaselevel
        self.serial = serial

    def __lt__(self, other):
        my_index = self._levels.index(self.releaselevel)
        other_index = self._levels.index(other.releaselevel)
        return (self.major, self.minor, self.micro, my_index, self.serial) < (
            other.major,
            other.minor,
            other.micro,
            other_index,
            other.serial,
        )

    def __repr__(self):
        return "VersionInfo(major={}, minor={}, micro={}, releaselevel={}, serial={})".format(
            self.major, self.minor, self.micro, self.releaselevel, self.serial
        )

    def to_json(self):
        return [self.major, self.minor, self.micro, self.releaselevel, self.serial]


__version__ = "3.0.0b16"
version_info = VersionInfo(3, 0, 0, "beta", 16)
