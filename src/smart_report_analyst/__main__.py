import asyncio
import argparse
import sys
import logging

from smart_report_analyst.app import SmartReportAnalystApp, run_streamlit, run_chainlit
def main():
    """Main entry point that determines which mode to run.
    
    Usage:
        python -m smart_report_analyst              # CLI mode
        python -m smart_report_analyst --streamlit  # Streamlit UI mode
    """

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)  # Force logs to stdout
        ],
        force=True
    )

    parser = argparse.ArgumentParser(description="Smart Report Analyst")
    parser.add_argument(
        "--streamlit",
        action="store_true",
        help="Run Streamlit UI",
    )

    parser.add_argument(
        "--chainlit",
        action="store_true",
        help="Run Chainlit UI",
    )

    args = parser.parse_args()

    app = SmartReportAnalystApp()

    if args.streamlit:
        run_streamlit()
    elif args.chainlit:
        run_chainlit()
    else:
        asyncio.run(app.run_cli())


if __name__ == "__main__":
    main()