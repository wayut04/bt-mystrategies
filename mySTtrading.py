import backtrader as bt
from backtradermql5.mt5store import MTraderStore
from datetime import datetime, timedelta
from local.ind_supertrend import SuperTrend

class MyStrategy(bt.Strategy):
    params = (('ma1period', 30), ('ma2period', 5), ('ma3period', 30),
              ('atrperiod', 6), ('stop_loss', 0.08), ('stperiod',7), ('stmultiplier',3), ('doprint',False), )

    #def log(self, txt, dt=None):
    def log(self, txt, dt=None, doprint=False):
        ''' Logging function for this strategy'''
        if doprint or self.params.doprint:
            dt = dt or self.datas[0].datetime.datetime()
            print(f'{dt}: {txt}')

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.data1close = self.datas[1].close
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.inBuyPosition = False
        self.inSellPosition = False
        self.last2ST = 0

        #super().__init__()
        #self.broker.set_coc(True)

        # indicators
        self.ma1 = bt.indicators.SimpleMovingAverage(
            self.datas[1], period=self.params.ma1period)
        self.ma2 = bt.indicators.SimpleMovingAverage(
            self.datas[1], period=self.params.ma2period)
        self.ma3 = bt.indicators.SimpleMovingAverage(
            self.datas[1], period=self.params.ma3period)

        self.macross = bt.ind.CrossOver(self.ma1, self.ma3) # ma2

        #
        #self.atr = bt.ind.AverageTrueRange(period=self.params.atrperiod,
        #                                   plot=False)
        self.x = SuperTrend(self.datas[0], period=self.params.stperiod, multiplier=self.params.stmultiplier, plot=True)
        self.stcross = bt.ind.CrossOver(self.x, self.dataclose)

    def notify_order(self, order):

        if order.status in [order.Submitted, order.Accepted]:
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Price: %.5f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price, order.executed.value,
                          order.executed.comm))
                # set stop price
                #stop_price = order.executed.price * (1.0 - self.p.stop_loss)
                #self.sell(exectype=bt.Order.Stop, price=stop_price)

            elif order.issell():
                self.log('SELL EXECUTED, Price: %.5f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price, order.executed.value,
                          order.executed.comm))
                # set stop price
                #stop_price = order.executed.price * (1.0 + self.p.stop_loss)
                #self.buy(exectype=bt.Order.Stop, price=stop_price)

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
        # get pos and dpos parameter
        pos = self.getposition(self.data)
        dpos = pos.size

        self.log('Close, %.5f, Pos size: %.5f' % (self.dataclose[0], dpos))

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # Not yet ... we MIGHT BUY if

            # if moving average is crossing.. or supertrend cross (re-enter) (fix the moving average .. to include 3 MA)
            #if (self.macross==1) or (self.stcross==1 and (self.ma1[0] > self.ma2[0] > self.ma3[0])):
            #if (self.stcross<0) :  # condition supertrend crossing
            if (self.stcross<0) or ((self.dataclose[0] > self.last2ST) and self.last2ST!=0):
                # BUY!!! (with all possible default parameters)
                self.log('BUY CREATE1, %.5f' % self.dataclose[0])
                self.order = self.buy()
                self.inBuyPosition = True

            # if moving average is crossing.. or supertrend cross (re-enter)
            #if self.macross==-1 or (self.stcross==-1 and (self.ma1[0] < self.ma2[0] < self.ma3[0])):
            #if self.stcross>0:
            if (self.stcross>0) or ((self.dataclose[0] < self.last2ST) and self.last2ST!=0):
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE1, %.5f' % self.dataclose[0])
                self.order = self.sell()
                self.inSellPosition = True

        else:
            # Already in the market ..
            # we will buy if existing position is sell

            if self.inBuyPosition == True:
                # MA no longer aligned, close position
                #if (not (self.ma1[0] > self.ma2[0] > self.ma3[0])) or (self.stcross==-1 and dpos >= 0):
                #if (not (self.ma1[0] > self.ma3[0])) or (self.stcross > 0 and dpos >= 0):
                if self.stcross > 0 and dpos >= 0:
                    # SELL, SELL, SELL!!! (with all possible default parameters)
                    self.log('SELL CREATE2, %.5f' % self.dataclose[0])
                    #self.order = self.sell()
                    self.order = self.close()
                    #self.inSellPosition = True
                    self.inBuyPosition = False
                    self.last2ST = self.x[0] # set the last 2 ST.

                    #stop_price = self.data.close[0] * (1.0 + self.p.stop_loss)
                    #self.buy(exectype=bt.Order.Stop, price=stop_price)

            if self.inSellPosition == True:
                # MA no longer aligned, close position
                #if (not (self.ma1[0] < self.ma2[0] < self.ma3[0])) or (self.stcross==1 and dpos <= 0):
                #if (not (self.ma1[0] < self.ma3[0])) or (self.stcross < 0 and dpos <= 0):
                if self.stcross < 0 and dpos <= 0:
                    # BUY!!! (with all possible default parameters)
                    self.log('BUY CREATE2, %.5f' % self.dataclose[0])
                    #self.order = self.buy()
                    self.order = self.close()
                    #self.inBuyPosition = True
                    self.inSellPosition = False
                    self.last2ST = self.x[0] # set the last 2 ST.

                    #stop_price = self.data.close[0] * (1.0 - self.p.stop_loss)
                    #self.sell(exectype=bt.Order.Stop, price=stop_price)

    def stop(self):
        self.log('(SMA period %2d, %2d, %2d: ST (period,mul): %2d, %2d) Ending Value %.2f' %
                 (self.params.ma1period, self.params.ma2period,
                  self.params.ma3period, self.params.stperiod, self.params.stmultiplier,
                  self.broker.getvalue()),
                 doprint=True)

def runstrat(ppair='EURUSD',
             ptf=bt.TimeFrame.Minutes,
             pcomp=1,
             ptf1=bt.TimeFrame.Minutes,
             pcomp1=0,
             pstart_date="2020-03-21",
             pend_date="",
             phost='192.168.100.110',
             pdebug=False,
             phistory=True,
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
             pma1period=5,
             pma2period=10,
             pma3period=15,
             patrperiod=20,
             pstperiod=7,
             pstmultiplier=3,
             pdoprint=False,
             optimize=False):

    cerebro = bt.Cerebro()
    store = MTraderStore(host=phost, debug=pdebug)

    # get data
    data = store.getdata(dataname=ppair,
                         timeframe=ptf,
                         compression=pcomp,
                         fromdate=pstart_date,
                         todate=pend_date,
                         historical=phistory)

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # resample the data if required
    if pcomp1:
        cerebro.resampledata(data, timeframe=ptf1, compression=pcomp1)
        #cerebro.replaydata(data, timeframe=ptf1, compression=pcomp1)

    # Set our desired cash start
    cerebro.broker.setcash(pcash)

    # set sizer
    cerebro.addsizer(psizer_type, stake=pstake)

    #----- Normal Strategy
    #cerebro.addstrategy(MyStrategy, ma1period=5, ma2period=10, ma3period=17, atrperiod=10)
    #    pstrategy,
    if optimize == True:
        strats = cerebro.optstrategy(pstrategy,
                                     ma1period=pma1period,
                                     ma2period=pma2period,
                                     ma3period=pma3period,
                                     atrperiod=patrperiod,
                                     stperiod=range(5,9),
                                     stmultiplier=range(6,10))

    else:
        cerebro.addstrategy(pstrategy,
                            ma1period=pma1period,
                            ma2period=pma2period,
                            ma3period=pma3period,
                            atrperiod=patrperiod,
                            stperiod=pstperiod,
                            stmultiplier=pstmultiplier)
        #doprint=pdoprint)

    #----- Set commission
    #cerebro.broker.setcommission(commission=15,margin=1000, mult=100000)
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

    if optimize==True:
        results = cerebro.run(maxcpus=1, stdstats=False)
    else:
        results = cerebro.run()
    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    if pplot and not(optimize):
        cerebro.plot(style='candlestick', volume=False)

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


#pend_date=datetime.now() - timedelta(days=20),
runstrat(ppair='EURUSD',
         ptf=bt.TimeFrame.Minutes,
         pcomp=30,
         ptf1=bt.TimeFrame.Minutes,
         pcomp1=30,
         pstart_date=datetime.now() - timedelta(days=10),
         phost='192.168.100.113',
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
         panalyze=False,
         pstrategy=MyStrategy,
         pma1period=1,
         pma2period=1,
         pma3period=1,
         patrperiod=1,
         pstperiod=6,
         pstmultiplier=9,
         pdoprint = False,
         optimize = False
        ) 
