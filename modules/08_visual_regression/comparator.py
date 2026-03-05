import cv2
import os
import glob
import logging
import json
import shutil
import numpy as np
from skimage.metrics import structural_similarity as ssim

class VisualComparator:
    def __init__(self, baseline_dir="data/screenshots/baseline", current_dir="cypress/screenshots", diff_dir="data/screenshots/diffs"):
        self.baseline_dir = baseline_dir
        self.current_dir = current_dir
        self.diff_dir = diff_dir
        self.logger = logging.getLogger(__name__)

        os.makedirs(self.baseline_dir, exist_ok=True)
        os.makedirs(self.diff_dir, exist_ok=True)

    def compare_run(self, run_id):
        self.logger.info(f"Starting Visual Regression Analysis for run: {run_id}")
        diff_results = []
        
        # Search for screenshots captured during this specific run_id (Cypress stores deeply)
        import glob
        # Ensure deep recursive fetching from cypress default screenshots nested dirs
        current_images = glob.glob(self.current_dir + "/**/*.png", recursive=True)
        
        # We need to fall back if the user runs the tests from the root or changes paths
        if not current_images:
            current_images = glob.glob("cypress/screenshots/**/*.png", recursive=True)
        
        processed_count = 0
        for curr_img_path in current_images:
            filename = os.path.basename(curr_img_path)
            
            # Since Cypress might save generic screenshots if tests fail to hit the anchor,
            # we will dynamically capture BOTH anchored screenshots (run_xxx__TC_1.png)
            # OR Cypress default failed screenshots ("* (failed).png") and map them.
            
            # Normalize canonical UI test mapping
            if "__" in filename: # Explicit viewport snapshot anchor triggered
                canonical_name = filename.split("__")[-1]
                test_id = canonical_name.replace(".png", "")
            elif "(failed)" in filename: # Cypress natively snapshotted a crashed state
                # Fallback to map the folder name which is the spec file (e.g. 01_TC_FORM...)
                spec_folder = os.path.basename(os.path.dirname(curr_img_path))
                test_id = spec_folder.replace(".cy.js", "").split("_", 1)[-1] # 01_TC_FORM -> TC_FORM
                canonical_name = f"{test_id}_failed.png"
            else:
                continue # Ignore generic artifacts
                
            processed_count += 1
            
            base_img_path = os.path.join(self.baseline_dir, canonical_name)
            diff_img_path = os.path.join(self.diff_dir, f"{run_id}__{canonical_name}")

            if not os.path.exists(base_img_path):
                self.logger.info(f"No baseline found for {canonical_name}. Setting current as new baseline.")
                shutil.copy(curr_img_path, base_img_path)
                diff_results.append({
                    "test_id": canonical_name.replace(".png", ""),
                    "filename": filename,
                    "status": "new_baseline",
                    "score": 1.0,
                    "current_path": curr_img_path,
                    "baseline_path": base_img_path
                })
                continue

            # Both images exist, perform deep pixel analysis
            imgA = cv2.imread(base_img_path)
            imgB = cv2.imread(curr_img_path)
            
            # Snap dimensions to equalize (in case browser viewport shifted slightly)
            if imgA.shape != imgB.shape:
                imgB = cv2.resize(imgB, (imgA.shape[1], imgA.shape[0]))

            grayA = cv2.cvtColor(imgA, cv2.COLOR_BGR2GRAY)
            grayB = cv2.cvtColor(imgB, cv2.COLOR_BGR2GRAY)

            # Structural Similarity Index
            (score, diff) = ssim(grayA, grayB, full=True)
            diff = (diff * 255).astype("uint8")

            # 0.999 is a strict ratio allowing extremely minor artifacting but flagging pixel shifts
            if score < 0.999: 
                # Create a binary threshold from the pixel diff map
                thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
                contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                # Draw beautiful red bounding boxes over the current image to highlight shifts
                heatmap = imgB.copy()
                for c in contours:
                    (x, y, w, h) = cv2.boundingRect(c)
                    if w > 5 and h > 5: # Filter out absolute tiny noise
                        # BGR Red rectangle
                        cv2.rectangle(heatmap, (x, y), (x + w, y + h), (0, 0, 255), 2)
                
                cv2.imwrite(diff_img_path, heatmap)
                diff_results.append({
                    "test_id": canonical_name.replace(".png", ""),
                    "filename": filename,
                    "status": "diff_found",
                    "score": round(score, 4),
                    "current_path": curr_img_path,
                    "baseline_path": base_img_path,
                    "diff_path": diff_img_path
                })
                self.logger.warning(f"Visual Diff found in {canonical_name}! Score: {score}")
            else:
                diff_results.append({
                    "test_id": canonical_name.replace(".png", ""),
                    "filename": filename,
                    "status": "identical",
                    "score": round(score, 4),
                    "current_path": curr_img_path,
                    "baseline_path": base_img_path
                })

        self.logger.info(f"Visual Regression Complete. Processed {processed_count} screenshots.")

        result_file = os.path.join("results", f"{run_id}_visual_regression.json")
        with open(result_file, "w") as f:
            json.dump({"run_id": run_id, "visual_diffs": diff_results}, f, indent=4)
            
        return result_file

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    if len(sys.argv) > 1:
        VisualComparator().compare_run(sys.argv[1])
    else:
        VisualComparator().compare_run("test_run")
