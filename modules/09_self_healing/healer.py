import json
import os
import logging
import re

class SelfHealer:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.healed_file = os.path.join(self.data_dir, "healed_selectors.json")
        self.logger = logging.getLogger(__name__)

        if not os.path.exists(self.healed_file):
            with open(self.healed_file, "w") as f:
                json.dump({}, f)

    def get_fallback(self, original_selector):
        """Retrieve a known good fallback selector if one exists."""
        with open(self.healed_file, "r") as f:
            data = json.load(f)
        entry = data.get(original_selector)
        if entry is None:
            return None
        # Support both old format (string) and new format (dict with "fallback" key)
        if isinstance(entry, dict):
            return entry.get("fallback")
        return entry

    def _extract_tag_from_selector(self, selector):
        """Extract the base tag name from a CSS selector string."""
        # Match leading tag name: 'form#id', 'button.class', 'a[href]', 'input'
        match = re.match(r'^([a-zA-Z][a-zA-Z0-9]*)', selector)
        return match.group(1) if match else None

    def _search_dom_snapshot(self, original_selector, run_id):
        """Search DOM snapshot files to find alternative selectors for the failed element."""
        import glob
        # Look for any DOM snapshot from this run
        dom_files = glob.glob(os.path.join(self.data_dir, f"{run_id}*.json"))
        # Also check for general dom files
        dom_files += glob.glob(os.path.join(self.data_dir, "run_*_url*.json"))
        
        tag = self._extract_tag_from_selector(original_selector)
        
        for dom_file in dom_files:
            # Skip non-DOM files (scenarios, approved, prioritized, etc.)
            basename = os.path.basename(dom_file)
            if any(kw in basename for kw in ["scenarios", "approved", "prioritized", "healed"]):
                continue
            try:
                with open(dom_file, "r", encoding="utf-8") as f:
                    dom_data = json.load(f)
                
                for el in dom_data.get("elements", []):
                    el_selector = el.get("selector_guess", "")
                    
                    # Skip if it's the exact same selector that already failed
                    if el_selector == original_selector:
                        continue
                    
                    # Match by tag type
                    if tag and el.get("tag") == tag and el.get("isVisible", False):
                        # Strategy: Build a robust attribute selector
                        el_name = el.get("name", "")
                        el_type = el.get("type", "")
                        el_text = el.get("text", "").strip()
                        
                        if el_name:
                            return f"{tag}[name='{el_name}']"
                        elif el_type and el_type not in ["submit", "button"]:
                            return f"{tag}[type='{el_type}']"
                        elif el_text and len(el_text) < 30:
                            return f"{tag}:contains('{el_text}')"
                        elif el_selector != original_selector:
                            return el_selector
            except Exception:
                continue
        
        return None

    def register_failure(self, original_selector, test_id, run_id):
        """Multi-strategy self-healing: generate intelligent fallback selectors."""
        self.logger.info(f"Self-Healer triggered for {test_id} on selector '{original_selector}'")
        
        fallback = None
        tag = self._extract_tag_from_selector(original_selector)
        
        # =====================================================
        # Strategy 1: DOM Snapshot Lookup (most accurate)
        # Search the actual crawled DOM for alternative elements
        # =====================================================
        fallback = self._search_dom_snapshot(original_selector, run_id)
        if fallback:
            self.logger.info(f"Strategy 1 (DOM Lookup) found fallback: '{fallback}'")
            self._save_fallback(original_selector, fallback, "dom_lookup")
            return fallback
        
        # =====================================================
        # Strategy 2: Attribute-Based Fallback
        # If selector uses class/id, try name/data-testid/aria-label
        # =====================================================
        if tag:
            if '.' in original_selector or '#' in original_selector:
                # Class/ID-based selector failed — try robust attribute selectors
                fallback = f"{tag}[name], {tag}[data-testid], {tag}[aria-label]"
                self.logger.info(f"Strategy 2 (Attribute Fallback) generated: '{fallback}'")
                self._save_fallback(original_selector, fallback, "attribute_fallback")
                return fallback
        
        # =====================================================
        # Strategy 3: Tag + Visibility Fallback
        # Use the base tag with :visible to find any matching visible element
        # =====================================================
        if tag:
            if tag in ["button", "a", "input", "select", "textarea"]:
                fallback = f"{tag}:visible:first"
            elif tag == "form":
                fallback = "form:visible:first"
            else:
                fallback = f"{tag}:visible:first"
            
            self.logger.info(f"Strategy 3 (Visibility Fallback) generated: '{fallback}'")
            self._save_fallback(original_selector, fallback, "visibility_fallback")
            return fallback
        
        # =====================================================
        # Strategy 4: Generic Last Resort
        # =====================================================
        fallback = "*:visible:first"
        self.logger.warning(f"Strategy 4 (Generic Fallback) used as last resort for '{original_selector}'")
        self._save_fallback(original_selector, fallback, "generic_fallback")
        return fallback

    def _save_fallback(self, original_selector, fallback, strategy_used):
        """Persist the learned fallback to the healed selectors memory bank."""
        with open(self.healed_file, "r") as f:
            data = json.load(f)
        
        data[original_selector] = {
            "fallback": fallback,
            "strategy": strategy_used,
            "healed": True
        }
        
        with open(self.healed_file, "w") as f:
            json.dump(data, f, indent=4)
        
        self.logger.warning(f"Learned new fallback for '{original_selector}' -> '{fallback}' (strategy: {strategy_used})")

    def get_healing_summary(self):
        """Return a summary of all learned healings for dashboard display."""
        with open(self.healed_file, "r") as f:
            data = json.load(f)
        return {
            "total_healed": len(data),
            "healings": data
        }

