from dotenv import load_dotenv
from pathlib import Path
from langchain_community.document_loaders import UnstructuredRSTLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from pydantic import BaseModel
from qdrant_client import QdrantClient
import os

load_dotenv()

def create_collection_from_folder(
        folder_name: str,
        collection_name_: str
):
    # loader = UnstructuredRSTLoader(f"{folder_name}/", glob="**/*.rst")
    # docs = loader.load()

    loader = DirectoryLoader(
        folder_name,
        glob="**/*.rst",
        show_progress=True,
        loader_cls=UnstructuredRSTLoader
    )
    docs = loader.load()

    for doc in docs:
        doc.metadata["filename"] = os.path.basename(doc.metadata["source"])

    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 800,
        chunk_overlap = 100
    )
    chunks = splitter.split_documents(docs)
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
    vector_store = QdrantVectorStore.from_documents(
        chunks,
        embedding_model,
        collection_name = collection_name_,
        url = "http://localhost:6333"
    )

create_collection_from_folder("renpy_docs/", "renpy_docs")