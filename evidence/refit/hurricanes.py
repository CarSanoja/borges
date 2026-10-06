import pandas as pd, numpy as np, statsmodels.api as sm
df=pd.read_parquet("cases/hurricanes/data.parquet")
def run(tr,cov,model):
    d=df[df.alldeaths<=df.alldeaths.quantile(0.99)].copy()
    d["outcome"]={"log":np.log1p,"sqrt":np.sqrt,"asinh":np.arcsinh}[tr](d.alldeaths)
    d=d.dropna(subset=["masfem","outcome"]+cov)
    X=sm.add_constant(d[["masfem"]+cov].astype(float))
    if model=="ols":
        m=sm.OLS(d.outcome,X).fit(cov_type="HC3")
        ci=m.conf_int().loc["masfem"]
        return m.params["masfem"],ci[0],ci[1],m.pvalues["masfem"],int(m.nobs)
    y=np.expm1(d.outcome) if tr=="log" else d.outcome
    m=sm.GLM(y,X,family=sm.families.Poisson()).fit(cov_type="HC1")
    s=(np.exp(m.params["masfem"])-1)*y.mean()
    ci=m.conf_int().loc["masfem"]
    return s,(np.exp(ci[0])-1)*y.mean(),(np.exp(ci[1])-1)*y.mean(),m.pvalues["masfem"],int(m.nobs)
for name,a in [("baseline u_b4716afa30",("log",["category","wind"],"ols")),
    ("farthest u_6ac18fdb4b log/ndam15/poisson",("log",["category","wind","ndam15"],"poisson")),
    ("u_9e7f0b3070 sqrt/opt3a/poisson",("sqrt",["category","wind"],"poisson")),
    ("u_37eb021af7 asinh/opt3a/poisson",("asinh",["category","wind"],"poisson"))]:
    print(name,*run(*a))
