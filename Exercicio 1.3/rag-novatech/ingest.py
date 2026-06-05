# Pipeline de ingestão RAG — NovaTech
# Estratégia de chunking: por seção semântica (## e ###)
# Justificativa: perguntas dos atendentes são sobre seções específicas
# (ex: "qual a regra da seção 3.2"). Chunking por seção preserva
# unidades de significado completas e evita cortar tabelas no meio.

import os
import re
import chromadb
from sentence_transformers import SentenceTransformer

# Configuração
DOCS_FOLDER = "docs"
CHROMA_PATH = "chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

def load_markdown_files(folder):
    """Lê todos os arquivos .md da pasta docs/"""
    documents = []
    for filename in os.listdir(folder):
        if filename.endswith(".md"):
            filepath = os.path.join(folder, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            documents.append({
                "filename": filename,
                "content": content
            })
    print(f"{len(documents)} documentos carregados.")
    return documents

def split_by_section(content, filename):
    """
    Divide o documento em chunks por seção (## e ###).
    Cada chunk recebe metadados de fonte e título da seção.
    """
    chunks = []
    
    # Divide nas linhas de cabeçalho ## ou ###
    pattern = r'(#{2,3} .+)'
    sections = re.split(pattern, content)
    
    current_title = filename  # fallback se não houver título
    buffer = []
    
    for part in sections:
        if re.match(pattern, part):
            # Salva o buffer anterior como chunk
            if buffer:
                chunk_text = "\n".join(buffer).strip()
                if len(chunk_text) > 50:  # ignora chunks muito pequenos
                    chunks.append({
                        "text": chunk_text,
                        "source": filename,
                        "section": current_title
                    })
            current_title = part.strip()
            buffer = [part]
        else:
            buffer.append(part)
    
    # Salva o último buffer
    if buffer:
        chunk_text = "\n".join(buffer).strip()
        if len(chunk_text) > 50:
            chunks.append({
                "text": chunk_text,
                "source": filename,
                "section": current_title
            })
    
    return chunks

def ingest():
    # Carrega documentos
    documents = load_markdown_files(DOCS_FOLDER)
    
    # Gera chunks
    all_chunks = []
    for doc in documents:
        chunks = split_by_section(doc["content"], doc["filename"])
        all_chunks.extend(chunks)
        print(f"  {doc['filename']}: {len(chunks)} chunks")
    
    print(f"\nTotal: {len(all_chunks)} chunks gerados.")
    
    # Gera embeddings
    print("\nGerando embeddings...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [chunk["text"] for chunk in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True)
    
    # Armazena no ChromaDB
    print("\nArmazenando no ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Recria a coleção se já existir
    try:
        client.delete_collection("novatech")
    except:
        pass
    
    collection = client.create_collection("novatech")
    
    collection.add(
        ids=[f"chunk_{i}" for i in range(len(all_chunks))],
        embeddings=embeddings.tolist(),
        documents=texts,
        metadatas=[{
            "source": chunk["source"],
            "section": chunk["section"]
        } for chunk in all_chunks]
    )
    
    print(f"✓ {len(all_chunks)} chunks armazenados no ChromaDB.")

if __name__ == "__main__":
    ingest()