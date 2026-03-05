import json
import os
import glob
import logging
from collections import defaultdict

class FlakinessDetector:
    """
    Module 6: Analyzes historical test runs to identify flaky tests 
    (tests that pass and fail without code changes).
    """
    def __init__(self, results_dir="results"):
        self.results_dir = results_dir
        self.logger = logging.getLogger(__name__)

    def _get_all_historical_results(self):
        """Load all historical run outputs from the results directory."""
        files = glob.glob(os.path.join(self.results_dir, "*_results.json"))
        files.sort() # Oldest to newest (string sorting works with our timestamp approach)
        
        all_runs = []
        for f in files:
            with open(f, "r", encoding="utf-8") as file:
                all_runs.append(json.load(file))
        return all_runs

    def calculate_flakiness(self):
        historical_runs = self._get_all_historical_results()
        
        if len(historical_runs) < 3:
            self.logger.info("Not enough historical data to calculate flakiness (need at least 3 runs).")
            return None
            
        # Dictionary to track pass/fail history per test ID
        # e.g., "TC_FORM_1": ["passed", "failed", "passed", "passed"]
        test_history = defaultdict(list)
        
        for run in historical_runs:
            for test in run.get("tests", []):
                test_history[test["test_id"]].append(1 if test["status"] == "passed" else 0)

        flakiness_report = []

        # Calculate variance/flakiness factor
        for test_id, history in test_history.items():
            total_runs = len(history)
            passed = sum(history)
            failed = total_runs - passed

            # Flakiness definition: if it has failed AND passed at least once
            is_flaky = False
            flakiness_score = 0.0

            if passed > 0 and failed > 0:
                is_flaky = True
                
                # Basic Flakiness calculation (e.g. failure rate, ideally we look for flip-flops)
                # the closer to 0.5 (50%), the flakier it is. So flip-rate * 2. 
                # (1.0 = perfectly flaky, flip flops every time)
                flips = 0
                for i in range(1, len(history)):
                    if history[i] != history[i-1]:
                        flips += 1
                        
                # Max possible flips is len-1. Real flakiness = flips / possible_flips
                flakiness_score = round(flips / max(1, (len(history) - 1)), 2)

            flakiness_report.append({
                "test_id": test_id,
                "total_executions": total_runs,
                "pass_count": passed,
                "fail_count": failed,
                "is_flaky": is_flaky,
                "flakiness_score": flakiness_score
            })
            
        # Sort by flakiest
        flakiness_report.sort(key=lambda x: x["flakiness_score"], reverse=True)
        
        # Save flakiness report
        report_file = os.path.join(self.results_dir, "flakiness_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump({"flakiness_analysis": flakiness_report}, f, indent=4)
            
        self.logger.info(f"Flakiness analysis completed on {len(historical_runs)} historical runs.")
        return report_file

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    detector = FlakinessDetector()
