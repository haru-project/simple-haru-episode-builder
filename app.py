"""
Haru Scenario Builder - Main entry point with navigation
"""

import streamlit as st

st.set_page_config(
    page_title="Haru Scenario Builder",
    page_icon="🤖",
    layout="wide",
)

# Define pages with custom names
scenario_page = st.Page("views/scenario_builder.py", title="Scenario Builder", icon="🎬", default=True)
task_page = st.Page("views/task_builder.py", title="Task Builder", icon="📝")

# Navigation
pg = st.navigation([scenario_page, task_page])
pg.run()
