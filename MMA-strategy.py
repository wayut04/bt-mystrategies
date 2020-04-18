import collections
import backtrader as bt
from backtradermql5.mt5store import MTraderStore
from datetime import datetime, timedelta
from local.ind_supertrend import SuperTrend
import os
import time

class MMA_Strategy(bt.Strategy):
    params = (
        ('mt5broker', False),
        ('ma1period', 2),
        ('ma2period', 4),
        ('ma3period', 6),
        ('doprint', False),
    )

    def log(self, txt, dt=None, doprint=False):
        ''' Logging function for this strategy'''
        if doprint or self.params.doprint:
            dt = dt or self.datas[0].datetime.datetime()
            print(f'{dt}: {txt}')

    def __init__(self):

        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.inBuyPosition = False
        self.inSellPosition = False

        # indicators
        self.ma1 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.ma1period)
        self.ma2 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.ma2period)
        self.ma3 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.ma3period)

        # entry and exit point
        #self.crossover1 = bt.ind.CrossOver(self.ma1, self.ma2, plot=True)
        #self.crossover2 = bt.ind.CrossOver(self.ma2, self.ma3, plot=True)
        
    def notify_order(self, order):
        
        if order.status in [order.Submitted, order.Accepted]:
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.5f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))
                
            elif order.issell():
                self.log('SELL EXECUTED, Price: %.5f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None
        
    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # get pos and dpos parameter
        pos = self.getposition(self.data)
        dpos = pos.size
        cash = self.broker.getcash()

        # for multiple data
        for data in self.datas:
            data = self.data
            self.log(f'{data._name} | Cash {cash} | O: {data.open[0]} H: {data.high[0]} L: {data.low[0]} C: {data.close[0]} V:{data.volume[0]} Pos:{dpos}')

        # Check if we are in the market
        if not self.position:
            # Not yet ... we MIGHT BUY if .. cross-over (close and entry sma)

            #if ((self.crossover1 > 0) and (self.ma2 >= self.ma3)) or (self.crossover2 > 0 and (self.ma1 >= self.ma2)): 
            if (self.ma1 >= self.ma2) and (self.ma2 >= self.ma3):
                # BUY!!! (with all possible default parameters)
                self.log('BUY CREATE1, %.5f' % self.dataclose[0])
                self.order = self.buy()
                self.inBuyPosition = True
                
            #if ((self.crossover1 < 0) and (self.ma2 <= self.ma3)) or (self.crossover2 < 0 and (self.ma1 <= self.ma2)): 
            if (self.ma1 <= self.ma2) and (self.ma2 <= self.ma3):
                # SELL !!! (with all possible default parameters)
                self.log('SELL CREATE1, %.5f' % self.dataclose[0])
                self.order = self.sell()
                self.inSellPosition = True

        else:
            # Already in the market ... we might sell (fast and slow exit sma crossdown)
            #if self.crossdown > 0:
            #    self.log('SELL CREATE, %.5f' % self.dataclose[0])
            #    self.order = self.sell()
            if ((self.dataclose[0] > self.ma2) or (self.ma1 > self.ma2) or (self.ma2 > self.ma3) or (self.ma1 > self.ma3)) and self.inSellPosition:
                # BUY!!! (with all possible default parameters)
                self.log('BUY CREATE2, %.5f' % self.dataclose[0])
                self.order = self.close()
                self.inSellPosition = False
            
            if ((self.dataclose[0] < self.ma2) or (self.ma1 < self.ma2) or (self.ma2 < self.ma3) or (self.ma1 < self.ma3)) and self.inBuyPosition:
                # SELL !!! (with all possible default parameters)
                self.log('SELL CREATE2, %.5f' % self.dataclose[0])
                self.order = self.close()            
                self.inBuyPosition = False

    def stop(self):
        self.log('(Entry SMA period: %2d, %2d, %2d) Ending Value %.2f' %
                 (self.params.ma1period, self.params.ma2period, self.params.ma3period, self.broker.getvalue()), doprint=True)
        


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
             pstrategy=MMA_Strategy,
             pma1period=1,
             pma2period=1,
             pma3period=1,
             pdoprint=True,
             p_usepositions=False,
             pma1periodmin=1,
             pma1periodmax=2,
             pma2periodmin=1,
             pma2periodmax=2,
             pma3periodmin=1,
             pma3periodmax=2,
             optimize=False):

    to_str = collections.OrderedDict((
        (bt.TimeFrame.Ticks, 'T'),
        (bt.TimeFrame.Minutes, 'M'),
        (bt.TimeFrame.Days, 'Day'),
        (bt.TimeFrame.Weeks, 'W'),
        (bt.TimeFrame.Months, 'MM'),
        (bt.TimeFrame.Years, 'Y'),
        ('Hours', 'H'),
    ))

    # convert 60M to 1H
    if (ptf == bt.TimeFrame.Minutes) and (pcomp >= 60): 
        pptf = 'Hours'
        ppcomp = pcomp//60
    else :
        pptf = ptf
        ppcomp = pcomp

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
        #elif not pmt5broker:
        #store = MTraderStore(host=phost, debug=pdebug)
        if not pread_csv:
            store = MTraderStore(host=phost, debug=pdebug)
            data = store.getdata(dataname=ppair,
                                timeframe=ptf,
                                compression=pcomp,
                                fromdate=pstart_date,
                                todate=pend_date,
                                historical=True)

            if pwrite_csv:
                store.write_csv(symbol=ppair,
                                timeframe=ptf,
                                compression=pcomp,
                                fromdate=pstart_date,
                                todate=pend_date)

                time.sleep(0.250)
                # convert to utf-8
                cmd = f'iconv -f UTF-16 -t UTF-8 -o /home/awahyudi/Downloads/datas/{ppair}-{to_str[pptf]}{ppcomp}-utf8.csv /media/winshare/{ppair}-{to_str[pptf]}{ppcomp}.csv'

                os.system(cmd)

        else:  # read csv
            data = bt.feeds.GenericCSVData(
                dataname=
                f'/home/awahyudi/Downloads/datas/{ppair}-{to_str[pptf]}{ppcomp}-utf8.csv',
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

    # add data
    if pcomp1:
        if preplay:
            cerebro.replaydata(data, timeframe=ptf1, compression=pcomp1)
        else:
            cerebro.resampledata(data, timeframe=ptf1, compression=pcomp1)

    # set sizer
    cerebro.addsizer(psizer_type, stake=pstake)

    if optimize == True:
        strats = cerebro.optstrategy(pstrategy,
                                     ma1period=range(pma1periodmin, pma1periodmax),
                                     ma2period=range(pma2periodmin, pma2periodmax),
                                     ma3period=range(pma3periodmin, pma3periodmax))
    else:
        cerebro.addstrategy(pstrategy,
                            ma1period=pma1period,
                            ma2period=pma2period,
                            ma3period=pma3period,
                            mt5broker=pmt5broker,
                            doprint=pdoprint)

    #----- Set commission
    cerebro.broker.setcommission(commission=pcommission,
                                 margin=pmargin,
                                 mult=pmult)

    # test analyzer
    if panalyze:
        cerebro.addanalyzer(bt.analyzers.TimeReturn,
                            timeframe=bt.TimeFrame.Years)
        cerebro.addanalyzer(bt.analyzers.SharpeRatio,
                            timeframe=bt.TimeFrame.Years)
        cerebro.addanalyzer(bt.analyzers.SQN, )

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    if not optimize:
        results = cerebro.run(stdstats=True)
    elif pread_csv:
        results = cerebro.run(maxcpus=4, stdstats=False)
    else:
        results = cerebro.run(maxcpus=1, stdstats=False)

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    if pplot and not (optimize):
        #cerebro.plot()
        cerebro.plot(style='candlestick', volume=True)

    if panalyze:
        strat = results[0]
        # Results of own analyzers
        al = strat.analyzers.timereturn
        print('-- Time Return:')
        for k, v in al.get_analysis().items():
            print('{}: {}'.format(k, v))

        al = strat.analyzers.sharperatio
        print('-- Sharpe Ratio:')
        for k, v in al.get_analysis().items():
            print('{}: {}'.format(k, v))

        al = strat.analyzers.sqn
        print('-- SQN:')
        for k, v in al.get_analysis().items():
            print('{}: {}'.format(k, v))


         #pstart_date = datetime(2019,12,16),
         #pend_date = datetime(2019,12,19),
runstrat(ppair='AUDUSD',
         ptf = bt.TimeFrame.Minutes,
         pcomp= 60,
         ptf1 = bt.TimeFrame.Minutes,
         pcomp1 = 60,
         preplay=False, 
         pstart_date=datetime.now() - timedelta(days=22) - timedelta(hours=4) - timedelta(minutes=5),
         pend_date=datetime.now() - timedelta(days=4) - timedelta(hours=4),
         pread_csv=True,
         pwrite_csv=True,
         phost='192.168.100.113',
         pdebug=True,
         pdoprint = True,
         pmt5broker=False,
         pplot=True,
         p_usepositions = False,
         psizer_type=bt.sizers.FixedSize,
         pcash=10000,
         pstake=1.5,
         pcommission=15,
         pmargin=1000,
         pmult=100000,
         pstrategy=MMA_Strategy,
        pma1period=4,
        pma2period=9,
        pma3period=14,
        pma1periodmin=2,
        pma1periodmax=9,
        pma2periodmin=5,
        pma2periodmax=15,
        pma3periodmin=8,
        pma3periodmax=20,
         optimize = False,
         panalyze=False
        ) 
        # good for GBPUSD: (M1)
        # pstperiod=5,
        # pstmultiplier=7,
