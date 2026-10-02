from __future__ import annotations

import re

FILE_FRAME = re.compile(r'File "([^"]+)"')
SITE_PACKAGES = re.compile(r"^.*?[/\\]((?:site|dist)-packages[/\\].*)$")
ABSOLUTE_PATH = re.compile(
    r"(?<![\w.])(?:/(?:Users|home|root|private|var|opt|tmp|usr)|[A-Za-z]:\\)[^\s'\"):,]*"
)


def _frame_path(match: re.Match[str]) -> str:
    path = match.group(1)
    library = SITE_PACKAGES.match(path)
    if library:
        return f'File "{library.group(1)}"'
    if path.startswith(("/", "\\")) or re.match(r"[A-Za-z]:\\", path):
        return f'File "{re.split(r"[/\\\\]", path)[-1]}"'
    return match.group(0)


def _bare_path(match: re.Match[str]) -> str:
    path = match.group(0)
    library = SITE_PACKAGES.match(path)
    if library:
        return library.group(1)
    return re.split(r"[/\\]", path)[-1] or "path"


def scrub_paths(text: str) -> str:
    text = FILE_FRAME.sub(_frame_path, text)
    return ABSOLUTE_PATH.sub(_bare_path, text)
