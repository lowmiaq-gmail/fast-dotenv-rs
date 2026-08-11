"""Public Python orchestration for the python-dotenv-compatible facade."""

import io
import logging
import os
import pathlib
import stat
import sys
import tempfile
from collections import OrderedDict
from contextlib import contextmanager
from typing import IO, Dict, Iterable, Iterator, Mapping, Optional, Tuple, Union

from ._core import parse_resolved as _parse_resolved

from .parser import Binding, parse_stream
from .variables import parse_variables

StrPath = Union[str, "os.PathLike[str]"]
logger = logging.getLogger(__name__)


def _load_dotenv_disabled() -> bool:
    value = os.environ.get("PYTHON_DOTENV_DISABLED")
    return value is not None and value.casefold() in {"1", "true", "t", "yes", "y"}


def with_warn_for_invalid_lines(mappings: Iterator[Binding]) -> Iterator[Binding]:
    for mapping in mappings:
        if mapping.error:
            logger.warning(
                "python-dotenv could not parse statement starting at line %s",
                mapping.original.line,
            )
        yield mapping


class DotEnv:
    def __init__(
        self,
        dotenv_path: Optional[StrPath],
        stream: Optional[IO[str]] = None,
        verbose: bool = False,
        encoding: Optional[str] = None,
        interpolate: bool = True,
        override: bool = True,
    ) -> None:
        self.dotenv_path = dotenv_path
        self.stream = stream
        self._dict: Optional[Dict[str, Optional[str]]] = None
        self.verbose = verbose
        self.encoding = encoding
        self.interpolate = interpolate
        self.override = override

    @contextmanager
    def _get_stream(self) -> Iterator[IO[str]]:
        if self.dotenv_path and _is_file_or_fifo(self.dotenv_path):
            with open(self.dotenv_path, encoding=self.encoding) as stream:
                yield stream
        elif self.stream is not None:
            yield self.stream
        else:
            if self.verbose:
                logger.info(
                    "python-dotenv could not find configuration file %s.",
                    self.dotenv_path or ".env",
                )
            yield io.StringIO("")

    def dict(self) -> Dict[str, Optional[str]]:
        if self._dict:
            return self._dict
        with self._get_stream() as stream:
            text = stream.read()

        if isinstance(text, str):
            pairs, invalid_lines = _parse_resolved(
                text,
                self.interpolate,
                self.override,
                dict(os.environ),
            )
            for line in invalid_lines:
                logger.warning(
                    "python-dotenv could not parse statement starting at line %s",
                    line,
                )
            self._dict = OrderedDict(pairs)
            return self._dict

        # Preserve the upstream exception and edge behavior for non-text
        # streams. In particular, BytesIO must retain Python's
        # "cannot use a string pattern on a bytes-like object" TypeError rather
        # than receiving a PyO3 conversion error from the batch API.
        class _ReadOnce:
            def __init__(self, value: object) -> None:
                self.value = value

            def read(self) -> object:
                return self.value

        raw_values = []
        for mapping in with_warn_for_invalid_lines(parse_stream(_ReadOnce(text))):
            if mapping.key is not None:
                raw_values.append((mapping.key, mapping.value))
        if self.interpolate:
            self._dict = OrderedDict(resolve_variables(raw_values, override=self.override))
        else:
            self._dict = OrderedDict(raw_values)
        return self._dict

    def parse(self) -> Iterator[Tuple[str, Optional[str]]]:
        with self._get_stream() as stream:
            for mapping in with_warn_for_invalid_lines(parse_stream(stream)):
                if mapping.key is not None:
                    yield mapping.key, mapping.value

    def set_as_environment_variables(self) -> bool:
        if not self.dict():
            return False
        for key, value in self.dict().items():
            if key in os.environ and not self.override:
                continue
            if value is not None:
                os.environ[key] = value
        return True

    def get(self, key: str) -> Optional[str]:
        data = self.dict()
        if key in data:
            return data[key]
        if self.verbose:
            logger.warning("Key %s not found in %s.", key, self.dotenv_path)
        return None


def get_key(
    dotenv_path: StrPath,
    key_to_get: str,
    encoding: Optional[str] = "utf-8",
) -> Optional[str]:
    return DotEnv(dotenv_path, verbose=True, encoding=encoding).get(key_to_get)


@contextmanager
def rewrite(
    path: StrPath,
    encoding: Optional[str],
    follow_symlinks: bool = False,
) -> Iterator[Tuple[IO[str], IO[str]]]:
    if follow_symlinks:
        path = os.path.realpath(path)

    try:
        source: IO[str] = open(path, encoding=encoding)
        try:
            path_stat = os.lstat(path)
            original_mode: Optional[int] = (
                stat.S_IMODE(path_stat.st_mode) if stat.S_ISREG(path_stat.st_mode) else None
            )
        except BaseException:
            source.close()
            raise
    except FileNotFoundError:
        source = io.StringIO("")
        original_mode = None

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        delete=False,
        prefix=".tmp_",
        dir=os.path.dirname(os.path.abspath(path)),
    ) as dest:
        dest_path = pathlib.Path(dest.name)
        error = None
        try:
            with source:
                yield source, dest
        except BaseException as err:
            error = err

    if error is None:
        try:
            if original_mode is not None:
                os.chmod(dest_path, original_mode)
            os.replace(dest_path, path)
        except BaseException:
            dest_path.unlink(missing_ok=True)
            raise
    else:
        dest_path.unlink(missing_ok=True)
        raise error from None


def set_key(
    dotenv_path: StrPath,
    key_to_set: str,
    value_to_set: str,
    quote_mode: str = "always",
    export: bool = False,
    encoding: Optional[str] = "utf-8",
    follow_symlinks: bool = False,
) -> Tuple[Optional[bool], str, str]:
    if quote_mode not in ("always", "auto", "never"):
        raise ValueError(f"Unknown quote_mode: {quote_mode}")
    quote = quote_mode == "always" or (
        quote_mode == "auto" and not value_to_set.isalnum()
    )
    value_out = "'{}'".format(value_to_set.replace("'", "\\'")) if quote else value_to_set
    line_out = f"{'export ' if export else ''}{key_to_set}={value_out}\n"

    with rewrite(dotenv_path, encoding=encoding, follow_symlinks=follow_symlinks) as (
        source,
        dest,
    ):
        replaced = False
        missing_newline = False
        for mapping in with_warn_for_invalid_lines(parse_stream(source)):
            if mapping.key == key_to_set:
                dest.write(line_out)
                replaced = True
            else:
                dest.write(mapping.original.string)
                missing_newline = not mapping.original.string.endswith("\n")
        if not replaced:
            if missing_newline:
                dest.write("\n")
            dest.write(line_out)
    return True, key_to_set, value_to_set


def unset_key(
    dotenv_path: StrPath,
    key_to_unset: str,
    quote_mode: str = "always",
    encoding: Optional[str] = "utf-8",
    follow_symlinks: bool = False,
) -> Tuple[Optional[bool], str]:
    if not os.path.exists(dotenv_path):
        logger.warning("Can't delete from %s - it doesn't exist.", dotenv_path)
        return None, key_to_unset
    removed = False
    with rewrite(dotenv_path, encoding=encoding, follow_symlinks=follow_symlinks) as (
        source,
        dest,
    ):
        for mapping in with_warn_for_invalid_lines(parse_stream(source)):
            if mapping.key == key_to_unset:
                removed = True
            else:
                dest.write(mapping.original.string)
    if not removed:
        logger.warning(
            "Key %s not removed from %s - key doesn't exist.", key_to_unset, dotenv_path
        )
        return None, key_to_unset
    return removed, key_to_unset


def resolve_variables(
    values: Iterable[Tuple[str, Optional[str]]],
    override: bool,
) -> Mapping[str, Optional[str]]:
    new_values: Dict[str, Optional[str]] = {}
    for name, value in values:
        if value is None:
            result = None
        else:
            atoms = parse_variables(value)
            env: Dict[str, Optional[str]] = {}
            if override:
                env.update(os.environ)
                env.update(new_values)
            else:
                env.update(new_values)
                env.update(os.environ)
            result = "".join(atom.resolve(env) for atom in atoms)
        new_values[name] = result
    return new_values


def _walk_to_root(path: str) -> Iterator[str]:
    if not os.path.exists(path):
        raise IOError("Starting path not found")
    if os.path.isfile(path):
        path = os.path.dirname(path)
    last_dir = None
    current_dir = os.path.abspath(path)
    while last_dir != current_dir:
        yield current_dir
        parent_dir = os.path.abspath(os.path.join(current_dir, os.path.pardir))
        last_dir, current_dir = current_dir, parent_dir


def find_dotenv(
    filename: str = ".env",
    raise_error_if_not_found: bool = False,
    usecwd: bool = False,
) -> str:
    def _is_interactive() -> bool:
        if hasattr(sys, "ps1") or hasattr(sys, "ps2"):
            return True
        try:
            main = __import__("__main__", None, None, fromlist=["__file__"])
        except ModuleNotFoundError:
            return False
        return not hasattr(main, "__file__")

    def _is_debugger() -> bool:
        return sys.gettrace() is not None

    if usecwd or _is_interactive() or _is_debugger() or getattr(sys, "frozen", False):
        path = os.getcwd()
    else:
        frame = sys._getframe()
        current_file = __file__
        while frame.f_code.co_filename == current_file or not os.path.exists(
            frame.f_code.co_filename
        ):
            assert frame.f_back is not None
            frame = frame.f_back
        path = os.path.dirname(os.path.abspath(frame.f_code.co_filename))

    for dirname in _walk_to_root(path):
        check_path = os.path.join(dirname, filename)
        if _is_file_or_fifo(check_path):
            return check_path
    if raise_error_if_not_found:
        raise IOError("File not found")
    return ""


def load_dotenv(
    dotenv_path: Optional[StrPath] = None,
    stream: Optional[IO[str]] = None,
    verbose: bool = False,
    override: bool = False,
    interpolate: bool = True,
    encoding: Optional[str] = "utf-8",
) -> bool:
    if _load_dotenv_disabled():
        logger.debug(
            "python-dotenv: .env loading disabled by PYTHON_DOTENV_DISABLED environment variable"
        )
        return False
    if dotenv_path is None and stream is None:
        dotenv_path = find_dotenv()
    dotenv = DotEnv(
        dotenv_path=dotenv_path,
        stream=stream,
        verbose=verbose,
        interpolate=interpolate,
        override=override,
        encoding=encoding,
    )
    return dotenv.set_as_environment_variables()


def dotenv_values(
    dotenv_path: Optional[StrPath] = None,
    stream: Optional[IO[str]] = None,
    verbose: bool = False,
    interpolate: bool = True,
    encoding: Optional[str] = "utf-8",
) -> Dict[str, Optional[str]]:
    if dotenv_path is None and stream is None:
        dotenv_path = find_dotenv()
    return DotEnv(
        dotenv_path=dotenv_path,
        stream=stream,
        verbose=verbose,
        interpolate=interpolate,
        override=True,
        encoding=encoding,
    ).dict()


def _is_file_or_fifo(path: StrPath) -> bool:
    if os.path.isfile(path):
        return True
    try:
        st = os.stat(path)
    except (FileNotFoundError, OSError):
        return False
    return stat.S_ISFIFO(st.st_mode)
