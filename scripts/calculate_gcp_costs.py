"""Reproduce the aggregate M0-05 monthly GCP cost estimate.

The defaults are deliberately conservative and contain no project or account data.
They are a planning model, not a replacement for the Google Cloud invoice.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


HOURS_PER_MONTH = 730.5
SQL_COMPUTE_USD_PER_HOUR = 0.0105
SQL_SSD_USD_PER_GIB_HOUR = 0.000465753
SQL_BACKUP_USD_PER_GIB_HOUR = 0.000109589


@dataclass(frozen=True)
class CostEstimate:
    fx_czk_per_usd: float
    sql_compute_usd: float
    sql_storage_usd: float
    sql_backup_usd: float
    cloud_storage_usd: float
    artifact_registry_usd: float
    cloud_run_usd: float
    reserve_usd: float
    total_usd: float
    total_czk_excluding_tax: float


def calculate_cost(
    *,
    fx_czk_per_usd: float = 24.0,
    sql_disk_gib: float = 10.0,
    sql_backup_gib: float = 2.0,
    cloud_storage_usd: float = 0.20,
    artifact_registry_usd: float = 0.05,
    cloud_run_usd: float = 0.0,
    reserve_usd: float = 0.0,
) -> CostEstimate:
    """Calculate costs that are expected to be non-zero for this project."""
    sql_compute = HOURS_PER_MONTH * SQL_COMPUTE_USD_PER_HOUR
    sql_storage = HOURS_PER_MONTH * sql_disk_gib * SQL_SSD_USD_PER_GIB_HOUR
    sql_backup = HOURS_PER_MONTH * sql_backup_gib * SQL_BACKUP_USD_PER_GIB_HOUR
    total = sum(
        (
            sql_compute,
            sql_storage,
            sql_backup,
            cloud_storage_usd,
            artifact_registry_usd,
            cloud_run_usd,
            reserve_usd,
        )
    )
    return CostEstimate(
        fx_czk_per_usd=fx_czk_per_usd,
        sql_compute_usd=round(sql_compute, 4),
        sql_storage_usd=round(sql_storage, 4),
        sql_backup_usd=round(sql_backup, 4),
        cloud_storage_usd=cloud_storage_usd,
        artifact_registry_usd=artifact_registry_usd,
        cloud_run_usd=cloud_run_usd,
        reserve_usd=reserve_usd,
        total_usd=round(total, 4),
        total_czk_excluding_tax=round(total * fx_czk_per_usd, 2),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fx", type=float, default=24.0, help="Planning CZK/USD rate")
    parser.add_argument("--backup-gib", type=float, default=2.0)
    parser.add_argument("--cloud-storage-usd", type=float, default=0.20)
    parser.add_argument("--artifact-registry-usd", type=float, default=0.05)
    parser.add_argument("--cloud-run-usd", type=float, default=0.0)
    parser.add_argument("--reserve-usd", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    estimate = calculate_cost(
        fx_czk_per_usd=args.fx,
        sql_backup_gib=args.backup_gib,
        cloud_storage_usd=args.cloud_storage_usd,
        artifact_registry_usd=args.artifact_registry_usd,
        cloud_run_usd=args.cloud_run_usd,
        reserve_usd=args.reserve_usd,
    )
    print(json.dumps(asdict(estimate), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

