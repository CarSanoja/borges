from __future__ import annotations

ALLOWED_IMPORTS = frozenset(
    {
        "pandas",
        "numpy",
        "math",
        "scipy",
        "scipy.stats",
        "statsmodels",
        "statsmodels.api",
        "statsmodels.formula.api",
    }
)

FORBIDDEN_NAMES = frozenset(
    {
        "eval",
        "exec",
        "open",
        "compile",
        "__import__",
        "globals",
        "locals",
        "vars",
        "getattr",
        "setattr",
        "delattr",
        "input",
        "breakpoint",
        "exit",
        "quit",
        "SystemExit",
        "KeyboardInterrupt",
        "BaseException",
    }
)

FORBIDDEN_MODULES = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "socket",
        "shutil",
        "pathlib",
        "requests",
        "urllib",
        "importlib",
        "pickle",
        "io",
        "builtins",
    }
)

FORBIDDEN_ATTRIBUTES = frozenset(
    {
        "load",
        "loads",
        "save",
        "savez",
        "savez_compressed",
        "savetxt",
        "loadtxt",
        "genfromtxt",
        "fromfile",
        "fromregex",
        "tofile",
        "open",
        "memmap",
        "DataSource",
        "lib",
        "ctypeslib",
        "f2py",
        "system",
        "popen",
        "eval",
        "query",
        "format",
        "format_map",
        "dump",
        "dumps",
        "save_npz",
        "load_npz",
        "datasets",
        "iolib",
        "HDFStore",
        "ExcelFile",
        "ExcelWriter",
        "get_rdataset",
        "webuse",
    }
)

ALLOWED_TO_ATTRIBUTES = frozenset(
    {
        "to_numpy",
        "to_dict",
        "to_list",
        "to_frame",
        "to_numeric",
        "to_datetime",
        "to_timedelta",
        "to_string",
    }
)

FORMULA_CALLS = frozenset(
    {
        "I",
        "C",
        "Q",
        "log",
        "exp",
        "sqrt",
        "abs",
        "center",
        "standardize",
        "scale",
        "np.log",
        "np.exp",
        "np.sqrt",
        "np.log1p",
        "np.abs",
        "np.square",
        "pow",
    }
)

IO_PREFIXES = ("read_", "to_", "save")
