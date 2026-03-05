import json
import logging
import os
import glob

class APIAnomalyDetector:
    """
    Module 7: Detects anomalous test execution patterns using real data from
    Cypress execution results, status files, and historical baselines.
    Replaces the previous simulated random-data approach with data-driven analysis.
    """
    def __init__(self, data_dir="data", results_dir="results"):
        self.data_dir = data_dir
        self.results_dir = results_dir
        self.logger = logging.getLogger(__name__)

    def _compute_historical_baseline(self):
        """Compute average execution time per module from all historical results."""
        module_times = {}  # module -> [durations]
        result_files = glob.glob(os.path.join(self.results_dir, "*_results.json"))

        for rf in result_files:
            try:
                with open(rf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for test in data.get("tests", []):
                    module = test.get("module", "General")
                    duration = test.get("execution_time_ms", 0)
                    if duration > 0:
                        module_times.setdefault(module, []).append(duration)
            except Exception:
                continue

        # Compute mean and standard deviation per module
        baselines = {}
        for module, times in module_times.items():
            if len(times) >= 2:
                mean = sum(times) / len(times)
                variance = sum((t - mean) ** 2 for t in times) / len(times)
                std_dev = variance ** 0.5
                baselines[module] = {"mean": mean, "std_dev": max(std_dev, 1.0)}  # min 1ms std
            elif times:
                baselines[module] = {"mean": times[0], "std_dev": times[0] * 0.5}

        return baselines

    def analyze_api_responses(self, run_id):
        """Analyze real test execution data for anomalies using statistical comparison."""
        anomalies = []

        # 1. Build historical baselines from past runs
        baselines = self._compute_historical_baseline()

        # 2. Load the CURRENT run's real results
        result_file = os.path.join(self.results_dir, f"{run_id}_results.json")

        if os.path.exists(result_file):
            with open(result_file, "r", encoding="utf-8") as f:
                run_data = json.load(f)

            for test in run_data.get("tests", []):
                test_id = test.get("test_id", "unknown")
                module = test.get("module", "General")
                duration = test.get("execution_time_ms", 0)
                status = test.get("status", "unknown")
                attempts = test.get("attempts", 1)
                selector = test.get("selector_used", "N/A")

                anomaly_reasons = []

                # Anomaly Type 1: Execution time significantly above historical mean (z-score > 2.0)
                baseline = baselines.get(module)
                if baseline and duration > 0:
                    z_score = (duration - baseline["mean"]) / baseline["std_dev"]
                    if z_score > 2.0:
                        anomaly_reasons.append(
                            f"Execution time {duration}ms is {z_score:.1f}σ above "
                            f"historical mean of {baseline['mean']:.0f}ms for module '{module}'"
                        )

                # Anomaly Type 2: Zero-duration failures (crash/syntax errors before execution)
                if duration == 0 and status == "failed":
                    anomaly_reasons.append(
                        "Test crashed instantly (0ms execution) — likely code generation syntax error or setup failure"
                    )

                # Anomaly Type 3: Multi-retry failures (required 2+ attempts = instability)
                if attempts >= 2 and status == "failed":
                    anomaly_reasons.append(
                        f"Failed after {attempts} retry attempts — persistent instability on selector '{selector}'"
                    )

                # Anomaly Type 4: Flaky recovery (passed only after retry)
                if attempts >= 2 and status == "passed":
                    anomaly_reasons.append(
                        f"Required {attempts} attempts to pass — intermittent flakiness detected"
                    )

                if anomaly_reasons:
                    anomalies.append({
                        "test_id": test_id,
                        "module": module,
                        "execution_time_ms": duration,
                        "status": status,
                        "attempts": attempts,
                        "selector": selector,
                        "reason": " | ".join(anomaly_reasons)
                    })

            self.logger.info(f"Analyzed {len(run_data.get('tests', []))} real test results for anomalies.")
        else:
            # Fallback: Scan Cypress status files if results aren't compiled yet
            status_files = glob.glob(os.path.join(self.results_dir, "*_status.json"))
            for sf in status_files:
                try:
                    with open(sf, "r", encoding="utf-8") as f:
                        status_data = json.load(f)
                    if status_data.get("failed", False):
                        duration = status_data.get("duration", 0)
                        anomalies.append({
                            "test_id": status_data.get("spec", "unknown"),
                            "module": "Unknown",
                            "execution_time_ms": duration,
                            "status": "failed",
                            "attempts": 1,
                            "selector": "N/A",
                            "reason": f"Cypress spec reported failure (duration: {duration}ms)"
                        })
                except Exception:
                    continue
            self.logger.info(f"No compiled results found. Scanned {len(status_files)} Cypress status files.")

        # Save Report
        anomaly_file = os.path.join(self.results_dir, f"{run_id}_anomalies.json")
        with open(anomaly_file, "w", encoding="utf-8") as f:
            json.dump({
                "run_id": run_id,
                "anomalies_detected": len(anomalies),
                "analysis_source": "real_execution_data",
                "anomalies": anomalies
            }, f, indent=4)

        self.logger.info(f"API Anomaly Detection found {len(anomalies)} real anomalies on {run_id}.")
        return anomaly_file

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    detector = APIAnomalyDetector()
    if len(sys.argv) > 1:
        detector.analyze_api_responses(sys.argv[1])
    else:
        detector.analyze_api_responses("run_20260301_160228")

