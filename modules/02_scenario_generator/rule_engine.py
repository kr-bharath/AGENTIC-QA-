import json
import os
import logging
from datetime import datetime

class RuleEngine:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.logger = logging.getLogger(__name__)

    def generate_scenarios(self, dom_data):
        if not dom_data or "interactive_elements" not in dom_data:
            self.logger.error("Invalid DOM data provided to Rule Engine.")
            return []

        scenarios = []
        elements = dom_data["interactive_elements"]
        from urllib.parse import urlparse, urljoin
        url = dom_data.get("url", "unknown_url")
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        test_counter: int = 1
        
        # Per-tier caps to prevent test suite bloat
        MAX_FORM_SCENARIOS = 30      # 3 scenarios per form × max ~10 forms
        MAX_NAV_SCENARIOS = 15       # Limit navigation tests
        MAX_INTERACT_SCENARIOS = 10  # Limit button/interaction tests
        MAX_SELECT_SCENARIOS = 10    # Limit dropdown tests
        MAX_TEXTAREA_SCENARIOS = 5   # Limit textarea tests

        # =========================================================
        # TIER 1: E2E FORM VALIDATION (Positive & Negative)
        # =========================================================
        forms = [e for e in elements if e["tag"] == "form"]
        form_count: int = 0
        seen_form_selectors = set()  # Dedup forms by selector
        
        for form in forms:
            if form_count >= MAX_FORM_SCENARIOS:
                break
                
            action = form.get("selector_guess", "form")
            
            # Deduplicate forms by selector (prevents duplicate tests for same form)
            if action in seen_form_selectors:
                continue
            seen_form_selectors.add(action)
            
            form_id = form.get("id", str(test_counter))
            
            # Scenario 1: Positive Submit
            scenarios.append({
                "test_id": f"TC_FORM_POS_{test_counter}",
                "scenario": f"E2E Validate successful data submission via {action}",
                "module": "Forms",
                "priority": "HIGH",
                "status": "pending",
                "selector_used": action,
                "url": url,
                "strategy": "Fill all inputs -> Submit -> Verify success state"
            })
            
            # Scenario 2: Negative Submit (Missing required data)
            scenarios.append({
                "test_id": f"TC_FORM_NEG_{test_counter}_EMPTY",
                "scenario": f"Verify validation errors trigger when {action} submitted empty",
                "module": "Forms",
                "priority": "HIGH",
                "status": "pending",
                "selector_used": action,
                "url": url,
                "strategy": "Leave inputs blank -> Submit -> Verify error messages visible"
            })
            
            # Scenario 3: Negative Submit (Malformed data)
            scenarios.append({
                "test_id": f"TC_FORM_NEG_{test_counter}_MALFORMED",
                "scenario": f"Verify security/format rejection on malformed inputs for {action}",
                "module": "Security",
                "priority": "MEDIUM",
                "status": "pending",
                "selector_used": action,
                "url": url,
                "strategy": "Inject SQLi/NoSQL strings & invalid email formats -> Submit -> Verify rejection"
            })
            test_counter += 1
            form_count += 3

        # =========================================================
        # TIER 2: INTELLIGENT NAVIGATION TRACING
        # =========================================================
        links = [e for e in elements if e["tag"] == "a" and e.get("href")]
        nav_targets = set()       # Deduplicate by href
        resolved_urls = set()     # Also deduplicate by resolved URL
        nav_count: int = 0
        
        for link in links:
            if nav_count >= MAX_NAV_SCENARIOS:
                break
                
            href = link.get("href")
            text = link.get("text", "link").strip()
            
            # Ignore anchors, mailtos, javascript:void, empty, tel:, social links
            if not href or href.startswith("#") or "mailto:" in href or "tel:" in href:
                continue
            if "javascript:" in href.lower():
                continue
            # Skip common social media links (they're external and not testable)
            social_domains = ["facebook.com", "twitter.com", "instagram.com", "linkedin.com", "youtube.com", "pinterest.com"]
            if any(social in href.lower() for social in social_domains):
                continue
            
            # Deduplicate by raw href AND resolved URL
            if href in nav_targets:
                continue
            resolved = urljoin(base_url, href)
            if resolved in resolved_urls:
                continue
                
            nav_targets.add(href)
            resolved_urls.add(resolved)
            target_url = resolved
            
            scenarios.append({
                "test_id": f"TC_NAV_{test_counter}",
                "scenario": f"E2E Trace navigation to '{text[:40]}' tab/page",
                "module": "Navigation",
                "priority": "MEDIUM",
                "status": "pending",
                "selector_used": link.get("selector_guess"),
                "url": url,
                "target_url": target_url,
                "strategy": "Click -> Wait for routing -> Verify URL change -> Verify target DOM renders"
            })
            test_counter += 1
            nav_count += 1

        # =========================================================
        # TIER 3: DYNAMIC INTERACTIVITY (Buttons, Modals, Tabs)
        # =========================================================
        buttons = [e for e in elements if e["tag"] == "button" or e.get("type") in ["submit", "button"]]
        interact_count: int = 0
        
        for button in buttons:
            if interact_count >= MAX_INTERACT_SCENARIOS:
                break
                
            text = button.get("text", "Button").strip()
            
            # Avoid duplicating form submissions if we already caught them above
            if button.get("type") == "submit":
                continue
                
            scenarios.append({
                "test_id": f"TC_INTERACT_{test_counter}",
                "scenario": f"Verify state change/modal trigger upon clicking '{text[:40]}'",
                "module": "UI/UX",
                "priority": "LOW",
                "status": "pending",
                "selector_used": button.get("selector_guess"),
                "url": url,
                "strategy": "Click -> Wait for DOM mutation (modal/dropdown/accordion) -> Verify new elements visible"
            })
            test_counter += 1
            interact_count += 1

        # =========================================================
        # TIER 4: DROPDOWN / SELECT ELEMENT TESTING
        # =========================================================
        selects = [e for e in elements if e["tag"] == "select" and e.get("isVisible", True)]
        select_count: int = 0
        
        for sel in selects:
            if select_count >= MAX_SELECT_SCENARIOS:
                break
                
            sel_selector = sel.get("selector_guess", "select")
            sel_name = sel.get("name", "") or sel.get("id", f"dropdown_{test_counter}")
            
            scenarios.append({
                "test_id": f"TC_SELECT_{test_counter}",
                "scenario": f"Verify dropdown selection and value change for '{sel_name}'",
                "module": "Forms",
                "priority": "MEDIUM",
                "status": "pending",
                "selector_used": sel_selector,
                "url": url,
                "strategy": "Select random option -> Verify value changed -> Validate form context"
            })
            test_counter += 1
            select_count += 1

        # =========================================================
        # TIER 5: TEXTAREA INPUT VALIDATION
        # =========================================================
        textareas = [e for e in elements if e["tag"] == "textarea" and e.get("isVisible", True)]
        textarea_count: int = 0
        
        for ta in textareas:
            if textarea_count >= MAX_TEXTAREA_SCENARIOS:
                break
                
            ta_selector = ta.get("selector_guess", "textarea")
            ta_name = ta.get("name", "") or ta.get("id", f"textarea_{test_counter}")
            
            scenarios.append({
                "test_id": f"TC_TEXTAREA_{test_counter}",
                "scenario": f"Verify textarea accepts multi-line input and special characters for '{ta_name}'",
                "module": "Forms",
                "priority": "LOW",
                "status": "pending",
                "selector_used": ta_selector,
                "url": url,
                "strategy": "Type multi-line content -> Verify value persists -> Check special char handling"
            })
            test_counter += 1
            textarea_count += 1

        # =========================================================
        # TIER 6: ACCESSIBILITY AUDITING (Page-level, not per-element)
        # =========================================================
        scenarios.append({
            "test_id": f"TC_A11Y_{test_counter}",
            "scenario": f"Accessibility audit: Verify images have alt text, inputs have labels, elements are keyboard-focusable",
            "module": "Accessibility",
            "priority": "LOW",
            "status": "pending",
            "selector_used": "img, input, button",
            "url": url,
            "strategy": "Scan all img tags for alt -> Scan all inputs for label/aria-label -> Check keyboard focusability"
        })
        test_counter += 1

        self.logger.info(f"Rule Engine dynamically created {len(scenarios)} advanced End-to-End Scenarios across 6 tiers.")
        return scenarios

    def save_scenarios(self, scenarios, run_id):
        filepath = os.path.join(self.data_dir, f"{run_id}_scenarios.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"run_id": run_id, "scenarios": scenarios}, f, indent=4)
        self.logger.info(f"Saved scenarios to {filepath}")
        return filepath

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = RuleEngine()
