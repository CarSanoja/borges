import pandas as pd
import statsmodels.api as sm

df = pd.read_parquet("cases/teaching_ratings/data.parquet")
for c in ("students", "allstudents"):
    df[c] = df[c].clip(lower=df[c].quantile(0.01), upper=df[c].quantile(0.99))


def fit(covariates, cov_type, **kwds):
    x = sm.add_constant(pd.get_dummies(df[["beauty", *covariates]], drop_first=True).astype(float))
    m = sm.OLS(df["eval"], x).fit(cov_type=cov_type, **kwds)
    lo, hi = m.conf_int().loc["beauty"]
    return m.params["beauty"], lo, hi, m.pvalues["beauty"], int(m.nobs)


covariates = ["gender", "minority", "native", "tenure", "division", "credits"]
print("baseline u_6cefe77c73 recorded 0.1645 [0.1034, 0.2257] p 1.333e-07 n 463")
print("  refit", *fit(covariates, "HC1"))
print("farthest u_0c7221cc4f recorded 0.1330 [0.0252, 0.2408] p 0.01562 n 463")
print("  refit", *fit([], "cluster", cov_kwds={"groups": df["prof"]}))
