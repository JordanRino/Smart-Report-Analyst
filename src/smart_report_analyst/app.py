import asyncio
import logging
import uuid

from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.bedrock.manager import BedrockManager
from smart_report_analyst.service.streamlit import run_app
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
                    
                response = await asyncio.to_thread(self.bedrock_manager.invoke_orchestration, user_prompt, session_id)
                print(f"\nSmart Report Analyst: {response}\n")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\nAn error occurred: {e}\n")
                print("Please try again or type 'exit' to quit.\n")


def run_streamlit():
    """Start the Streamlit UI application.
    
    This function sets up logging and runs the Streamlit web interface.
    Run with: streamlit run streamlit_app.py
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting Smart Report Analyst Streamlit UI")
        
    run_app()