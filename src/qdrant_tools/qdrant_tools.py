# PROJECT_KARLA/src/qdrantTools/qdrant_tools.py

from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from typing import Any

load_dotenv()

qdrant_url = "http://localhost:6333"
qdrant_client = QdrantClient(qdrant_url)
embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

def qdrant_foo():
    return("\n\nqdrant_bar\n\n")


def collection_exists(client: QdrantClient, collection_name: str) -> bool:
    try:
        client.get_collection(collection_name)
        return True
    except:
        return False
    
def get_genre_howto_db(genre_name: str):

    howto_name = f"{genre_name}_howto"
    
    if not collection_exists(qdrant_client, howto_name):
        raise ValueError(f"ERROR: Can't find howto for genre: {genre_name}")
    
    return QdrantVectorStore.from_existing_collection(
        url=qdrant_url,
        collection_name=howto_name,
        embedding=embedding_model
    )

def get_genre_examples_db(genre_name: str):

    examples_name = f"{genre_name}_examples"

    if not collection_exists(qdrant_client, examples_name):
        raise ValueError(f"ERROR: Can't find examples for genre: {genre_name}")
    
    return QdrantVectorStore.from_existing_collection(
        url=qdrant_url,
        collection_name=examples_name,
        embedding=embedding_model
    )

def search_genre_howto(genre_name: str, search_query: str) -> str:
    howto_db = get_genre_howto_db(genre_name)
    search_result = howto_db.similarity_search(query=search_query)
    return "\n\n\n".join(
        [ f"Context chunk {i+1}:\n{doc.page_content}"  for i, doc in enumerate(search_result)]
    )

def search_genre_examples(genre_name: str, search_query: str) -> str:
    examples_db = get_genre_examples_db(genre_name)
    search_result = examples_db.similarity_search(query=search_query)
    return "\n\n\n".join(
        [ f"Context chunk {i+1}:\n{doc.page_content}"  for i, doc in enumerate(search_result)]
    )