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

    AGENT_BACKEND: Literal["bedrock_agent", "strands"] = Field(
        default="bedrock_agent",
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