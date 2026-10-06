import pandas as pd, numpy as np, statsmodels.api as sm
from scipy import stats
df=pd.read_parquet("cases/hurricanes/data.parquet")
d=df[df.alldeaths<=df.alldeaths.quantile(0.99)]
def ame(y,cov):
    X=sm.add_constant(d[["masfem"]+cov].astype(float))
    m=sm.GLM(y,X,family=sm.families.Poisson()).fit(cov_type="HC1")
    mu=m.mu;b=m.params["masfem"]
    g=b*(np.asarray(mu)[:,None]*X.values).mean(0);g[list(X.columns).index("masfem")]+=mu.mean()
    se=np.sqrt(g@np.asarray(m.cov_params())@g);v=b*mu.mean()
    return v,v-1.959963984540054*se,v+1.959963984540054*se,2*stats.norm.sf(abs(v/se)),int(m.nobs),b
print("AME deaths ndam15",*ame(d.alldeaths.astype(float),["category","wind","ndam15"]))
print("literal sqrt-outcome poisson",*ame(np.sqrt(d.alldeaths),["category","wind"]))
print("literal asinh-outcome poisson",*ame(np.arcsinh(d.alldeaths),["category","wind"]))
