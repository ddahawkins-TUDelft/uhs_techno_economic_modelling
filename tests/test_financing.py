from uhs_costs.cost_model.financing import capital_recovery_factor, annualised_capex


def test_capital_recovery_factor_zero_discount_rate():
    assert capital_recovery_factor(0, 10) == 0.1


def test_capital_recovery_factor_positive():
    crf = capital_recovery_factor(0.07, 30)
    assert 0.07 < crf < 0.09


def test_annualised_capex():
    result = annualised_capex(1_000_000, 0, 10)
    assert result == 100_000