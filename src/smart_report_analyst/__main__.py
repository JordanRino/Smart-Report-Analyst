import asyncio
import argparse
import sys
import logging

from smart_report_analyst.app import SmartReportAnalystApp


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

    parser.add_argument(
        "--copilot",
        action="store_true",
        help="Run CopilotKit/AG-UI Backend Server",
    )

    args = parser.parse_args()

    app = SmartReportAnalystApp()

    if args.streamlit:
        app.run_streamlit()
    elif args.chainlit:
        app.run_chainlit()
    elif args.copilot:
        app.run_copilot()
    else:
        asyncio.run(app.run_cli())


if __name__ == "__main__":
    main()