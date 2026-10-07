import numpy as np
import pandas as pd
import statsmodels.api as sm

raw = pd.read_parquet("cases/fertility_religiosity/data.parquet")


def cells(d, high, committed):
    d = d.copy()
    d["high"] = high.astype(float)
    d["committed"] = committed.astype(float)
    d["both"] = d.high * d.committed
    d = d.dropna(subset=["religiosity"])
    return d, sm.add_constant(d[["high", "committed", "both"]])


def report(m):
    lo, hi = m.conf_int().loc["both"]
    return m.params["both"], lo, hi, m.pvalues["both"], int(m.nobs)


certain = raw[~((raw.Sure1 <= 5) | (raw.Sure2 <= 5))].copy()
certain["religiosity"] = certain[["Rel1", "Rel2", "Rel3"]].mean(axis=1)
days = (certain.DateTesting - certain.StartDateofLastPeriod).dt.days
d, x = cells(certain, (days >= 6) & (days <= 11), certain.Relationship.isin([2, 3, 4]))
print("baseline u_311ac33ed6 recorded 0.2746 [-2.0530, 2.6022] p 0.8171 n 171")
print("  refit", *report(sm.OLS(d.religiosity, x).fit(cov_type="HC3")))

kept = raw.copy()
kept["religiosity"] = kept[["Rel1", "Rel2", "Rel3"]].mean(axis=1)
days = (kept.DateTesting - kept.StartDateofLastPeriod).dt.days
d, x = cells(kept, (days >= 6) & (days <= 11), kept.Relationship.isin([2, 3, 4]))
print("the plan's own default, every participant kept (rejected by the judge)")
print("  refit", *report(sm.OLS(d.religiosity, x).fit(cov_type="HC3")))

far = raw[~((raw.Sure1 <= 5) | (raw.Sure2 <= 5))].copy()
items = far[["Rel1", "Rel2", "Rel3"]]
far["religiosity"] = np.where(items.notna().sum(axis=1) >= 2, items.median(axis=1), np.nan)
days = (far.DateTesting - far.StartDateofLastPeriod).dt.days
ovulation = far.ReportedCycleLength - 14
high = (days >= ovulation - 5) & (days <= ovulation + 1)
d, x = cells(far, high, far.Relationship.isin([2, 3, 4]))
ols = sm.OLS(d.religiosity, x).fit()
weights = 1 / sm.OLS(ols.resid**2, x).fit().fittedvalues
print("farthest u_1b2af9882d recorded -0.3189 [-3.0602, 2.4224] p 0.8199 n 161")
print("  refit of the spec (squared residuals)", *report(sm.WLS(d.religiosity, x, weights).fit()))
outcome_weights = 1 / sm.OLS(d.religiosity**2, x).fit().fittedvalues
m = sm.WLS(d.religiosity, x, outcome_weights).fit()
b, se = m.params["both"], m.bse["both"]
print("  recorded code (squared outcome, 1.96 interval)", b, b - 1.96 * se, b + 1.96 * se)
