import json
import os
import glob
import logging

class RiskScorer:
    def __init__(self, data_dir="data", results_dir="results"):
        self.data_dir = data_dir
        self.results_dir = results_dir
        self.logger = logging.getLogger(__name__)
        # Pre-compute historical failure rates once per scoring session
        self._historical_cache = None

    def _build_historical_failure_map(self):
        """Scan ALL historical results and compute real failure rates per test_id."""
        if self._historical_cache is not None:
            return self._historical_cache

        test_stats = {}  # test_id -> {"passed": N, "failed": N}
        result_files = glob.glob(os.path.join(self.results_dir, "*_results.json"))

        for rf in result_files:
            try:
                with open(rf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for test in data.get("tests", []):
                    tid = test.get("test_id", "")
                    if tid not in test_stats:
                        test_stats[tid] = {"passed": 0, "failed": 0}
                    if test.get("status") == "passed":
                        test_stats[tid]["passed"] += 1
                    else:
                        test_stats[tid]["failed"] += 1
            except Exception:
                continue

        self._historical_cache = test_stats
        self.logger.info(f"Built historical failure map from {len(result_files)} result files covering {len(test_stats)} unique test IDs.")
        return test_stats

    def _get_real_failure_rate(self, test_id):
        """Return the real historical failure rate for a specific test_id (0.0 to 1.0)."""
        history = self._build_historical_failure_map()
        stats = history.get(test_id)
        if not stats:
            return 0.10  # Default 10% for never-seen-before tests (conservative)
        total = stats["passed"] + stats["failed"]
        if total == 0:
            return 0.10
        return round(stats["failed"] / total, 2)

    def score_and_prioritize(self, run_id):
        approved_file = os.path.join(self.data_dir, f"{run_id}_approved.json")
        prioritized_file = os.path.join(self.data_dir, f"{run_id}_prioritized.json")

        if not os.path.exists(approved_file):
            self.logger.error(f"Approved scenarios file not found: {approved_file}")
            return None

        with open(approved_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        scenarios = data.get("approved_scenarios", [])

        # Step 1.5: Week 6 CI Failure Predictor Integration
        import importlib
        try:
            predictor_mod = importlib.import_module("modules.10_ci_predictor.predictor")
            predictor = predictor_mod.FailurePredictor(results_dir=self.results_dir)
            scenarios = predictor.predict_failures(run_id, scenarios)
        except Exception as e:
            self.logger.warning(f"Predictor module failed, skipping ML heuristic: {e}")
            for s in scenarios:
                s["failure_probability"] = 0.05  # Baseline default

        # Step 1: Score Tests using REAL historical data
        for scenario in scenarios:
            priority = scenario.get("priority", "LOW")
            base_score = 0.8 if priority == "HIGH" else (0.5 if priority == "MEDIUM" else 0.2)

            # Real ML prediction probability from Week 6 engine
            fail_prob = scenario.get("failure_probability", 0.0)

            # Real historical failure rate from actual past results (replaces random.uniform)
            historical_failure_rate = self._get_real_failure_rate(scenario.get("test_id", ""))

            # Calculate final risk score with heavy weighting on the new predictor
            scenario["risk_score"] = round(base_score + (historical_failure_rate * 0.3) + (fail_prob * 0.7), 2)
            scenario["historical_failure_rate"] = historical_failure_rate  # Expose for dashboard transparency

            # Reassign priority based on calculated risk score
            if scenario["risk_score"] >= 0.8:
                scenario["execution_order"] = 1
                scenario["risk_level"] = "CRITICAL"
            elif scenario["risk_score"] >= 0.5:
                scenario["execution_order"] = 2
                scenario["risk_level"] = "MODERATE"
            else:
                scenario["execution_order"] = 3
                scenario["risk_level"] = "LOW"

        # Step 2: Sort based on risk score (Highest risk runs first)
        scenarios.sort(key=lambda x: x["risk_score"], reverse=True)

        # Step 3: Save to prioritized execution list
        with open(prioritized_file, "w", encoding="utf-8") as f:
            json.dump({
                "run_id": run_id,
                "total_tests": len(scenarios),
                "execution_plan": scenarios
            }, f, indent=4)

        self.logger.info(f"Risk Engine processed and prioritized {len(scenarios)} tests using real historical data.")
        return prioritized_file

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    scorer = RiskScorer()
    if len(sys.argv) > 1:
        scorer.score_and_prioritize(sys.argv[1])
    else:
        scorer.score_and_prioritize("run_20260301_160228")
