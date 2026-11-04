"""0219E0 read-only research. No order endpoints, no account number."""
import argparse, json, os, time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import numpy as np
import pandas as pd

SYMBOL='0219E0'
KST=ZoneInfo('Asia/Seoul')

def request_json(url, headers=None, body=None):
    req=Request(url,headers=headers or {},data=None if body is None else json.dumps(body).encode())
    # Never include URLs or response bodies in exceptions: Telegram URLs contain secrets.
    try:
        with urlopen(req,timeout=25) as r: return json.load(r)
    except Exception: raise RuntimeError('Remote request failed; check credentials/network in service console') from None

class KIS:
    base='https://openapi.koreainvestment.com:9443'
    def __init__(self):
        self.key=os.environ['KIS_APP_KEY']; self.secret=os.environ['KIS_APP_SECRET']
        r=request_json(self.base+'/oauth2/tokenP',{'Content-Type':'application/json'},
                       {'grant_type':'client_credentials','appkey':self.key,'appsecret':self.secret})
        if 'access_token' not in r: raise RuntimeError('KIS authentication failed')
        self.token=r['access_token']
    def get(self,path,tr,params):
        if path!='/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice':
            raise ValueError('Endpoint not allowed')
        r=request_json(self.base+path+'?'+urlencode(params),
            {'authorization':'Bearer '+self.token,'appkey':self.key,'appsecret':self.secret,'tr_id':tr,'custtype':'P'})
        if r.get('rt_cd')!='0': raise RuntimeError('KIS quotation rejected; verify API entitlement and symbol')
        return r
    def daily(self,today):
        end=today; start=today-timedelta(days=3*366); rows=[]
        for _ in range(15):
            r=self.get('/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice','FHKST03010100',
              {'FID_COND_MRKT_DIV_CODE':'J','FID_INPUT_ISCD':SYMBOL,'FID_INPUT_DATE_1':start.strftime('%Y%m%d'),
               'FID_INPUT_DATE_2':end.strftime('%Y%m%d'),'FID_PERIOD_DIV_CODE':'D','FID_ORG_ADJ_PRC':'1'})
            batch=[x for x in r.get('output2',[]) if x.get('stck_bsop_date')]
            if not batch: break
            rows.extend(batch); oldest=datetime.strptime(min(x['stck_bsop_date'] for x in batch),'%Y%m%d').date()
            if oldest<=start or oldest>=end: break
            end=oldest-timedelta(days=1); time.sleep(.25)
        return validate(pd.DataFrame(rows).rename(columns={'stck_bsop_date':'date','stck_oprc':'open',
          'stck_hgpr':'high','stck_lwpr':'low','stck_clpr':'close','acml_vol':'volume'}))

def validate(d):
    cols=['open','high','low','close','volume']
    if not {'date',*cols}.issubset(d): raise ValueError('Missing OHLCV/date columns')
    d=d[['date']+cols].copy(); d['date']=pd.to_datetime(d.date,format='mixed')
    for c in cols: d[c]=pd.to_numeric(d[c],errors='raise')
    d=d.sort_values('date').drop_duplicates('date',keep='last').set_index('date')
    if not np.isfinite(d[cols].to_numpy()).all(): raise ValueError('Nonfinite OHLCV')
    if ((d[cols[:4]]<=0).any(axis=1)|(d.volume<0)|(d.high<d[['open','close','low']].max(axis=1))|
        (d.low>d[['open','close','high']].min(axis=1))).any(): raise ValueError('Invalid OHLCV')
    if len(d)<65: raise ValueError('Need at least 65 daily bars; no invented history')
    return d

def indicators(d):
    d=d.copy(); c=d.close; delta=c.diff()
    # Wilder RSI: initial simple mean, then recursive Wilder smoothing.
    g=delta.clip(lower=0).to_numpy(); l=(-delta.clip(upper=0)).to_numpy(); rsi=np.full(len(d),np.nan)
    ag=float(np.mean(g[1:15])); al=float(np.mean(l[1:15]))
    for i in range(14,len(d)):
        if i>14: ag=(ag*13+g[i])/14; al=(al*13+l[i])/14
        rsi[i]=50 if ag==al==0 else 100 if al==0 else 100-100/(1+ag/al)
    d['rsi']=rsi
    for n in (5,20,60): d[f'ma{n}']=c.rolling(n).mean()
    d['macd']=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean()
    d['macd_signal']=d.macd.ewm(span=9,adjust=False).mean()
    d['volume_ratio']=d.volume/d.volume.shift(1).rolling(20).mean().replace(0,np.nan)
    d['score']=((c>d.ma20).astype(int)+(d.ma5>d.ma20).astype(int)+
      ((d.rsi>=40)&(d.rsi<=65)).astype(int)+(d.macd>d.macd_signal).astype(int)+
      (d.volume_ratio>=1.2).astype(int))
    d['signal']=np.select([d.score>=4,d.score<=1],['매수 검토','위험 축소 검토'],default='관망')
    d.loc[d.ma60.isna(),'signal']='자료 부족'
    return d

def backtest(d,bps=10):
    if bps<0 or bps>=1000: raise ValueError('Invalid cost bps')
    # Close t decides position at open t+1. Preserve exposure across overnight gaps.
    cash=1.; shares=0.; holdshares=None; events=0; values=[]; hold=[]; f=bps/10000
    for i in range(60,len(d)):
        row=d.iloc[i]; prev=d.iloc[i-1]; target=1 if prev.score>=4 else 0 if prev.score<=1 else int(shares>0)
        if target and shares==0: shares=cash/(row.open*(1+f));cash=0.;events+=1
        elif not target and shares>0: cash=shares*row.open*(1-f);shares=0.;events+=1
        if holdshares is None: holdshares=1/(row.open*(1+f))
        values.append(cash+shares*row.close*(1-f));hold.append(holdshares*row.close*(1-f))
    def metric(v):
        a=np.array([1.]+v);return {'return_pct':round((a[-1]-1)*100,3),
           'max_drawdown_pct':round(float(np.min(a/np.maximum.accumulate(a)-1))*100,3)}
    return {'strategy':metric(values),'buy_hold':metric(hold),'trade_events':events,
      'start':str(d.index[60].date()),'end':str(d.index[-1].date()),'bars':len(values),
      'cost_bps_each_side':bps,'basis':'가격 수익률만; 분배금·세금 제외. 분배락 영향 포함. 최종 청산비용 포함.'}

def notify(text,state,key):
    token=os.getenv('TELEGRAM_BOT_TOKEN');chat=os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat: return 'not_configured'
    if state.exists() and state.read_text()==key: return 'duplicate_skipped'
    r=request_json('https://api.telegram.org/bot'+token+'/sendMessage',{'Content-Type':'application/json'},
                   {'chat_id':chat,'text':text})
    if not r.get('ok'): raise RuntimeError('Telegram rejected message')
    state.parent.mkdir(parents=True,exist_ok=True);state.write_text(key);return 'sent'

def dashboard(report,out):
    template=Path(__file__).with_name('dashboard.html').read_text()
    (out/'index.html').write_text(template.replace('__REPORT__',json.dumps(report,ensure_ascii=False).replace('<','\\u003c')))

def run():
    p=argparse.ArgumentParser();p.add_argument('--csv');p.add_argument('--demo',action='store_true')
    p.add_argument('--mode',choices=['intraday','close'],default='close');p.add_argument('--alert',action='store_true')
    p.add_argument('--out',default='results');p.add_argument('--cost-bps',type=float,default=10);a=p.parse_args()
    now=datetime.now(KST); out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if a.demo:
        rng=np.random.default_rng(219); dates=pd.bdate_range(end=now.date(),periods=260)
        close=6500*np.exp(np.cumsum(rng.normal(0,.008,260)));op=close*np.exp(rng.normal(0,.003,260))
        d=validate(pd.DataFrame({'date':dates,'open':op,'close':close,'high':np.maximum(op,close)*1.004,
            'low':np.minimum(op,close)*.996,'volume':rng.integers(10000,100000,260)}))
    elif a.csv: d=validate(pd.read_csv(a.csv))
    else: d=KIS().daily(now.date())
    if d.index[-1].date()>now.date(): raise ValueError('Future data')
    if not (a.demo or a.csv) and d.index[-1].date()!=now.date():
        raise RuntimeError('No current-session bar: holiday, stale feed or delayed market opening; no signal sent')
    x=indicators(d);last=x.iloc[-1]
    complete=x.loc[x.index.date<now.date()] if (a.mode=='intraday' or now.hour*60+now.minute<950) else x
    report={'symbol':SYMBOL,'demo':a.demo,'source':'SYNTHETIC DEMO' if a.demo else 'CSV import' if a.csv else 'KIS official API',
      'generated_at':now.isoformat(),'bar_date':str(x.index[-1].date()),'mode':a.mode,
      'provisional':a.mode=='intraday' or now.hour*60+now.minute<950,'signal':last.signal,'score':int(last.score),
      'indicators':{k:None if pd.isna(last[k]) else round(float(last[k]),3) for k in ['rsi','macd','macd_signal','volume_ratio']},
      'checks':{'종가 > 20일선':bool(last.close>last.ma20),'5일선 > 20일선':bool(last.ma5>last.ma20),
                '종가 > 60일선 (참고)':bool(last.close>last.ma60)},
      'backtest':backtest(complete,a.cost_bps),
      'notice':'규칙 기반 분석. 학습형 AI 아님. 장중 누적 거래량은 일일 평균 대비 비교로 보수적으로 판정. 분배락·NAV 괴리 별도 검토 필요.'}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));dashboard(report,out)
    text=f"{SYMBOL} {'[가상 테스트]' if a.demo else ''} {a.mode}\n{report['bar_date']} {last.signal} {last.score}/5\nRSI {last.rsi:.1f} | 잠정 {report['provisional']}\n주문 실행 없음 / 분배금 미포함 백테스트"
    report['telegram']=notify(text,Path('state/last_alert.txt'),f"{report['bar_date']}:{a.mode}:{last.signal}:{a.demo}") if a.alert else 'disabled'
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':
    try: run()
    except Exception as e:
        print(f'Analysis failed: {type(e).__name__}: {e}');raise SystemExit(1)
