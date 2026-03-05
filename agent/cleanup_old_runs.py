"""
Data Retention Policy — Automatic Garbage Collector for Historical Run Data.

This module enforces two independent retention limits:
  1. TIME-BASED:  Delete any run files older than `retention_days` (default 30).
  2. COUNT-BASED: Keep only the most recent `max_runs` (default 50).

Both limits run independently. A file is deleted if it violates EITHER limit.

WHY the defaults are safe for AI/ML:
  - Module 03 (Risk Engine):    Improves with more history, but 20+ runs is already excellent.
  - Module 06 (Flakiness):      Needs minimum 3 runs. 50 runs gives deep statistical power.
  - Module 07 (Anomaly):        Z-Score stabilizes after ~10 runs of baseline data.
  - Module 10 (CI Predictor):   Random Forest trains well with 10+ labeled samples.
  - Module 11 (Optimizer):      Only looks at the 3 most recent runs anyway.

WHAT gets cleaned:
  - data/run_*              (DOM extractions, scenarios, approved, prioritized JSONs)
  - results/run_*           (execution results, anomalies, visual regression, status JSONs)
  - cypress/screenshots/*   (execution screenshots — NOT baselines)
  - data/screenshots/diffs/* (visual diff heatmaps from old runs)

WHAT is NEVER cleaned:
  - data/healed_selectors.json           (persistent self-healing memory bank)
  - data/screenshots/baseline/*          (visual regression golden masters)
  - results/flakiness_report.json        (cross-run aggregate — regenerated each run)
  - config/agent_config.json             (user configuration)
"""

import os
import re
import glob
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Set, List, Tuple

logger = logging.getLogger(__name__)


class DataRetentionManager:
    """Enforces storage limits on historical run data."""

    def __init__(self, data_dir="./data", results_dir="./results",
                 screenshots_dir="./cypress/screenshots",
                 retention_days=30, max_runs=50):
        self.data_dir = data_dir
        self.results_dir = results_dir
        self.screenshots_dir = screenshots_dir
        self.retention_days = retention_days
        self.max_runs = max_runs

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enforce_retention_policy(self) -> dict:
        """
        Main entry point. Runs both time-based and count-based cleanup.
        Returns a summary dict of what was deleted.
        """
        logger.info("=" * 50)
        logger.info("DATA RETENTION POLICY — Garbage Collector Started")
        logger.info(f"  Time Limit : Delete runs older than {self.retention_days} days")
        logger.info(f"  Count Limit: Keep only the newest {self.max_runs} runs")
        logger.info("=" * 50)

        # Step 1: Discover all unique run_ids across both directories
        all_run_ids = self._discover_all_run_ids()
        logger.info(f"Found {len(all_run_ids)} unique run IDs in storage.")

        if len(all_run_ids) == 0:
            logger.info("No run data found. Nothing to clean.")
            return {"deleted_runs": 0, "deleted_files": 0, "freed_bytes": 0}

        # Step 2: Identify which run_ids violate the TIME limit
        time_expired = self._get_time_expired_runs(all_run_ids)

        # Step 3: Identify which run_ids violate the COUNT limit
        count_expired = self._get_count_expired_runs(all_run_ids)

        # Step 4: Union of both sets = everything to delete
        runs_to_delete = time_expired | count_expired

        if not runs_to_delete:
            logger.info("All runs are within retention limits. No cleanup needed.")
            return {"deleted_runs": 0, "deleted_files": 0, "freed_bytes": 0}

        logger.info(f"Runs to purge: {len(runs_to_delete)}")
        logger.info(f"  Expired by TIME  ({self.retention_days}d): {len(time_expired)}")
        logger.info(f"  Expired by COUNT (>{self.max_runs}):  {len(count_expired)}")

        # Step 5: Delete all files associated with those run_ids
        total_files, total_bytes = self._delete_run_files(runs_to_delete)

        # Step 6: Clean orphaned screenshot folders
        orphan_files, orphan_bytes = self._clean_old_screenshots(runs_to_delete)
        total_files += orphan_files
        total_bytes += orphan_bytes

        summary = {
            "deleted_runs": len(runs_to_delete),
            "deleted_files": total_files,
            "freed_bytes": total_bytes,
            "freed_mb": float("{:.2f}".format(total_bytes / (1024 * 1024))),
            "time_expired_runs": list(time_expired),
            "count_expired_runs": list(count_expired)
        }

        logger.info(f"Cleanup complete: {total_files} files deleted, {summary['freed_mb']} MB freed.")
        logger.info("=" * 50)

        return summary

    # ------------------------------------------------------------------
    # Internal: Discovery
    # ------------------------------------------------------------------

    def _discover_all_run_ids(self) -> List[str]:
        """Scan data/ and results/ to find all unique run_YYYYMMDD_HHMMSS IDs."""
        run_id_pattern = re.compile(r"(run_\d{8}_\d{6})")
        found_ids: Set[str] = set()

        for directory in [self.data_dir, self.results_dir]:
            if not os.path.exists(directory):
                continue
            for filename in os.listdir(directory):
                match = run_id_pattern.match(filename)
                if match:
                    found_ids.add(match.group(1))

        # Sort chronologically (the timestamp in the name IS the sort key)
        return sorted(found_ids)

    # ------------------------------------------------------------------
    # Internal: Time-Based Expiry
    # ------------------------------------------------------------------

    def _get_time_expired_runs(self, all_run_ids: List[str]) -> Set[str]:
        """Return run_ids whose timestamp is older than retention_days."""
        expired: Set[str] = set()
        cutoff = datetime.now() - timedelta(days=self.retention_days)

        for run_id in all_run_ids:
            run_date = self._parse_run_timestamp(run_id)
            if run_date and run_date < cutoff:
                expired.add(run_id)

        return expired

    def _parse_run_timestamp(self, run_id: str):
        """Extract datetime from run_YYYYMMDD_HHMMSS format."""
        try:
            # run_20260304_162750 → 20260304_162750
            ts_str = run_id.replace("run_", "")
            return datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Internal: Count-Based Expiry
    # ------------------------------------------------------------------

    def _get_count_expired_runs(self, all_run_ids: List[str]) -> Set[str]:
        """If total runs exceed max_runs, mark the oldest ones for deletion."""
        if len(all_run_ids) <= self.max_runs:
            return set()

        # all_run_ids is sorted oldest→newest, so slice the beginning
        excess_count: int = len(all_run_ids) - self.max_runs
        oldest_runs: list = []
        for i in range(excess_count):
            oldest_runs.append(all_run_ids[i])
        return set(oldest_runs)

    # ------------------------------------------------------------------
    # Internal: File Deletion
    # ------------------------------------------------------------------

    def _delete_run_files(self, runs_to_delete: Set[str]) -> Tuple[int, int]:
        """Delete all files whose name starts with any of the given run_ids."""
        deleted_sizes: list = []

        for directory in [self.data_dir, self.results_dir]:
            if not os.path.exists(directory):
                continue

            for filename in os.listdir(directory):
                for run_id in runs_to_delete:
                    if filename.startswith(run_id):
                        filepath = os.path.join(directory, filename)
                        if os.path.isfile(filepath):
                            try:
                                fsize = int(os.path.getsize(filepath))
                                os.remove(filepath)
                                deleted_sizes.append(fsize)
                                logger.debug(f"  Deleted: {filepath} ({fsize} bytes)")
                            except OSError as e:
                                logger.warning(f"  Failed to delete {filepath}: {e}")
                        break  # No need to check other run_ids for this file

        return len(deleted_sizes), sum(deleted_sizes)

    def _clean_old_screenshots(self, runs_to_delete: Set[str]) -> Tuple[int, int]:
        """Delete screenshot files and diff heatmaps associated with expired runs."""
        deleted_sizes: list = []

        # Clean cypress/screenshots/ — match by run_id prefix in filename
        if os.path.exists(self.screenshots_dir):
            for root, dirs, files in os.walk(self.screenshots_dir):
                for filename in files:
                    for run_id in runs_to_delete:
                        if run_id in filename:
                            filepath = os.path.join(root, filename)
                            try:
                                fsize = int(os.path.getsize(filepath))
                                os.remove(filepath)
                                deleted_sizes.append(fsize)
                            except OSError:
                                pass
                            break

        # Clean data/screenshots/diffs/ — match by run_id in filename
        diffs_dir = os.path.join(self.data_dir, "screenshots", "diffs")
        if os.path.exists(diffs_dir):
            for filename in os.listdir(diffs_dir):
                for run_id in runs_to_delete:
                    if run_id in filename:
                        filepath = os.path.join(diffs_dir, filename)
                        try:
                            fsize = int(os.path.getsize(filepath))
                            os.remove(filepath)
                            deleted_sizes.append(fsize)
                        except OSError:
                            pass
                        break

        return len(deleted_sizes), sum(deleted_sizes)


# ------------------------------------------------------------------
# Standalone CLI usage
# ------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description="QA Agent Data Retention Cleanup")
    parser.add_argument("--days", type=int, default=30, help="Delete runs older than N days (default: 30)")
    parser.add_argument("--max-runs", type=int, default=50, help="Keep only the latest N runs (default: 50)")
    parser.add_argument("--data-dir", type=str, default="./data", help="Path to data directory")
    parser.add_argument("--results-dir", type=str, default="./results", help="Path to results directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    args = parser.parse_args()

    manager = DataRetentionManager(
        data_dir=args.data_dir,
        results_dir=args.results_dir,
        retention_days=args.days,
        max_runs=args.max_runs
    )

    if args.dry_run:
        all_ids = manager._discover_all_run_ids()
        time_expired = manager._get_time_expired_runs(all_ids)
        count_expired = manager._get_count_expired_runs(all_ids)
        to_delete = time_expired | count_expired

        print(f"\n[DRY RUN] Total runs found: {len(all_ids)}")
        print(f"[DRY RUN] Would delete {len(to_delete)} runs:")
        for rid in sorted(to_delete):
            reason = []
            if rid in time_expired:
                reason.append(f"older than {args.days} days")
            if rid in count_expired:
                reason.append(f"exceeds {args.max_runs} run limit")
            print(f"  - {rid}  ({', '.join(reason)})")
        print(f"[DRY RUN] Would keep {len(all_ids) - len(to_delete)} runs.")
    else:
        summary = manager.enforce_retention_policy()
        print(f"\nSummary: {json.dumps(summary, indent=2)}")
