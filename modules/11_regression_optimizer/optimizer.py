import os
import json
import logging

class RegressionOptimizer:
    def __init__(self, results_dir="results"):
        self.results_dir = results_dir
        self.logger = logging.getLogger(__name__)

        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)

    def optimize_regression_suite(self, run_id, scenarios):
        """
        Deterministic Regression Optimization:
        Analyze recent historical runs. If a module has consistently passed 
        across all recent runs, apply priority-based deterministic pruning:
        - HIGH priority: NEVER pruned (always critical to verify)
        - MEDIUM priority: Keep 1-in-3 as canary tests from stable modules
        - LOW priority: Pruned entirely from deeply stable modules
        
        This replaces the previous random.random() approach for CI/CD reproducibility.
        """
        self.logger.info("Initializing Regression Optimizer (Deterministic Mode)...")
        import glob
        
        # 1. Grab 3 most recent historical results
        result_files = glob.glob(os.path.join(self.results_dir, "*_results.json"))
        result_files.sort(key=os.path.getmtime, reverse=True)
        recent_files = result_files[:3]

        if not recent_files:
            self.logger.info("No historical data found. Regression Optimizer reverting to Full Suite mode.")
            return scenarios

        # 2. Map Module health from real execution data
        module_health = {}
        
        for file in recent_files:
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                    
                for test in data.get("tests", []):
                    module = test.get("module", "General")
                    status = test.get("status")
                    
                    if module not in module_health:
                        module_health[module] = {"passed": 0, "failed": 0}
                        
                    if status == "passed":
                         module_health[module]["passed"] += 1
                    else:
                         module_health[module]["failed"] += 1
            except Exception:
                continue
                
        # 3. Deterministic Optimization Logic (no randomness)
        optimized_scenarios = []
        pruned_count = 0
        medium_counter = 0  # Counter for deterministic 1-in-3 canary selection
        
        for scenario in scenarios:
            module = scenario.get("module", "General")
            priority = scenario.get("priority", "LOW").upper()
            health = module_health.get(module)
            
            # HIGH priority tests are NEVER pruned regardless of historical stability
            if priority == "HIGH":
                optimized_scenarios.append(scenario)
                continue
            
            # Check if module is "deeply stable" (never failed in recent runs with sufficient history)
            is_deeply_stable = (health and health["failed"] == 0 and health["passed"] > 5)
            
            if is_deeply_stable:
                if priority == "LOW":
                    # LOW priority + deeply stable = safe to prune entirely
                    pruned_count += 1
                    continue
                elif priority == "MEDIUM":
                    # MEDIUM priority + deeply stable = keep every 3rd test as a canary
                    medium_counter += 1
                    if medium_counter % 3 != 0:
                        pruned_count += 1
                        continue
            
            # All other cases: keep the scenario
            optimized_scenarios.append(scenario)

        self.logger.info(
            f"Regression Optimizer active (Deterministic). "
            f"Pruned {pruned_count} deeply stable tests. "
            f"Keeping {len(optimized_scenarios)}/{len(scenarios)} scenarios for execution."
        )
        return optimized_scenarios

