import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import numpy as np
import analyzer as a

def bars(c):
    c=np.array(c,dtype=float)
    return a.validate(pd.DataFrame({'date':pd.bdate_range('2025-01-01',periods=len(c)),
      'open':c,'high':c+1,'low':c-1,'close':c,'volume':100}))
class Tests(unittest.TestCase):
    def test_flat_rsi(self): self.assertEqual(a.indicators(bars([100]*100)).rsi.iloc[-1],50)
    def test_rising_rsi(self): self.assertEqual(a.indicators(bars(range(100,200))).rsi.iloc[-1],100)
    def test_falling_rsi(self): self.assertEqual(a.indicators(bars(range(200,100,-1))).rsi.iloc[-1],0)
    def test_causality(self):
        d=bars(range(100,220));x=a.indicators(d);d.iloc[-1,d.columns.get_loc('close')]=10000
        pd.testing.assert_frame_equal(x.iloc[:-1],a.indicators(d).iloc[:-1])
    def test_next_open_and_cost(self):
        d=a.indicators(bars([100]*66));d['score']=0;d.iloc[59,d.columns.get_loc('score')]=5
        d.iloc[60,d.columns.get_loc('open')]=200
        r=a.backtest(d,0);self.assertEqual(r['strategy']['return_pct'],-50)
        self.assertLess(a.backtest(d,10)['strategy']['return_pct'],-50)
    def test_bad_data(self):
        d=bars([100]*100).reset_index();d.loc[0,'high']=50
        with self.assertRaises(ValueError):a.validate(d)
    def test_short_history(self):
        with self.assertRaises(ValueError):bars([100]*20)
    def test_telegram_dedup(self):
        with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'TELEGRAM_BOT_TOKEN':'dummy','TELEGRAM_CHAT_ID':'1'}),patch('analyzer.request_json',return_value={'ok':True}) as mock:
            path=Path(t)/'state';self.assertEqual(a.notify('test',path,'key'),'sent')
            self.assertEqual(a.notify('test',path,'key'),'duplicate_skipped');self.assertEqual(mock.call_count,1)
    def test_failed_telegram_does_not_mark_sent(self):
        with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'TELEGRAM_BOT_TOKEN':'dummy','TELEGRAM_CHAT_ID':'1'}),patch('analyzer.request_json',return_value={'ok':False}):
            path=Path(t)/'state'
            with self.assertRaises(RuntimeError):a.notify('test',path,'key')
            self.assertFalse(path.exists())
    def test_endpoint_allowlist(self):
        kis=object.__new__(a.KIS)
        with self.assertRaises(ValueError):kis.get('/forbidden','x',{})
if __name__=='__main__':unittest.main()
