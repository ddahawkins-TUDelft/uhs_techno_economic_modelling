from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace, fields
from typing import Any, Literal

import pandas as pd
import matplotlib.pyplot as plt
from uhs_costs.design.helpers.project import StorageTechnology

from uhs_costs.design.default_design_assumptions import construct_hystories_design_assumptions

from uhs_costs.design.salt_cavern import construct_project as construct_salt_cavern_project
from uhs_costs.design.aquifer import construct_project as construct_aquifer_project
from uhs_costs.design.depleted_gas_field import construct_project as construct_dgf_project

from uhs_costs.cost_model.depleted_gas_field import calculate_depleted_gas_field_cost_components
from uhs_costs.cost_model.salt_cavern import calculate_salt_cavern_cost_components
from uhs_costs.cost_model.aquifer import calculate_cost_components as calculate_aquifer_cost_components




from uhs_costs.design.default_design_assumptions import (
    SaltCavernDesignAssumptions,
    DepletedGasFieldDesignAssumptions,
    AquiferDesignAssumptions,
)

from uhs_costs.cost_model.default_cost_assumptions import (
    construct_hystories_cost_assumptions,
)


SensitivityLevel = Literal["low", "default", "high"]

# ----------------------------------------------------------------------------------------------------------------------
#
#                                       Sensitivity Class
#
# ----------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class SensitivitySpec:
    name: str
    parameter_group: str
    parameter_name: str
    values: dict[SensitivityLevel, Any]
    description: str = ""
    applies_to: tuple[StorageTechnology, ...] = (
        StorageTechnology.SALT_CAVERN,
        StorageTechnology.DEPLETED_GAS_FIELD,
        StorageTechnology.AQUIFER,
    )

# ----------------------------------------------------------------------------------------------------------------------
#
#                                       Defaults
#
# ----------------------------------------------------------------------------------------------------------------------

DEFAULT_SENSITIVITIES = [
    SensitivitySpec(
        name="working_gas_capacity",
        parameter_group="project",
        parameter_name="working_gas_capacity_kwh_lhv",
        values={
            "low": 350e6,
            "default": None,
            "high": 1_400e6,
        },
        description="Working gas capacity in kWh LHV.",
    ),
    SensitivitySpec(
        name="withdrawal_capacity",
        parameter_group="project",
        parameter_name="withdrawal_capacity_kw_h2_lhv",
        values={
            "low": 1_500_000,
            "default": None,
            "high": 6_000_000,
        },
        description="Withdrawal capacity in kW H2 LHV.",
    ),
    SensitivitySpec(
        name="injection_capacity",
        parameter_group="project",
        parameter_name="injection_capacity_kw_h2_lhv",
        values={
            "low": 750_000,
            "default": None,
            "high": 3_000_000,
        },
        description="Injection capacity in kW H2 LHV.",
    ),
    SensitivitySpec(
        name="purification_factor",
        parameter_group="design_general",
        parameter_name="purification_factor",
        values={
            "low": 1.0,
            "default": None,
            "high": 2.0,
        },
        description="Purification factor in the general design assumptions.",
        applies_to=(
            StorageTechnology.DEPLETED_GAS_FIELD,
            StorageTechnology.AQUIFER,
        ),
    ),
    SensitivitySpec(
        name="reference_reservoir_depth",
        parameter_group="design_general",
        parameter_name="reference_reservoir_depth_m",
        values={
            "low": 800.0,
            "default": None,
            "high": 1_800.0,
        },
        description="Reference reservoir depth in metres.",
    ),
]

# ----------------------------------------------------------------------------------------------------------------------
#
#                                       Functions
#
# ----------------------------------------------------------------------------------------------------------------------


def get_default_project_kwargs() -> dict:
    """
    Return default project-construction keyword arguments.

    Frozen dataclass assumptions are not constructed here. Instead, this returns
    override dictionaries that are passed into the official assumption
    constructors later.
    """
    return {
        "working_gas_capacity_kwh_lhv": 700e6,
        "withdrawal_capacity_kw_h2_lhv": 3_000_000,
        "injection_capacity_kw_h2_lhv": 1_500_000,
        "general_design_overrides": {},
        "technology_design_overrides": {},
        "cost_overrides": {},
    }

def apply_override_to_project_kwargs(
    project_kwargs: dict,
    sensitivity: SensitivitySpec,
    value,
) -> dict:
    """
    Apply one sensitivity override to project kwargs.

    This does not mutate frozen dataclasses. It only updates plain dictionaries
    that will later be passed into assumption constructors.
    """
    project_kwargs = {
        key: value_.copy() if isinstance(value_, dict) else value_
        for key, value_ in project_kwargs.items()
    }

    if value is None:
        return project_kwargs

    if sensitivity.parameter_group == "project":
        project_kwargs[sensitivity.parameter_name] = value

    elif sensitivity.parameter_group == "design_general":
        project_kwargs["general_design_overrides"][
            sensitivity.parameter_name
        ] = value

    elif sensitivity.parameter_group == "design_technology":
        project_kwargs["technology_design_overrides"][
            sensitivity.parameter_name
        ] = value

    elif sensitivity.parameter_group == "cost":
        project_kwargs["cost_overrides"][
            sensitivity.parameter_name
        ] = value

    else:
        raise ValueError(
            f"Unknown sensitivity parameter_group: {sensitivity.parameter_group}"
        )

    return project_kwargs

def apply_frozen_dataclass_overrides(instance, overrides: dict | None):
    """
    Return a new frozen dataclass instance with overrides applied.

    This avoids setattr(), which fails for frozen dataclasses.
    """
    if not overrides:
        return instance

    valid_field_names = {field.name for field in fields(instance)}
    invalid_field_names = set(overrides) - valid_field_names

    if invalid_field_names:
        invalid = ", ".join(sorted(invalid_field_names))
        raise ValueError(
            f"Invalid override field(s) for {type(instance).__name__}: {invalid}"
        )

    return replace(instance, **overrides)

def apply_nested_override(obj, path: tuple[str, ...], value):
    """
    Apply a nested override to either dictionaries or dataclass-like objects.

    Returns a modified copy rather than mutating the original object.
    """
    if value is None:
        return obj

    obj = deepcopy(obj)

    target = obj
    for key in path[:-1]:
        if isinstance(target, dict):
            target = target[key]
        else:
            target = getattr(target, key)

    final_key = path[-1]

    if isinstance(target, dict):
        target[final_key] = value
    else:
        setattr(target, final_key, value)

    return obj

def apply_override_to_project_kwargs(
    project_kwargs: dict,
    parameter_path: tuple[str, ...],
    value,
) -> dict:
    """
    Apply a sensitivity override to project keyword arguments.

    Handles:
    - top-level parameters, e.g. working_gas_capacity_kwh_lhv
    - nested parameters, e.g. cost_assumptions.purification_factor
    """
    project_kwargs = deepcopy(project_kwargs)

    if value is None:
        return project_kwargs

    if len(parameter_path) == 1:
        project_kwargs[parameter_path[0]] = value
        return project_kwargs

    top_level_key = parameter_path[0]
    nested_path = parameter_path[1:]

    project_kwargs[top_level_key] = apply_nested_override(
        obj=project_kwargs[top_level_key],
        path=nested_path,
        value=value,
    )

    return project_kwargs





def build_project(
    technology: StorageTechnology,
    **project_kwargs,
):
    design_assumptions = construct_hystories_design_assumptions(
        storage_technology=technology,
        general_overrides=project_kwargs["general_design_overrides"],
        technology_overrides=project_kwargs["technology_design_overrides"],
    )

    base_cost_assumptions = construct_hystories_cost_assumptions()

    cost_assumptions = apply_frozen_dataclass_overrides(
        base_cost_assumptions,
        project_kwargs["cost_overrides"],
    )

    if technology == StorageTechnology.SALT_CAVERN:
        return construct_salt_cavern_project(
            working_gas_capacity_kwh_lhv=project_kwargs[
                "working_gas_capacity_kwh_lhv"
            ],
            withdrawal_capacity_kw_h2_lhv=project_kwargs[
                "withdrawal_capacity_kw_h2_lhv"
            ],
            injection_capacity_kw_h2_lhv=project_kwargs[
                "injection_capacity_kw_h2_lhv"
            ],
            assumptions=design_assumptions,
            case='salt_cavern',
        )

    if technology == StorageTechnology.DEPLETED_GAS_FIELD:
        return construct_dgf_project(
            working_gas_capacity_kwh_lhv=project_kwargs[
                "working_gas_capacity_kwh_lhv"
            ],
            withdrawal_capacity_kw_h2_lhv=project_kwargs[
                "withdrawal_capacity_kw_h2_lhv"
            ],
            injection_capacity_kw_h2_lhv=project_kwargs[
                "injection_capacity_kw_h2_lhv"
            ],
            assumptions=design_assumptions,
            case='dgf',
        )

    if technology == StorageTechnology.AQUIFER:
        return construct_aquifer_project(
            working_gas_capacity_kwh_lhv=project_kwargs[
                "working_gas_capacity_kwh_lhv"
            ],
            withdrawal_capacity_kw_h2_lhv=project_kwargs[
                "withdrawal_capacity_kw_h2_lhv"
            ],
            injection_capacity_kw_h2_lhv=project_kwargs[
                "injection_capacity_kw_h2_lhv"
            ],
            assumptions=design_assumptions,
            case='aquifer',
        )

    raise ValueError(f"Unknown technology: {technology}")

def get_value_from_project_kwargs(
    project_kwargs: dict,
    sensitivity: SensitivitySpec,
):
    """
    Retrieve the resolved sensitivity parameter value from project kwargs.

    For default cases where value=None, this only returns the raw project kwargs
    value for project-level parameters. For assumption-level defaults, the
    resolved value should be read after constructing the assumptions.
    """
    if sensitivity.parameter_group == "project":
        return project_kwargs[sensitivity.parameter_name]

    if sensitivity.parameter_group == "design_general":
        return project_kwargs["general_design_overrides"].get(
            sensitivity.parameter_name,
            None,
        )

    if sensitivity.parameter_group == "design_technology":
        return project_kwargs["technology_design_overrides"].get(
            sensitivity.parameter_name,
            None,
        )

    if sensitivity.parameter_group == "cost":
        return project_kwargs["cost_overrides"].get(
            sensitivity.parameter_name,
            None,
        )

    raise ValueError(
        f"Unknown sensitivity parameter_group: {sensitivity.parameter_group}"
    )

def resolve_parameter_value_from_assumptions(
    sensitivity: SensitivitySpec,
    project_kwargs: dict,
    design_assumptions,
    cost_assumptions,
):
    """
    Resolve the actual parameter value after defaults and overrides have been
    applied.
    """
    if sensitivity.parameter_group == "project":
        return project_kwargs[sensitivity.parameter_name]

    if sensitivity.parameter_group == "design_general":
        return getattr(
            design_assumptions.general,
            sensitivity.parameter_name,
        )

    if sensitivity.parameter_group == "design_technology":
        return getattr(
            design_assumptions.technology_specific,
            sensitivity.parameter_name,
        )

    if sensitivity.parameter_group == "cost":
        return getattr(
            cost_assumptions,
            sensitivity.parameter_name,
        )

    raise ValueError(
        f"Unknown sensitivity parameter_group: {sensitivity.parameter_group}"
    )

def construct_assumptions_for_project(
    technology: StorageTechnology,
    project_kwargs: dict,
):
    design_assumptions = construct_hystories_design_assumptions(
        storage_technology=technology,
        general_overrides=project_kwargs["general_design_overrides"],
        technology_overrides=project_kwargs["technology_design_overrides"],
    )

    base_cost_assumptions = construct_hystories_cost_assumptions()

    cost_assumptions = apply_frozen_dataclass_overrides(
        base_cost_assumptions,
        project_kwargs["cost_overrides"],
    )

    return design_assumptions, cost_assumptions

def run_single_sensitivity_case(
    technology: StorageTechnology,
    sensitivity: SensitivitySpec,
    level: SensitivityLevel,
    override_value,
) -> dict:
    project_kwargs = get_default_project_kwargs(technology)

    project_kwargs = apply_override_to_project_kwargs(
        project_kwargs=project_kwargs,
        sensitivity=sensitivity,
        value=override_value,
    )

    design_assumptions, cost_assumptions = construct_assumptions_for_project(
        technology=technology,
        project_kwargs=project_kwargs,
    )

    resolved_parameter_value = resolve_parameter_value_from_assumptions(
        sensitivity=sensitivity,
        project_kwargs=project_kwargs,
        design_assumptions=design_assumptions,
        cost_assumptions=cost_assumptions,
    )

    project = build_project(
        technology=technology,
        project_kwargs=project_kwargs,
        design_assumptions=design_assumptions,
        cost_assumptions=cost_assumptions,
    )

    if technology == StorageTechnology.SALT_CAVERN:
        cost_rates = calculate_salt_cavern_cost_components(project)
    elif technology ==  StorageTechnology.AQUIFER:
        cost_rates = calculate_aquifer_cost_components(project)
    else:
        cost_rates = calculate_depleted_gas_field_cost_components(project)

    return {
        "technology": technology.value,
        "sensitivity": sensitivity.name,
        "level": level,
        "parameter_group": sensitivity.parameter_group,
        "parameter_name": sensitivity.parameter_name,
        "parameter_value": resolved_parameter_value,
        "description": sensitivity.description,
        **cost_rates,
    }