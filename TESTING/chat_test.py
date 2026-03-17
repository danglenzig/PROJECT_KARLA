from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
openai_client: OpenAI = OpenAI()

# create embedding model
embedding_model: OpenAIEmbeddings = OpenAIEmbeddings(
    model = "text-embedding-3-large"
)


def collection_exists(
        client: QdrantClient,
        collection_name_: str
):
    try:
        client.get_collection(collection_name_)
        return True
    except Exception:
        return False

def get_vector_store(collection_name_: str):

    if not collection_exists(collection_name_):
        raise ValueError(f"ERROR: {collection_name_} does not exist.")
    
    vector_db: QdrantVectorStore = QdrantVectorStore.from_existing_collection(
        url             = "http://localhost:6333",
        collection_name = "karla_collection",
        embedding       = embedding_model
    )
    return vector_db

