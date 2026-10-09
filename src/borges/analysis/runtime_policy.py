from borges.analysis.runtime_policy_access import _borges_make_access, _borges_refuse
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
from borges.analysis.runtime_policy_routes import _borges_close_routes, _borges_guard_builtins


def _borges_install_policy(home_override, audit_path):
    import _imp
    import ctypes
    import os
    import signal
    import subprocess
    import sys

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

    secret_path, is_directory, read_allowed, open_allowed, write_allowed, target_ok, limit_ok = (
        _borges_make_access(
            read_roots,
            system_roots,
            system_files,
            home,
            root_real,
            always_writable,
            secret_proc,
            pid,
            sep,
        )
    )

    protected = set()
    create_builtin, guarded_builtin = _borges_guard_builtins(_imp, blocked_modules, deny, sys.audit)

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
        create_builtin=create_builtin,
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
        if event == "borges.create_builtin":
            create_builtin(args)
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

    refuse = _borges_refuse

    _borges_close_routes(os, signal, subprocess, sys, refuse)

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
        create_builtin,
        guarded_builtin,
    ):
        protected.add(id(guarded))

    sys.addaudithook(hook)


_borges_install_policy(None, None)
del _borges_install_policy
