# Função de busca semântica no ChromaDB — NovaTech
# Recebe uma pergunta, busca os chunks mais similares
# e retorna com score de similaridade e metadados de fonte

import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

def search(query, n_results=5):
    """
    Busca os N chunks mais similares à pergunta.
    Retorna lista com texto, fonte, seção e score.
    """
    model = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection("novatech")

    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for i in range(len(results["documents"][0])):
        chunks.append({
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "section": results["metadatas"][0][i]["section"],
            "score": round(1 - results["distances"][0][i], 4)
        })

    return chunks

def print_results(query, chunks):
    print(f"\nPergunta: {query}")
    print("-" * 60)
    for i, chunk in enumerate(chunks):
        print(f"\n[{i+1}] Score: {chunk['score']}")
        print(f"    Fonte: {chunk['source']}")
        print(f"    Seção: {chunk['section']}")
        print(f"    Texto: {chunk['text'][:200]}...")

if __name__ == "__main__":
    # Teste rápido
    query = "Qual o prazo de devolução?"
    chunks = search(query)
    print_results(query, chunks)