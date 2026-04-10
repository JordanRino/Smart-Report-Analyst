import asyncio
import argparse
import sys
import logging

from smart_report_analyst.app import SmartReportAnalystApp


def main():
    """Main entry point that determines which mode to run.
    
    Usage:
        python -m smart_report_analyst              # CLI mode
    """

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)  # Force logs to stdout
        ],
        force=True
    )

    # Root DEBUG would otherwise flood stdout with botocore parsers / HTTP wire logs.
    for _name in ("botocore", "boto3", "urllib3", "s3transfer"):
        logging.getLogger(_name).setLevel(logging.WARNING)
    # Strands Bedrock client logs full model requests at DEBUG (tokens, tool I/O).
    logging.getLogger("strands.models.bedrock").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description="Smart Report Analyst")


    parser.add_argument(
        "--copilot",
        action="store_true",
        help="Run CopilotKit/AG-UI Backend Server",
    )
    parser.add_argument(
        "--host",
        default=None,
        metavar="ADDR",
        help="Bind address for --copilot (overrides COPILOT_HOST; default from env or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        metavar="PORT",
        help="Bind port for --copilot (overrides COPILOT_PORT; default from env or 8000)",
    )

    args = parser.parse_args()

    app = SmartReportAnalystApp()

    if args.copilot:
        app.run_copilot(host=args.host, port=args.port)
    else:
        asyncio.run(app.run_cli())


if __name__ == "__main__":
    main()