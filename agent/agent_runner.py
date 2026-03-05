import argparse
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any

# Set up simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(config_path="config/agent_config.json"):
    with open(config_path, "r") as f:
        return json.load(f)

def run_agent(override_url=None, auto_approve=False, max_scenarios=0):
    logging.info("Starting QA Agent Orchestrator...")
    
    # Apply override URL if provided
    if override_url:
        config_path = "config/agent_config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        config["target_url"] = override_url
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        logging.info(f"Target URL overridden for this job: {override_url}")

    config = load_config()
    target_url = override_url if override_url else config.get("target_url")
    logging.info(f"Target URL: {target_url}")
    
    # Generate timestamp for this run
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{run_timestamp}"
    logging.info(f"Initialized Run ID: {run_id}")
    
    # Ensure results and data directories exist
    results_dir = config.get("results_dir", "results")
    data_dir = config.get("data_dir", "data")
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    # Module 1 - DOM Crawler Trigger
    logging.info("=========================================")
    logging.info("STEP 1: DOM Crawler initialized")
    logging.info("Executing Cypress spec to extract DOM...")
    
    try:
        import subprocess
        cmd_list = ["npx", "cypress", "run", "--spec", "cypress/e2e/crawler.cy.js", "--env", f"run_id={run_id}", "--config", f"baseUrl={target_url},pageLoadTimeout=15000"]
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            check=True,
            shell=True,
            encoding="utf-8"
        )
        logging.info("Cypress extraction completed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Cypress extraction failed: {e.stderr}")
        return

    # Call DOM Parser
    logging.info("Parsing extracted DOM data...")
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    
    import importlib
    dom_parser_mod = importlib.import_module("modules.01_dom_crawler.dom_parser")
    DOMParser = dom_parser_mod.DOMParser
    
    parser = DOMParser(data_dir=data_dir)
    parsed_data = parser.parse_dom(f"{run_id}.json")
    
    if parsed_data:
        logging.info(f"DOM Parsing completed. Found {parsed_data.get('forms_found', 0)} forms and {parsed_data.get('buttons_found', 0)} buttons.")
        # We can eventually save this to results/run_TIMESTAMP.json
        run_file = os.path.join(results_dir, f"{run_id}_dom.json")
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, indent=4)
        logging.info(f"Run Step 1 outputs saved to {run_file}")
    
    logging.info("=========================================")
    logging.info("STEP 2: Scenario Generator initialized")
    
    rule_engine_mod = importlib.import_module("modules.02_scenario_generator.rule_engine")
    RuleEngine = rule_engine_mod.RuleEngine
    
    engine = RuleEngine(data_dir=data_dir)
    scenarios = engine.generate_scenarios(parsed_data)
    
    # NEW: Inject the 26 Core Application Test Cases 
    integration_mod = importlib.import_module("modules.02_scenario_generator.integration_engine")
    IntegrationEngine = integration_mod.IntegrationEngine
    integrator = IntegrationEngine(data_dir=data_dir)
    scenarios = integrator.inject_core_scenarios(scenarios, target_url=target_url)
    
    # NEW Week 7: Regression Optimizer (Smart Filtering)
    try:
        optimizer_mod = importlib.import_module("modules.11_regression_optimizer.optimizer")
        RegressionOptimizer = optimizer_mod.RegressionOptimizer
        optimizer = RegressionOptimizer(results_dir=results_dir)
        scenarios = optimizer.optimize_regression_suite(run_id, scenarios)
    except Exception as e:
        logging.warning(f"Regression Optimizer unavailable. Running full suite payload. {e}")
    
    if scenarios:
        engine.save_scenarios(scenarios, run_id)
        logging.info(f"Saved total {len(scenarios)} testing scenarios (DOM + Core).")
        logging.info(f"-> Please open the UI to approve these scenarios: 'streamlit run dashboard/app.py'")
    else:
        logging.warning("No interactive elements found to generate scenarios.")

    logging.info("=========================================")
    logging.info(f"Agent Orchestrator requires human-in-the-loop approval.")
    logging.info(f"Run ID: {run_id} is pending in the Dashboard.")
    
    # -------------------------------------------------------------
    # WEEK 3: Module 3 and 4 (Risk Engine & Test Code Gen)
    # Note: normally this would be triggered from Streamlit backend
    # but for standalone CLI execution, we'll auto-check if approved 
    # and execute them immediately.
    # -------------------------------------------------------------
    import time
    approved_file = os.path.join(data_dir, f"{run_id}_approved.json")

    # If fully automated flag is set, auto-approve the first 50 immediately!
    if auto_approve and len(scenarios) > 0:
        logging.info("🚀 Auto-Approve flag detected! Bypassing Human-in-the-Loop.")
        limit = len(scenarios) if max_scenarios <= 0 else min(max_scenarios, len(scenarios))
        selected: List[Dict[str, Any]] = []
        for i in range(limit):
            s = scenarios[i]
            s["status"] = "approved"
            selected.append(s)
        with open(approved_file, "w", encoding="utf-8") as f:
            json.dump({"run_id": run_id, "approved_scenarios": selected}, f, indent=4)
        logging.info(f"✅ Auto-approved {len(selected)} scenarios for single-site extraction.")

    logging.info(f"Waiting for human approval on run {run_id} ... (Press CTRL+C to skip/exit if GUI not running)")
    try:
        # Simple blocking polling for demo purposes when running from CLI
        # In a real microservice, Streamlit hitting an endpoint would trigger Week 3 instead
        max_wait_seconds = 900
        waited = 0
        while waited < max_wait_seconds:
            if os.path.exists(approved_file):
                break
            time.sleep(5)
            waited += 5
            
        if os.path.exists(approved_file):
            logging.info("=========================================")
            logging.info("STEP 3: Risk Engine & Prioritizer Triggered")
            
            scorer_mod = importlib.import_module("modules.03_risk_engine.scorer")
            RiskScorer = scorer_mod.RiskScorer
            scorer = RiskScorer(data_dir=data_dir)
            
            prioritized_file = scorer.score_and_prioritize(run_id)
            if prioritized_file:
                logging.info(f"Test Execution Order dynamically prioritized based on Risk Engine.")
            
            logging.info("=========================================")
            logging.info("STEP 4: Cypress Test Code Generator Triggered")
            
            cypress_builder_mod = importlib.import_module("modules.04_test_code_generator.cypress_builder")
            CypressBuilder = cypress_builder_mod.CypressBuilder
            builder = CypressBuilder(data_dir=data_dir)
            
            if builder.build_test_suite(run_id):
                logging.info("Dynamic Cypress .cy.js test suite generated and ready in 'cypress/e2e/generated'!")
            
            logging.info("=========================================")
            logging.info("STEP 5: Cypress Executor Triggered")
            
            executor_mod = importlib.import_module("modules.05_executor.run_tests")
            CypressExecutor = executor_mod.CypressExecutor
            executor = CypressExecutor(e2e_dir="cypress/e2e/generated", results_dir=results_dir)
            
            # Execute the tests and parse results
            result_file = executor.execute_and_log(run_id)
            
            if result_file:
                logging.info(f"Test Execution recorded in Shared Data Contract: {result_file}")
                
            logging.info("=========================================")
            logging.info("STEP 5.5: Visual Regression Heatmap Engine Triggered")
            
            try:
                visual_mod = importlib.import_module("modules.08_visual_regression.comparator")
                VisualComparator = visual_mod.VisualComparator
                visual_engine = VisualComparator()
                visual_report = visual_engine.compare_run(run_id)
                if visual_report:
                    logging.info(f"Visual Diff Analysis successfully saved to {visual_report}")
            except Exception as e:
                logging.error(f"Visual Regression Module failed to execute: {e}")
                
            logging.info("=========================================")
            logging.info("STEP 6: Flakiness Detector & API Anomaly Intelligence Triggered")
            
            # Flakiness
            flakiness_mod = importlib.import_module("modules.06_flakiness_detector.flakiness")
            FlakinessDetector = flakiness_mod.FlakinessDetector
            flakiness_engine = FlakinessDetector(results_dir=results_dir)
            flakiness_report = flakiness_engine.calculate_flakiness()
            
            # Anomaly
            anomaly_mod = importlib.import_module("modules.07_api_anomaly_detector.anomaly")
            APIAnomalyDetector = anomaly_mod.APIAnomalyDetector
            anomaly_engine = APIAnomalyDetector(data_dir=data_dir)
            anomaly_report = anomaly_engine.analyze_api_responses(run_id)
            
            logging.info(f"Intelligence Processing Complete for {run_id}. See Streamlit Dashboard for Analysis!")
            
            # DATA RETENTION: Automatic Garbage Collection
            try:
                retention_config = config.get("data_retention", {})
                if retention_config.get("enable_auto_cleanup", True):
                    logging.info("=========================================")
                    logging.info("STEP 7: Data Retention Policy — Garbage Collector")
                    cleanup_mod = importlib.import_module("agent.cleanup_old_runs")
                    DataRetentionManager = cleanup_mod.DataRetentionManager
                    gc = DataRetentionManager(
                        data_dir=data_dir,
                        results_dir=results_dir,
                        retention_days=retention_config.get("retention_days", 30),
                        max_runs=retention_config.get("max_runs", 50)
                    )
                    gc.enforce_retention_policy()
            except Exception as e:
                logging.warning(f"Data Retention cleanup skipped: {e}")
            
            logging.info("=========================================")
            logging.info("QA Agent Run completed successfully.")
            
        else:
            logging.warning("No approval received within the timeout window. Agent paused.")

    except KeyboardInterrupt:
        logging.info("Agent manual override exited gracefully.")

def run_multi_agent(urls_str, auto_approve=False, max_scenarios=0):
    """Dynamic Multi-URL Pipeline: Crawl N URLs, combine all scenarios into ONE run."""
    import importlib
    import subprocess
    import time
    
    # Parse URLs from comma/newline separated string
    urls = []
    for line in urls_str.replace(',', '\n').splitlines():
        cleaned = line.strip()
        if cleaned:
            urls.append(cleaned)
    
    if not urls:
        logging.error("No valid URLs provided.")
        return
    
    logging.info(f"Multi-URL Pipeline started with {len(urls)} URLs")
    for i, u in enumerate(urls, 1):
        logging.info(f"  [{i}] {u}")
    
    config = load_config()
    results_dir = config.get("results_dir", "results")
    data_dir = config.get("data_dir", "data")
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    
    # Single unified run_id for the whole batch
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{run_timestamp}"
    logging.info(f"Unified Run ID: {run_id}")
    
    # Ensure module paths are available
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    
    # Import modules once
    DOMParser = importlib.import_module("modules.01_dom_crawler.dom_parser").DOMParser
    RuleEngine = importlib.import_module("modules.02_scenario_generator.rule_engine").RuleEngine
    IntegrationEngine = importlib.import_module("modules.02_scenario_generator.integration_engine").IntegrationEngine
    
    all_scenarios: List[Dict[str, Any]] = []
    crawled_urls: List[str] = []
    
    for idx, url in enumerate(urls, 1):
        logging.info("=========================================")
        logging.info(f"CRAWLING [{idx}/{len(urls)}]: {url}")
        logging.info("=========================================")
        
        # Unique DOM filename per URL to avoid overwrites
        dom_file_id = f"{run_id}_url{idx}"
        
        try:
            cmd_list = ["npx", "cypress", "run", "--spec", "cypress/e2e/crawler.cy.js",
                        "--env", f"run_id={dom_file_id}",
                        "--config", f"baseUrl={url},pageLoadTimeout=15000"]
            result = subprocess.run(cmd_list, capture_output=True, text=True, check=True,
                                   shell=True, encoding="utf-8")
            logging.info(f"Cypress extraction completed for {url}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Cypress FAILED for {url}: {e.stderr[:200] if e.stderr else 'unknown'}")
            continue
        
        # Parse DOM
        parser = DOMParser(data_dir=data_dir)
        parsed_data = parser.parse_dom(f"{dom_file_id}.json")
        
        if not parsed_data:
            logging.warning(f"No DOM data extracted for {url}, skipping.")
            continue
        
        elem_count = len(parsed_data.get("interactive_elements", []))
        forms_count = parsed_data.get("forms_found", 0)
        logging.info(f"Extracted {elem_count} elements, {forms_count} forms from {url}")
        
        # Generate scenarios
        engine = RuleEngine(data_dir=data_dir)
        url_scenarios = engine.generate_scenarios(parsed_data)
        
        # Inject core scenarios (only for automationexercise domains)
        integrator = IntegrationEngine(data_dir=data_dir)
        url_scenarios = integrator.inject_core_scenarios(url_scenarios, target_url=url)
        
        # Tag each scenario with its source URL for the dashboard display
        for s in url_scenarios:
            s["source_url"] = url
        
        logging.info(f"Generated {len(url_scenarios)} scenarios for {url}")
        all_scenarios.extend(url_scenarios)
        crawled_urls.append(url)
        
        # Small delay to avoid port contention between Cypress launches
        if idx < len(urls):
            time.sleep(2)
    
    logging.info("=========================================")
    logging.info(f"MULTI-URL CRAWL COMPLETE")
    logging.info(f"Crawled {len(crawled_urls)}/{len(urls)} URLs successfully")
    logging.info(f"Total scenarios generated: {len(all_scenarios)}")
    logging.info("=========================================")
    
    if not all_scenarios:
        logging.warning("No scenarios generated from any URL.")
        return
    
    # Deduplicate test_ids (they may overlap across URLs) — prefix with URL index
    seen_ids = {}
    for s in all_scenarios:
        original_id = s["test_id"]
        if original_id in seen_ids:
            seen_ids[original_id] += 1
            s["test_id"] = f"{original_id}_v{seen_ids[original_id]}"
        else:
            seen_ids[original_id] = 1
    
    # Save combined scenarios under ONE run_id
    engine = RuleEngine(data_dir=data_dir)
    engine.save_scenarios(all_scenarios, run_id)
    logging.info(f"Saved {len(all_scenarios)} combined scenarios to {run_id}_scenarios.json")
    logging.info(f"Open the Dashboard to select and approve scenarios for execution.")
    
    # Update config with first URL for display
    config["target_url"] = crawled_urls[0] if crawled_urls else urls[0]
    with open("config/agent_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    
    # ---- Now wait for human approval, then continue pipeline ----
    import time as _time
    approved_file = os.path.join(data_dir, f"{run_id}_approved.json")
    
    if auto_approve and len(all_scenarios) > 0:
        logging.info("Auto-Approve flag detected! Bypassing Human-in-the-Loop.")
        limit = len(all_scenarios) if max_scenarios <= 0 else min(max_scenarios, len(all_scenarios))
        selected: List[Dict[str, Any]] = []
        for i in range(limit):
            s = all_scenarios[i]
            s["status"] = "approved"
            selected.append(s)
        with open(approved_file, "w", encoding="utf-8") as f:
            json.dump({"run_id": run_id, "approved_scenarios": selected}, f, indent=4)
        logging.info(f"Auto-approved {len(selected)} scenarios.")
    
    logging.info(f"Waiting for human approval on run {run_id} ...")
    try:
        max_wait_seconds = 900
        waited = 0
        while waited < max_wait_seconds:
            if os.path.exists(approved_file):
                break
            _time.sleep(5)
            waited += 5
        
        if os.path.exists(approved_file):
            logging.info("=========================================")
            logging.info("STEP 3: Risk Engine & Prioritizer")
            
            scorer_mod = importlib.import_module("modules.03_risk_engine.scorer")
            scorer = scorer_mod.RiskScorer(data_dir=data_dir)
            scorer.score_and_prioritize(run_id)
            
            logging.info("=========================================")
            logging.info("STEP 4: Cypress Test Code Generator")
            
            cypress_builder_mod = importlib.import_module("modules.04_test_code_generator.cypress_builder")
            builder = cypress_builder_mod.CypressBuilder(data_dir=data_dir)
            builder.build_test_suite(run_id)
            
            logging.info("=========================================")
            logging.info("STEP 5: Cypress Executor")
            
            executor_mod = importlib.import_module("modules.05_executor.run_tests")
            executor = executor_mod.CypressExecutor(e2e_dir="cypress/e2e/generated", results_dir=results_dir)
            executor.execute_and_log(run_id)
            
            logging.info("=========================================")
            logging.info("STEP 5.5: Visual Regression")
            try:
                visual_mod = importlib.import_module("modules.08_visual_regression.comparator")
                visual_mod.VisualComparator().compare_run(run_id)
            except Exception as e:
                logging.error(f"Visual Regression failed: {e}")
            
            logging.info("=========================================")
            logging.info("STEP 6: Flakiness & Anomaly Detection")
            
            flakiness_mod = importlib.import_module("modules.06_flakiness_detector.flakiness")
            flakiness_mod.FlakinessDetector(results_dir=results_dir).calculate_flakiness()
            
            anomaly_mod = importlib.import_module("modules.07_api_anomaly_detector.anomaly")
            anomaly_mod.APIAnomalyDetector(data_dir=data_dir).analyze_api_responses(run_id)
            
            # DATA RETENTION: Automatic Garbage Collection
            try:
                retention_config = config.get("data_retention", {})
                if retention_config.get("enable_auto_cleanup", True):
                    logging.info("=========================================")
                    logging.info("STEP 7: Data Retention Policy — Garbage Collector")
                    cleanup_mod = importlib.import_module("agent.cleanup_old_runs")
                    DataRetentionManager = cleanup_mod.DataRetentionManager
                    gc = DataRetentionManager(
                        data_dir=data_dir,
                        results_dir=results_dir,
                        retention_days=retention_config.get("retention_days", 30),
                        max_runs=retention_config.get("max_runs", 50)
                    )
                    gc.enforce_retention_policy()
            except Exception as e:
                logging.warning(f"Data Retention cleanup skipped: {e}")
            
            logging.info(f"Multi-URL Pipeline Complete for {run_id}!")
            logging.info("=========================================")
        else:
            logging.warning("No approval received within timeout.")
    except KeyboardInterrupt:
        logging.info("Agent manually exited.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Master QA Agent Orchestrator")
    parser.add_argument("--url", type=str, help="Override target URL from config (single URL)")
    parser.add_argument("--urls", type=str, help="Comma-separated list of URLs for multi-URL batch crawl")
    parser.add_argument("--auto-approve", action="store_true", help="Automatically approve scenarios and bypass HITL")
    parser.add_argument("--max-scenarios", type=int, default=0, help="Max scenarios to auto-approve. 0 means all.")
    args = parser.parse_args()
    
    if args.urls:
        # Multi-URL mode: crawl all, combine scenarios into ONE run
        run_multi_agent(args.urls, auto_approve=args.auto_approve, max_scenarios=args.max_scenarios)
    else:
        # Single URL mode (legacy)
        run_agent(override_url=args.url, auto_approve=args.auto_approve, max_scenarios=args.max_scenarios)
