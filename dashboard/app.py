import streamlit as st  # type: ignore
import json
import os
import glob
from datetime import datetime
import sys
from typing import Dict, Any, List

# Import the ApprovalGate from agent
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from agent.approval_gate import ApprovalGate  # type: ignore

st.set_page_config(page_title="QA Agent Dashboard", layout="wide", page_icon="🤖")

st.markdown("""
<style>
    /* Professional Enterprise Typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    :root {
        --bg-primary: #020617;
        --bg-secondary: #0f172a;
        --accent-blue: #38bdf8;
        --accent-emerald: #10b981;
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
        --border-color: rgba(51, 65, 85, 0.5);
        --glass-bg: rgba(15, 23, 42, 0.7);
    }
    
    html, body, .stApp {
        font-family: 'Inter', sans-serif;
        color: var(--text-main);
    }
    
    h1, h2, h3, h4, h5, h6, .hero-section h1 {
        font-family: 'Outfit', sans-serif !important;
    }

    /* Professional Sidebar Redesign */
    [data-testid="stSidebar"] {
        background-color: var(--bg-secondary);
        border-right: 1px solid var(--border-color);
    }
    
    [data-testid="stSidebar"] .stMarkdown h2 {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--accent-blue);
        letter-spacing: -0.02em;
    }

    /* Ultra-Compact Hero Section */
    .hero-section {
        background: radial-gradient(circle at top left, rgba(56, 189, 248, 0.08), transparent),
                    linear-gradient(135deg, #020617 0%, #0f172a 100%);
        padding: 20px 30px;
        border-radius: 12px;
        border: 1px solid var(--border-color);
        margin-bottom: 15px;
        box-shadow: 0 10px 20px -10px rgba(0, 0, 0, 0.5);
        position: relative;
        overflow: hidden;
    }
    
    .hero-badge {
        display: inline-flex;
        align-items: center;
        background: rgba(56, 189, 248, 0.1);
        color: var(--accent-blue);
        padding: 3px 10px;
        border-radius: 99px;
        font-size: 0.6rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border: 1px solid rgba(56, 189, 248, 0.2);
        margin-bottom: 10px;
    }
    
    .hero-section h1 {
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
        line-height: 1.1;
        letter-spacing: -0.04em;
        background: linear-gradient(to right, #ffffff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .hero-subtitle {
        color: var(--text-muted);
        font-size: 0.9rem;
        max-width: 800px;
        line-height: 1.3;
        margin-top: 5px;
    }

    /* Compact Metric Cards */
    .metric-card {
        background: var(--glass-bg);
        border: 1px solid var(--border-color);
        padding: 15px 20px;
        border-radius: 12px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .metric-card:hover {
        border-color: rgba(56, 189, 248, 0.4);
        transform: translateY(-1px);
    }
    
    .stMetric {
        background: transparent !important;
        padding: 0 !important;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        font-family: 'Outfit', sans-serif !important;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        color: var(--text-muted) !important;
        font-weight: 600 !important;
    }

    /* Tab Upgrades */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: transparent;
        overflow-x: auto !important;
        scrollbar-width: thin;
    }

    .stTabs [data-baseweb="tab"] {
        height: 38px;
        background-color: rgba(30, 41, 59, 0.4);
        border-radius: 6px 6px 0 0;
        border: 1px solid var(--border-color);
        border-bottom: none;
        padding: 0 12px;
        color: var(--text-muted);
        font-weight: 500;
        font-size: 0.85rem;
        white-space: nowrap;
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--bg-secondary) !important;
        color: var(--accent-blue) !important;
        border-top: 2px solid var(--accent-blue) !important;
    }

    /* Balanced Global Alignment */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    
    hr {
        margin: 1.5rem 0 !important;
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: var(--bg-primary);
    }
    ::-webkit-scrollbar-thumb {
        background: #334155;
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #475569;
    }
</style>

<div class="hero-section">
    <div class="hero-badge">Autonomous QA v2.5 • Enterprise Edition</div>
    <h1>Master QA Agent</h1>
    <p class="hero-subtitle">
        High-performance autonomous testing engine using multi-model neural verification. 
        Zero-maintenance execution for complex web architectures.
    </p>
</div>
""", unsafe_allow_html=True)

# Initialize state
if "approved_scenarios" not in st.session_state:
    st.session_state.approved_scenarios = []

# Sidebar for controls
with st.sidebar:
    st.header("Control Panel")
    
    # Refresh runs from both data and results directories
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
    
    all_files = glob.glob(os.path.join(data_dir, "run_*")) + glob.glob(os.path.join(results_dir, "run_*"))
    
    run_ids = set()
    for f in all_files:
        filename = os.path.basename(f)
        if filename.startswith("run_"):
            # Extract run_id (e.g. run_20260301_170000_results.json -> run_20260301_170000)
            parts = filename.split("_")
            if len(parts) >= 3:
                run_id = f"{parts[0]}_{parts[1]}_{parts[2]}"
                run_ids.add(run_id)
        
    available_runs_temp = list(run_ids)
    available_runs_temp.sort(reverse=True)
    available_runs = []
    for i in range(min(20, len(available_runs_temp))):
        available_runs.append(available_runs_temp[i])
        
    st.markdown("#### Pending Approvals")
    selected_run = st.selectbox("Select a Run ID", available_runs if available_runs else ["No runs available"])

    # Get execution results if they exist to bind dynamic target URLs
    results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
    result_file = os.path.join(results_dir, f"{selected_run}_results.json")
    run_results: Dict[str, Any] = {}
    if os.path.exists(result_file):
        with open(result_file, "r", encoding="utf-8") as f:
            run_results = json.load(f)

    st.markdown("---")
    st.markdown("#### Run Pipeline")
    display_url = "https://automationexercise.com"
    if run_results:
        display_url = run_results.get("target_url", display_url)
    else:
        # If it's still pending, extract the URL from the dynamically generated scenarios instead!
        scenarios_file = os.path.join(os.path.dirname(__file__), '..', 'data', f"{selected_run}_scenarios.json")
        if os.path.exists(scenarios_file):
            try:
                with open(scenarios_file, "r", encoding="utf-8") as f:
                    scenario_data = json.load(f)
                    if scenario_data.get("scenarios"):
                        # Usually the first navigation step has the correct base URL
                        display_url = scenario_data["scenarios"][0].get("url", display_url)
            except Exception:
                pass

    target_url = st.text_area("Target URLs", display_url, height=120)
    if st.button("Start New Extraction", type="primary"):
        import subprocess
        import sys
        
        # Parse multiple URLs
        urls = []
        for line in target_url.splitlines():
            for part in line.split(','):
                cleaned = part.strip()
                if cleaned:
                    urls.append(cleaned)
                    
        if not urls:
            st.warning("Please enter at least one valid URL.")
        else:
            try:
                # Join all URLs into comma-separated string for ONE batch process
                urls_joined = ",".join(urls)
                subprocess.Popen([sys.executable, "agent/agent_runner.py", "--urls", urls_joined])
                    
                st.success(f"Sent {len(urls)} URLs to Multi-URL Pipeline! ONE unified run will be created.")
                with st.expander(f"Show {len(urls)} Triggered Sites:"):
                    for i, u in enumerate(urls, 1):
                        st.write(f"{i}. `{u}`")
                        
                st.info("The crawler is processing URLs sequentially. All scenarios will appear in ONE run when complete. Check the 'Pending Approvals' dropdown in a few moments!")
            except Exception as e:
                st.error(f"Failed to trigger engine: {e}")

    st.markdown("---")
    st.markdown("#### Live Monitoring")
    auto_refresh = st.checkbox("Auto-Refresh Live Data (10s)", value=False)

# Week 8: Compute Historical Trends for Charts
historical_results = []
for rid in reversed(available_runs): # Oldest to newest for plotting
    rfile = os.path.join(results_dir, f"{rid}_results.json")
    if os.path.exists(rfile):
        try:
            with open(rfile, "r") as f:
                result_data = json.load(f)
                result_summary = result_data.get("summary", {})
                historical_results.append({
                    "run": rid.split("_", 1)[-1], 
                    "passed": result_summary.get("passed", 0), 
                    "failed": result_summary.get("failed", 0)
                })
        except:
            pass

# Main dashboard layout
metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

if run_results:
    summary = run_results.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    
    with metrics_col1:
        st.markdown(f"""
        <div class="metric-card">
            <div data-testid="stMetricLabel">Tests Executed</div>
            <div data-testid="stMetricValue">{summary.get("total", "0")}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with metrics_col2:
        st.markdown(f"""
        <div class="metric-card">
            <div data-testid="stMetricLabel">Passed</div>
            <div data-testid="stMetricValue">{summary.get("passed", "0")}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with metrics_col3:
        st.markdown(f"""
        <div class="metric-card">
            <div data-testid="stMetricLabel">Failed</div>
            <div data-testid="stMetricValue">{summary.get("failed", "0")}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with metrics_col4:
        status_text = "PASSING" if summary.get("status") == "passed" else "FAILING"
        status_color = "#10b981" if status_text == "PASSING" else "#ef4444"
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid {status_color}">
            <div data-testid="stMetricLabel">Status</div>
            <div data-testid="stMetricValue" style="color: {status_color}">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    is_go = summary.get("status") == "passed"
    decision_color = "#10b981" if is_go else "#ef4444"
    decision_bg = "rgba(16, 185, 129, 0.1)" if is_go else "rgba(239, 68, 68, 0.1)"
    decision_text = "✅ GO - PRODUCTION READY" if is_go else "🛑 NO-GO - BLOCK DEPLOYMENT"
    
    st.markdown("---")
    is_go = summary.get("status") == "passed"
    decision_color = "#10b981" if is_go else "#ef4444"
    decision_bg = "rgba(16, 185, 129, 0.05)" if is_go else "rgba(239, 68, 68, 0.05)"
    decision_text = "✅ GO - PRODUCTION READY" if is_go else "🛑 NO-GO - BLOCK DEPLOYMENT"
    
    st.markdown(f"""
    <div style="background: {decision_bg}; border: 1px solid {decision_color}; padding: 25px; border-radius: 12px; text-align: center; margin-bottom: 25px;">
        <div style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 10px; font-weight: 600;">Neural Decision Engine</div>
        <div style="color: {decision_color}; font-size: 2.2rem; font-weight: 800; font-family: 'Outfit', sans-serif;">{decision_text}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if len(historical_results) > 1:
        import pandas as pd  # type: ignore
        st.markdown("<h4 style='margin-bottom:15px; font-size: 1.25rem;'>Regression Trend (Last 10 Runs)</h4>", unsafe_allow_html=True)
        chart_df = pd.DataFrame(historical_results).set_index("run")
        st.line_chart(chart_df, color=["#10b981", "#ef4444"], height=300)
else:
    with metrics_col1:
        st.markdown('<div class="metric-card"><div data-testid="stMetricLabel">Tests Executed</div><div data-testid="stMetricValue">0</div></div>', unsafe_allow_html=True)
    with metrics_col2:
        st.markdown('<div class="metric-card"><div data-testid="stMetricLabel">Passed</div><div data-testid="stMetricValue">0</div></div>', unsafe_allow_html=True)
    with metrics_col3:
        st.markdown('<div class="metric-card"><div data-testid="stMetricLabel">Failed</div><div data-testid="stMetricValue">0</div></div>', unsafe_allow_html=True)
    with metrics_col4:
        st.markdown('<div class="metric-card"><div data-testid="stMetricLabel">Status</div><div data-testid="stMetricValue" style="color: var(--text-muted)">PENDING</div></div>', unsafe_allow_html=True)

st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🔘 Approval Gate", 
    "📜 Execution History", 
    "⚡ Risk & Flakiness", 
    "🖼️ Visual Diffs", 
    "🧠 AI Insights", 
    "🌐 Swarm Comparison", 
    "🔍 Root Cause Analyzer"
])

# The Approval Gate logic
with tab1:
    st.subheader("Scenario Waiting For Approval")
    
    if selected_run != "No runs available":
        gate = ApprovalGate(data_dir=data_dir)
        scenarios = gate.get_pending_scenarios(selected_run)
        
        # Check if already approved
        approved_file = os.path.join(data_dir, f"{selected_run}_approved.json")
        if os.path.exists(approved_file):
            st.success(f"Run {selected_run} has already been approved!")
            with open(approved_file, "r") as f:
                approved_data = json.load(f)
                st.write(f"Approved {len(approved_data.get('approved_scenarios', []))} scenarios.")
            
            if os.path.exists(result_file):
                st.info("Execution for this run is already complete. Check 'Execution History' tab.")
            else:
                st.warning("Execution is currently running or pending...")
        elif scenarios:
            st.info(f"Found **{len(scenarios)}** generated scenarios for {selected_run}. Select the ones you want to execute.")
            
            # Show summary of scenarios by source URL
            url_groups = {}
            for s in scenarios:
                src = s.get("source_url", s.get("url", "unknown"))
                url_groups.setdefault(src, []).append(s)
            
            if len(url_groups) > 1:
                st.markdown("**Scenarios by Source URL:**")
                for src_url, group in url_groups.items():
                    st.write(f"- `{src_url}` : **{len(group)}** scenarios")
                st.markdown("---")
            
            # Priority Filter Toggles
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                select_all = st.checkbox("Select All / Deselect All", value=True)
            with col2:
                select_high = st.checkbox("High Priority", value=select_all, key=f"chk_high_{select_all}")
            with col3:
                select_medium = st.checkbox("Medium Priority", value=select_all, key=f"chk_med_{select_all}")
            with col4:
                select_low = st.checkbox("Low Priority", value=select_all, key=f"chk_low_{select_all}")
            
            with st.form("approval_form"):
                selections = {}
                
                # Group scenarios by source URL for better organization
                if len(url_groups) > 1:
                    for src_url, group in url_groups.items():
                        st.markdown(f"##### From: `{src_url}` ({len(group)} scenarios)")
                        for s in group:
                            p = str(s.get('priority', '')).upper()
                            default_val = select_all or (p == 'HIGH' and select_high) or (p == 'MEDIUM' and select_medium) or (p == 'LOW' and select_low)
                            
                            label = f"**[{s['priority']}]** {s['test_id']} - {s['scenario']} *(Module: {s.get('module', 'N/A')})*"
                            widget_key = f"scen_{s['test_id']}_{select_all}_{select_high}_{select_medium}_{select_low}"
                            selections[s["test_id"]] = st.checkbox(label, value=default_val, key=widget_key)
                else:
                    for s in scenarios:
                        p = str(s.get('priority', '')).upper()
                        default_val = select_all or (p == 'HIGH' and select_high) or (p == 'MEDIUM' and select_medium) or (p == 'LOW' and select_low)
                        
                        label = f"**[{s['priority']}]** {s['test_id']} - {s['scenario']} *(Selector: {s['selector_used']})*"
                        widget_key = f"scen_{s['test_id']}_{select_all}_{select_high}_{select_medium}_{select_low}"
                        selections[s["test_id"]] = st.checkbox(label, value=default_val, key=widget_key)
                    
                submitted = st.form_submit_button("Approve Selected Scenarios")
                
                if submitted:
                    approved_ids = [tid for tid, is_selected in selections.items() if is_selected]
                    if approved_ids:
                        success = gate.save_approved(selected_run, approved_ids)
                        if success:
                            st.success(f"Approved {len(approved_ids)} scenarios successfully! Pipeline will now continue with Code Generation.")
                            st.rerun()
                    else:
                        st.error("Please select at least one scenario to approve.")
        else:
            st.warning("No pending scenarios found for this run.")
    else:
        st.info("Execute 'python agent/agent_runner.py' in your terminal to generate a run first.")

with tab2:
    st.subheader("Last Execution Results")
    if run_results:
        import pandas as pd  # type: ignore
        tests: List[Dict[str, Any]] = run_results.get("tests", [])
        if tests:
            df = pd.DataFrame(tests)
            def color_status(val):
                color = '#bcffbc' if val == 'passed' else '#ffbcbc'
                return f'background-color: {color}'
            
            st.dataframe(df.style.map(color_status, subset=['status']), use_container_width=True)
    else:
        st.info("No execution results found for this run.")

with tab3:
    st.subheader("Flakiness Report")
    flaky_file = os.path.join(results_dir, "flakiness_report.json")
    if os.path.exists(flaky_file):
        with open(flaky_file, "r") as f:
            flaky_data = json.load(f)
        report = flaky_data.get("flakiness_analysis", [])
        if report:
            import pandas as pd  # type: ignore
            df = pd.DataFrame(report)
            st.dataframe(df, use_container_width=True)
    else:
        st.info("Not enough historical data to map flakiness. Need at least 3 runs.")

with tab4:
    st.subheader("Visual Regression Heatmaps")
    visual_file = os.path.join(results_dir, f"{selected_run}_visual_regression.json")
    if os.path.exists(visual_file):
        with open(visual_file, "r") as f:
            visual_data = json.load(f)
            
        diffs = visual_data.get("visual_diffs", [])
        if not diffs:
            st.info("No visual screenshots found for this run.")
        else:
            found_diffs = [d for d in diffs if d.get("status") == "diff_found"]
            new_bases = [d for d in diffs if d.get("status") == "new_baseline"]
            
            st.metric("Total Screenshots Processed", len(diffs))
            col_d1, col_d2 = st.columns(2)
            col_d1.metric("New Baselines Created", len(new_bases))
            col_d2.metric("Visual Anomalies Detected", len(found_diffs), delta_color="inverse")
            
            if found_diffs:
                st.markdown(f"#### 🚨 {len(found_diffs)} Visual Anomalies Detected")
                for diff in found_diffs:
                    with st.container():
                        st.markdown(f"""
                        <div style="background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.2); padding: 20px; border-radius: 12px; margin-bottom: 20px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                                <span style="font-weight: 700; font-family: 'Outfit';">Scenario ID: {diff['test_id']}</span>
                                <span style="background: rgba(239, 68, 68, 0.2); color: #ef4444; padding: 4px 12px; border-radius: 99px; font-size: 0.8rem; font-weight: 600;">Match: {diff['score'] * 100:.2f}%</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        try:
                            c_col1, c_col2, c_col3 = st.columns(3)
                            with c_col1:
                                st.image(diff['baseline_path'], caption="Baseline Image", use_column_width=True)
                            with c_col2:
                                st.image(diff['current_path'], caption="Recent Screenshot", use_column_width=True)
                            with c_col3:
                                st.image(diff['diff_path'], caption="Pixel Difference (Red)", use_column_width=True)
                        except Exception as e:
                            st.error(f"Image load failed: {e}")
                        st.divider()
            elif new_bases:
                st.success("No deviations found. However, new baselines were established for future runs.")
            else:
                st.success("No deviations found! UI represents 100% pixel-perfect match to baselines.")
                
            # If no diffs found but we want to show a sample, let's just dump a sample 
            with st.expander("View All Processed Screens Details"):
                import pandas as pd  # type: ignore
                st.dataframe(pd.DataFrame(diffs))
    else:
        st.info("No Visual Regression data found. Visual engine has yet to run for this ID.")
with tab5:
    st.header("🧠 Deep AI Business Insights")
    st.markdown("Detailed breakdown of Neural Pipeline intelligence triggers for this run.")
    
    i_col1, i_col2 = st.columns(2)
    # AI Insights Refactor
    i_col1, i_col2 = st.columns(2)
    with i_col1:
        st.markdown("""
        <div style="border-left: 3px solid var(--accent-blue); padding-left: 15px; margin-bottom: 20px;">
            <h3 style="margin-bottom: 5px;">🧬 API Anomaly Detection</h3>
            <p style="color: var(--text-muted); font-size: 0.9rem;">Real-time correlation of network failures with frontend state transitions.</p>
        </div>
        """, unsafe_allow_html=True)
        
        anomaly_file = os.path.join(results_dir, f"{selected_run}_anomalies.json")
        if os.path.exists(anomaly_file):
            with open(anomaly_file, "r") as f:
                anomaly_data = json.load(f)
                
            anomalies = anomaly_data.get("anomalies", [])
            if anomalies:
                st.error(f"⚠️ {len(anomalies)} API Anomalies Detected during execution!")
                import pandas as pd  # type: ignore
                st.dataframe(pd.DataFrame(anomalies), hide_index=True)
            else:
                st.success("Network layer is completely healthy. No API anomalies detected.")
        else:
             st.info("No anomaly data available for this run.")
             
    with i_col2:
        st.markdown("""
        <div style="border-left: 3px solid var(--accent-emerald); padding-left: 15px; margin-bottom: 25px;">
            <h3 style="margin-bottom: 5px;">🛡️ Self-Healing Diagnostics</h3>
            <p style="color: var(--text-muted); font-size: 0.9rem;">Proactive DOM mutation recovery and fallback selector strategy.</p>
        </div>
        
        <div style="background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.2); padding: 20px; border-radius: 12px; margin-bottom: 20px;">
            <div style="font-weight: 600; color: var(--accent-emerald); margin-bottom: 5px;">Module 09 Status</div>
            <div style="font-size: 0.85rem;">Healer engine ready. Cross-referential DOM cache operational.</div>
        </div>
        
        <div style="border-left: 3px solid #f59e0b; padding-left: 15px; margin-bottom: 20px;">
            <h3 style="margin-bottom: 5px;">🔮 Regression Risk Predictor</h3>
            <p style="color: var(--text-muted); font-size: 0.9rem;">Heuristic failure probability based on component AST complexity.</p>
        </div>
        """, unsafe_allow_html=True)

with tab6:
    st.header("🌐 Cross-Site Swarm Comparison")
    st.markdown("Compares the latest execution results across **all distinct target URLs** tested by the QA Agent.")
    
    # Scan ALL result files in the results directory (not limited to available_runs dropdown)
    all_result_files = sorted(glob.glob(os.path.join(results_dir, "run_*_results.json")), reverse=True)
    
    url_stats = {}  # type: ignore
    
    for rfile in all_result_files:
        try:
            with open(rfile, "r", encoding="utf-8") as f:
                result_data = json.load(f)
                rid = result_data.get("run_id", os.path.basename(rfile).replace("_results.json", ""))
                tests = result_data.get("tests", [])
                
                # Check for anomalies once per run ID
                anomaly_count_total = 0
                anomaly_file = os.path.join(results_dir, f"{rid}_anomalies.json")
                if os.path.exists(anomaly_file):
                    try:
                        with open(anomaly_file, "r", encoding="utf-8") as af:
                            anomaly_data = json.load(af)
                            anomaly_count_total = len(anomaly_data.get("anomalies", []))
                    except: pass

                # Aggregate by source_url
                for t in tests:
                    t_url = t.get("source_url", result_data.get("target_url", "Unknown"))
                    if t_url == "N/A" or not t_url:
                        t_url = result_data.get("target_url", "Unknown")
                        
                    if t_url not in url_stats:
                        url_stats[t_url] = {
                            "Application": t_url,
                            "Latest Run ID": rid,
                            "Count": 0,
                            "Pass 🟢": 0,
                            "Fail 🔴": 0,
                            "Reliability %": 0,
                            "Time (s)": 0,
                            "Deployment Health": "PENDING",
                            "Anomalies ⚠️": 0,
                            "timestamp": result_data.get("timestamp", "")
                        }
                    
                    # Only update if this is the latest result for this URL
                    # (Strictly speaking, we want the most recent data for each URL)
                    # Since we sort rfiles by date, the first time we see a URL, it's the latest.
                    # Wait, if one run has 5 URLs, we should process all tests in that run.
                    # If we already have "Latest Run ID" for this URL from a PREVIOUS (newer) file, skip.
                    
                    stats = url_stats.get(t_url)
                    if stats and stats["Latest Run ID"] == rid:
                        stats["Count"] = int(stats.get("Count", 0)) + 1
                        if t.get("status") == "passed":
                            stats["Pass 🟢"] = int(stats.get("Pass 🟢", 0)) + 1
                        else:
                            stats["Fail 🔴"] = int(stats.get("Fail 🔴", 0)) + 1
                        stats["Time (s)"] = float(stats.get("Time (s)", 0)) + float(t.get("execution_time_ms", 0)) / 1000
                        stats["Anomalies ⚠️"] = anomaly_count_total # Simplification
        except Exception:
            pass
            
    # Finalize stats
    for t_url, stats in url_stats.items():
        count = int(stats.get("Count", 0))
        if count > 0:
            stats["Reliability %"] = float(f"{(float(stats.get('Pass 🟢', 0)) / count) * 100:.1f}")
            stats["Deployment Health"] = "✅ STABLE" if int(stats.get("Fail 🔴", 0)) == 0 else "❌ UNSTABLE"
            stats["Time (s)"] = float(f"{float(stats.get('Time (s)', 0)):.1f}")

    url_latest_run = url_stats
    
    # Display  
    if len(url_latest_run) > 1:
        import pandas as pd  # type: ignore
        swarm_df = pd.DataFrame(list(url_latest_run.values()))
        
        # Summary metrics row
        total_sites = len(swarm_df)
        stable_sites = len(swarm_df[swarm_df["Deployment Health"] == "✅ STABLE"])
        avg_pass_rate = round(swarm_df["Reliability %"].mean(), 1)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Sites Compared", total_sites)
        m2.metric("Stable Sites", f"{stable_sites}/{total_sites}")
        m3.metric("Avg Pass Rate", f"{avg_pass_rate}%")
        m4.metric("Total Scenarios", int(swarm_df["Count"].sum()))
        
        st.markdown("---")
        st.markdown("#### 🔬 Neural Swarm Benchmarks")
        st.dataframe(
            swarm_df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Reliability %": st.column_config.ProgressColumn(
                    "Reliability %",
                    help="Pass rate across all tests for this target",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
            }
        )
        
        st.markdown("#### 📊 Scenario Recovery Variance")
        chart_data = swarm_df[["Application", "Pass 🟢", "Fail 🔴"]].set_index("Application")
        st.bar_chart(chart_data, color=["#10b981", "#ef4444"])
        
        st.markdown("#### ⚡ Infrastructure Stability Score")
        rate_data = swarm_df[["Application", "Reliability %"]].set_index("Application")
        st.bar_chart(rate_data, color=["#38bdf8"])
    elif len(url_latest_run) == 1:
        st.info("🌐 Swarm Comparison requires results from **at least 2 distinct URLs**. Currently only one domain found in recent results. Run the agent against more URLs to populate this view.")
        import pandas as pd  # type: ignore
        st.dataframe(pd.DataFrame(list(url_latest_run.values())), use_container_width=True, hide_index=True)
    else:
        st.info("Awaiting Swarm Execution completion. No structural comparison data found across distinct URLs.")

with tab7:
    st.header("🔍 Root Cause Analyzer")
    st.markdown("Automated analysis using **real Cypress error diagnostics** combined with heuristic classification.")
    
    if run_results:
        tests: List[Dict[str, Any]] = run_results.get("tests", [])
        failed_tests = [t for t in tests if isinstance(t, dict) and t.get("status") == "failed"]
        
        if failed_tests:
            st.warning(f"Analyzed {len(failed_tests)} failures from the latest execution.")
            
            # Load real Cypress error data from status files
            error_data_map = {}
            for f_test in failed_tests:
                test_id = f_test.get("test_id", "")
                # Find the matching status file (format: NN_test_id.cy.js_status.json)
                import glob as _glob
                status_pattern = os.path.join(results_dir, f"*{test_id}*_status.json")
                status_files = _glob.glob(status_pattern)
                if status_files:
                    try:
                        with open(status_files[0], "r") as sf:
                            error_data_map[test_id] = json.load(sf)
                    except Exception:
                        pass
            
            for f_test in failed_tests:
                test_id = f_test.get("test_id", "")
                exec_time = f_test.get("execution_time_ms", 0)
                module = f_test.get("module", "")
                
                # Try to get REAL error data from Cypress
                real_error = error_data_map.get(test_id, {})
                real_message = real_error.get("errorMessage")
                real_type = real_error.get("errorType")
                real_stack = real_error.get("errorStack")
                
                # Generate diagnosis: prefer real data, fallback to heuristics
                if real_message and real_type:
                    # Real Cypress error available
                    type_descriptions = {
                        "TIMEOUT": "⏱️ Element or page load timed out. The selector exists but the element didn't become actionable within the configured timeout.",
                        "ELEMENT_NOT_FOUND": "🔍 Selector not found in DOM. The element may have been renamed, removed, or conditionally rendered.",
                        "DETACHED_DOM": "💥 Element was found but detached during interaction. Common with SPAs that re-render components.",
                        "ASSERTION_FAILURE": "❌ Element was found and interacted with, but the post-action assertion failed.",
                        "SYNTAX_ERROR": "🛠️ Generated test code has a syntax error. The CypressBuilder produced invalid JavaScript.",
                        "NAVIGATION_FAILURE": "🧭 Navigation action didn't reach the expected destination URL.",
                        "UNKNOWN": "⚠️ Unclassified error. Review the Cypress error message below for details."
                    }
                    diagnosis = type_descriptions.get(real_type, "⚠️ Unclassified error.")
                    source_label = "🔬 Real Cypress Error"
                else:
                    # Fallback: heuristic analysis
                    if exec_time == 0:
                        diagnosis = "Fatal Syntax Error or Setup Crash before execution began. Check Cypress generator syntax for unescaped quotes or invalid chaining."
                    elif "Navigation" in module:
                        diagnosis = "Timeout: The anchor tag clicked correctly, but the application routed to a dead-end or stayed on the same view."
                    elif "Forms" in module:
                        diagnosis = "Timeout: Form submitted, but validation or backend response didn't meet assertion expectations."
                    elif "Security" in module:
                        diagnosis = "Security Block: Malformed payload halted. The framework verified resilience but assertions couldn't map the fallback DOM."
                    else:
                        diagnosis = "Timeout/Detached DOM: Cypress failed to establish continuous visibility on the element within configured limits."
                    source_label = "🔮 Heuristic Analysis"
                    real_type = "HEURISTIC"
                
                with st.expander(f"🔴 {f_test['test_id']} — {module} ({real_type})"):
                    st.markdown(f"""
                        <div style="margin-bottom: 15px;">
                            <div style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; margin-bottom: 5px;">Scenario Description</div>
                            <div style="font-weight: 500;">{f_test['scenario']}</div>
                        </div>
                        <div style="display: flex; gap: 20px; margin-bottom: 20px;">
                            <div>
                                <div style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; margin-bottom: 5px;">Selector</div>
                                <code style="background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px;">{f_test.get('selector_used', 'N/A')}</code>
                            </div>
                            <div>
                                <div style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; margin-bottom: 5px;">Exec Time</div>
                                <div style="font-weight: 500;">{exec_time}ms</div>
                            </div>
                            <div>
                                <div style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; margin-bottom: 5px;">Attempts</div>
                                <div style="font-weight: 500;">{f_test.get('attempts', 1)}</div>
                            </div>
                        </div>
                        <div style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; padding: 15px; border-radius: 4px; margin-bottom: 15px;">
                            <div style="font-weight: 700; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 5px; color: #ef4444;">{source_label}</div>
                            <div style="font-size: 0.9rem;">{diagnosis}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Show real Cypress error if available
                    if real_message:
                        st.markdown("**Cypress Error Message:**")
                        st.code(real_message, language="text")
                    if real_stack:
                        with st.expander("View Full Stack Trace"):
                            st.code(real_stack, language="text")
        else:
            st.success("No failures to analyze in this run! Excellent.")
    else:
        st.info("No execution results found for this run. Awaiting test completion.")

import time
if auto_refresh:
    time.sleep(10)
    st.rerun()
