"""Streamlit pages."""

from smart_report_analyst.service.streamlit.pages.chat import chat_page
from smart_report_analyst.service.streamlit.pages.home import home_page
from smart_report_analyst.service.streamlit.pages.settings import settings_page

__all__ = [
    "chat_page",
    "home_page",
    "settings_page",
]
