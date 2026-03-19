"""Home/Dashboard page."""

import streamlit as st


def home_page():
    """Render the home page."""
    st.title("📊 Smart Report Analyst")
    st.subheader("AI-Powered Data Analysis Assistant")

    st.write(
        """
    Welcome to Smart Report Analyst! This tool harnesses the power of AWS Bedrock agents 
    to help you analyze your data and get insights in natural language.
    """
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="💬 Chat Available",
            value="Yes",
            delta="Ready to analyze",
        )

    with col2:
        st.metric(
            label="🤖 AI Engine",
            value="Bedrock",
            delta="AWS Agents",
        )

    with col3:
        st.metric(
            label="⚡ Status",
            value="Active",
            delta="Connected",
        )

    st.divider()

    st.subheader("Quick Start")
    st.write(
        """
    1. **Go to Chat** — Navigate to the Chat page using the sidebar
    2. **Ask Questions** — Ask about your data in natural language
    3. **Get Insights** — The AI agent will analyze and respond
    4. **Export** — Download your conversation anytime
    """
    )

    st.divider()

    st.subheader("Features")
    col1, col2 = st.columns(2)

    with col1:
        st.write(
            """
        ✅ Natural language queries
        ✅ Real-time streaming responses
        ✅ Conversation history management
        """
        )

    with col2:
        st.write(
            """
        ✅ Export conversations
        ✅ Session persistence
        ✅ Customizable settings
        """
        )

    st.divider()

    st.info(
        "💡 **Tip**: Visit Settings to customize your experience and preferences."
    )
