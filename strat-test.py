import collections
import backtrader as bt
from backtradermql5.mt5store import MTraderStore
from datetime import datetime, timedelta
from local.ind_supertrend import SuperTrend
import matplotlib
import os
import time

##############################################################################################
class MyStrategy(bt.Strategy):
    params = (
        ('mt5broker', False),
        ('stperiod', 7),
        ('stmultiplier', 3),
        ('doprint', False),
    )

    def log(self, txt, dt=None, doprint=False):
        ''' Logging function for this strategy'''
        if doprint or self.params.doprint:
            #dt = dt or self.datas[0].datetime.datetime()
            dt = dt or self.data.datetime.datetime()
            print(f'{dt}: {txt}')

    def __init__(self):
        self.dataclose = self.datas[0].close
        #self.data1close = self.datas[1].close
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.inBuyPosition = False
        self.inSellPosition = False
        self.live_data = False
        self.last2ST = 0
        #self.activetradeid = None
        #global buy_order
        #self.bar_executed = 0

        super().__init__()
        #self.broker.set_coc(True)

        self.ma1 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=3)
            #self.datas[1], period=self.params.ma1period)

    def notify_order(self, order):

        if order.status in [order.Submitted]:
            self.log('Order submitted')
            return
        if order.status in [order.Accepted]:
            self.log('Order accepted')
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Price: %.5f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price, order.executed.value,
                          order.executed.comm))

            elif order.issell():
                self.log('SELL EXECUTED, Price: %.5f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price, order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)
            self.bar_executed2 = 0 # reset for higher tf

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            # capture the trade id
            self.log('Notify trade: a new position')
            return

        self.log('Notify trade (closed): OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # get pos and dpos parameter
        pos = self.getposition(self.data)
        dpos = pos.size
        #self.log('Close, %.5f, Pos size: %.5f' % (self.dataclose[0], dpos))

        cash = self.broker.getcash()
        #if self.live_data:
        #    cash = self.broker.getcash()
        #else
        #    cash = 'NA'

        # for multiple data
        for data in self.datas:
            data = self.data
            self.log(f'{data._name} | Cash {cash} | O: {data.open[0]} H: {data.high[0]} L: {data.low[0]} C: {data.close[0]} V:{data.volume[0]} Pos:{dpos}')
        #data = self.data
        #self.log(f'{data._name} | Cash {cash} | O: {data.open[0]} H: {data.high[0]} L: {data.low[0]} C: {data.close[0]} V:{data.volume[0]} Pos:{dpos}')

        # Check if we are in the market
        #if not self.position:
        ''' Test strategy '''
        #### simple strategi from cerebro (just for test.. )

        if not dpos:
            # Not yet ... we MIGHT BUY if ...
            if self.dataclose[0] > self.dataclose[-1]:
                    # current close less than previous close

                # BUY, BUY, BUY!!! (with default parameters)
                self.log('BUY CREATE, %.5f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                if self.live_data or not self.params.mt5broker:
                    self.order = self.buy()
                    self.buy_order = self.order

        else:
            # Already in the market ... we might sell
            if len(self) >= (self.bar_executed + 2):
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.5f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                # self.order = self.sell()
                if self.live_data:
                    self.cancel(self.buy_order) # self.trade.tradeid)
                elif not self.params.mt5broker:
                    self.order = self.close() # self.trade.tradeid)

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.now()

        self.log('Data Status: %s' % data._getstatusname(status), dt=dt)
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False

    def notify_store(self, msg): # is it causing the trouble?
        self.log('Notify store: %s' % msg)

    def stop(self):
        self.log('(ST (period,mul): %2d, %2d) Ending Value %.2f'
            % (self.params.stperiod, self.params.stmultiplier, self.broker.getvalue()),
                 doprint=True)

########################################################################################

def runstrat(ppair='EURUSD',
             ptf=bt.TimeFrame.Minutes,
             pcomp=None,
             ptf1=bt.TimeFrame.Minutes,
             pcomp1=30,
             preplay=True,
             pstart_date="2020-03-21",
             pend_date="2020-03-22",
             pwrite_csv=False,
             pread_csv=False,
             phost='192.168.100.110',
             pdebug=False,
             phistory=False,
             pmt5broker=False,
             psizer_type=bt.sizers.FixedSize,
             pcash=10000,
             pstake=1,
             pcommission=15,
             pmargin=1000,
             pmult=100000,
             pplot=True,
             panalyze=True,
             pstrategy=MyStrategy,
             pstperiod=7,
             pstmultiplier=3,
             pdoprint=False,
             p_usepositions=True,
             optimize=False):

    to_str = collections.OrderedDict((
        (bt.TimeFrame.Ticks, 'T'),
        (bt.TimeFrame.Minutes, 'M'),
        (bt.TimeFrame.Days, 'Day'),
        (bt.TimeFrame.Weeks, 'W'),
        (bt.TimeFrame.Months, 'M'),
        (bt.TimeFrame.Years, 'Y'),
    ))

    cerebro = bt.Cerebro()

    if pmt5broker:
        store = MTraderStore(host=phost, debug=pdebug)
        broker = store.getbroker(use_positions=p_usepositions)  #
        cerebro.setbroker(broker)

        data = store.getdata(dataname=ppair,
                             timeframe=ptf,
                             compression=pcomp,
                             fromdate=pstart_date,
                             historical=False)
    else:
        if pwrite_csv:
            store = MTraderStore(host=phost, debug=pdebug)
            store.write_csv(symbol=ppair,
                            timeframe=ptf,
                            compression=pcomp,
                            fromdate=pstart_date,
                            todate=pend_date)

            time.sleep(0.250)
            # convert to utf-8
            cmd = f'iconv -f UTF-16 -t UTF-8 -o /home/awahyudi/Downloads/datas/{ppair}-{to_str[ptf]}{pcomp}-utf8.csv /media/winshare/{ppair}-{to_str[ptf]}{pcomp}.csv'
            os.system(cmd)

        if pread_csv:
            data = bt.feeds.GenericCSVData(
                dataname=
                f'/home/awahyudi/Downloads/datas/{ppair}-{to_str[ptf]}{pcomp}-utf8.csv',
                compression=1,
                timeframe=ptf,
                fromdate=pstart_date,
                todate=pend_date,
                dtformat=('%Y.%m.%d %H:%M:%S\t'),
                nullvalue=0.0,
                datetime=0,
                open=1,
                high=2,
                low=3,
                close=4,
                volume=5,
                openinterest=-1)

        elif not pmt5broker:
            store = MTraderStore(host=phost, debug=pdebug)
            data = store.getdata(dataname=ppair,
                                timeframe=ptf,
                                compression=pcomp,
                                fromdate=pstart_date,
                                todate=pend_date,
                                historical=True)

    if pcomp1:
        if preplay:
            cerebro.replaydata(data, timeframe=ptf1, compression=pcomp1)
        else:
            cerebro.resampledata(data, timeframe=ptf1, compression=pcomp1)

    # set sizer
    cerebro.addsizer(psizer_type, stake=pstake)

    if optimize == True:
        strats = cerebro.optstrategy(pstrategy,
                                     stperiod=range(5, 12),
                                     stmultiplier=range(5, 12))
    else:
        cerebro.addstrategy(pstrategy,
                            stperiod=pstperiod,
                            stmultiplier=pstmultiplier,
                            mt5broker=pmt5broker,
                            doprint=pdoprint)

    cerebro.broker.setcommission(commission=pcommission,
                                 margin=pmargin,
                                 mult=pmult)

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    if not optimize:
        results = cerebro.run()
    elif pread_csv:
        results = cerebro.run(maxcpus=4, stdstats=False)
    else:
        results = cerebro.run(maxcpus=1, stdstats=False)

    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    if pplot and not (optimize):
        cerebro.plot(style='candlestick', volume=True)

    #end_date=datetime(2019,3,1),
    #start_date = datetime(2019,1,1)
    #pstart_date=datetime(2020,3,27,19,10,0) - timedelta(hours=5),
    #pstart_date=datetime.now() - timedelta(hours=4) - timedelta(minutes=15),
         #pstart_date=datetime(2020,4,3,2,15,00),

runstrat(ppair='GBPUSD',
         ptf=bt.TimeFrame.Minutes,
         pcomp=1,
         ptf1=bt.TimeFrame.Minutes,
         pcomp1=1,
         preplay=False, 
         pstart_date=datetime.now() - timedelta(hours=4) - timedelta(minutes=15),
         pend_date=datetime.now() - timedelta(hours=4),
         pmt5broker=True,
         pread_csv=False,
         pwrite_csv=True,
         phost='192.168.100.113',
         pdebug=True,
         pplot=False,
         pdoprint = True,
         p_usepositions = False,
         psizer_type=bt.sizers.FixedSize,
         pcash=10000,
         pstake=1,
         pcommission=15,
         pmargin=1000,
         pmult=100000,
         panalyze=False,
         pstrategy=MyStrategy,
         pstperiod=5,
         pstmultiplier=9,
         optimize = False
        ) 
         #pstperiod=6, 10
         #pstmultiplier=9, 11
