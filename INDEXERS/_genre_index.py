from dotenv import load_dotenv
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from pydantic import BaseModel


# load the openai key from .env
load_dotenv()

def create_genre_collection(
        file_path: Path,
        collection_name_: str
):
    
    # load the source document, according to its type
    if file_path.suffix == ".pdf":
        loader = PyPDFLoader(file_path)
    else:
        loader = TextLoader(file_path)
    docs = loader.load()
    
    # Split the soource document into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 600,
        chunk_overlap = 200
    )
    chunks = splitter.split_documents(docs)

    # create the embedding model
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
    
    # create the qdrant vector store
    vector_store = QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embedding_model,
        url = "http://localhost:6333",
        collection_name = collection_name_
    )


# USAGE PATTERN
# embedding_model: OpenAIEmbeddings = OpenAIEmbeddings(
#     model = "text-embedding-3-large"
# )
# vector_db: QdrantVectorStore = QdrantVectorStore.from_existing_collection(
#     url             = "http://localhost:6333",
#     collection_name = "{collection_name}",
#     embedding       = embedding_model
# )
# search_result = vector_db.similarity_search(query="whatever")
