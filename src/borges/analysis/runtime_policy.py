from borges.analysis.runtime_policy_config import (
    _BORGES_ALWAYS_WRITABLE,
    _BORGES_BLOCKED_EVENTS,
    _BORGES_BLOCKED_MODULES,
    _BORGES_FRAME_ATTRS,
    _BORGES_PATH_EVENTS,
    _BORGES_SECRET_PROC,
    _BORGES_TAMPER_ATTRS,
    _borges_roots,
)
from borges.analysis.runtime_policy_paths import (
    _borges_joined,
    _borges_text,
    _borges_under,
    _borges_under_any,
    _borges_walk,
)


def _borges_install_policy(home_override, audit_path):
    import ctypes
    import os
    import resource
    import signal
    import subprocess
    import sys

    try:
        import _posixsubprocess
    except ImportError:
        _posixsubprocess = None

    del ctypes
    root_real = _borges_walk(os.getcwd(), True)
    sep = os.sep
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
    home, read_roots, system_roots, system_files = _borges_roots(home_override, root_real)
    blocked_exact = _BORGES_BLOCKED_EVENTS
    blocked_modules = _BORGES_BLOCKED_MODULES
    tamper_attrs = _BORGES_TAMPER_ATTRS
    frame_attrs = _BORGES_FRAME_ATTRS
    always_writable = _BORGES_ALWAYS_WRITABLE
    path_events = _BORGES_PATH_EVENTS
    secret_proc = _BORGES_SECRET_PROC
    pid = os.getpid()
    audit_fd = None
    if audit_path:
        audit_fd = os.open(audit_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)

    def deny(event, perm=PermissionError):
        raise perm("runtime policy denied " + event)

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

    protected = set()

    def check(
        event,
        args,
        nested,
        blocked_exact=blocked_exact,
        blocked_modules=blocked_modules,
        tamper_attrs=tamper_attrs,
        frame_attrs=frame_attrs,
        path_events=path_events,
        write_flags=write_flags,
        deny=deny,
        target_ok=target_ok,
        read_allowed=read_allowed,
        open_allowed=open_allowed,
        write_allowed=write_allowed,
        limit_ok=limit_ok,
        audit_fd=audit_fd,
        write=os.write,
        type_=type,
        len_=len,
        repr_=repr,
        str_=str,
        int_=int,
        id_=id,
        protected=protected,
    ):
        if event in blocked_exact:
            deny(event)
        if event[:7] == "ctypes.":
            deny(event)
        if event == "import":
            name = args[0]
            if type_(name) is not str_:
                deny(event)
            if name.partition(".")[0] in blocked_modules:
                deny(event + " " + name)
            return
        if event == "open":
            flags = args[2] if len_(args) > 2 and type_(args[2]) is int_ else 0
            if flags & write_flags:
                if not target_ok(args[0], write_allowed):
                    deny("open for writing")
            elif not target_ok(args[0], open_allowed):
                if audit_fd is None:
                    deny("open for reading")
                write(audit_fd, (event + " " + repr_(args[0]) + "\n").encode())
            return
        if event == "os.listdir" or event == "os.scandir":
            target = args[0] if args else None
            if not target_ok(target, read_allowed):
                if audit_fd is None:
                    deny(event)
                write(audit_fd, (event + " " + repr_(target) + "\n").encode())
            return
        if event == "object.__setattr__" or event == "object.__delattr__":
            if args[1] in tamper_attrs and id_(args[0]) in protected:
                deny(event + " " + args[1])
            return
        if event == "object.__getattr__":
            if nested and args[1] in frame_attrs:
                deny(event + " " + args[1])
            return
        if event == "sys._getframe":
            if nested:
                deny(event)
            return
        if event == "resource.setrlimit":
            if not limit_ok(args[1], args[0]):
                deny(event)
            return
        indexes = path_events.get(event)
        if indexes is None:
            return
        for index in indexes:
            if index < len_(args) and not target_ok(args[index], write_allowed):
                deny(event)

    depth_cell = [0]

    def hook(event, args, check=check, depth=depth_cell, perm=PermissionError, base=BaseException):
        depth[0] += 1
        try:
            check(event, args, depth[0] > 1)
        except perm:
            raise
        except base:
            raise perm("runtime policy denied internal error") from None
        finally:
            depth[0] -= 1

    def refuse(
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

    for module, names in (
        (os, ("setsid", "setpgid", "setpgrp")),
        (signal, ("signal", "setitimer", "alarm", "set_wakeup_fd")),
        (sys.modules.get("posix"), ("setsid", "setpgid", "setpgrp")),
        (sys.modules.get("_signal"), ("signal", "setitimer", "alarm", "set_wakeup_fd")),
        (getattr(sys, "monitoring", None), ("use_tool_id", "set_events", "set_local_events")),
        (getattr(sys, "monitoring", None), ("register_callback",)),
        (_posixsubprocess, ("fork_exec",)),
        (subprocess, ("_fork_exec",)),
    ):
        for name in names:
            if module is not None and hasattr(module, name):
                setattr(module, name, refuse)

    for guarded in (
        _borges_text,
        _borges_walk,
        _borges_joined,
        _borges_under,
        _borges_under_any,
        deny,
        secret_path,
        is_directory,
        read_allowed,
        open_allowed,
        write_allowed,
        target_ok,
        limit_ok,
        check,
        hook,
        refuse,
    ):
        protected.add(id(guarded))

    sys.addaudithook(hook)


_borges_install_policy(None, None)
del _borges_install_policy
