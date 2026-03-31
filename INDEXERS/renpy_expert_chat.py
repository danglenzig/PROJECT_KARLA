from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from openai import OpenAI

load_dotenv()
openai_client = OpenAI()
chat_model = "gpt-4.1"

emdedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
vector_db = QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="renpy_docs",
    embedding=emdedding_model
)

print("FOO")
user_query: str = input("--> ")

search_results = vector_db.similarity_search(user_query, k=5)

context = "\n\n".join(
    f"Page content: {[result.page_content for result in search_results]}\nFile: {result.metadata['filename']}" for result in search_results
)

SYSTEM_PROMPT = f"""
You are an expert in the Ren'Py visual novel engine. You have access to the official Ren'Py documentation, which is provided as context for answering user questions.
Use the provided context to answer the user's question about Ren'Py. If you don't know the answer, say you don't know.
Context:
{context}
"""



response = openai_client.chat.completions.create(
    model=chat_model,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query}
    ]
)
print(f"\n\nAnswer: {response.choices[0].message.content}")

for result in search_results:
    print(f"\n\nPage content: {result.page_content}\nFile: {result.metadata['filename']}")
