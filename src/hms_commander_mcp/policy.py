"""Configured roots and no-follow descriptor access; no project mutation."""
from contextlib import contextmanager
from pathlib import Path
import os
import stat
import sys

EXTENSIONS = frozenset({"hms", "basin", "met", "control", "run", "gage"})
MAX_FILE_BYTES = 2 * 1024 * 1024

def _extended_path(path: Path) -> str:
    """Return the Windows extended-length form so reads work beyond MAX_PATH."""
    text = str(path)
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text[2:]
    return "\\\\?\\" + text

class Policy:
    def __init__(self, roots: list[str]):
        if not roots:
            raise ValueError("Configure at least one --root; unrestricted access is unavailable")
        self.roots = tuple(str(Path(p).expanduser().resolve(strict=True)) for p in roots)
        if any(not Path(p).is_dir() for p in self.roots):
            raise ValueError("All roots must be existing directories")

    def selected_root(self, root: str) -> str:
        # Match configured identity, not any descendant or client-supplied MCP root.
        if root not in self.roots:
            raise ValueError("Root is not configured for this server")
        return root

    @contextmanager
    def open_file(self, root: str, relative: str, kind: str):
        root = self.selected_root(root)
        # Accept either separator, as Windows clients send native paths.
        parts = relative.replace("\\", "/").split("/")
        if (Path(relative).is_absolute() or any(p in {"", ".", ".."} for p in parts)
                or ":" in relative or "\x00" in relative):
            raise ValueError("Use a relative file without traversal, drive or alternate-stream syntax")
        path = Path(*parts)
        if kind not in EXTENSIONS or path.suffix.lower() != "." + kind:
            raise ValueError("File extension must match an approved text type")
        if os.name == "posix":
            opened = []
            try:
                configured = Path(root)
                fd = os.open(configured.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                opened.append(fd)
                for part in configured.parts[1:]:
                    fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    opened.append(fd)
                for part in path.parts[:-1]:
                    fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    opened.append(fd)
                leaf = os.open(path.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                opened.append(leaf)
                yield leaf
            finally:
                for fd in reversed(opened):
                    os.close(fd)
        elif sys.platform == "win32":
            # Resolve actual opened target before reading, including junctions.
            import ctypes
            import msvcrt
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            create = kernel.CreateFileW
            create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                               wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
            create.restype = wintypes.HANDLE
            close = kernel.CloseHandle
            close.argtypes = [wintypes.HANDLE]
            close.restype = wintypes.BOOL
            final_path = kernel.GetFinalPathNameByHandleW
            final_path.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
            final_path.restype = wintypes.DWORD
            # Components are validated above, so the extended-length form
            # (which skips normalization) cannot introduce traversal.
            handle = create(_extended_path(Path(root) / path), 0x80000000, 1, None, 3, 0x00200000, None)
            if handle == ctypes.c_void_p(-1).value:
                raise OSError(ctypes.get_last_error(), "Could not open approved text file")
            try:
                buffer = ctypes.create_unicode_buffer(32768)
                size = final_path(handle, buffer, len(buffer), 0)
                if not size or size >= len(buffer):
                    raise ValueError("Could not establish opened file identity")
                actual = buffer.value
                if actual.startswith("\\\\?\\UNC\\"):
                    actual = "\\\\" + actual[8:]
                elif actual.startswith("\\\\?\\"):
                    actual = actual[4:]
                if not Path(actual).is_relative_to(Path(root)):
                    raise ValueError("Opened target escapes configured root")
                # Refuse leaf reparse points, including links that remain in root.
                if getattr(os.lstat(_extended_path(Path(root) / path)), "st_file_attributes", 0) & 0x400:
                    raise ValueError("Reparse-point inputs are not accepted")
                fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
                handle = None  # fd owns it from here.
                try:
                    yield fd
                finally:
                    os.close(fd)
            finally:
                if handle is not None:
                    close(handle)
        else:
            raise ValueError("This platform has no qualified secure file reader")

    def read_bytes(self, root: str, relative: str, kind: str) -> bytes:
        with self.open_file(root, relative, kind) as fd:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
                raise ValueError("Input must be a regular text file no larger than 2 MiB")
            parts, count = [], 0
            while True:
                piece = os.read(fd, min(65536, MAX_FILE_BYTES + 1 - count))
                if not piece:
                    break
                parts.append(piece)
                count += len(piece)
                if count > MAX_FILE_BYTES:
                    raise ValueError("Text input exceeded the file budget")
            after = os.fstat(fd)
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError("Input changed while reading; retry against a stable source")
            data = b"".join(parts)
            if b"\x00" in data or any(b < 9 or 13 < b < 32 for b in data):
                raise ValueError("Binary or control-character inputs are not accepted")
            return data
