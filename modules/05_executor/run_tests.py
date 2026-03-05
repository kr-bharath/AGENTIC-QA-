import os
import json
import logging
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime

class CypressExecutor:
    """
    Module 5: Executes the dynamically prioritized test suite 
    from 'cypress/e2e/generated' and compiles the results.
    """
    def __init__(self, e2e_dir="cypress/e2e/generated", results_dir="results"):
        self.e2e_dir = e2e_dir
        self.results_dir = results_dir
        self.logger = logging.getLogger(__name__)

        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)

    def execute_and_log(self, run_id):
        self.logger.info(f"Starting execution of generated Cypress test suite for {run_id}...")
        
        # We use concurrent parallel execution bounds to drastically cut time on 70+ Scenarios
        # For simplicity, we create chunks of specs instead of relying on slow parallel libraries requiring cloud.
        self.logger.info("Executing Cypress tests in Local Parallel Batches to maximize speed.")
        
        # Grab all generated test spec paths
        import glob
        import concurrent.futures

        data_dir = "data"
        prioritized_file = os.path.join(data_dir, f"{run_id}_prioritized.json")
        scenarios = []
        if os.path.exists(prioritized_file):
            with open(prioritized_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                scenarios = data.get("execution_plan", [])
                
        # Map specs to their scenario data mapping correctly
        execution_items: Dict[str, Any] = {}
        for i, scenario in enumerate(scenarios):
            spec_name = f"{i+1:02d}_{scenario['test_id']}.cy.js"
            spec_file = os.path.join(self.e2e_dir, spec_name).replace("\\", "/") # Normalize for Cypress CLI
            spec_file_str: str = str(spec_file)
            if os.path.exists(spec_file_str):
                execution_items[spec_file_str] = scenario
        
        start_time = datetime.now()
        
        # Setup healer and builder dynamically
        import importlib
        healer_mod = importlib.import_module("modules.09_self_healing.healer")
        healer = healer_mod.SelfHealer(data_dir=data_dir)
        
        cypress_builder_mod = importlib.import_module("modules.04_test_code_generator.cypress_builder")
        builder = cypress_builder_mod.CypressBuilder(data_dir=data_dir)
        
        # Tracking states
        final_tests: List[Dict[str, Any]] = []
        status_map: Dict[str, Dict[str, Any]] = {}
        for spec_file in execution_items:
            status_map[spec_file] = {
                "status": "pending", "flaky": False, "attempts": 0, 
                "duration": 0, "error_message": None, "error_type": None
            }
            
        max_retries: int = 3
        current_attempt: int = 1
        specs_to_run: List[str] = list(execution_items.keys())
        
        self.logger.info(f"Batched Execution Mode with Auto-Healing & {max_retries} Retries Enabled.")
        
        while current_attempt <= max_retries and specs_to_run:
            self.logger.info(f"--- ATTEMPT {current_attempt}/{max_retries}: Running Batch of {len(specs_to_run)} Specs ---")
            
            # Clean up old status JSON files to prevent false reads
            import glob
            for f in glob.glob(os.path.join(self.results_dir, "*_status.json")):
                try:
                    os.remove(f)
                except:
                    pass
            
            # Use comma separated specs for cypress --spec "a.js,b.js"
            spec_arg = ",".join([str(s) for s in specs_to_run])
            cmd = ["npx", "cypress", "run", "--spec", spec_arg]
            
            # Execute batch synchronously
            subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding="utf-8")
            
            # Assess Results from mapped Native JSON
            failed_specs_this_round: List[str] = []
            
            for spec_file in specs_to_run:
                status_map[spec_file]["attempts"] += 1
                spec_name = os.path.basename(spec_file)
                status_json = os.path.join(self.results_dir, f"{spec_name}_status.json")
                
                scenario = execution_items[spec_file]
                test_id = scenario["test_id"]
                
                # Check outcome natively output from cypress.config.js
                did_fail = True
                duration = 0
                error_message = None
                error_type = None
                if os.path.exists(status_json):
                    try:
                        with open(status_json, "r") as f:
                            res_data = json.load(f)
                            did_fail = res_data.get("failed", True)
                            duration = res_data.get("duration", 0)
                            error_message = res_data.get("errorMessage")
                            error_type = res_data.get("errorType")
                            status_map[spec_file]["duration"] += duration
                            status_map[spec_file]["error_message"] = error_message
                            status_map[spec_file]["error_type"] = error_type
                    except Exception:
                        pass
                else:
                    self.logger.warning(f"No result JSON found for {spec_name}. Assuming failed.")
                    
                if not did_fail:
                    status_map[spec_file]["status"] = "passed"
                    if current_attempt > 1:
                        status_map[spec_file]["flaky"] = True 
                else:
                    self.logger.warning(f"Test {test_id} failed attempt {current_attempt}/{max_retries}.")
                    status_map[spec_file]["status"] = "failed"
                    
                    if current_attempt < max_retries:
                        # Smart Retry: Don't retry syntax errors (0ms = code gen crash)
                        if duration == 0 and error_type == "SYNTAX_ERROR":
                            self.logger.warning(f"Skipping retry for {test_id} — syntax/setup error won't be fixed by retrying.")
                        else:
                            failed_specs_this_round.append(spec_file)
                            selector = scenario.get("selector_used")
                            self.logger.info(f"Triggering Self-Healing for {test_id}...")
                            if selector:
                                new_fallback = healer.register_failure(selector, test_id, run_id)
                                if new_fallback:
                                    # Re-write the spec file injecting the new robust multi-selector payload
                                    builder.write_spec(scenario, spec_file, run_id)

            specs_to_run = failed_specs_this_round
            current_attempt += 1

        # Execution done, compile payloads
        passed_count: int = 0
        failed_count: int = 0
        overall_status: str = "passed"
        
        for spec_file, info in status_map.items():
            scenario = execution_items[spec_file]
            if info["status"] == "passed":
                passed_count += 1
            else:
                failed_count += 1
                overall_status = "failed"
                
            final_tests.append({
                "test_id": scenario["test_id"],
                "scenario": scenario["scenario"],
                "module": scenario["module"],
                "priority": scenario["priority"],
                "status": info["status"],
                "flaky": info["flaky"],
                "attempts": info["attempts"],
                "execution_time_ms": int(info.get("duration", 0)),
                "selector_used": scenario.get("selector_used"),
                "risk_score": scenario.get("risk_score", 0.0),
                "source_url": scenario.get("source_url", "N/A"),
                "error_message": info.get("error_message"),
                "error_type": info.get("error_type")
            })
            
        execution_duration: float = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"Execution Completed! {str(overall_status).upper()} in {round(float(execution_duration), 2)}s")
            
        # Read the current active target URL from config
        config_path = "config/agent_config.json"
        active_url = "https://automationexercise.com"
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                active_url = config_data.get("target_url", active_url)

        # Write FINAL the Shared Data Contract 
        final_payload = {
            "run_id": run_id,
            "target_url": active_url,
            "timestamp": start_time.isoformat(),
            "tests": final_tests,
            "summary": {
                "total": len(final_tests),
                "passed": passed_count,
                "failed": failed_count,
                "execution_time_sec": round(float(execution_duration), 2),
                "status": overall_status
            }
        }
        
        run_file = os.path.join(self.results_dir, f"{run_id}_results.json")
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(final_payload, f, indent=4)
            
        self.logger.info(f"Saved completed execution results to {run_file}")
        return run_file

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    executor = CypressExecutor()
    if len(sys.argv) > 1:
        executor.execute_and_log(sys.argv[1])
    else:
        executor.execute_and_log("run_20260301_160228")
