from functools import lru_cache
from typing import Optional
import uuid

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

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
    COORDINATOR_BEDROCK_AGENT_ID: str = Field(
        default=None,
        description="The unique identifier of the Bedrock agent to use",
        validation_alias="COORDINATOR_BEDROCK_AGENT_ID"
    )
    COORDINATOR_BEDROCK_AGENT_ALIAS_ID: str = Field(
        default=None,
        description="The alias identifier of the Bedrock agent to use",
        validation_alias="COORDINATOR_BEDROCK_AGENT_ALIAS_ID"
    )
    SQL_GENERATOR_BEDROCK_AGENT_ID: str = Field(
        default=None,
        description="The unique identifier of the SQL Generator agent to use",
        validation_alias="SQL_GENERATOR_BEDROCK_AGENT_ID"
    )
    SQL_GENERATOR_BEDROCK_AGENT_ALIAS_ID: str = Field(
        default=None,
        description="The alias identifier of the SQL Generator agent to use",
        validation_alias="SQL_GENERATOR_BEDROCK_AGENT_ALIAS_ID"
    )
    SQL_EXECUTOR_BEDROCK_AGENT_ID: str = Field(
        default=None,
        description="The unique identifier of the SQL Executor agent to use",
        validation_alias="SQL_EXECUTOR_BEDROCK_AGENT_ID"
    )
    SQL_EXECUTOR_BEDROCK_AGENT_ALIAS_ID: str = Field(
        default=None,
        description="The alias identifier of the SQL Executor agent to use",
        validation_alias="SQL_EXECUTOR_BEDROCK_AGENT_ALIAS_ID"
    )
    STORE_SQL_LAMBDA_FUNCTION_NAME: str = Field(
        default="store_sql_sra",
        description="The name of the Lambda function that stores SQL queries and execution results",
        validation_alias="STORE_SQL_LAMBDA_FUNCTION_NAME"
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