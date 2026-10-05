from __future__ import annotations

ALLOWED_IMPORTS = frozenset(
    {
        "pandas",
        "numpy",
        "math",
        "scipy",
        "scipy.optimize",
        "scipy.special",
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

FORMULA_FUNCTIONS = frozenset({"C", "I", "Q", "center", "standardize", "scale", "bs", "cr", "poly"})

FORMULA_NUMPY_FUNCTIONS = frozenset({"log", "log1p", "exp", "sqrt", "abs"})

IO_PREFIXES = ("read_", "to_", "save")

INTROSPECTION_ATTRIBUTES = frozenset(
    {
        "gi_frame",
        "gi_code",
        "gi_yieldfrom",
        "cr_frame",
        "cr_code",
        "cr_await",
        "ag_frame",
        "ag_code",
        "f_back",
        "f_builtins",
        "f_globals",
        "f_locals",
        "f_code",
        "f_trace",
        "tb_frame",
        "tb_next",
        "co_code",
        "mro",
        "func_globals",
    }
)

INTROSPECTION_NAMES = frozenset(
    {
        "type",
        "super",
        "object",
        "memoryview",
        "classmethod",
        "staticmethod",
        "property",
        "builtins",
        "chr",
        "bytes",
        "bytearray",
    }
)

STRING_BUILDERS = frozenset({"join", "decode", "encode", "replace", "format", "translate"})
