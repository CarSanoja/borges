def _borges_install_policy():
    import ctypes
    import os
    import sys

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
            if flags & write_flags and not inside(args[0]):
                deny("open for writing")
            return
        indexes = path_events.get(event)
        if indexes is None:
            return
        for index in indexes:
            if index < len(args) and not inside(args[index]):
                deny(event)

    sys.addaudithook(hook)


_borges_install_policy()
del _borges_install_policy
