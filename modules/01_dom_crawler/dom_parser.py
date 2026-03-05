import json
import os
import logging

class DOMParser:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.logger = logging.getLogger(__name__)

    def parse_dom(self, filename="dom_structure.json"):
        filepath = os.path.join(self.data_dir, filename)
        
        if not os.path.exists(filepath):
            self.logger.error(f"File not found: {filepath}")
            return None
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Check for bot protection flag set by crawler
        bot_blocked = data.get("bot_protection_detected", False)
        if bot_blocked:
            self.logger.warning(f"⚠️ Bot protection was detected on {data['url']}. DOM may be from a challenge page.")
            self.logger.warning(f"   Only {len(data['elements'])} elements found — filtering out hidden/challenge elements.")
        
        self.logger.info(f"Loaded DOM data containing {len(data['elements'])} elements from {data['url']}")
        
        # Filter out hidden elements and known bot-protection artifacts
        bot_artifacts = ['cloudflare', 'turnstile', 'captcha', 'challenge', 'cf-chl', 'hcaptcha', 'recaptcha']
        filtered_elements = []
        for el in data["elements"]:
            # Skip hidden elements (not useful for test generation)
            if not el.get("isVisible", True) and el.get("tag") != "form":
                continue
            # Skip known bot-protection elements
            selector = el.get("selector_guess", "").lower()
            text = el.get("text", "").lower()
            href = el.get("href", "").lower()
            is_bot_artifact = any(kw in selector or kw in text or kw in href for kw in bot_artifacts)
            if is_bot_artifact:
                continue
            filtered_elements.append(el)
        
        parsed_data = {
            "url": data["url"],
            "interactive_elements": filtered_elements,
            "forms_found": len([e for e in filtered_elements if e["tag"] == "form"]),
            "buttons_found": len([e for e in filtered_elements if e["tag"] == "button" or e.get("type") == "submit"]),
            "bot_protection_detected": bot_blocked
        }
        
        if bot_blocked and len(filtered_elements) == 0:
            self.logger.warning(f"   No usable elements after filtering bot artifacts. Scenarios will be empty.")
        
        return parsed_data

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    parser = DOMParser()
    # Attempting to load DOM payload, this won't do anything yet until Cypress runs.
    parser.parse_dom()
