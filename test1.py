'''
Author: www.backtest-rookies.com

MIT License

Copyright (c) 2017 backtest-rookies.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import backtrader as bt
from datetime import datetime


class Mltests(bt.Strategy):
    '''
    This strategy contains some additional methods that can be used to calcuate
    whether a position should be subject to a margin close out from Oanda.
    '''
    params = (('size', 100000),)

    def __init__(self):
        self.count = 0
        self.buybars = [1, 150]
        self.closebars = [100, 250]

    def next(self):
        bar = len(self.data)
        self.dt = self.data.datetime.date()
        if not self.position:
            if bar in self.buybars:
                self.cash_before = self.broker.getcash()
                #value = self.broker.get_value()
                entry = self.buy(size=self.p.size)
                entry.addinfo(name='Entry')
        else:
            '''
            First check if margin close out conditions are met. If not, check
            to see if we should close the position through the strategy rules.

            If a close out occurs, we need to addinfo to the order so that we
            can log it properly later
            '''
            mco_result = self.check_mco(
                value=self.broker.get_value(),
                margin_used=self.margin
            )

            if mco_result == True:
                close = self.close()
                close.addinfo(name='MCO')

            elif bar in self.closebars:
                close = self.close()
                close.addinfo(name='Close')

        self.count += 1

    def notify_trade(self, trade):
        if trade.isclosed:
            print('{}: Trade closed '.format(self.dt))
            print('{}: PnL Gross {}, Net {}\n\n'.format(self.dt,
                                                round(trade.pnl,2),
                                                round(trade.pnlcomm,2)))

    def notify_order(self,order):
        if order.status == order.Completed:
            ep = order.executed.price
            es = order.executed.size
            tv = ep * es
            leverage = self.broker.getcommissioninfo(self.data).get_leverage()
            self.margin = abs((ep * es) / leverage)

            if 'name' in order.info:
                if order.info['name'] == 'Entry':
                    print('{}: Entry Order Completed '.format(self.dt))
                    print('{}: Order Executed Price: {}, Executed Size {}'.format(self.dt,ep,es,))
                    print('{}: Position Value: {} Margin Used: {}'.format(self.dt,tv,self.margin))
                elif order.info['name'] == 'MCO':
                    print('{}: WARNING: Margin Close Out'.format(self.dt))
                else:
                    print('{}: Close Order Completed'.format(self.dt))

    def check_mco(self, value, margin_used):
        '''
        Make a check to see if the margin close out value has fallen below half
        of the margin used, close the position.

        value: value of the portfolio for a given data. This is essentially the
        same as the margin close out value which is balance + pnl
        margin_used: Initial margin
        '''

        if value < (margin_used /2):
            return True
        else:
            return False

class OandaCSVData(bt.feeds.GenericCSVData):
    params = (
        ('nullvalue', float('NaN')),
        ('dtformat', '%Y-%m-%dT%H:%M:%S.%fZ'),
        ('datetime', 6),
        ('time', -1),
        ('open', 5),
        ('high', 3),
        ('low', 4),
        ('close', 1),
        ('volume', 7),
        ('openinterest', -1),
    )

#tframes = dict(
#    minutes=bt.TimeFrame.Minutes,
#    daily=bt.TimeFrame.Days,
#    weekly=bt.TimeFrame.Weeks,
#    monthly=bt.TimeFrame.Months)

#Variable for our starting cash
startcash = 10000

#Create an instance of cerebro
cerebro = bt.Cerebro()

#Set commission
cerebro.broker.setcommission(leverage=50)

#Add our strategy
cerebro.addstrategy(Mltests)

#get oanda data
data = OandaCSVData(
    dataname='data/EUR_USD-2005-2017-D1.csv',
    fromdate=datetime(2005,1,1),
    todate=datetime(2006,1,1))

#Add the data to Cerebro
cerebro.adddata(data)

# Set our desired cash start
cerebro.broker.setcash(startcash)

# Run over everything
cerebro.run()

portvalue = cerebro.broker.getvalue()
pnl = portvalue - startcash

print('Final Portfolio Value: ${}'.format(portvalue))
print('P/L: ${}'.format(pnl))

#Finally plot the end results
cerebro.plot(style='candlestick')
