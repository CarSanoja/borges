from __future__ import annotations

REL_9 = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    items = ["rel_1", "rel_2", "rel_3", "rel_4", "rel_5", "rel_6", "rel_7", "rel_8", "rel_9"]
    out["rel"] = out[items].mean(axis=1)
    return out
"""

REL_7 = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    items = ["rel_1", "rel_2", "rel_5", "rel_6", "rel_7", "rel_8", "rel_9"]
    out["rel"] = out[items].mean(axis=1)
    return out
"""

REL_SELF_ID = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    out["rel"] = out["rel_3"]
    return out
"""

REL_IMPORTANCE = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    out["rel"] = out[["rel_8", "rel_9"]].mean(axis=1)
    return out
"""

WB_OVERALL = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    out["wb"] = out["wb_overall_mean"]
    return out
"""

WB_NO_SEXUAL = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    items = [
        "wb_gen_1", "wb_gen_2", "wb_phys_1", "wb_phys_2", "wb_phys_3", "wb_phys_4",
        "wb_phys_5", "wb_phys_6", "wb_phys_7", "wb_psych_1", "wb_psych_2", "wb_psych_3",
        "wb_psych_4", "wb_psych_5", "wb_psych_6", "wb_soc_1", "wb_soc_2",
    ]
    out["wb"] = out[items].mean(axis=1)
    return out
"""

WB_SUBSCALES = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    out["wb"] = out[["wb_phys_mean", "wb_psych_mean", "wb_soc_mean"]].mean(axis=1)
    return out
"""

WB_GENERAL = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    out["wb"] = out[["wb_gen_1", "wb_gen_2"]].mean(axis=1)
    return out
"""

NORMS_INDIVIDUAL = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    out["norm"] = out[["cnorm_1", "cnorm_2"]].mean(axis=1)
    return out
"""

NORMS_COUNTRY = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    perceived = out[["cnorm_1", "cnorm_2"]].mean(axis=1)
    out["norm"] = perceived.groupby(out["country"], observed=True).transform("mean")
    return out
"""

EXCL_ALL = """import pandas as pd


def apply(df, ctx):
    return df.copy()
"""

EXCL_ATTENTION = """import pandas as pd


def apply(df, ctx):
    return df[df["attention_check"] == 1].copy()
"""

COV_NONE = """import pandas as pd


def apply(df, ctx):
    ctx["covariates"] = []
    return df
"""

COV_DEMOGRAPHICS = """import pandas as pd


def apply(df, ctx):
    out = df.dropna(subset=["age", "gender", "ses", "education"]).copy()
    ctx["covariates"] = ["age", "C(gender)", "ses", "education"]
    return out
"""

COV_DEMOGRAPHICS_GDP = """import pandas as pd


def apply(df, ctx):
    out = df.dropna(subset=["age", "gender", "ses", "education", "gdp_scaled"]).copy()
    ctx["covariates"] = ["age", "C(gender)", "ses", "education", "gdp_scaled"]
    return out
"""

SCALE_GLOBAL = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    columns = [c for c in ("wb", "rel", "norm") if c in out.columns]
    out = out.dropna(subset=columns)
    out["y"] = (out["wb"] - out["wb"].mean()) / out["wb"].std()
    out["x"] = (out["rel"] - out["rel"].mean()) / out["rel"].std()
    if "norm" in out.columns:
        out["m"] = (out["norm"] - out["norm"].mean()) / out["norm"].std()
    return out
"""

SCALE_WITHIN = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    columns = [c for c in ("wb", "rel", "norm") if c in out.columns]
    out = out.dropna(subset=columns)
    by_country = out.groupby("country", observed=True)
    for source, target in (("wb", "y"), ("rel", "x")):
        centred = out[source] - by_country[source].transform("mean")
        out[target] = centred / centred.std()
    if "norm" in out.columns:
        out["m"] = (out["norm"] - out["norm"].mean()) / out["norm"].std()
    return out
"""
