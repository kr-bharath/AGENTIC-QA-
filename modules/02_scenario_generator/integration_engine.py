import json
import os
import logging

class IntegrationEngine:
    """
    Simulates importing the 26 core automationexercise.com 
    test cases directly into the Scenario Generator pipeline.
    """
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.logger = logging.getLogger(__name__)

        self.core_scenarios = [
            {"id": "TC_01", "name": "Register User", "module": "Auth", "priority": "HIGH", "selector": "a[href='/login']"},
            {"id": "TC_02", "name": "Login User with correct email and password", "module": "Auth", "priority": "HIGH", "selector": "form[action='/login']"},
            {"id": "TC_03", "name": "Login User with incorrect email and password", "module": "Auth", "priority": "HIGH", "selector": "form[action='/login']"},
            {"id": "TC_04", "name": "Logout User", "module": "Auth", "priority": "MEDIUM", "selector": "a[href='/logout']"},
            {"id": "TC_05", "name": "Register User with existing email", "module": "Auth", "priority": "MEDIUM", "selector": "form[action='/signup']"},
            {"id": "TC_06", "name": "Contact Us Form", "module": "Forms", "priority": "MEDIUM", "selector": "form#contact-us-form"},
            {"id": "TC_07", "name": "Verify Test Cases Page", "module": "Navigation", "priority": "LOW", "selector": "a[href='/test_cases']"},
            {"id": "TC_08", "name": "Verify All Products and product detail page", "module": "Products", "priority": "HIGH", "selector": "a[href='/products']"},
            {"id": "TC_09", "name": "Search Product", "module": "Products", "priority": "HIGH", "selector": "input#search_product"},
            {"id": "TC_10", "name": "Verify Subscription in home page", "module": "Forms", "priority": "LOW", "selector": "input#susbscribe_email"},
            {"id": "TC_11", "name": "Verify Subscription in Cart page", "module": "Cart", "priority": "LOW", "selector": "input#susbscribe_email"},
            {"id": "TC_12", "name": "Add Products in Cart", "module": "Cart", "priority": "HIGH", "selector": "a.add-to-cart"},
            {"id": "TC_13", "name": "Verify Product quantity in Cart", "module": "Cart", "priority": "MEDIUM", "selector": "button.disabled"},
            {"id": "TC_14", "name": "Place Order: Register while Checkout", "module": "Checkout", "priority": "HIGH", "selector": "a.check_out"},
            {"id": "TC_15", "name": "Place Order: Register before Checkout", "module": "Checkout", "priority": "HIGH", "selector": "a[href='/checkout']"},
            {"id": "TC_16", "name": "Place Order: Login before Checkout", "module": "Checkout", "priority": "HIGH", "selector": "a[href='/checkout']"},
            {"id": "TC_17", "name": "Remove Products From Cart", "module": "Cart", "priority": "MEDIUM", "selector": "a.cart_quantity_delete"},
            {"id": "TC_18", "name": "View Category Products", "module": "Products", "priority": "MEDIUM", "selector": "div.panel-group"},
            {"id": "TC_19", "name": "View & Cart Brand Products", "module": "Products", "priority": "MEDIUM", "selector": "div.brands_products"},
            {"id": "TC_20", "name": "Search Products and Verify Cart After Login", "module": "Integration", "priority": "HIGH", "selector": "input#search_product"},
            {"id": "TC_21", "name": "Add review on product", "module": "Products", "priority": "LOW", "selector": "form#review-form"},
            {"id": "TC_22", "name": "Add to cart from Recommended items", "module": "Cart", "priority": "MEDIUM", "selector": "div.recommended_items"},
            {"id": "TC_23", "name": "Verify address details in checkout page", "module": "Checkout", "priority": "HIGH", "selector": "ul#address_delivery"},
            {"id": "TC_24", "name": "Download Invoice after purchase order", "module": "Checkout", "priority": "MEDIUM", "selector": "a.check_out"},
            {"id": "TC_25", "name": "Verify Scroll Up using 'Arrow' button and Scroll Down functionality", "module": "UI", "priority": "LOW", "selector": "a#scrollUp"},
            {"id": "TC_26", "name": "Verify Scroll Up without 'Arrow' button and Scroll Down functionality", "module": "UI", "priority": "LOW", "selector": "html"}
        ]

    def inject_core_scenarios(self, existing_scenarios, target_url=None):
        # Prevent injection if target URL is not automationexercise.com to avoid polluting other domain tests
        if target_url and "automationexercise" not in target_url:
            self.logger.info("Skipping Core System Tests injection. Target domain is not automationexercise.com.")
            return existing_scenarios

        # Prevent duplicates if they already exist
        existing_ids = [s["test_id"] for s in existing_scenarios]
        
        injected = 0
        for core in self.core_scenarios:
            if core["id"] not in existing_ids:
                existing_scenarios.append({
                    "test_id": core["id"],
                    "scenario": core["name"],
                    "module": core["module"],
                    "priority": core["priority"],
                    "status": "pending",
                    "selector_used": core["selector"],
                    "url": "https://automationexercise.com/",
                    "is_core": True # Flag to indicate this is a mandatory core test
                })
                injected += 1
                
        self.logger.info(f"Injected {injected} Core System Tests into the pipeline.")
        return existing_scenarios

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    IntegrationEngine()
