import boto3
from config.settings import AWS_REGION


class BedrockManager:

    def __init__(self):
        self.bedrockRuntimeClient = boto3.client(
            "bedrock-runtime", region_name=AWS_REGION
        )

    def get_bedrock_runtime_client(self):
        return self.bedrockRuntimeClient