import collections
import backtrader as bt
from backtradermql5.mt5store import MTraderStore
from datetime import datetime, timedelta
from local.ind_supertrend import SuperTrend
import os
import time

class PSAR_Strategy(bt.Strategy):
    params = (
        ('mt5broker', False),
        ('period', 2),
        ('af', 0.02),
        ('afmax', 0.02),
        ('reversed', False),
        ('alternating', False),
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
        self.psar0 = bt.ind.ParabolicSAR(self.data0)
        self.psar1 = bt.ind.ParabolicSAR(self.data1)

        self.reversed = self.params.reversed
        self.loss_ctr = 0
        pass

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

        if self.params.alternating:
            if trade.pnlcomm < 0: 
                self.loss_ctr += 1

            if self.loss_ctr >= 1:
                self.reversed = not self.reversed
                self.loss_ctr = 0

    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # get pos and dpos parameter
        pos = self.getposition(self.data)
        dpos = pos.size
        cash = self.broker.getcash()

        # for multiple data
        data = self.data0
        self.log(f'{data._name} | Cash {cash} | O: {data.open[0]} H: {data.high[0]} L: {data.low[0]} C: {data.close[0]} V:{data.volume[0]} Pos:{dpos} PSAR:{self.psar0[0]}')
        data = self.data1
        self.log(f'{data._name} | Cash {cash} | O: {data.open[0]} H: {data.high[0]} L: {data.low[0]} C: {data.close[0]} V:{data.volume[0]} Pos:{dpos} PSAR:{self.psar1[0]}')

        #Check if we are in the market
        if not self.position:
            # if higher TF (data1) is higher than higher TF PSAR and 
            #   lower TF (data0) is higher than lower TF PSAR
            #       buy
            if (self.data1.close[0] > self.psar1[0]) and (self.data0.close[0] > self.psar0[0]):
                if not self.reversed:
                    self.log('BUY CREATE1, %.5f' % self.dataclose[0])
                    self.order = self.buy()
                    self.inBuyPosition = True
                else:
                    self.log('SELL CREATE1, %.5f' % self.dataclose[0])
                    self.order = self.sell()
                    self.inSellPosition = True


            # If higher TF (data1) is lower than higher TF PSAR and 
            #   lower TF (data0) is lower than lower TF PSAR
            #       sell
            if (self.data1.close[0] < self.psar1[0]) and (self.data0.close[0] < self.psar0[0]):
                if not self.reversed:
                    self.log('SELL CREATE1, %.5f' % self.dataclose[0])
                    self.order = self.sell()
                    self.inSellPosition = True
                else:
                    self.log('BUY CREATE1, %.5f' % self.dataclose[0])
                    self.order = self.buy()
                    self.inBuyPosition = True

        else:
            # if self.inBuyPosition: 
            # if higher TF (data1) is higher than higher TF PSAR or
            #   if lower TF (data0) is higher than lower TF PSAR
            #       sell (close)
            if (self.data1.close[0] < self.psar1[0]) or (self.data0.close[0] < self.psar0[0]):
                if not self.reversed:
                    if self.inBuyPosition:
                        self.log('SELL CREATE2, %.5f' % self.dataclose[0])
                        self.order = self.close()            
                        self.inBuyPosition = False
                else:
                    if self.inSellPosition:
                        self.log('BUY CREATE2, %.5f' % self.dataclose[0])
                        self.order = self.close()
                        self.inSellPosition = False

            # if self.inSellPosition
            # If higher TF (data1) is lower than higher TF PSAR or 
            #   if lower TF (data0) is lower than lower TF PSAR
            #       buy (close)
            if (self.data1.close[0] > self.psar1[0]) or (self.data0.close[0] > self.psar0[0]):
                if not self.reversed:
                    if self.inSellPosition:
                        self.log('BUY CREATE2, %.5f' % self.dataclose[0])
                        self.order = self.close()
                        self.inSellPosition = False
                else:
                    if self.inBuyPosition:
                        self.log('SELL CREATE2, %.5f' % self.dataclose[0])
                        self.order = self.close()            
                        self.inBuyPosition = False

    def stop(self):
        self.log('(PSAR params: %2d, %.2f, %.2f) Ending Value %.2f' %
                 (self.params.period, self.params.af, self.params.afmax, self.broker.getvalue()), doprint=True)
        pass
        


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
             pstrategy=PSAR_Strategy,
             pperiod=1,
             paf=1,
             pafmax=1,
             pdoprint=True,
             p_usepositions=False,
             preversed=False,
             palternating=False,
             pperiod_min=2,
             pperiod_max=3,
             paf_min=0.02,
             paf_max=0.03,
             pafmax_min=0.20,
             pafmax_max=0.30,
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
    # lower timeframe
    cerebro.adddata(data)

    # higher timeframe
    if pcomp1:
        if preplay:
            cerebro.replaydata(data, timeframe=ptf1, compression=pcomp1)
        else:
            cerebro.resampledata(data, timeframe=ptf1, compression=pcomp1)

    # set sizer
    cerebro.addsizer(psizer_type, stake=pstake)

    # if optimize == True:
    #     strats = cerebro.optstrategy(pstrategy,
    #                                  ma1period=range(pma1periodmin, pma1periodmax),
    #                                  ma2period=range(pma2periodmin, pma2periodmax),
    #                                  ma3period=range(pma3periodmin, pma3periodmax))
    # else:
    #     cerebro.addstrategy(pstrategy,
    #                         ma1period=pma1period,
    #                         ma2period=pma2period,
    #                         ma3period=pma3period,
    #                         mt5broker=pmt5broker,
    #                         doprint=pdoprint)

    cerebro.addstrategy(pstrategy, reversed=preversed, alternating=palternating, doprint=pdoprint)

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
runstrat(ppair='EURUSD',
        ptf = bt.TimeFrame.Minutes,
        pcomp= 240,
        ptf1 = bt.TimeFrame.Days,
        pcomp1 = 1,
        preplay=False, 
        pstart_date=datetime.now() - timedelta(days=300) - timedelta(hours=4) - timedelta(minutes=5),
        pend_date=datetime.now() - timedelta(days=0) - timedelta(hours=4),
        pread_csv=True,
        pwrite_csv=True,
        phost='192.168.100.113',
        pdebug=True,
        pdoprint = False,
        pmt5broker=False,
        pplot=True,
        p_usepositions = False,
        psizer_type=bt.sizers.FixedSize,
        pcash=10000,
        pstake=1.5,
        pcommission=15,
        pmargin=1000,
        pmult=100000,
        pstrategy=PSAR_Strategy,
        pperiod=1,
        paf=1,
        pafmax=1,
        pperiod_min=2,
        pperiod_max=3,
        paf_min=0.02,
        paf_max=0.03,
        pafmax_min=0.20,
        pafmax_max=0.30,
        preversed=False,
        palternating=False,
        optimize = False,
        panalyze=False
        ) 
        # good for GBPUSD: (M1)
        # pstperiod=5,
        # pstmultiplier=7,

