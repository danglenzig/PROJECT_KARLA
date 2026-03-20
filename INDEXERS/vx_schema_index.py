from dotenv import load_dotenv
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from pydantic import BaseModel


# load the openai key from .env
load_dotenv()


###################
# INGESTION PHASE #
###################

pdf_path: Path = Path(__file__).parent / "vn_narrative_design_guide.pdf"

# load this file in current python program
pdf_loader: PyPDFLoader = PyPDFLoader(
    file_path=pdf_path
)


# a list of objects of type langchain_core.documents.base.Document
docs = pdf_loader.load()

##################
# CHUNKING PHASE #
##################

CHUNK_SIZE      = 600
OVERLAP_SIZE    = 200

r_text_splitter: RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter(
    chunk_size  = CHUNK_SIZE,
    chunk_overlap     = OVERLAP_SIZE
)



# also a list of objects of type langchain_core.documents.base.Document
chunks = r_text_splitter.split_documents(
    documents = docs
)


#####################
# VECTOR EMBEDDINGS #
#####################

# create embedding model
embedding_model: OpenAIEmbeddings = OpenAIEmbeddings(
    model = "text-embedding-3-large"
)

#######################
# BRIDGE TO QDRANT DB #
#######################

vector_store: QdrantVectorStore = QdrantVectorStore.from_documents(
    documents       = chunks,
    embedding       = embedding_model,
    url             = "http://localhost:6333",
    collection_name = "karla_collection"
)

print("Indexing complete...")
# ^^ this is all good. I have verified that the DB is properly running at
# localhost:6333