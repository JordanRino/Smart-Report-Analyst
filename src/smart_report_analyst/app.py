import asyncio
import logging
import uuid

from smart_report_analyst.config.settings import get_settings
from smart_report_analyst.service.bedrock.agent_manager import BedrockManager
from smart_report_analyst.service.strands.runner import run_sync

logger = logging.getLogger(__name__)
settings = get_settings()


class SmartReportAnalystApp:
    def __init__(self):
        self.bedrock_manager = BedrockManager()

    async def run_cli(self):
        """Start the interactive CLI loop."""
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

    def run_copilot(self, host: str | None = None, port: int | None = None):
        """
        Start the FastAPI server used by the Next.js UI (CopilotKit/AG-UI backend).

        Note: `host`/`port` override environment defaults for this process only.
        """

        import uvicorn
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from smart_report_analyst.routes.routes import router as api_router

        app = FastAPI(title="Smart Report Analyst - Copilot API")

        origins = settings.copilot_cors_origin_list
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        app.include_router(api_router, prefix="/api")

        bind_host = host if host is not None else settings.COPILOT_HOST
        bind_port = port if port is not None else settings.COPILOT_PORT
        print(f"Starting CopilotKit Backend on http://{bind_host}:{bind_port}")
        print(f"CORS allow_origins: {origins}")

        uvicorn.run(app, host=bind_host, port=bind_port)