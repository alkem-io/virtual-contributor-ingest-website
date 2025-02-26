from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from chromadb.utils.embedding_functions import openai_embedding_function

from config import env

embedding_function = openai_embedding_function.OpenAIEmbeddingFunction(
    api_key=env.openai_key,
    api_base=env.openai_endpoint,
    api_type="azure",
    api_version=env.openai_api_version,
    deployment_id=env.embeddings_model_name,
)

llm = ChatCompletionsClient(
    endpoint=env.mistral_endpoint,
    credential=AzureKeyCredential(env.mistral_key),
)
