import numpy as np, pandas as pd, statsmodels.api as sm
D='cases/bank_marketing_calls/data.parquet'
raw=pd.read_parquet(D)
NUM=['balance','duration','campaign','pdays','previous']
MISS=['job','education','contact','poutcome']
MIN=['job','marital','education','default','housing','loan']
EXT=MIN+['contact','day_of_week','month','pdays','previous']
def run(f,cov,cluster):
    df=raw.copy()
    if f=='winsor':
        for c in NUM:
            lo,hi=df[c].quantile(.01),df[c].quantile(.99)
            df[c]=df[c].clip(lo,hi)
    for c in MISS:
        df[c+'_missing']=df[c].isna().astype(int)
        df[c]=df[c].fillna('missing')
    X=df[['campaign']+cov]
    X=pd.get_dummies(X,drop_first=True,dtype=float)
    X=sm.add_constant(X.astype(float))
    m=sm.Logit(df['y'].astype(float),X)
    r=m.fit(disp=0,maxiter=200) if not cluster else m.fit(disp=0,maxiter=200,cov_type='cluster',cov_kwds={'groups':pd.factorize(df['job'])[0]})
    b=r.params['campaign']; ci=r.conf_int().loc['campaign']
    return np.exp(b),np.exp(ci[0]),np.exp(ci[1]),r.pvalues['campaign'],int(r.nobs),b
rec={
'baseline':(0.8716478003856315,0.8573078031351178,0.8862276595858356,3.0650282834623336e-59,45211),
'far_opt1c_3b_4a':(0.903290640413125,0.8880984107122842,0.9187427555506462,6.826660908558692e-32,45211),
'far_opt1c_3b_4b':(0.903290640413125,0.884264530035996,0.9227261224927105,7.650315052412833e-21,45211)}
cfg={'baseline':('winsor',MIN,False),'far_opt1c_3b_4a':('none',EXT,False),'far_opt1c_3b_4b':('none',EXT,True)}
for k,(f,c,cl) in cfg.items():
    o=run(f,c,cl); R=rec[k]
    print(k,'OR %.12g CI [%.12g, %.12g] p %.6g n %d coef %.8f'%o)
    print('  rec',R)
    print('  reldiff',[abs(o[i]-R[i])/abs(R[i]) for i in range(4)],'n same',o[4]==R[4])
