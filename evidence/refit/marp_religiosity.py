import sys
sys.path.insert(0, "evidence/refit")
from common import *

CASE = "marp_religiosity"
raw = load(CASE)
rec = recorded(CASE)
REL = [f"rel_{i}" for i in range(1, 10)]

def run(attn, relmode, covs, model, zy=False):
    df = raw.copy()
    if attn:
        df = df[df.attention_check == 1].copy()
    if relmode == "mean":
        r = df[REL].astype(float).sum(axis=1) / 9
    else:
        r = pd.Series(pc1(df[REL]), index=df.index)
    df["religiosity_z"] = (r - r.mean()) / r.std(ddof=0)
    X = design(df, covs, extra=["religiosity_z"])
    kind = {"ols": "hc3", "cluster": "cluster", "quant": "quant"}[model]
    _, cols, se, pv, n = fit(df, "wb_overall_mean", X, kind, groups=df["country"], zy=zy)
    return pack(cols, se, pv, n, "religiosity_z")

DEM = ["age", "gender", "education", "ses"]
EXT = DEM + ["country", "gdp_scaled"]
cases = [
    ("baseline", "u_abc552de6d", (True, "mean", DEM, "ols")),
    ("farthest (PCA, extended covs, median regression)", "u_2b28306b3a", (True, "pca", EXT, "quant")),
]
res = []
for label, uid, args in cases:
    res.append((label, uid, compare(CASE, label, uid, run(*args), rec)))
extra = [
    ("single: cluster", "u_c57a0e0c2c", (True, "mean", DEM, "cluster")),
    ("single: extended", "u_34b85d3fa0", (True, "mean", EXT, "ols")),
    ("single: quantile", "u_0e615ae60a", (True, "mean", DEM, "quant")),
    ("extended+quantile mean", "u_ec6b2896e9", (True, "mean", EXT, "quant")),
]
for label, uid, args in extra:
    res.append((label, uid, compare(CASE, label, uid, run(*args), rec)))


def run2(attn, relmode, covs, model, vcov="robust"):
    df = raw.copy()
    if attn:
        df = df[df.attention_check == 1].copy()
    if relmode == "mean":
        r = df[REL].astype(float).sum(axis=1) / 9
    else:
        r = pd.Series(pc1(df[REL]), index=df.index)
    df["religiosity_z"] = (r - r.mean()) / r.std(ddof=0)
    X = design(df, covs, extra=["religiosity_z"])
    d = pd.concat([df["wb_overall_mean"].astype(float).rename("_y"), X], axis=1).dropna()
    if model in ("ols", "cluster"):
        for c in ("_y", "religiosity_z"):
            d[c] = (d[c] - d[c].mean()) / d[c].std(ddof=1)
        Xc = sm.add_constant(d.drop(columns="_y"), has_constant="add")
        if model == "ols":
            r_ = sm.OLS(d["_y"], Xc).fit(cov_type="HC3")
        else:
            g = pd.factorize(df.loc[d.index, "country"])[0]
            r_ = sm.OLS(d["_y"], Xc).fit(cov_type="cluster", cov_kwds={"groups": g})
    else:
        Xc = sm.add_constant(d.drop(columns="_y"), has_constant="add")
        r_ = sm.QuantReg(d["_y"], Xc).fit(q=0.5, vcov=vcov)
    b = float(r_.params["religiosity_z"])
    lo, hi = (float(v) for v in r_.conf_int().loc["religiosity_z"])
    return dict(estimate=b, ci_low=lo, ci_high=hi, p_value=float(r_.pvalues["religiosity_z"]), n=len(d))

print("---- variant: OLS outcome and exposure re-z-scored ddof=1 after dropna; quantile on raw outcome ----")
for label, uid, args in cases + extra:
    compare(CASE, label + " [v2]", uid, run2(*args), rec)
print("---- quantile with iid vcov (spec) vs robust (default) ----")
for label, uid, args in [c for c in cases + extra if c[2][3] == "quant"]:
    compare(CASE, label + " [iid]", uid, run2(*args, vcov="iid"), rec)
print("---- quantile universes on the standardised-outcome scale (same scale as OLS headline) ----")
def run3(args):
    attn, relmode, covs, model = args
    df = raw[raw.attention_check == 1].copy()
    r = df[REL].astype(float).sum(axis=1) / 9 if relmode == "mean" else pd.Series(pc1(df[REL]), index=df.index)
    df["religiosity_z"] = (r - r.mean()) / r.std(ddof=0)
    X = design(df, covs, extra=["religiosity_z"])
    d = pd.concat([df["wb_overall_mean"].astype(float).rename("_y"), X], axis=1).dropna()
    sdy = d["_y"].std(ddof=1)
    d["_y"] = (d["_y"] - d["_y"].mean()) / sdy
    Xc = sm.add_constant(d.drop(columns="_y"), has_constant="add")
    r_ = sm.QuantReg(d["_y"], Xc).fit(q=0.5)
    lo, hi = (float(v) for v in r_.conf_int().loc["religiosity_z"])
    print(f"  {args[1:]} quantile z-outcome est={r_.params['religiosity_z']:.6f} CI=({lo:.6f},{hi:.6f}) sd_y={sdy:.6f} n={len(d)}")
for label, uid, args in [c for c in cases + extra if c[2][3] == "quant"]:
    run3(args)
