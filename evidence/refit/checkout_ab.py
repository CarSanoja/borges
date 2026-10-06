import pandas as pd, numpy as np, statsmodels.api as sm
df=pd.read_parquet("cases/checkout_ab/data.parquet")
def run(filt):
    d=df
    if filt=="exclude_internal": d=d[~d.is_internal]
    g=d.sort_values("session_id").groupby("user_id")
    u=pd.DataFrame({"user_converted":g.converted.max(),"user_treatment":(g.variant.first()=="treatment").astype(float),
        "user_platform":g.platform.agg(lambda s:s.mode().iloc[0]),"user_day_mean":g.day.mean()}).reset_index()
    X=pd.get_dummies(u[["user_treatment","user_platform"]],columns=["user_platform"],drop_first=True,dtype=float)
    X=sm.add_constant(X)
    m=sm.OLS(u.user_converted.astype(float),X).fit(cov_type="HC1")
    ci=m.conf_int().loc["user_treatment"]
    return 100*m.params["user_treatment"],100*ci[0],100*ci[1],m.pvalues["user_treatment"],int(m.nobs)
for name,f in [("baseline u_e929526ea4","keep_all"),("flip u_fb948f9bb7","exclude_internal")]:
    print(name,*run(f))
