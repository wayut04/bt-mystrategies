# download data as tick data [MT5 Terminal]/MQL/Files/Data

from datetime import datetime, timedelta
from backtradermql5.mt5store import MTraderStore
import backtrader as bt

store = MTraderStore(host="192.168.100.114") # Metatrader 5 running on a diffenet host

start_date = datetime.now() - timedelta(days=20)

cerebro = bt.Cerebro()
data2 = store.getdata(dataname='EURUSD',
     timeframe=bt.TimeFrame.Seconds,
     fromdate=start_date
     )

cerebro.run(stdstats=False)


