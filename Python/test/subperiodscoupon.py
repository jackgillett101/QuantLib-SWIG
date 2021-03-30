"""
 Copyright (C) 2021 Marcin Rybacki

 This file is part of QuantLib, a free-software/open-source library
 for financial quantitative analysts and developers - http://quantlib.org/

 QuantLib is free software: you can redistribute it and/or modify it
 under the terms of the QuantLib license.  You should have received a
 copy of the license along with this program; if not, please email
 <quantlib-dev@lists.sf.net>. The license is also available online at
 <http://quantlib.org/license.shtml>.

 This program is distributed in the hope that it will be useful, but WITHOUT
 ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 FOR A PARTICULAR PURPOSE.  See the license for more details.
"""

import unittest
import QuantLib as ql


EPSILON = 1.e-9

CAL = ql.TARGET()

DAY_COUNTER = ql.ActualActual()

BDC = ql.ModifiedFollowing

VALUATION_DATE = CAL.adjust(ql.Date(15, ql.March, 2021))

SETTLEMENT_DELAY = 2


def flat_rate(rate):
    return ql.FlatForward(
        SETTLEMENT_DELAY, CAL, ql.QuoteHandle(ql.SimpleQuote(rate)), DAY_COUNTER)


def create_ibor_leg(ibor_idx, start, end):
    sch = ql.MakeSchedule(effectiveDate=start,
                          terminationDate=end,
                          tenor=ibor_idx.tenor(),
                          calendar=ibor_idx.fixingCalendar(),
                          convention=ibor_idx.businessDayConvention(),
                          backwards=True)
    return ql.IborLeg([1.0], sch, ibor_idx)


def create_sub_periods_coupon(ibor_idx, start, end, averaging_method):
    payment_calendar = ibor_idx.fixingCalendar()
    payment_bdc = ibor_idx.businessDayConvention()
    payment_date = payment_calendar.adjust(end, payment_bdc)
    fixing_delay = ibor_idx.fixingDays()
    cpn = ql.SubPeriodsCoupon(
        payment_date, 1.0, start, end, fixing_delay, ibor_idx)
    use_compounded_rate = (averaging_method == ql.RateAveraging.Compound)
    if use_compounded_rate:
        cpn.setPricer(ql.CompoundingRatePricer())
    else:
        cpn.setPricer(ql.AveragingRatePricer())
    return cpn


def create_sub_periods_leg(
        ibor_idx, start, end, cpn_frequency, averaging_method):
    sch = ql.MakeSchedule(effectiveDate=start,
                          terminationDate=end,
                          tenor=cpn_frequency,
                          calendar=ibor_idx.fixingCalendar(),
                          convention=ibor_idx.businessDayConvention(),
                          backwards=True)
    day_count = ibor_idx.dayCounter()
    return ql.SubPeriodsLeg(
        [1.0], 
        sch, 
        ibor_idx,
        day_count, 
        ql.Following, 
        CAL, 
        0, 
        [2], 
        [1.0], 
        [0.0], 
        [0.0], 
        ql.Period(), 
        CAL, 
        ql.Unadjusted, 
        False, 
        averaging_method)


def sum_ibor_leg_payments(leg):
    return sum([cf.amount() for cf in leg])


def compounded_ibor_leg_payment(leg):
    compound = 1.0
    for cf in leg:
        floating_cf = ql.as_floating_rate_coupon(cf)
        year_fraction = floating_cf.accrualPeriod()
        fixing = floating_cf.indexFixing()
        compound *= (1.0 + year_fraction * fixing)
    return compound - 1.0


def averaged_ibor_leg_payment(leg):
    acc = 0.0
    for cf in leg:
        floating_cf = ql.as_floating_rate_coupon(cf)
        year_fraction = floating_cf.accrualPeriod()
        fixing = floating_cf.indexFixing()
        acc += year_fraction * fixing
    return acc


class SubPeriodsCouponTest(unittest.TestCase):
    def setUp(self):
        ql.Settings.instance().evaluationDate = VALUATION_DATE
        self.nominal_ts_handle = ql.YieldTermStructureHandle(flat_rate(0.007))
        self.ibor_idx = ql.Euribor6M(self.nominal_ts_handle)
        self.ibor_idx.addFixing(ql.Date(10, ql.February, 2021), 0.0085)

    def check_single_period_coupon_replication(self, start, end, averaging):
        ibor_leg = create_ibor_leg(self.ibor_idx, start, end)
        sub_periods_cpn = create_sub_periods_coupon(
            self.ibor_idx, start, end, averaging)
        
        actual_payment = sub_periods_cpn.amount()
        expected_payment = sum_ibor_leg_payments(ibor_leg)

        fail_msg = """ Unable to replicate single period coupon payment:
                            calculated: {actual}
                            expected: {expected}
                            start: {start}
                            end: {end}
                   """.format(actual=actual_payment,
                              expected=expected_payment,
                              start=start,
                              end=end)
        self.assertTrue(
            abs(actual_payment - expected_payment) < EPSILON,
            msg=fail_msg)

    def test_regular_single_period_forward_starting_coupon(self):
        """Testing regular single period forward starting coupon"""
        start = ql.Date(15, ql.April, 2021)
        end = ql.Date(15, ql.October, 2021)

        self.check_single_period_coupon_replication(
            start, end, ql.RateAveraging.Simple)
        self.check_single_period_coupon_replication(
            start, end, ql.RateAveraging.Compound)

    def test_regular_single_period_coupon_after_fixing(self):
        """Testing regular single period coupon after fixing"""
        start = ql.Date(12, ql.February, 2021)
        end = ql.Date(12, ql.August, 2021)

        self.check_single_period_coupon_replication(
            start, end, ql.RateAveraging.Simple)
        self.check_single_period_coupon_replication(
            start, end, ql.RateAveraging.Compound)

    def test_irregular_single_period_coupon_after_fixing(self):
        """Testing irregular single period coupon after fixing"""
        start = ql.Date(12, ql.February, 2021)
        end = ql.Date(12, ql.June, 2021)

        self.check_single_period_coupon_replication(
            start, end, ql.RateAveraging.Simple)
        self.check_single_period_coupon_replication(
            start, end, ql.RateAveraging.Compound)


if __name__ == '__main__':
    print('testing QuantLib ' + ql.__version__)
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SubPeriodsCouponTest, 'test'))
    unittest.TextTestRunner(verbosity=2).run(suite)
