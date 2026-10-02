def _borges_install_policy(home_override, audit_path):
    import ctypes
    import os
    import sys
    import sysconfig

    del ctypes
    root = os.path.realpath(os.getcwd())
    realpath = os.path.realpath
    fsdecode = os.fsdecode
    getcwd = os.getcwd
    join = os.path.join
    sep = os.sep
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
    blocked_exact = frozenset(
        {
            "subprocess.Popen",
            "os.system",
            "os.exec",
            "os.spawn",
            "os.posix_spawn",
            "os.fork",
            "os.forkpty",
            "os.startfile",
            "pty.spawn",
            "webbrowser.open",
            "socket.connect",
            "socket.bind",
            "socket.getaddrinfo",
            "socket.sendto",
            "socket.sendmsg",
            "socket.gethostbyname",
            "socket.gethostbyaddr",
            "socket.getnameinfo",
            "socket.getservbyname",
            "socket.getservbyport",
            "sys.addaudithook",
            "_posixsubprocess.fork_exec",
        }
    )
    blocked_modules = frozenset({"ctypes", "_ctypes", "cffi", "_cffi_backend"})
    always_writable = frozenset({"/dev/null"})
    path_events = {
        "os.remove": (0,),
        "os.rmdir": (0,),
        "os.rename": (0, 1),
        "os.mkdir": (0,),
        "os.symlink": (1,),
        "os.link": (0, 1),
        "os.truncate": (0,),
        "os.chmod": (0,),
        "os.chown": (0,),
        "os.chdir": (0,),
        "os.chroot": (0,),
        "shutil.rmtree": (0,),
        "shutil.move": (0, 1),
        "shutil.copyfile": (0, 1),
        "shutil.copytree": (0, 1),
    }

    library_roots = tuple(
        {realpath(p) + sep for p in (sys.prefix, sys.base_prefix, sys.exec_prefix)}
    )

    pid = os.getpid()
    try:
        import pwd

        real_home = pwd.getpwuid(os.getuid()).pw_dir
    except (ImportError, KeyError):
        real_home = os.path.expanduser("~")
    home = realpath(home_override or real_home).rstrip(sep) or None
    secret_proc = frozenset({"environ", "mem", "maps", "smaps", "pagemap", "mountinfo"})
    system_roots = tuple(
        realpath(p)
        for p in (
            "/usr/lib",
            "/usr/share",
            "/usr/local/lib",
            "/usr/local/share",
            "/lib",
            "/lib64",
            "/System/Library",
            "/Library/Fonts",
            "/opt/homebrew",
            "/private/var/db/timezone",
            "/sys/devices/system/cpu",
            "/sys/fs/cgroup",
            "/proc/" + str(pid),
        )
    )
    system_files = frozenset(
        {realpath(p) for p in ("/dev/null", "/dev/urandom", "/dev/random", "/proc/cpuinfo")}
        | {realpath(p) for p in ("/proc/meminfo", "/etc/localtime", "/etc/timezone")}
    )
    audit_fd = None
    if audit_path:
        audit_fd = os.open(audit_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)

    def under(path, base):
        return path == base or path.startswith(base.rstrip(sep) + sep)

    def under_any(path, bases):
        return any(under(path, base) for base in bases)

    def python_roots():
        found = {
            realpath(p)
            for p in (sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix)
        }
        found.update(realpath(p) for p in sysconfig.get_paths().values())
        trusted = tuple(found)
        for entry in sys.path:
            if entry and os.path.isdir(entry):
                resolved = realpath(entry)
                if not (home and under(resolved, home)) or under_any(resolved, trusted):
                    found.add(resolved)
        return tuple(r for r in found if r != sep and not (home and under(home, r)))

    read_roots = (root,) + python_roots()

    def secret_path(path):
        name = path.rpartition(sep)[2]
        if name == ".env" or name.startswith(".env."):
            return True
        if not under(path, "/proc"):
            return False
        parts = path.split(sep)[2:]
        if not parts:
            return False
        if parts[0].isdigit() and parts[0] != str(pid):
            return True
        return bool(secret_proc & set(parts[1:]))

    def allowed_read(target):
        if isinstance(target, int) or target is None:
            return True
        try:
            text = fsdecode(target)
        except TypeError:
            return False
        if not text:
            return False
        joined = os.path.normpath(join(getcwd(), text))
        resolved = realpath(joined)
        if secret_path(joined) or secret_path(resolved):
            return False
        if resolved in system_files or under_any(resolved, read_roots):
            return True
        if home and under(resolved, home):
            return False
        return under_any(resolved, system_roots)

    def check_read(target, event):
        if allowed_read(target):
            return
        if audit_fd is not None:
            os.write(audit_fd, (event + " " + repr(target) + "\n").encode())
            return
        deny(event + " for reading" if event == "open" else event)

    def imported_by_library():
        frame = sys._getframe(2)
        while frame is not None and frame.f_code.co_filename.startswith("<frozen importlib"):
            frame = frame.f_back
        if frame is None:
            return False
        return realpath(frame.f_code.co_filename).startswith(library_roots)

    def deny(event):
        raise PermissionError("runtime policy denied " + event)

    def inside(target):
        if isinstance(target, int) or target is None:
            return True
        try:
            text = fsdecode(target)
        except TypeError:
            return False
        if not text:
            return False
        if text in always_writable:
            return True
        resolved = realpath(join(getcwd(), text))
        return resolved == root or resolved.startswith(root + sep)

    def hook(event, args):
        if event in blocked_exact:
            deny(event)
        if event.startswith("ctypes."):
            deny(event)
        if event == "import":
            name = args[0]
            if name.partition(".")[0] in blocked_modules and not imported_by_library():
                deny(event + " " + name)
            return
        if event == "open":
            flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
            if flags & write_flags:
                if not inside(args[0]):
                    deny("open for writing")
            else:
                check_read(args[0], "open")
            return
        if event in ("os.listdir", "os.scandir"):
            check_read(args[0] if args else None, event)
            return
        indexes = path_events.get(event)
        if indexes is None:
            return
        for index in indexes:
            if index < len(args) and not inside(args[index]):
                deny(event)

    sys.addaudithook(hook)


_borges_install_policy(None, None)
del _borges_install_policy
