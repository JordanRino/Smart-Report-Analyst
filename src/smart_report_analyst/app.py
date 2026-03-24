import asyncio
import logging
import uuid
import subprocess
from pathlib import Path

from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.bedrock.manager import BedrockManager

logger = logging.getLogger(__name__)
settings = Settings()


class SmartReportAnalystApp:
    def __init__(self):
        self.bedrock_manager = BedrockManager()

    async def run_cli(self):
        """Start the interactive CLI for the Smart Report Analyst."""
        session_id = uuid.uuid4().hex
        
        print("Hi there! I'm your Smart Report Analyst. Ask me anything about your data, and I'll do my best to help you out.")
        print("Type 'exit' or 'quit' to end the conversation.")
        
        while True:
            try:
                user_prompt = input("\nYou: ").strip()
                if user_prompt.lower() in ["exit", "quit"]:
                    print("Goodbye!")
                    break
                if not user_prompt:
                    continue
                    
                response = await asyncio.to_thread(
                    self.bedrock_manager.invoke_agent,
                    user_prompt,
                    settings.SINGLE_COORDINATOR_BEDROCK_AGENT_ID,
                    settings.SINGLE_COORDINATOR_BEDROCK_AGENT_ALIAS_ID,
                    session_id
                )
                print(f"\nSmart Report Analyst: {response}\n")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\nAn error occurred: {e}\n")
                print("Please try again or type 'exit' to quit.\n")


def run_streamlit():
    """Start the Streamlit UI application via CLI."""
    
    logger.info("Starting Smart Report Analyst Streamlit UI")

    # Get absolute path to manager.py
    streamlit_file = Path(__file__).parent / "service/streamlit/manager.py"

    # Run Streamlit properly
    subprocess.run([
        "streamlit",
        "run",
        str(streamlit_file)
    ])

def run_chainlit():
    """Start the Chainlit UI application via CLI."""

    logger.info("Starting Smart Report Analyst Chainlit UI")

    chainlit_file = Path(__file__).parent / "ui/chainlit/manager.py"

    subprocess.run([
        "chainlit",
        "run",
        str(chainlit_file),
        "-w"  # auto-reload (super useful for dev)
    ])