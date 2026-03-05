import os
import json
import logging

class ApprovalGate:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.logger = logging.getLogger(__name__)

    def save_approved(self, run_id, approved_test_ids):
        """Called by Streamlit UI when user clicks 'Approve'"""
        scenarios_file = os.path.join(self.data_dir, f"{run_id}_scenarios.json")
        approved_file = os.path.join(self.data_dir, f"{run_id}_approved.json")

        if not os.path.exists(scenarios_file):
            self.logger.error(f"Scenarios file not found: {scenarios_file}")
            return False

        with open(scenarios_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        approved = []
        for scenario in data.get("scenarios", []):
            if scenario["test_id"] in approved_test_ids:
                scenario["status"] = "approved"
                approved.append(scenario)

        with open(approved_file, "w", encoding="utf-8") as f:
            json.dump({"run_id": run_id, "approved_scenarios": approved}, f, indent=4)

        self.logger.info(f"Saved {len(approved)} approved scenarios to {approved_file}")
        return True

    def get_pending_scenarios(self, run_id):
        """Called by Streamlit UI to load scenarios for approval"""
        filepath = os.path.join(self.data_dir, f"{run_id}_scenarios.json")
        if not os.path.exists(filepath):
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("scenarios", [])
