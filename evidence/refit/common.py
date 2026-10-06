import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.sandwich_covariance import cov_cluster
from statsmodels.regression.quantile_regression import QuantReg

BASE = "cases"

def load(case):
    return pd.read_parquet(f"{BASE}/{case}/data.parquet")

def recorded(case):
    out = {}
    for line in open(f"{BASE}/{case}/recorded-live/events.jsonl"):
        e = json.loads(line)
        if e["type"] == "universe.finished":
            u = e["data"]["universe"]
            if u["status"] == "done":
                out[u["id"]] = u
    return out

def design(df, covs, extra=None):
    X = pd.DataFrame(index=df.index)
    for c in extra or []:
        X[c] = df[c].astype(float)
    for c in covs:
        if c in ("gender", "country"):
            X = X.join(pd.get_dummies(df[c], prefix=c, drop_first=True, dtype=float))
        else:
            X[c] = df[c].astype(float)
    return X

def fit(df, y, X, kind, groups=None, zy=False):
    d = pd.concat([df[y].astype(float).rename("_y"), X], axis=1).dropna()
    if zy:
        d["_y"] = (d["_y"] - d["_y"].mean()) / d["_y"].std(ddof=0)
    Xc = sm.add_constant(d.drop(columns="_y"), has_constant="add")
    if kind == "hc3":
        r = sm.OLS(d["_y"], Xc).fit(cov_type="HC3")
        se = r.bse
        pv = r.pvalues
        cols = r.params
    elif kind == "cluster":
        r = sm.OLS(d["_y"], Xc).fit()
        cov = cov_cluster(r, groups.loc[d.index].astype(str).values)
        cols = r.params
        se = pd.Series(np.sqrt(np.diag(cov)), index=cols.index)
        pv = pd.Series(2 * stats.norm.sf(np.abs(cols / se)), index=cols.index)
    elif kind == "quant":
        r = QuantReg(d["_y"], Xc).fit(q=0.5, vcov="iid")
        cols = r.params
        se = r.bse
        pv = pd.Series(2 * stats.norm.sf(np.abs(cols / se)), index=cols.index)
    return r, cols, se, pv, len(d)

def pack(cols, se, pv, n, name):
    b = float(cols[name])
    s = float(se[name])
    return dict(estimate=b, ci_low=b - 1.96 * s, ci_high=b + 1.96 * s, p_value=float(pv[name]), n=int(n))

def compare(case, label, uid, mine, rec_all):
    rec = rec_all[uid]["result"]
    rows = []
    for k in ("estimate", "ci_low", "ci_high"):
        rows.append(abs(mine[k] - rec[k]) / max(abs(rec[k]), 1e-12))
    rd = max(rows)
    agree = rd < 1e-6 and mine["n"] == rec["n"]
    print(f"[{case}] {label} {uid}")
    print(f"  mine: est={mine['estimate']:.9f} CI=({mine['ci_low']:.9f},{mine['ci_high']:.9f}) p={mine['p_value']:.4g} n={mine['n']}")
    print(f"  rec : est={rec['estimate']:.9f} CI=({rec['ci_low']:.9f},{rec['ci_high']:.9f}) p={rec['p_value']:.4g} n={rec['n']}")
    print(f"  maxreldiff={rd:.3e} p_reldiff={abs(mine['p_value']-rec['p_value'])/rec['p_value']:.3e} agree={agree}")
    return agree

def pc1(M, orient_col=0):
    M = np.asarray(M, dtype=float)
    Mc = M - M.mean(axis=0)
    _, _, vt = np.linalg.svd(Mc, full_matrices=False)
    v = vt[0]
    if v[orient_col] < 0:
        v = -v
    return Mc @ v
