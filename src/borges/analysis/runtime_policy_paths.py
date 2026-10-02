import os as _os


def _borges_text(target, type_=type, str_=str, bytes_=bytes):
    kind = type_(target)
    if kind is str_:
        return target
    if kind is bytes_:
        return target.decode("utf-8", "surrogateescape")
    return None


def _borges_walk(
    path,
    follow,
    lstat=_os.lstat,
    readlink=_os.readlink,
    sep=_os.sep,
    perm=PermissionError,
    oserror=OSError,
):
    pending = path.split(sep)
    pending.reverse()
    out = []
    hops = 0
    while pending:
        part = pending.pop()
        if part == "" or part == ".":
            continue
        if part == "..":
            if out:
                out.pop()
            continue
        out.append(part)
        if not follow:
            continue
        current = sep + sep.join(out)
        try:
            mode = lstat(current).st_mode
        except oserror:
            continue
        if (mode & 0o170000) != 0o120000:
            continue
        hops += 1
        if hops > 40:
            raise perm("runtime policy denied symlink loop")
        out.pop()
        link = readlink(current)
        if link[:1] == sep:
            out = []
        extra = link.split(sep)
        extra.reverse()
        pending.extend(extra)
    return sep + sep.join(out)


def _borges_joined(text, getcwd=_os.getcwd, sep=_os.sep):
    if text[:1] == sep:
        return text
    return getcwd() + sep + text


def _borges_under(path, base, sep=_os.sep):
    return path == base or path.startswith(base + sep)


def _borges_under_any(path, bases, under=_borges_under):
    found = False
    for base in bases:
        if under(path, base):
            found = True
    return found
