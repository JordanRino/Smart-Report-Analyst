import asyncio
import logging
import uuid
import subprocess
from pathlib import Path

from smart_report_analyst.config.settings import get_settings
from smart_report_analyst.service.bedrock.agent_manager import BedrockManager
from smart_report_analyst.service.strands.runner import run_sync

logger = logging.getLogger(__name__)
settings = get_settings()


class SmartReportAnalystApp:
    def __init__(self):
        self.bedrock_manager = BedrockManager()

    async def run_cli(self):
        """Start the interactive CLI for the Smart Report Analyst."""
        session_id = uuid.uuid4().hex
        strands_history: list[dict] = []

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

                if settings.AGENT_BACKEND == "strands":
                    strands_history.append({"role": "user", "content": user_prompt})
                    response = await asyncio.to_thread(run_sync, user_prompt, session_id)
                    assistant_text = response.get("final_response", "")
                    strands_history.append({"role": "assistant", "content": assistant_text})
                    print(f"\nSmart Report Analyst: {assistant_text}\n")
                else:
                    response = await asyncio.to_thread(
                        self.bedrock_manager.invoke_agent,
                        user_prompt,
                        settings.SINGLE_COORDINATOR_BEDROCK_AGENT_ID,
                        settings.SINGLE_COORDINATOR_BEDROCK_AGENT_ALIAS_ID,
                        session_id
                    )
                    print(f"\nSmart Report Analyst: {response.get('final_response', response)}\n")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\nAn error occurred: {e}\n")
                print("Please try again or type 'exit' to quit.\n")


    def run_streamlit(self):
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

    def run_chainlit(self):
        """Start the Chainlit UI application via CLI."""

        logger.info("Starting Smart Report Analyst Chainlit UI")

        chainlit_file = Path(__file__).parent / "ui/chainlit/manager.py"

        subprocess.run([
            "chainlit",
            "run",
            str(chainlit_file),
            "-w"  # auto-reload (super useful for dev)
        ])

    def run_copilot(self):

        import uvicorn
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from smart_report_analyst.routes.routes import router as api_router

        app = FastAPI(title="Smart Report Analyst - Copilot API")

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000"], # Next.js port
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        app.include_router(api_router, prefix="/api")
    
        print("Starting CopilotKit Backend on http://0.0.0.0:8000")

        uvicorn.run(app, host="0.0.0.0", port=8000)