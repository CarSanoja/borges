import numpy as np, pandas as pd, statsmodels.api as sm
from scipy.stats import norm
D='cases/red_cards/data.parquet'
raw=pd.read_parquet(D)

def run(min_games=1, thr='median', const=True, z=1.96):
    df=raw[raw.rater1.notna()&raw.rater2.notna()&(raw.games>=min_games)].copy()
    df['red_flag']=(df.redCards>=1).astype(int)
    df['skin_score']=(df.rater1+df.rater2)/2
    cut=df.skin_score.median() if thr=='median' else 0.5
    df['skin_group']=(df.skin_score>=cut).astype(int)
    cov=['games','leagueCountry']
    X=pd.get_dummies(df[['skin_group']+cov],columns=['leagueCountry'],drop_first=True).astype(float)
    if const: X=sm.add_constant(X)
    m=sm.Logit(df.red_flag,X).fit(cov_type='HC3',disp=0)
    b=m.params['skin_group'];se=m.bse['skin_group']
    return dict(est=np.exp(b),lo=np.exp(b-z*se),hi=np.exp(b+z*se),p=2*norm.cdf(-abs(b/se)),n=len(df))

REC={'baseline':(1.1702474306213824,1.0496720820981333,1.3046732138846344,124621),
'flip':(1.1230408676642243, 0.9811655967874693, 1.2854311184304674, 61822)}
for name,kw in [('baseline',{}),('flip',dict(min_games=2,thr='half'))]:
    for z in (1.96,1.959963984540054):
        r=run(z=z,**kw)
        print(name,z,r)
        rec=REC[name]
        print('  reldiff est/lo/hi',[abs(a-b)/b for a,b in zip((r['est'],r['lo'],r['hi']),rec[:3])],r['n'],rec[3])
