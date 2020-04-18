import collections
import backtrader as bt
from backtradermql5.mt5store import MTraderStore
from datetime import datetime, timedelta
from local.ind_supertrend import SuperTrend
import os

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
            dt = dt or self.datas[0].datetime.datetime()
            print(f'{dt}: {txt}')

    def __init__(self):
        self.dataclose = self.datas[0].close
        #self.data1close = self.datas[1].close
        self.order = None
        #self.buyprice = None
        #self.buycomm = None
        self.inBuyPosition = False
        self.inSellPosition = False
        self.live_data = False
        self.last2ST = 0
        #self.order_resubmit_buy = None
        #self.order_resubmit_sell = None
        #self.bar_executed = 0

        self.x = SuperTrend(self.datas[0],
                            period=self.params.stperiod,
                            multiplier=self.params.stmultiplier,
                            plot=True)

        self.stcross = bt.ind.CrossOver(self.x, self.dataclose)

        super().__init__()
        #self.broker.set_coc(True)

    def notify_order(self, order):

        if order.status in [order.Submitted]:
            self.log('Order submitted')
            return
        if order.status in [order.Accepted]:
            self.log('Order accepted')
            return

        # Check if an order has been completed # Attention: broker could reject order if not enough cash
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

        elif order.status in [order.Canceled]:
            self.log('Order CANCELLED, Price: %.5f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price, order.executed.value,
                          order.executed.comm))

        elif order.status in [order.Margin]:
            self.log('Order Margin')
        elif order.status in [order.Rejected]:
            self.log('Order Rejected')
            # if order.isbuy(): 
            #     self.order_resubmit_buy = order  # flag order_resubmit
            # elif order.issell():
            #     self.order_resubmit_sell = order
        else:
            self.log('Order status: Others')  # just to check if there's other status we missed..

        # save the last order status, to be reviewed in _next_ call
        # self.last_order_status = order.status   # not usefull..

        # Write down: no pending order .. basically it means, close the order (?)
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            self.log('Notify trade: a new position?')
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # get pos and dpos parameter
        pos = self.getposition(self.data)
        dpos = pos.size
        #self.log('Close, %.5f, Pos size: %.5f' % (self.dataclose[0], dpos))
        cash = self.broker.getcash()
        #cash = 'NA'
        #if self.live_data:
        #    cash = self.broker.getcash()

        for data in self.datas:
            self.log(
                f'{data._name} | Cash {cash} | O: {data.open[0]} H: {data.high[0]} L: {data.low[0]} C: {data.close[0]} V:{data.volume[0]} Pos:{dpos}'
            )

        # Check if an order is pending ...
        if self.order:
            self.log('next: Order is pending')  #: ', self.last_order_status)
            return

        # Check if we are in the market
        #if not self.position:

        #### simple strategi from cerebro (just for test.. )
        #if not self.position:
        #### resubmitting last cancelled order
        #        if self.order_resubmit:
        #            time.sleep(0.25)
        #            self.submit(self.order_resubmit)
        #            self.log('ORDER resubmitted')
        #            self.order_resubmit = 0  # neutralize it!

        ####
        if not self.position:
            # There is no current position... we MIGHT BUY if 
            # this stcross only active on exactly the first the bar
            # add or condition if order is resubmitted (signalled by order.rejected)
            if (self.stcross < 0) or ((self.dataclose[0] > self.last2ST) and self.last2ST != 0):
                    # or self.order_resubmit_buy:

                self.log('BUY CREATE1, %.5f' % self.dataclose[0])

                #if self.live_data or not self.params.mt5broker:
                self.order = self.buy()
                #self.buy_order = self.order
                self.inBuyPosition = True

                # self.order_resubmit_buy = 0
                
            # if supertrend  is crossing..
            if (self.stcross > 0) or ((self.dataclose[0] < self.last2ST) and self.last2ST != 0):
                    # or self.order_resubmit_sell:

                self.log('SELL CREATE1, %.5f' % self.dataclose[0])

                #if self.live_data or not self.params.mt5broker:
                self.order = self.sell()
                #self.sell_order = self.order

                #self.order_resubmit_sell = 0
                self.inSellPosition = True

        else:
            # Already in the market ..
            if self.inBuyPosition == True:
            #if dpos > 0:
                # close position if..
                if (self.stcross > 0): # and dpos > 0):
                    # or self.order_resubmit_sell:
                    # CLOSE!!
                    self.log('SELL CREATE2, %.5f' % self.dataclose[0])

                    # if self.live_data:
                    #     self.cancel(self.buy_order)  # self.trade.tradeid)
                    # elif not self.params.mt5broker:
                    #     self.order = self.close()  # self.trade.tradeid)

                    self.order = self.close()

                    # self.order_resubmit_sell = 0
                    self.inBuyPosition = False
                    self.last2ST = self.x[0]   # TODO: this probably doesn't really works.. fix this!!!
                                                # create a function that captures the last ST position (right before crossing)

            if self.inSellPosition == True:
            #if dpos < 0:
                # close position if..
                if (self.stcross < 0): # and dpos <= 0): 
                    #or self.order_resubmit_buy:
                    # CLOSE!!
                    self.log('BUY CREATE2, %.5f' % self.dataclose[0])

                    # if self.live_data:
                    #     self.cancel(self.sell_order)  # self.trade.tradeid)
                    # elif not self.params.mt5broker:
                    #     self.order = self.close()  # self.trade.tradeid)

                    self.order = self.close()

                    # self.order_resubmit_buy = 0
                    self.inSellPosition = False
                    self.last2ST = self.x[0]

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.now()

        #print('Data Status: %s' % data._getstatusname(status))
        self.log('Data Status: %s' % data._getstatusname(status), dt=dt)
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False


#    def notify_store(self, msg): # is it causing the trouble?
#        self.log('Notify store: %s' % msg)

    def stop(self):
        self.log('(ST (period,mul): %2d, %2d) Ending Value %.2f' %
                 (self.params.stperiod, self.params.stmultiplier,
                  self.broker.getvalue()),
                 doprint=True)

import time

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
             pdoprint=True,
             p_usepositions=True,
             pstperiodmin=1,
             pstperiodmax=2,
             pstmultipliermin=1,
             pstmultipliermax=2,
             optimize=False):
    #             pma1period=5,
    #             pma2period=10,
    #             pma3period=15,
    #             patrperiod=20,
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
                                     stperiod=range(pstperiodmin, pstperiodmax),
                                     stmultiplier=range(pstmultipliermin, pstmultipliermax))
        #stperiod=range(5,9),
        #stmultiplier=range(6,10))
    else:
        cerebro.addstrategy(pstrategy,
                            stperiod=pstperiod,
                            stmultiplier=pstmultiplier,
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


runstrat(ppair='EURUSD',
         ptf = bt.TimeFrame.Minutes,
         pcomp= 240,
         ptf1 = bt.TimeFrame.Minutes,
         pcomp1 = 240,
         preplay=False, 
         pstart_date=datetime.now() - timedelta(days=200) - timedelta(hours=4) - timedelta(minutes=5),
         pend_date=datetime.now() - timedelta(days=0) - timedelta(hours=4),
         pread_csv=True,
         pwrite_csv=False,
         phost='192.168.100.113',
         pdebug=True,
         pdoprint = True,
         pmt5broker=False,
         pplot=True,
         p_usepositions = False,
         psizer_type=bt.sizers.FixedSize,
         pcash=10000,
         pstake=1,
         pcommission=15,
         pmargin=1000,
         pmult=100000,
         panalyze=False,
         pstrategy=MyStrategy,
         pstperiod=1,
         pstmultiplier=3,
         pstperiodmin=1,
         pstperiodmax=10,
         pstmultipliermin=1,
         pstmultipliermax=10,
         optimize = False
        ) 
        # good for GBPUSD: (M1)
        # pstperiod=5,
        # pstmultiplier=7,
