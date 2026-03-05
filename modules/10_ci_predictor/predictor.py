import os
import json
import logging
import random
from datetime import datetime

class FailurePredictor:
    def __init__(self, models_dir="models", results_dir="results"):
        self.models_dir = models_dir
        self.results_dir = results_dir
        self.logger = logging.getLogger(__name__)

        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir)

    def extract_features(self, scenario):
        """Extract ML features from a raw scenario."""
        priority_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        
        # Feature vector components
        priority_score = priority_map.get(scenario.get("priority", "LOW"), 1)
        selector_complexity = len(scenario.get("selector_used", ""))
        is_form = 1 if "form" in scenario.get("selector_used", "").lower() else 0
        has_interaction = 1 if "mutation" in scenario.get("strategy", "").lower() else 0
        
        return [priority_score, selector_complexity, is_form, has_interaction]

    def predict_failures(self, run_id, scenarios):
        """Train a lightweight dummy predictor on historical data and predict failure chance for current subset."""
        import glob
        import numpy as np
        try:
            from sklearn.ensemble import RandomForestClassifier
            has_sklearn = True
        except ImportError:
            has_sklearn = False

        self.logger.info(f"CI Predictor Pipeline Initialized for {len(scenarios)} tests.")
        
        # 1. Gather historical data
        historical_files = glob.glob(os.path.join(self.results_dir, "*_results.json"))
        X_train = []
        y_train = []
        
        for file in historical_files:
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                
                for test in data.get("tests", []):
                    # We map back standard features to train
                    features = self.extract_features(test)
                    label = 1 if test.get("status") == "failed" else 0
                    X_train.append(features)
                    y_train.append(label)
            except Exception:
                continue

        # 2. Train Model or Fallback
        if has_sklearn and len(X_train) > 10 and sum(y_train) > 0: # Ensure we have real failures to train on
            clf = RandomForestClassifier(n_estimators=10, random_state=42)
            clf.fit(X_train, y_train)
            
            for scenario in scenarios:
                features = np.array(self.extract_features(scenario)).reshape(1, -1)
                prob = clf.predict_proba(features)[0]
                fail_probability = prob[1] if len(prob) > 1 else 0.0
                scenario["failure_probability"] = round(float(fail_probability), 2)
        else:
            # Fallback heuristic logic if ML data is too sparse or sklearn isn't installed natively
            for scenario in scenarios:
                 features = self.extract_features(scenario)
                 # Heuristic: Complex forms have 15% fail chance natively, simple clicks 2%
                 base_prob = 0.15 if features[2] == 1 else 0.02
                 base_prob += (features[1] * 0.001) # Add tiny % per char of selector complexity
                 scenario["failure_probability"] = round(base_prob, 2)
                 
        self.logger.info(f"CI Failure Predictions calculated.")
        return scenarios
