import os as _os
import sys as _sys
import sysconfig as _sysconfig

from borges.analysis.runtime_policy_paths import _borges_under, _borges_under_any, _borges_walk

_BORGES_BLOCKED_EVENTS = frozenset(
    {
        "subprocess.Popen",
        "os.system",
        "os.exec",
        "os.posix_spawn",
        "os.fork",
        "os.forkpty",
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
        "gc.get_objects",
        "gc.get_referrers",
        "gc.get_referents",
        "sys._current_frames",
        "sys.settrace",
        "sys.setprofile",
        "os.kill",
        "os.killpg",
        "signal.pthread_kill",
        "resource.prlimit",
    }
)
_BORGES_BLOCKED_MODULES = frozenset(
    {
        "cffi",
        "_cffi_backend",
        "_posixsubprocess",
        "_interpreters",
        "_interpchannels",
        "_interpqueues",
        "_xxsubinterpreters",
        "_xxinterpchannels",
        "_xxinterpqueues",
        "_testcapi",
        "_testinternalcapi",
        "_testlimitedcapi",
        "_testexternalinspection",
        "_testsinglephase",
        "_testmultiphase",
        "_testimportmultiple",
        "_testbuffer",
        "_xxtestfuzz",
    }
)
_BORGES_TAMPER_ATTRS = frozenset({"__code__", "__defaults__", "__kwdefaults__", "__closure__"})
_BORGES_FRAME_ATTRS = frozenset({"tb_frame", "gi_frame", "gi_code", "f_code", "__code__"})
_BORGES_SECRET_PROC = frozenset({"environ", "mem", "maps", "smaps", "pagemap", "mountinfo"})
_BORGES_ALWAYS_WRITABLE = frozenset({"/dev/null"})
_BORGES_PATH_EVENTS = {
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


def _borges_roots(home_override, root_real):
    sep = _os.sep
    pid = _os.getpid()
    try:
        import pwd

        real_home = pwd.getpwuid(_os.getuid()).pw_dir
    except (ImportError, KeyError):
        real_home = _os.path.expanduser("~")
    home = _borges_walk(home_override or real_home, True).rstrip(sep) or None
    system_roots = tuple(
        _borges_walk(p, True)
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
        _borges_walk(p, True)
        for p in (
            "/dev/null",
            "/dev/urandom",
            "/dev/random",
            "/proc/cpuinfo",
            "/proc/meminfo",
            "/etc/localtime",
            "/etc/timezone",
        )
    )
    found = {
        _borges_walk(p, True)
        for p in (_sys.prefix, _sys.base_prefix, _sys.exec_prefix, _sys.base_exec_prefix)
    }
    found.update(_borges_walk(p, True) for p in _sysconfig.get_paths().values())
    trusted = tuple(found)
    for entry in _sys.path:
        if entry and _os.path.isdir(entry):
            resolved = _borges_walk(entry, True)
            outside_home = not (home and _borges_under(resolved, home))
            if outside_home or _borges_under_any(resolved, trusted):
                found.add(resolved)
    read_roots = (root_real,) + tuple(
        r for r in found if r != sep and not (home and _borges_under(home, r))
    )
    return home, read_roots, system_roots, system_files
