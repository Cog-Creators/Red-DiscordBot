import re as _re
import sys as _sys
import warnings as _warnings
from math import inf as _inf
from typing import (
    Any as _Any,
    ClassVar as _ClassVar,
    Dict as _Dict,
    List as _List,
    Optional as _Optional,
    Pattern as _Pattern,
    Tuple as _Tuple,
    Union as _Union,
)


MIN_PYTHON_VERSION = (3, 7, 0)

__all__ = ["MIN_PYTHON_VERSION", "__version__", "version_info", "VersionInfo"]

if _sys.version_info < MIN_PYTHON_VERSION:
    print(
        f"Python {'.'.join(map(str, MIN_PYTHON_VERSION))} is required to run Red, but you have "
        f"{_sys.version}! Please update Python."
    )
    _sys.exit(1)


class VersionInfo:
    ALPHA = "alpha"
    BETA = "beta"
    RELEASE_CANDIDATE = "release candidate"
    FINAL = "final"

    _VERSION_STR_PATTERN: _ClassVar[_Pattern[str]] = _re.compile(
        r"^"
        r"(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<micro>0|[1-9]\d*)"
        r"(?:(?P<releaselevel>a|b|rc)(?P<serial>0|[1-9]\d*))?"
        r"(?:\.post(?P<post_release>0|[1-9]\d*))?"
        r"(?:\.dev(?P<dev_release>0|[1-9]\d*))?"
        r"$",
        flags=_re.IGNORECASE,
    )
    _RELEASE_LEVELS: _ClassVar[_List[str]] = [ALPHA, BETA, RELEASE_CANDIDATE, FINAL]
    _SHORT_RELEASE_LEVELS: _ClassVar[_Dict[str, str]] = {
        "a": ALPHA,
        "b": BETA,
        "rc": RELEASE_CANDIDATE,
    }

    def __init__(
        self,
        major: int,
        minor: int,
        micro: int,
        releaselevel: str,
        serial: _Optional[int] = None,
        post_release: _Optional[int] = None,
        dev_release: _Optional[int] = None,
    ) -> None:
        self.major: int = major
        self.minor: int = minor
        self.micro: int = micro

        if releaselevel not in self._RELEASE_LEVELS:
            raise TypeError(
                f"'releaselevel' must be one of: {', '.join(self._RELEASE_LEVELS)}"
            )

        self.releaselevel: str = releaselevel
        self.serial: _Optional[int] = serial
        self.post_release: _Optional[int] = post_release
        self.dev_release: _Optional[int] = dev_release

    @classmethod
    def from_str(cls, version_str: str) -> "VersionInfo":
        """Parse a string into a VersionInfo object.

        Raises
        ------
        ValueError
            If the version info string is invalid.

        """
        match = cls._VERSION_STR_PATTERN.match(version_str)
        if not match:
            raise ValueError(f"Invalid version string: {version_str}")

        kwargs: _Dict[str, _Union[str, int]] = {}
        for key in ("major", "minor", "micro"):
            kwargs[key] = int(match[key])
        releaselevel = match["releaselevel"]
        if releaselevel is not None:
            kwargs["releaselevel"] = cls._SHORT_RELEASE_LEVELS[releaselevel]
        else:
            kwargs["releaselevel"] = cls.FINAL
        for key in ("serial", "post_release", "dev_release"):
            if match[key] is not None:
                kwargs[key] = int(match[key])
        return cls(**kwargs)

    @classmethod
    def from_json(
        cls, data: _Union[_Dict[str, _Union[int, str]], _List[_Union[int, str]]]
    ) -> "VersionInfo":
        if isinstance(data, _List):
            # For old versions, data was stored as a list:
            # [MAJOR, MINOR, MICRO, RELEASELEVEL, SERIAL]
            return cls(*data)
        else:
            return cls(**data)

    def to_json(self) -> _Dict[str, _Union[int, str]]:
        return {
            "major": self.major,
            "minor": self.minor,
            "micro": self.micro,
            "releaselevel": self.releaselevel,
            "serial": self.serial,
            "post_release": self.post_release,
            "dev_release": self.dev_release,
        }

    def _generate_comparison_tuples(
        self, other: "VersionInfo"
    ) -> _List[
        _Tuple[
            int,
            int,
            int,
            int,
            _Union[int, float],
            _Union[int, float],
            _Union[int, float],
        ]
    ]:
        tups: _List[
            _Tuple[
                int,
                int,
                int,
                int,
                _Union[int, float],
                _Union[int, float],
                _Union[int, float],
            ]
        ] = []
        for obj in (self, other):
            tups.append(
                (
                    obj.major,
                    obj.minor,
                    obj.micro,
                    obj._RELEASE_LEVELS.index(obj.releaselevel),
                    obj.serial if obj.serial is not None else _inf,
                    obj.post_release if obj.post_release is not None else -_inf,
                    obj.dev_release if obj.dev_release is not None else _inf,
                )
            )
        return tups

    def __lt__(self, other: "VersionInfo") -> bool:
        tups = self._generate_comparison_tuples(other)
        return tups[0] < tups[1]

    def __eq__(self, other: "VersionInfo") -> bool:
        tups = self._generate_comparison_tuples(other)
        return tups[0] == tups[1]

    def __le__(self, other: "VersionInfo") -> bool:
        tups = self._generate_comparison_tuples(other)
        return tups[0] <= tups[1]

    def __str__(self) -> str:
        ret = f"{self.major}.{self.minor}.{self.micro}"
        if self.releaselevel != self.FINAL:
            short = next(
                k
                for k, v in self._SHORT_RELEASE_LEVELS.items()
                if v == self.releaselevel
            )
            ret += f"{short}{self.serial}"
        if self.post_release is not None:
            ret += f".post{self.post_release}"
        if self.dev_release is not None:
            ret += f".dev{self.dev_release}"
        return ret

    def __repr__(self) -> str:
        return (
            "VersionInfo(major={major}, minor={minor}, micro={micro}, "
            "releaselevel={releaselevel}, serial={serial}, post={post_release}, "
            "dev={dev_release})".format(**self.to_json())
        )


__version__ = "3.1.1"
version_info = VersionInfo.from_str(__version__)

# Filter fuzzywuzzy slow sequence matcher warning
_warnings.filterwarnings("ignore", module=r"fuzzywuzzy.*")
