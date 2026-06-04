"""Financial calculations for techno-economic modelling."""


def capital_recovery_factor(
    discount_rate: float,
    lifetime_years: int,
) -> float:
    """Calculate the capital recovery factor.

    Parameters
    ----------
    discount_rate:
        Discount rate as a decimal, e.g. 0.07 for 7%.
    lifetime_years:
        Economic lifetime in years.
    """
    if lifetime_years <= 0:
        raise ValueError("lifetime_years must be positive.")

    if discount_rate == 0:
        return 1 / lifetime_years

    r = discount_rate
    n = lifetime_years

    return r * (1 + r) ** n / ((1 + r) ** n - 1)

def annualised_capex(
    capex: float,
    discount_rate: float,
    lifetime_years: int,
) -> float:
    """Annualise capital expenditure."""
    return capex * capital_recovery_factor(discount_rate, lifetime_years)

def fixed_om_cost(
    capex: float,
    fixed_om_fraction: float,
) -> float:
    """Calculate annual fixed O&M cost as a fraction of CAPEX."""
    return capex * fixed_om_fraction

