import os as _os
import resource as _resource

from borges.analysis.runtime_policy_paths import (
    _borges_joined,
    _borges_text,
    _borges_under,
    _borges_under_any,
    _borges_walk,
)


def _borges_make_access(
    read_roots, system_roots, system_files, home, root_real, always_writable, secret_proc, pid, sep
):
    os = _os
    resource = _resource

    def secret_path(path, pid_text=str(pid), secret_proc=secret_proc, sep=sep, under=_borges_under):
        name = path.rpartition(sep)[2]
        if name == ".env" or name[:5] == ".env.":
            return True
        if not under(path, "/proc"):
            return False
        parts = path.split(sep)[2:]
        if not parts:
            return False
        if parts[0].isdigit() and parts[0] != pid_text:
            return True
        hit = False
        for part in parts[1:]:
            if part in secret_proc:
                hit = True
        return hit

    def is_directory(path, stat=os.stat, oserror=OSError):
        try:
            return (stat(path).st_mode & 0o170000) == 0o040000
        except oserror:
            return False

    def read_allowed(
        text,
        joined_of=_borges_joined,
        walk=_borges_walk,
        secret_path=secret_path,
        under=_borges_under,
        under_any=_borges_under_any,
        read_roots=read_roots,
        root_real=root_real,
        system_files=system_files,
        system_roots=system_roots,
        home=home,
    ):
        if text == "":
            return False
        joined = joined_of(text)
        lexical = walk(joined, False)
        resolved = walk(joined, True)
        if secret_path(lexical) or secret_path(resolved):
            return False
        if resolved in system_files:
            return True
        if under_any(resolved, read_roots):
            return True
        if home and under(resolved, home):
            return False
        return under_any(resolved, system_roots)

    def open_allowed(
        text,
        read_allowed=read_allowed,
        joined_of=_borges_joined,
        walk=_borges_walk,
        is_directory=is_directory,
        under=_borges_under,
        root_real=root_real,
    ):
        if not read_allowed(text):
            return False
        resolved = walk(joined_of(text), True)
        return under(resolved, root_real) or not is_directory(resolved)

    def write_allowed(
        text,
        joined_of=_borges_joined,
        walk=_borges_walk,
        under=_borges_under,
        root_real=root_real,
        always_writable=always_writable,
    ):
        if text == "":
            return False
        if text in always_writable:
            return True
        return under(walk(joined_of(text), True), root_real)

    def target_ok(target, check, text_of=_borges_text, int_=int, type_=type):
        if target is None or type_(target) is int_:
            return True
        text = text_of(target)
        if text is None:
            return False
        return check(text)

    def limit_ok(
        new, resource_id, getrlimit=resource.getrlimit, type_=type, tuple_=tuple, int_=int, len_=len
    ):
        if type_(new) is not tuple_ or len_(new) != 2:
            return False
        current = getrlimit(resource_id)
        for index in (0, 1):
            value = new[index]
            if type_(value) is not int_:
                return False
            ceiling = current[index]
            if ceiling >= 0 and (value < 0 or value > ceiling):
                return False
        return True

    return (
        secret_path,
        is_directory,
        read_allowed,
        open_allowed,
        write_allowed,
        target_ok,
        limit_ok,
    )


def _borges_refuse(
    a=None,
    b=None,
    c=None,
    d=None,
    e=None,
    f=None,
    g=None,
    h=None,
    i=None,
    j=None,
    k=None,
    m=None,
    n=None,
    o=None,
    p=None,
    q=None,
    r=None,
    s=None,
    t=None,
    u=None,
    v=None,
    w=None,
    x=None,
    perm=PermissionError,
):
    raise perm("runtime policy denied a call that would reach the policy")
