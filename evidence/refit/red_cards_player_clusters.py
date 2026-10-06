import numpy as np, pandas as pd, statsmodels.api as sm
from scipy.stats import norm
raw=pd.read_parquet('cases/red_cards/data.parquet')

def run(min_games=1, thr='median', clustered=False, z=1.959963984540054):
    df=raw[raw.rater1.notna()&raw.rater2.notna()&(raw.games>=min_games)].copy()
    df['red_flag']=(df.redCards>=1).astype(int)
    score=(df.rater1+df.rater2)/2
    cut=score.median() if thr=='median' else 0.5
    df['skin_group']=(score>=cut).astype(int)
    X=sm.add_constant(pd.get_dummies(df[['skin_group','games','leagueCountry']],columns=['leagueCountry'],drop_first=True).astype(float))
    model=sm.Logit(df.red_flag,X)
    if clustered:
        fit=model.fit(disp=0,cov_type='cluster',cov_kwds={'groups':pd.factorize(df.playerShort)[0]})
    else:
        fit=model.fit(disp=0,cov_type='HC3')
    b=fit.params['skin_group'];se=fit.bse['skin_group']
    return dict(est=np.exp(b),lo=np.exp(b-z*se),hi=np.exp(b+z*se),p=2*norm.cdf(-abs(b/se)),n=len(df),players=df.playerShort.nunique())

for name,kw in [('baseline',{}),('flip',dict(min_games=2,thr='half'))]:
    for clustered in (False,True):
        print(name,'player clusters' if clustered else 'HC3',run(clustered=clustered,**kw))
