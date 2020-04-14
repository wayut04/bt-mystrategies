class superTrendStrategy(bt.Strategy):
    def log(self, txt, dt=None):
        if True:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s - %s' % (dt.isoformat(), txt))

    def __init__(self):
        #self.x = SuperTrend(self.data)
        self.x = SuperTrend(plot=True)
        self.dclose = self.datas[0].close
        self.cross = bt.ind.CrossOver(self.dclose, self.x)

    def notify(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return
        # Check if an order has been completed
        # Attention: broker could reject order if not enougth cash
        if order.status in [order.Completed, order.Canceled, order.Margin]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED: %s, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.data._name, order.executed.price,
                     order.executed.value, order.executed.comm))
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.opsize = order.executed.size
            else:  # Sell
                self.log(
                    'SELL EXECUTED: %s, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.data._name, order.executed.price,
                     order.executed.value, order.executed.comm))

    def notify_trade(self, trade):
        if trade.isclosed:
            self.log('TRADE PROFIT: EQ %s, GROSS %.2f, NET %.2f' %
                     ('Closed', trade.pnl, trade.pnlcomm))
        elif trade.justopened:
            self.log('TRADE OPENED: EQ %s, SIZE %2d' % ('Opened', trade.size))

    def next(self):
        pos = self.getposition(self.data)
        dpos = pos.size
        if self.cross[0] == 1 and dpos <= 0:
            self.order_target_percent(data=self.data, target=1)
        elif self.cross[0] == -1 and dpos >= 0:
            self.order_target_percent(data=self.data, target=-1)

