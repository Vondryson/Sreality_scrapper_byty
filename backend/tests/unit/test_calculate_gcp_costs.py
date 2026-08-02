from scripts.calculate_gcp_costs import calculate_cost


def test_default_cost_matches_documented_base_scenario() -> None:
    estimate = calculate_cost()

    assert estimate.sql_compute_usd == 7.6703
    assert estimate.sql_storage_usd == 3.4023
    assert estimate.sql_backup_usd == 0.1601
    assert estimate.total_usd == 11.4827
    assert estimate.total_czk_excluding_tax == 275.58


def test_conservative_cost_matches_documented_scenario() -> None:
    estimate = calculate_cost(
        sql_backup_gib=10,
        cloud_storage_usd=0.40,
        artifact_registry_usd=0.15,
        cloud_run_usd=0.10,
        reserve_usd=0.25,
    )

    assert estimate.total_usd == 12.7731
    assert estimate.total_czk_excluding_tax == 306.55
