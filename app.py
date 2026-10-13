"""
Haru Scenario Builder - Main entry point with navigation
"""

import streamlit as st
from src.services.demo_language import LANGUAGES, normalize_language

st.set_page_config(
    page_title="Haru Scenario Builder",
    page_icon="🤖",
    layout="wide",
)

st.sidebar.selectbox(
    "Demo language", list(LANGUAGES),
    index=list(LANGUAGES).index(normalize_language()),
    format_func=lambda locale: LANGUAGES[locale][0], key="demo_language",
)
st.sidebar.caption("Run the speech and LLM services with the same demo language. Scripted text requires translation.")

# Define pages with custom names
scenario_page = st.Page("views/scenario_builder.py", title="Scenario Builder", icon="🎬", default=True)
task_page = st.Page("views/task_builder.py", title="Task Builder", icon="📝")

# Navigation
pg = st.navigation([scenario_page, task_page])
pg.run()
