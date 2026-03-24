from dotenv import load_dotenv
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from pydantic import BaseModel
from qdrant_client import QdrantClient

# load the openai key from .env
load_dotenv()

def collection_exists(
        client: QdrantClient,
        collection_name_: str
):
    try:
        client.get_collection(collection_name_)
        return True
    except Exception:
        return False
    

def create_build_agent_rag():
    # maybe just do this with a system prompt
    pass

def create_genre_collection(
        file_path: Path,
        collection_name_: str
):
    
    # path check
    if not file_path.exists():
        raise FileNotFoundError(f"FILE NOT FOUND: {file_path}")
    
    # load the source document, according to its type
    print(f"\n\nLoading {file_path}...\n\n")
    if file_path.suffix == ".pdf":
        loader = PyPDFLoader(file_path)
    else:
        loader = TextLoader(
            file_path,
            encoding="utf-8",
            autodetect_encoding=True
        )
    docs = loader.load()
    
    # Split the soource document into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 600,
        chunk_overlap = 200
    )
    chunks = splitter.split_documents(docs)

    # create the embedding model
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

    # collection check -- fail if exists
    client = QdrantClient("http://localhost:6333")
    if collection_exists(client, collection_name_):
        raise ValueError(f"ERROR: {collection_name_} already exists. Use append function instead!")
    
    # create the qdrant vector store
    vector_store = QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embedding_model,
        url = "http://localhost:6333",
        collection_name = collection_name_
    )

    print(f"\n\nCreated {collection_name_}: {len(chunks)} chunks.\n\n")


def append_to_genre_collection(
        file_path: Path,
        collection_name_: str
):
    # path check 
    if not file_path.exists():
        raise FileNotFoundError(f"FILE NOT FOUND: {file_path}")


    # load the source document, according to its type
    print(f"\n\nLoading {file_path}...\n\n")
    if file_path.suffix == ".pdf":
        loader = PyPDFLoader(file_path)
    else:
        loader = TextLoader(
            file_path,
            encoding="utf-8",
            autodetect_encoding=True
        )
    docs = loader.load()

    # Split the source document into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 600,
        chunk_overlap = 200
    )
    new_chunks = splitter.split_documents(docs)

    # create the embedding model
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

    # Collection check -- fail if missing
    client = QdrantClient("http://localhost:6333")
    if not collection_exists(client, collection_name_):
        raise ValueError(f"ERROR: {collection_name_} does not exist. Use create function instead!")
    
    # append
    vector_store = QdrantVectorStore.from_existing_collection(
        embedding=embedding_model,
        url="http://localhost:6333",
        collection_name=collection_name_
    )
    vector_store.add_documents(new_chunks)

    print(f"\n\nAdded {file_path} to {collection_name_}: {len(new_chunks)} new chunks\n\n")

# add the source documents to the same folder as this script before running the indexer

# create_genre_collection(Path("_ROMANCE_howto_00.txt"), "romance_howto")
# append_to_genre_collection(Path("_ROMANCE_howto_01.txt"), "romance_howto")
# create_genre_collection(Path("_ROMANCE_examples_00.txt"), "romance_examples")
# append_to_genre_collection(Path("_ROMANCE_examples_01.txt"), "romance_examples")
# append_to_genre_collection(Path("_ROMANCE_examples_SOG.pdf"), "romance_examples")

# create_genre_collection(Path("_MYSTERY_howto_00.txt"), "mystery_howto")
# create_genre_collection(Path("_MYSTERY_examples_00.txt"), "mystery_examples")
# append_to_genre_collection(Path("_MYSTERY_examples_01.txt"), "mystery_examples")
# append_to_genre_collection(Path("_MYSTERY_examples_02.txt"), "mystery_examples")
# append_to_genre_collection(Path("_MYSTERY_examples_03.txt"), "mystery_examples")

# create_genre_collection(Path("_HORROR_howto_00.txt"), "horror_howto")
# create_genre_collection(Path("_HORROR_examples_00.txt"), "horror_examples")
# append_to_genre_collection(Path("_HORROR_examples_01.txt"), "horror_examples")
# append_to_genre_collection(Path("_HORROR_examples_02.txt"), "horror_examples")
# append_to_genre_collection(Path("_HORROR_examples_03.txt"), "horror_examples")
# append_to_genre_collection(Path("_HORROR_examples_04.txt"), "horror_examples")
# append_to_genre_collection(Path("_HORROR_examples_05.txt"), "horror_examples")
# append_to_genre_collection(Path("_HORROR_examples_06.txt"), "horror_examples")



# RETRIEVAL USAGE PATTERN
# embedding_model: OpenAIEmbeddings = OpenAIEmbeddings(
#     model = "text-embedding-3-large"
# )
# vector_db: QdrantVectorStore = QdrantVectorStore.from_existing_collection(
#     url             = "http://localhost:6333",
#     collection_name = "{collection_name}",
#     embedding       = embedding_model
# )
# search_result = vector_db.similarity_search(query="whatever")
