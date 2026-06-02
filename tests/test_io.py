from uhs_costs.io import project_root


def test_project_root_exists():
    assert project_root().exists()