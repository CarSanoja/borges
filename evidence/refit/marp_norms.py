import sys
sys.path.insert(0, "evidence/refit")
from common import *

CASE = "marp_norms"
raw = load(CASE)
rec = recorded(CASE)
REL = [f"rel_{i}" for i in range(1, 10)]
OUT = {"overall": "wb_overall_mean", "psych": "wb_psych_mean", "soc": "wb_soc_mean"}
COV = {"none": [], "demog": ["age", "gender", "education", "ses"], "ext": ["age", "gender", "education", "ses", "gdp_scaled"]}

def zs(s, ddof):
    return (s - s.mean()) / s.std(ddof=ddof)

def run(keep_all, rel, cn, out, cov, model, zy=False, ddof=0, zy_ddof=1):
    df = raw.copy()
    if not keep_all:
        df = df[df.attention_check == 1].copy()
    if rel == "mean":
        r = df[REL].astype(float).sum(axis=1) / 9
    else:
        Z = df[REL].astype(float)
        Z = (Z - Z.mean()) / Z.std(ddof=ddof)
        r = pd.Series(pc1(Z), index=df.index)
    if cn == "mean":
        c = (df["cnorm_1"].astype(float) + df["cnorm_2"].astype(float)) / 2
    else:
        Z = df[["cnorm_1", "cnorm_2"]].astype(float)
        Z = (Z - Z.mean()) / Z.std(ddof=ddof)
        c = pd.Series(pc1(Z), index=df.index)
    df["relig_z"] = zs(r, ddof)
    df["cnorm_z"] = zs(c, ddof)
    df["inter"] = df["relig_z"] * df["cnorm_z"]
    covs = COV[cov]
    X = design(df, [], extra=["relig_z", "cnorm_z", "inter"])
    for cc in covs:
        if cc == "gender":
            X = X.join(pd.get_dummies(df["gender"], prefix="gender", drop_first=True, dtype=float))
        else:
            X[cc] = zs(df[cc].astype(float), ddof)
    d = pd.concat([df[OUT[out]].astype(float).rename("_y"), X, df["country"]], axis=1).dropna()
    if zy:
        d["_y"] = zs(d["_y"], zy_ddof)
    Xc = sm.add_constant(d.drop(columns=["_y", "country"]), has_constant="add")
    if model == "hc3":
        r_ = sm.OLS(d["_y"], Xc).fit(cov_type="HC3")
    else:
        g = pd.factorize(d["country"])[0]
        r_ = sm.OLS(d["_y"], Xc).fit(cov_type="cluster", cov_kwds={"groups": g})
    b = float(r_.params["inter"])
    lo, hi = (float(v) for v in r_.conf_int().loc["inter"])
    return dict(estimate=b, ci_low=lo, ci_high=hi, p_value=float(r_.pvalues["inter"]), n=len(d))

cases = [
    ("baseline", "u_52d4b71a62", (True, "mean", "mean", "overall", "demog", "hc3")),
    ("farthest (soc, GDP covs, country-cluster SEs)", "u_23b24e6d08", (True, "mean", "mean", "soc", "ext", "cluster")),
]
extra = [
    ("exclude failures", "u_b2da091f71", (False, "mean", "mean", "overall", "demog", "hc3")),
    ("pca religiosity", "u_dc2d0df842", (True, "pca", "mean", "overall", "demog", "hc3")),
    ("psych outcome cluster", "u_2d21e732b9", (True, "mean", "mean", "psych", "demog", "cluster")),
    ("pca rel + extended, hc3", "u_d38fcf24d4", (True, "pca", "mean", "overall", "ext", "hc3")),
]
print("==== spec-literal (outcome raw, ddof=0) ====")
for label, uid, a in cases + extra:
    compare(CASE, label, uid, run(*a), rec)
for zd in (0, 1):
    print(f"==== outcome z-scored (ddof={zd}) ====")
    for label, uid, a in cases + extra:
        compare(CASE, label + f" [zy{zd}]", uid, run(*a, zy=True, zy_ddof=zd), rec)
for dd in (1,):
    print(f"==== predictors ddof={dd}, outcome z ddof=1 ====")
    for label, uid, a in cases + extra:
        compare(CASE, label + f" [ddof{dd}]", uid, run(*a, zy=True, ddof=dd), rec)

def run_v3(keep_all, rel, cn, out, cov, model, post=False):
    df = raw.copy()
    if not keep_all:
        df = df[df.attention_check == 1].copy()
    if rel == "mean":
        r = df[REL].astype(float).mean(axis=1)
    else:
        Z = df[REL].astype(float)
        Z = (Z - Z.mean()) / Z.std(ddof=1)
        r = pd.Series(pc1(Z), index=df.index)
    c = (df["cnorm_1"].astype(float) + df["cnorm_2"].astype(float)) / 2
    df["relig"] = r
    df["cnorm"] = c
    df["y"] = df[OUT[out]].astype(float)
    covs = COV[cov]
    need = ["y", "relig", "cnorm"] + [x for x in covs]
    if not post:
        df["relig"] = zs(df["relig"], 1)
        df["cnorm"] = zs(df["cnorm"], 1)
    d = df.dropna(subset=need).copy()
    if post:
        d["relig"] = zs(d["relig"], 1)
        d["cnorm"] = zs(d["cnorm"], 1)
    d["y"] = zs(d["y"], 1)
    d["inter"] = d["relig"] * d["cnorm"]
    X = d[["relig", "cnorm", "inter"]].copy()
    for cc in covs:
        if cc == "gender":
            X = X.join(pd.get_dummies(d["gender"], prefix="gender", drop_first=True, dtype=float))
        else:
            X[cc] = zs(d[cc].astype(float), 1)
    Xc = sm.add_constant(X, has_constant="add")
    if model == "hc3":
        r_ = sm.OLS(d["y"], Xc).fit(cov_type="HC3")
    else:
        g = pd.factorize(d["country"])[0]
        r_ = sm.OLS(d["y"], Xc).fit(cov_type="cluster", cov_kwds={"groups": g})
    b = float(r_.params["inter"])
    se = float(r_.bse["inter"])
    if model == "hc3":
        lo, hi = b - 1.96 * se, b + 1.96 * se
    else:
        lo, hi = (float(v) for v in r_.conf_int().loc["inter"])
    return dict(estimate=b, ci_low=lo, ci_high=hi, p_value=float(r_.pvalues["inter"]), n=len(d))

print("==== v3: ddof=1 everywhere, outcome z, HC3 CI = est +- 1.96 SE; HC3 standardises before NaN drop, cluster after ====")
allc = [
    ("baseline", "u_52d4b71a62", (True, "mean", "mean", "overall", "demog", "hc3"), False),
    ("farthest", "u_23b24e6d08", (True, "mean", "mean", "soc", "ext", "cluster"), True),
    ("exclude failures", "u_b2da091f71", (False, "mean", "mean", "overall", "demog", "hc3"), False),
    ("pca religiosity", "u_dc2d0df842", (True, "pca", "mean", "overall", "demog", "hc3"), False),
    ("psych outcome cluster", "u_2d21e732b9", (True, "mean", "mean", "psych", "demog", "cluster"), True),
    ("pca rel + extended hc3", "u_d38fcf24d4", (True, "pca", "mean", "overall", "ext", "hc3"), False),
    ("cluster baseline-like", "u_8d12fba4cf", (True, "mean", "mean", "overall", "demog", "cluster"), True),
]
for label, uid, a, post in allc:
    compare(CASE, label + " [v3]", uid, run_v3(*a, post=post), rec)
print("---- cluster universes if standardised BEFORE the NaN drop (as the HC3 option does) ----")
for label, uid, a, post in allc:
    if a[-1] == "cluster":
        compare(CASE, label + " [v3-pre]", uid, run_v3(*a, post=False), rec)
