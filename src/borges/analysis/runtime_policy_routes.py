"""Routes around the audit hook that the policy closes when it is installed.

Some calls reach process creation or the policy's own state without raising an audit event, so
they are replaced on their modules by a refusal. A module compiled into the interpreter (on Linux
builds, _posixsubprocess and _interpreters among them) is created by _imp.create_builtin, which
raises no audit event, so importlib.import_module brought back the original fork_exec and the
sub-interpreters, whose code runs outside the hook. Its creation is routed through the hook,
which keeps the original and refuses the blocked modules; the name is read from the spec before
the hook, so no object of the step's code is called inside it.
"""


def _borges_close_routes(os, signal, subprocess, sys, refuse):
    monitoring = getattr(sys, "monitoring", None)
    for module, names in (
        (os, ("setsid", "setpgid", "setpgrp")),
        (signal, ("signal", "setitimer", "alarm", "set_wakeup_fd")),
        (sys.modules.get("posix"), ("setsid", "setpgid", "setpgrp")),
        (sys.modules.get("_signal"), ("signal", "setitimer", "alarm", "set_wakeup_fd")),
        (monitoring, ("use_tool_id", "set_events", "set_local_events", "register_callback")),
        (sys.modules.get("_posixsubprocess"), ("fork_exec",)),
        (subprocess, ("_fork_exec",)),
    ):
        for name in names:
            if module is not None and hasattr(module, name):
                setattr(module, name, refuse)


def _borges_guard_builtins(imp, blocked_modules, deny, audit):
    class _BorgesSpec:
        __slots__ = ("name", "origin")

        def __init__(self, name):
            self.name = name
            self.origin = "built-in"

    def create(
        args,
        create_builtin=imp.create_builtin,
        spec_type=_BorgesSpec,
        blocked=blocked_modules,
        deny=deny,
        type_=type,
        str_=str,
        list_=list,
        len_=len,
    ):
        if len_(args) != 2 or type_(args[0]) is not str_ or type_(args[1]) is not list_:
            deny("borges.create_builtin")
        name = args[0]
        if name.partition(".")[0] in blocked:
            deny("import " + name)
        args[1].append(create_builtin(spec_type(name)))

    def guarded(spec, audit=audit, list_=list, str_=str):
        box = list_()
        audit("borges.create_builtin", str_(spec.name), box)
        return box[0]

    imp.create_builtin = guarded
    return create, guarded
