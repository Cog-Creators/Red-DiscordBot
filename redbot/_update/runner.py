import enum
import dataclasses
import json
import os
import sys
from pathlib import Path
from typing import Any, ClassVar, Dict, Iterable, NoReturn, Optional, Tuple, Union

from . import cmd, common

_RUNNER_DIR = Path(os.environ.get(common.RUNNER_DIR_ENV_VAR, ""))


class RequestType(enum.Enum):
    exec = "exec"
    spawn_command = "spawn_command"


@dataclasses.dataclass(frozen=True)
class RequestInput:
    request_type: ClassVar[RequestType]
    request_new_python_exe: str
    request_new_start_args: Tuple[str, ...]
    request_set_env_vars: Dict[str, Optional[str]]


@dataclasses.dataclass(frozen=True)
class RequestOutput:
    request_type: RequestType


@dataclasses.dataclass(frozen=True)
class ExecRequestInput(RequestInput):
    request_type: ClassVar = RequestType.exec


@dataclasses.dataclass(frozen=True)
class ExecRequestOutput(RequestOutput):
    pass


@dataclasses.dataclass(frozen=True)
class SpawnProcessRequestInput(RequestInput):
    request_type: ClassVar = RequestType.spawn_command
    command: str
    args: Tuple[str, ...]
    env: Optional[Dict[str, str]]


@dataclasses.dataclass(frozen=True)
class SpawnProcessRequestOutput(RequestOutput):
    exit_code: int
    exited: bool
    pid: int
    sys: Any
    sys_usage: Dict[str, Any]
    system_time: int
    user_time: int


def make_request(request: RequestInput) -> NoReturn:
    with open(_RUNNER_DIR / "request_input.json", "w", encoding="utf-8") as fp:
        data = dataclasses.asdict(request)
        data["request_type"] = request.request_type.value
        json.dump(data, fp)
    raise SystemExit(3)


def get_request_output() -> Union[ExecRequestOutput, SpawnProcessRequestOutput]:
    with open(_RUNNER_DIR / "request_output.json", encoding="utf-8") as fp:
        data = json.load(fp)
        request_type = RequestType(data.pop("request_type"))
        if request_type == RequestType.exec:
            return ExecRequestOutput(request_type=request_type)
        elif request_type == RequestType.spawn_command:
            return SpawnProcessRequestOutput(request_type=request_type, **data)
        raise RuntimeError("unreachable code")


def make_spawn_process_request(
    command: str,
    *args: str,
    env: Optional[Dict[str, str]] = None,
    new_start_args: Iterable[str],
    new_python_exe: str = sys.executable,
    set_env_vars: Optional[Dict[str, Optional[str]]] = None,
) -> NoReturn:
    if set_env_vars is None:
        set_env_vars = {}
    debug_args = (cmd.arg_names.DEBUG,) * common.get_log_cli_level()
    request = SpawnProcessRequestInput(
        request_new_python_exe=new_python_exe,
        request_new_start_args=("-m", "redbot._update.internal", *debug_args, *new_start_args),
        request_set_env_vars=set_env_vars,
        command=command,
        args=args,
        env=env,
    )
    make_request(request)


def make_exec_request(
    new_python_exe: str,
    *new_start_args: str,
    set_env_vars: Optional[Dict[str, Optional[str]]] = None,
) -> NoReturn:
    if set_env_vars is None:
        set_env_vars = {}
    debug_args = (cmd.arg_names.DEBUG,) * common.get_log_cli_level()
    request = ExecRequestInput(
        request_new_python_exe=new_python_exe,
        request_new_start_args=("-m", "redbot._update.internal", *debug_args, *new_start_args),
        request_set_env_vars=set_env_vars,
    )
    make_request(request)


def get_wrapper_executable() -> Path:
    return Path(os.environ[common.RUNNER_WRAPPER_EXE_ENV_VAR])
