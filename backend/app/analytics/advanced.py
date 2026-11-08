"""Experimental public-data tyre inference; never substitutes proprietary measurements."""
import math
import numpy as np


def observed_stint_points(laps, stints):
    lookup = {}
    for s in stints or []:
        try:
            a,b = int(s['lap_start']), int(s['lap_end'])
            if b < a: continue
            for n in range(a,b+1): lookup[n] = s
        except (ValueError, TypeError, KeyError): continue
    points=[]
    for lap in laps or []:
        try:
            n=int(lap['lap_number']); t=float(lap['lap_duration'])
            if n not in lookup or not math.isfinite(t) or not 0<t<300 or lap.get('is_pit_out_lap'): continue
            s=lookup[n]
            points.append({'lap_number':n,'age':n-int(s['lap_start']), 'lap_time':t,
                           'stint':str(s.get('stint_number','unknown')),'compound':s.get('compound')})
        except (ValueError,TypeError,KeyError): continue
    return sorted(points,key=lambda p:p['lap_number'])


def _kalman(y, q, r, mode="smooth"):
    if mode not in ("smooth", "filter"):
        raise ValueError("mode must be smooth or filter")
    """Local quadratic trend: level, slope, curvature (three-state IRW2 extension).
    Kalman filter + RTS smoother; no claim that curvature is a physical tyre cliff.
    """
    F=np.array([[1.,1.,.5],[0.,1.,1.],[0.,0.,1.]])
    H=np.array([[1.,0.,0.]])
    G=np.array([[1/6],[.5],[1.]])
    Q=q*(G@G.T)
    x=np.array([float(y[0]),0.,0.]); P=np.diag([25.,1.,.1]); I=np.eye(3)
    xf=[]; Pf=[]; xp=[]; Pp=[]; loglike=0.
    for obs in y:
        xprior=F@x; Pprior=F@P@F.T+Q
        residual=float(obs-(H@xprior)[0]); S=float((H@Pprior@H.T)[0,0]+r)
        K=(Pprior@H.T)/S
        x=xprior+K[:,0]*residual
        P=(I-K@H)@Pprior@(I-K@H).T+r*(K@K.T)
        P=(P+P.T)/2
        loglike+=-.5*(math.log(2*math.pi*S)+residual**2/S)
        xp.append(xprior); Pp.append(Pprior); xf.append(x.copy()); Pf.append(P.copy())
    if mode == "filter":
        return loglike, np.array(xf), np.array(Pf)
    xs=[v.copy() for v in xf]; Ps=[v.copy() for v in Pf]
    for k in range(len(y)-2,-1,-1):
        J=Pf[k]@F.T@np.linalg.inv(Pp[k+1])
        xs[k]=xf[k]+J@(xs[k+1]-xp[k+1]); Ps[k]=Pf[k]+J@(Ps[k+1]-Pp[k+1])@J.T
    return loglike,np.array(xs),np.array(Ps)


def state_space_stints(points, min_laps=6, mode="smooth", process_variance=None, measurement_variance=None):
    if mode not in ("smooth", "filter"):
        raise ValueError("mode must be smooth or filter")
    if mode == "filter" and (process_variance is None or measurement_variance is None):
        raise ValueError("Causal filter requires pre-specified q/r fitted on independent training data; tuning on full stint leaks future observations")
    """Fit independent observed stints. Grid ML tuning of process and observation variance.
    Returned smoothed states are IN-SAMPLE; use forward-only forecasts for evaluation.
    """
    grouped={}
    for p in points:
        try:
            t=float(p['lap_time']); age=float(p['age'])
            if math.isfinite(t) and math.isfinite(age): grouped.setdefault(str(p['stint']),[]).append((age,t))
        except (KeyError,ValueError,TypeError): pass
    outputs=[]
    for stint, rows in grouped.items():
        rows=sorted(rows)
        if len(rows)<min_laps or len(set(a for a,_ in rows))!=len(rows): continue
        ages=np.array([a for a,_ in rows]); y=np.array([v for _,v in rows]);
        # IRW assumes equal steps; reject missing ages instead of silently interpolating.
        if not np.allclose(np.diff(ages),1):
            outputs.append({'stint':stint,'ready':False,'reason':'Missing tyre-age steps; cannot assume equal sampling intervals'})
            continue
        best=None
        for q in ([process_variance] if mode == "filter" else [1e-6,1e-4,1e-2,1e-1]):
            for r in ([measurement_variance] if mode == "filter" else [.01,.1,1.,4.,16.]):
                try:
                    ll,x,P=_kalman(y,q,r,mode=mode)
                    if best is None or ll>best[0]: best=(ll,q,r,x,P)
                except np.linalg.LinAlgError: continue
        if best is None:
            outputs.append({'stint':stint,'ready':False,'reason':'Numerical filter failure'});continue
        ll,q,r,x,P=best
        outputs.append({'stint':stint,'ready':True,'observations':len(rows), 'ages':ages.tolist(),
                        'latent_pace_s':x[:,0].tolist(), 'latent_slope_s_per_lap':x[:,1].tolist(),
                        'latent_curvature_s_per_lap2':x[:,2].tolist(),
                        'slope_approx_95_interval':[[float(v-1.96*math.sqrt(max(0.,cov[1,1]))),float(v+1.96*math.sqrt(max(0.,cov[1,1])))] for v,cov in zip(x[:,1],P)],
                        'selected_process_variance':q,'selected_measurement_variance':r,'log_likelihood':ll})
    return {'ready':any(x.get('ready') for x in outputs),'stints':outputs,
            'mode':mode,'model':'Three-state local quadratic trend (IRW2-inspired) '+('forward Kalman filter' if mode == 'filter' else 'Kalman/RTS smoother'),
            'limitations':('Forward-filtered states are causal only with externally fixed q/r and prior initialization; they are updated with the current lap observation and are NOT next-lap forecasts.' if mode == 'filter' else 'Exploratory in-sample smoothing; curvature is not proven tyre cliff. Equal age spacing required. Hyperparameters chosen by discrete maximum likelihood on same stint.')}


def compare_stint_models(points):
    """Same retained observations, forward chronological split per stint; no smoothing leakage."""
    grouped={}
    for p in points: grouped.setdefault(str(p['stint']),[]).append(p)
    scores=[]
    for sid,rows in grouped.items():
        rows=sorted(rows,key=lambda p:p['age'])
        if len(rows)<10:continue
        n=max(6,int(.75*len(rows))); train=rows[:n]; test=rows[n:]
        a=np.array([float(p['age']) for p in train]); y=np.array([float(p['lap_time']) for p in train]); at=np.array([float(p['age']) for p in test]); yt=np.array([float(p['lap_time']) for p in test]);
        X=np.column_stack([np.ones(len(a)),a]); beta=np.linalg.lstsq(X,y,rcond=None)[0]
        predictions={'median':np.full(len(at),np.median(y)), 'ols':beta[0]+beta[1]*at}
        if len(train)>=8:
            candidates=[]
            for knot in sorted(set(a))[3:-3]:
                Z=np.column_stack([X,np.maximum(a-knot,0)])
                b=np.linalg.lstsq(Z,y,rcond=None)[0]; rss=max(1e-9,float(np.sum((y-Z@b)**2)))
                bic=len(y)*math.log(rss/len(y))+3*math.log(len(y))
                candidates.append((bic,knot,b))
            if candidates:
                _,k,b=min(candidates,key=lambda z:z[0]);predictions['piecewise_bic']=b[0]+b[1]*at+b[2]*np.maximum(at-k,0)
        # Bayesian regularized slope, explicit prior; no test-set tuning.
        prior=np.diag([1/10000,1/.25]); mean=np.array([np.median(y),0.]); prec=prior+X.T@X
        posterior=np.linalg.solve(prec,prior@mean+X.T@y)
        predictions['bayesian_mean']=posterior[0]+posterior[1]*at
        scores.append({'stint':sid,'train_laps':len(train),'test_laps':len(test),
                       'models':{name:{'mae_s':float(np.mean(np.abs(yt-pred))), 'rmse_s':float(np.sqrt(np.mean((yt-pred)**2)))} for name,pred in predictions.items()}})
    return {'ready':bool(scores),'folds':scores,'limitations':'Within-stint chronological holdout; same observed retained points. State-space smoother excluded from predictive ranking because retrospective smoothing would leak test data.'}
