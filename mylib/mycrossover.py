#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from . import Indicator, And


class NonZeroDifference(Indicator):
    '''
    Keeps track of the difference between two data inputs skipping, memorizing
    the last non zero value if the current difference is zero

    Formula:
      - diff = data - data1
      - nzd = diff if diff else diff(-1)
    '''
    _mindatas = 2  # requires two (2) data sources
    alias = ('NZD',)
    lines = ('nzd',)

    def nextstart(self):
        self.l.nzd[0] = self.data0[0] - self.data1[0]  # seed value

    def next(self):
        d = self.data0[0] - self.data1[0]
        self.l.nzd[0] = d if d else self.l.nzd[-1]

    def oncestart(self, start, end):
        self.line.array[start] = (
            self.data0.array[start] - self.data1.array[start])

    def once(self, start, end):
        d0array = self.data0.array
        d1array = self.data1.array
        larray = self.line.array

        prev = larray[start - 1]
        for i in range(start, end):
            d = d0array[i] - d1array[i]
            larray[i] = prev = d if d else prev


