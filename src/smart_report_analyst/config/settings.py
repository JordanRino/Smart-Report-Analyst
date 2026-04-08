from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    environment: str = Field(
        default="development",
        description="Runtime environment label (production, development, staging, etc.).",
        validation_alias="ENVIRONMENT",
    )

    AGENT_BACKEND: Literal["bedrock", "strands"] = Field(
        default="bedrock",
        description="LLM backend: managed Bedrock Agent (InvokeAgent) or Strands + BedrockModel.",
        validation_alias="AGENT_BACKEND",
    )

    BEDROCK_KNOWLEDGE_BASE_ID: Optional[str] = Field(
        default=None,
        description="Knowledge base ID for bedrock-agent-runtime.retrieve (required when AGENT_BACKEND=strands).",
        validation_alias="BEDROCK_KNOWLEDGE_BASE_ID",
    )

    BEDROCK_MODEL_ID: Optional[str] = Field(
        default=None,
        description="Bedrock model or inference profile ID for Strands BedrockModel (required when AGENT_BACKEND=strands).",
        validation_alias="BEDROCK_MODEL_ID",
    )

    BEDROCK_GUARDRAIL_ID: Optional[str] = Field(
        default=None,
        description="Optional Bedrock guardrail ID for Strands BedrockModel (InvokeModel guardrails).",
        validation_alias="BEDROCK_GUARDRAIL_ID",
    )
    BEDROCK_GUARDRAIL_VERSION: Optional[str] = Field(
        default=None,
        description="Guardrail version (e.g. DRAFT or numeric). Defaults to DRAFT when ID is set but version is empty.",
        validation_alias="BEDROCK_GUARDRAIL_VERSION",
    )
    BEDROCK_GUARDRAIL_TRACE: Optional[str] = Field(
        default=None,
        description="Guardrail trace: enabled, disabled, or enabled_full (Strands BedrockModel).",
        validation_alias="BEDROCK_GUARDRAIL_TRACE",
    )
    BEDROCK_GUARDRAIL_REDACT_INPUT: Optional[bool] = Field(
        default=None,
        description="When true, Strands overwrites blocked user input in history (see Strands BedrockModel).",
        validation_alias="BEDROCK_GUARDRAIL_REDACT_INPUT",
    )
    BEDROCK_GUARDRAIL_REDACT_INPUT_MESSAGE: Optional[str] = Field(
        default=None,
        description="Replacement text when guardrail_redact_input is used.",
        validation_alias="BEDROCK_GUARDRAIL_REDACT_INPUT_MESSAGE",
    )
    BEDROCK_GUARDRAIL_REDACT_OUTPUT: Optional[bool] = Field(
        default=None,
        description="When true, Strands can redact model output on guardrail intervention.",
        validation_alias="BEDROCK_GUARDRAIL_REDACT_OUTPUT",
    )
    BEDROCK_GUARDRAIL_REDACT_OUTPUT_MESSAGE: Optional[str] = Field(
        default=None,
        description="Replacement text when guardrail_redact_output is used.",
        validation_alias="BEDROCK_GUARDRAIL_REDACT_OUTPUT_MESSAGE",
    )

    RETRIEVAL_MAX_RESULTS: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Max KB chunks to include per retrieve_kb_context call.",
        validation_alias="RETRIEVAL_MAX_RESULTS",
    )

    RETRIEVAL_MAX_CHARS: int = Field(
        default=48_000,
        ge=1000,
        description="Max characters of KB context to pass to the model after flattening.",
        validation_alias="RETRIEVAL_MAX_CHARS",
    )

    AWS_REGION: str = Field(
        default="us-east-1",
        description="AWS region where Bedrock agent is deployed",
        validation_alias="AWS_REGION"
    )
    SINGLE_COORDINATOR_BEDROCK_AGENT_ID: Optional[str] = Field(
        default=None,
        description="The unique identifier of the single coordinator Bedrock agent to use for all interactions.",
        validation_alias="SINGLE_COORDINATOR_BEDROCK_AGENT_ID"
    )
    SINGLE_COORDINATOR_BEDROCK_AGENT_ALIAS_ID: Optional[str] = Field(
        default=None,
        description="The alias identifier of the single coordinator Bedrock agent to use for all interactions.",
        validation_alias="SINGLE_COORDINATOR_BEDROCK_AGENT_ALIAS_ID"
    )
    COORDINATOR_BEDROCK_AGENT_ID: Optional[str] = Field(
        default=None,
        description="The unique identifier of the Bedrock agent to use",
        validation_alias="COORDINATOR_BEDROCK_AGENT_ID"
    )
    COORDINATOR_BEDROCK_AGENT_ALIAS_ID: Optional[str] = Field(
        default=None,
        description="The alias identifier of the Bedrock agent to use",
        validation_alias="COORDINATOR_BEDROCK_AGENT_ALIAS_ID"
    )
    SQL_GENERATOR_BEDROCK_AGENT_ID: Optional[str] = Field(
        default=None,
        description="The unique identifier of the SQL Generator agent to use",
        validation_alias="SQL_GENERATOR_BEDROCK_AGENT_ID"
    )
    SQL_GENERATOR_BEDROCK_AGENT_ALIAS_ID: Optional[str] = Field(
        default=None,
        description="The alias identifier of the SQL Generator agent to use",
        validation_alias="SQL_GENERATOR_BEDROCK_AGENT_ALIAS_ID"
    )
    SQL_EXECUTOR_BEDROCK_AGENT_ID: Optional[str] = Field(
        default=None,
        description="The unique identifier of the SQL Executor agent to use",
        validation_alias="SQL_EXECUTOR_BEDROCK_AGENT_ID"
    )
    SQL_EXECUTOR_BEDROCK_AGENT_ALIAS_ID: Optional[str] = Field(
        default=None,
        description="The alias identifier of the SQL Executor agent to use",
        validation_alias="SQL_EXECUTOR_BEDROCK_AGENT_ALIAS_ID"
    )
    STORE_SQL_LAMBDA_FUNCTION_NAME: str = Field(
        default="store_sql_sra",
        description="The name of the Lambda function that stores SQL queries and execution results",
        validation_alias="STORE_SQL_LAMBDA_FUNCTION_NAME"
    )
    STRANDS_SQL_LAMBDA_FUNCTION_NAME: Optional[str] = Field(
        default=None,
        description="Optional Lambda name for Strands execute_sql; falls back to STORE_SQL_LAMBDA_FUNCTION_NAME.",
        validation_alias="STRANDS_SQL_LAMBDA_FUNCTION_NAME",
    )

    STRANDS_SESSION_STORAGE_DIR: Optional[str] = Field(
        default=None,
        description="Base directory for Strands file sessions; defaults to package strands/session/storage/.",
        validation_alias="STRANDS_SESSION_STORAGE_DIR",
    )
    STRANDS_CONVERSATION_SUMMARY_RATIO: float = Field(
        default=0.3,
        ge=0.1,
        le=0.8,
        description="Fraction of messages to summarize when reducing context (Strands SummarizingConversationManager).",
        validation_alias="STRANDS_CONVERSATION_SUMMARY_RATIO",
    )
    STRANDS_CONVERSATION_PRESERVE_RECENT_MESSAGES: int = Field(
        default=10,
        ge=1,
        description="Minimum recent messages to keep verbatim before summarization.",
        validation_alias="STRANDS_CONVERSATION_PRESERVE_RECENT_MESSAGES",
    )
    MYSQL_HOST: Optional[str] = Field(
        default=None,
        description="The hostname of the MySQL database",
        validation_alias="MYSQL_HOST"
    )
    MYSQL_PORT: int = Field(
        default=3306,
        description="The port of the MySQL database",
        validation_alias="MYSQL_PORT"
    )
    MYSQL_USER: Optional[str] = Field(
        default=None,
        description="The username for the MySQL database",
        validation_alias="MYSQL_USER"
    )
    MYSQL_PASSWORD: Optional[str] = Field(
        default=None,
        description="The password for the MySQL database",
        validation_alias="MYSQL_PASSWORD"
    )
    MYSQL_DB: Optional[str] = Field(
        default=None,
        description="The name of the MySQL database",
        validation_alias="MYSQL_DB"
    )

    COPILOT_HOST: str = Field(
        default="0.0.0.0",
        description="Bind address for FastAPI when running --copilot.",
        validation_alias="COPILOT_HOST",
    )
    COPILOT_PORT: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Bind port for FastAPI when running --copilot.",
        validation_alias="COPILOT_PORT",
    )
    COPILOT_CORS_ORIGINS: str = Field(
        default="http://localhost:3000",
        description="Comma-separated browser Origins allowed to call the Copilot API (Next.js URL(s)).",
        validation_alias="COPILOT_CORS_ORIGINS",
    )

     # Pydantic Settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",  # Automatically load from .env file
        env_file_encoding="utf-8",
        case_sensitive=False,  # Case-insensitive environment variables
        extra="ignore",  # Ignore extra environment variables
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() in {"production", "prod"}

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() in {"development", "dev"}

    @property
    def is_staging(self) -> bool:
        """Check if running in staging/test."""
        return self.environment.lower() in {"staging", "stage", "test"}

    @property
    def copilot_cors_origin_list(self) -> list[str]:
        """Parsed COPILOT_CORS_ORIGINS for FastAPI CORSMiddleware."""
        return [o.strip() for o in self.COPILOT_CORS_ORIGINS.split(",") if o.strip()]



@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to create a singleton - settings are loaded once
    and reused throughout the application lifecycle.

    Returns:
        Settings instance with validated configuration
    """
    return Settings()