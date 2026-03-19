"""Main Streamlit app manager and orchestrator."""

import logging

import streamlit as st

from smart_report_analyst.service.streamlit import config
from smart_report_analyst.service.streamlit.components import render_sidebar
from smart_report_analyst.service.streamlit.pages import chat_page, home_page, settings_page
from smart_report_analyst.service.streamlit.state import UIState

logger = logging.getLogger(__name__)


def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title=config.PAGE_TITLE,
        page_icon=config.PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for better styling
    st.markdown(
        """
        <style>
        .main {
            max-width: 1200px;
            margin: 0 auto;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_app():
    """Initialize the application."""
    UIState.initialize()
    logger.info("Application initialized")


def run_app():
    """Main application entry point."""
    configure_page()
    initialize_app()

    # Render sidebar and get selected page
    selected_page = render_sidebar()

    # Route to appropriate page
    if selected_page == "Chat":
        chat_page()
    elif selected_page == "Settings":
        settings_page()
    else:  # Home
        home_page()


if __name__ == "__main__":
    run_app()
