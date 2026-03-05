# Intelligent Test Flakiness Detector & Self-Healing Framework (Master QA Agent)

## 1. What is this Project?

This project is an **Enterprise-Grade Autonomous Automated Testing Framework** built for modern web applications using **Python**, **Cypress**, and **Artificial Intelligence**.

Unlike traditional test automation suites that rely on static, manually written scripts, this project is "intelligent." It actively crawls live applications, dynamically generates Cypress E2E test code, monitors its own execution health, detects "flaky" (unstable) tests, uses fallback strategies to heal itself when UI code changes, and applies smart execution prioritization based on historical risk data.

## 2. Why Have We Implemented This Project?

In fast-moving Agile and CI/CD environments, developers constantly push new code. UI tests often fail not because the application is fundamentally broken, but because:

* A developer changed a CSS class name or ID (e.g., a brittle selector).
* The page took 1 second too long to load (Network latency) or an element detached from the DOM.
* Dynamic A/B testing changed the layout slightly.
* Third-party popups or modals appeared unexpectedly.

These "false negatives" are called **Test Flakiness**. When tests are flaky, developers lose trust in the automation suite and begin ignoring failures. QA engineers waste countless hours maintaining fragile scripts instead of writing new tests.

We implemented this project to **solve the Test Flakiness and Automation Maintenance problem completely**.

## 3. What is the Use of this Project?

This framework actively fights test fragility through four core innovations:

1. **Autonomous Code Generation & Execution:** Instead of humans writing tests, the Python orchestrator crawls the target URL, extracts the DOM, and generates robust `.cy.js` files using resilient jQuery-based assertions and wait-states.
2. **Self-Healing Selectors:** If a web element's ID changes or a brittle selector fails, the framework intercepts the Cypress failure mid-run. It automatically learns a fallback strategy (like switching to CSS attribute selectors or text matching) and rewrites the test to heal it dynamically.
3. **Flakiness Detection & Smart Retries:** The integrated executor runs tests in high-speed batches. If a test is known to be unstable, the engine applies targeted retries. It mathematically determines which tests are genuinely flaky versus consistently failing, tracking this in historical JSON ledgers.
4. **AI/ML Insights & Root Cause Analysis:** An interactive Streamlit dashboard identifies overarching failure clusters, generates heuristic-powered root cause analysis to explain *why* a test failed (Timing, Security Block, Navigation dead-end), and provides mathematical Risk Scoring for future executions.

## 4. What is the Real Outcome of this Project?

By implementing this project, an organization achieves:

* **Trustworthy CI/CD Pipelines:** Developers can trust that a "red" build means a real bug, not just a flaky script. The Dashboard clearly recommends "GO / NO GO" for deployment.
* **Zero Maintenance Overhead:** The self-healing engine and autonomous code generator drastically reduce the need for QAs to manually write or update test scripts every time a minor UI change is deployed.
* **Massive Time Savings:** The Batched Cypress Engine executes tests concurrently without thrashing OS resources.
* **Actionable Analytics:** An executive Streamlit Dashboard is automatically generated, showing management exactly where technical debt lies across single or multi-URL (Swarm) executions.

---

## 5. Detailed Test Scenario Architecture

The engine dynamically maps and injects up to 30 highly structured test cases covering critical e-commerce and application domains based on the crawled DOM payload.

### Search & Form Navigation (TC_FORM_POS / TC_FORM_NEG)

*Use:* Validates the most critical revenue-generating flow of a site—submitting data safely.

* **Positive Forms:** Injects standard valid E2E data (emails, passwords) into discovered forms.
* **Negative Forms:** Validates application resilience by blindly submitting empty forms and verifying the system doesn't crash (readyState integrity).
* **Security/Malformed Forms:** Actively attempts native SQL/NoSQL injection (e.g., `''' OR 1=1; --`) to ensure the backend natively blocks or gracefully rejects malformed inputs without throwing a 500 error.

### Navigation Tracing (TC_NAV)

*Use:* Tests the site's architecture (hamburger menus, pagination) and routing.

* Iterates through discovered anchor tags `<a>` and attempts to interact with them, verifying that the target application successfully routes the view state and the DOM mutates as expected.

### Core Interactivity (TC_BTN)

*Use:* Ensures dynamic elements do not crash the UI thread.

* Clicks isolated buttons or interactive components and waits for split-second JavaScript mutations (like dropdowns or modals rendering) without relying on fragile URL changes.

---

## 6. Setup Guide

### Prerequisites

* **Python** 3.10 or higher
* **Node.js** 18 or higher (recommended: v20 LTS)
* **npm** package manager (bundled with Node.js)
* A stable internet connection

### Step-by-Step Installation

#### Step 1: Clone & Python Environment

```bash
# Clone or extract the project
cd MASTER_QA_AGENT

# Set up Python Virtual Environment
python -m venv venv

# Activate (Windows)
.\\venv\\Scripts\\activate
# Activate (Mac/Linux)
source venv/bin/activate

# Install Python ML & Orchestrator dependencies
pip install -r requirements.txt
```

#### Step 2: Install Node Dependencies

```bash
# Install Cypress and local node modules
npm install
```

#### Step 3: Verify Cypress

```bash
# Verify Cypress binary is installed
npx cypress verify
```

---

## 7. Running the Autonomous Agent (Data Collection)

The core of this framework is the Python orchestrator which drives the entire lifecycle asynchronously.

### Single URL Target

```bash
python agent/agent_runner.py --url "https://automationexercise.com/" --auto-approve
```

### Multi-URL Swarm Target (Batch Crawl)

```bash
python agent/agent_runner.py --urls "https://automationexercise.com/,https://automationexercise.com/products" --auto-approve
```

**What Happens During Execution:**

1. **Extraction (Crawler):** Crawls the provided URLs and dumps the DOM state.
2. **Generation:** NLP/Rule engines write 30 robust Cypress scenarios into `cypress/e2e/generated/`.
3. **Execution:** The built-in executor triggers Cypress to run the scripts in headless mode.
4. **Self-Healing:** If a test fails, `healer.py` intercepts it, learns a fallback, rewrites the JS, and retries.
5. **Analytics:** Generates comprehensive JSON result matrices in the `results/` folder.

---

## 8. Generating & Viewing the AI Dashboard

### Step 1: Launch Streamlit

```bash
streamlit run dashboard/app.py
```

### Step 2: Access the Analytics

Open your browser to `http://localhost:8501`.

**Dashboard Sections:**

1. **Approval Gate** — Human-in-the-loop control to filter High/Medium/Low priority tests before execution.
2. **Execution History** — Raw tabular pass/fail matrices of the latest executions.
3. **Risk & Flakiness** — Reports identifying historically unstable tests.
4. **Visual Diffs** — Pixel-by-pixel computer vision comparisons of UI deviation.
5. **AI Insights** — Correlated Network API anomalies and predicted test regression risks.
6. **Swarm Comparison** — Bar charts tracking pass-rate variance across multi-URL boundaries.
7. **Root Cause Analyzer** — Heuristic text generation explaining exactly *why* a specific test timed out or broke.

---

## 9. Interactive Cypress Mode

To open the Cypress Test Runner GUI for manually debugging individual generated tests:

```bash
npx cypress open
```

This launches the Cypress UI where you can watch the dynamically generated code execute in a real Chrome/Edge browser.

---

## 10. Troubleshooting

### Issue: "Missing or Unapproved Scenarios"

**Solution:** The agent implements a Human-in-the-Loop gateway. If you run the agent without `--auto-approve`, you MUST open the Streamlit dashboard, go to the **Approval Gate** tab, and click "Approve Selected Scenarios" to allow code generation to begin.

### Issue: "Cypress extraction failed / Timed out"

**Solution:** The target website might be running slow. The engine sets a default 15,000ms page load timeout. You can increase this limit inside the `cypress_builder.py` or `agent_runner.py` configuration blocks.

---

## 11. Daily Usage Workflow

**After initial setup, daily usage is simple:**

```bash
# Step 1: Open Terminal 1 - Start the persistent Dashboard
streamlit run dashboard/app.py

# Step 2: Open Terminal 2 - Trigger a new targeted sweep
python agent/agent_runner.py --urls "https://www.your-target-site.com/" --auto-approve
```

**That's it!** The dashboard will instantly update, showing you Root Causes, Swarm Comparisons, and CI/CD Go/No-Go Recommendations.

---

## 12. Project Reference

### Project Structure

```text
MASTER QA AGENT/
├── agent/
│   ├── agent_runner.py          # Main CLI orchestrator
│   └── approval_gate.py         # Human-in-the-Loop Gateway logic
├── config/                      # Agent configuration parameters
├── cypress/
│   ├── e2e/
│   │   ├── crawler.cy.js        # Native DOM extraction spider
│   │   └── generated/           # Dynamically generated .cy.js tests
│   └── support/                 # Cypress base overrides
├── dashboard/
│   └── app.py                   # Streamlit Intelligence Dashboard
├── data/                        # Intermediary JSON extracts & scopes
├── modules/
│   ├── 01_dom_crawler/          # DOM extraction and parsing
│   ├── 02_scenario_generator/   # Rule & Integration engines
│   ├── 03_risk_engine/          # Predictive failure heuristics
│   ├── 04_test_code_generator/  # AST code building (CypressBuilder)
│   ├── 05_executor/             # Native batched execution hooks
│   ├── 06_flakiness_detector/   # Historical data mapping
│   ├── 07_api_anomaly_detector/ # Network layer intercept mapping
│   ├── 08_visual_regression/    # Pixel diffing computer vision
│   ├── 09_self_healing/         # Fallback intercept mapping
│   └── 11_regression_optimizer/ # Smart pruning of stable modules
├── results/                     # Final execution logs & matrices
├── package.json                 # Node/Cypress dependencies
└── requirements.txt             # Python ML/Data dependencies
```

### License

Educational and Portfolio Use.
