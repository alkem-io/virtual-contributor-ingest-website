import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Env:
    local_path: str
    log_level: str
    vebose: bool
    chunk_size: int
    openai_endpoint: str
    openai_key: str
    openai_api_version: str
    embeddings_model_name: str
    mistral_endpoint: str
    mistral_key: str
    process_pages_limit: int

    def __init__(self):
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.local_path = os.getenv("LOCAL_PATH", "./")
        self.verbose = self.log_level == "DEBUG"
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "3000"))
        self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.openai_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.openai_api_version = os.getenv("OPENAI_API_VERSION", "")
        self.embeddings_model_name = os.getenv("EMBEDDINGS_DEPLOYMENT_NAME", "")
        self.mistral_endpoint = os.getenv("AZURE_MISTRAL_ENDPOINT", "")
        self.mistral_key = os.getenv("AZURE_MISTRAL_API_KEY", "")
        self.process_pages_limit = int(os.getenv("PROCESS_PAGES_LIMIT", "20"))

        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "")
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "")
        self.rabbitmq_input_queue = os.getenv("RABBITMQ_QUEUE", "")
        self.rabbitmq_result_queue = os.getenv("RABBITMQ_RESULT_QUEUE", "")
        self.rabbitmq_exchange = os.getenv("RABBITMQ_EVENT_BUS_EXCHANGE", "")
        self.rabbitmq_result_routing_key = os.getenv("RABBITMQ_RESULT_ROUTING_KEY", "")


env = Env()
