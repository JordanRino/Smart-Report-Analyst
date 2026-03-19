import asyncio
import sys

from smart_report_analyst.app import SmartReportAnalystApp, run_streamlit


async def main_cli():
    """Async entry point for the Smart Report Analyst CLI."""
    await SmartReportAnalystApp().run_cli()


def main():
    """Main entry point that determines which mode to run.
    
    Usage:
        python -m smart_report_analyst              # CLI mode
        python -m smart_report_analyst --streamlit  # Streamlit UI mode
    """
    if "--streamlit" in sys.argv:
        run_streamlit()
    else:
        asyncio.run(main_cli())


if __name__ == "__main__":
    main()