from __future__ import annotations

import pytest

from borges.analysis.code_guard import check_code

JURY_BYPASS = """
def apply(df, ctx):
    g = (c for c in [1])
    b = g.gi_frame.f_builtins
    u = "_" * 2
    imp = b[u + "import" + u]
    m = imp("o" + "s")
    ctx["x"] = m.listdir("/")
    return df
"""


def wrap(body: str) -> str:
    return "def apply(df, ctx):\n" + "\n".join("    " + line for line in body.splitlines())


def test_jury_bypass_is_rejected() -> None:
    violations = check_code(JURY_BYPASS, "filter")
    assert any("gi_frame" in v for v in violations)
    assert any("f_builtins" in v for v in violations)
    assert any("computed string key" in v for v in violations)


@pytest.mark.parametrize(
    "body",
    [
        "x = (c for c in [1]).gi_frame\nreturn df",
        "x = df.f_back\nreturn df",
        "x = df.f_globals\nreturn df",
        "x = df.f_locals\nreturn df",
        "x = df.f_code\nreturn df",
        "x = df.cr_frame\nreturn df",
        "x = df.ag_frame\nreturn df",
        "x = df.tb_frame\nreturn df",
        "x = df.tb_next\nreturn df",
        "x = df.mro()\nreturn df",
        "x = df._private\nreturn df",
        "x = df._mgr\nreturn df",
        "x = type(df)\nreturn df",
        "x = vars(df)\nreturn df",
        "x = globals()\nreturn df",
        "x = locals()\nreturn df",
        "x = getattr(df, 'a')\nreturn df",
        "x = setattr(df, 'a', 1)\nreturn df",
        "x = delattr(df, 'a')\nreturn df",
        "x = compile('1', 'a', 'eval')\nreturn df",
        "x = exec('1')\nreturn df",
        "x = eval('1')\nreturn df",
        "x = open('f')\nreturn df",
        "x = input()\nreturn df",
        "breakpoint()\nreturn df",
        "x = chr(95)\nreturn df",
        "x = b['_' + '_import__']\nreturn df",
        "x = b[f'{u}import']\nreturn df",
        "x = b['_'.join(['', 'import'])]\nreturn df",
        "x = b[''.join(['a'])]\nreturn df",
        "x = b['a' * 2]\nreturn df",
    ],
)
def test_introspection_variants_rejected(body: str) -> None:
    assert check_code(wrap(body), "filter") != []


@pytest.mark.parametrize(
    "body",
    [
        "return df[df['x'] > 0]",
        "return df[['a', 'b']]",
        "col = 'a'\nreturn df[col]",
        "return df[df['a'].isin(['x', 'y'])]",
        "ctx['n'] = len(df)\nreturn df.loc[df['a'] > 1, ['a']]",
    ],
)
def test_ordinary_pandas_still_accepted(body: str) -> None:
    assert check_code(wrap(body), "filter") == []
