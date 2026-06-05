# 8 testes — 5 originais + 3 armadilhas intencionais do Anexo B
# Métrica ajustada: chunk correto deve estar no top 2, não apenas no top 5

from search import search
from prompt import build_prompt

GABARITO = {
    "Qual o prazo de devolução?": {
        "chunks_esperados": ["3.1", "3.2"],
        "docs_esperados": ["POL-001-politica-devolucao.md"],
        "armadilha": None
    },
    "Posso devolver carga perigosa?": {
        "chunks_esperados": ["3.2"],
        "docs_esperados": ["POL-001-politica-devolucao.md"],
        "armadilha": "Inversão de regra — resposta correta é NÃO pode devolver"
    },
    "Qual o SLA do cliente Gold?": {
        "chunks_esperados": ["2"],
        "docs_esperados": ["SLA-2024-tabela-sla-clientes.md"],
        "armadilha": None
    },
    "Quanto custa o frete para 600kg para Manaus?": {
        "chunks_esperados": ["2.1", "2"],
        "docs_esperados": ["PROC-042-v2-frete-especial-revisado.md"],
        "armadilha": None
    },
    "Qual o multiplicador para o Sudeste?": {
        "chunks_esperados": ["2.1"],
        "docs_esperados": ["PROC-042-v2-frete-especial-revisado.md"],
        "armadilha": None
    },
    # --- ARMADILHAS INTENCIONAIS DO ANEXO B ---
    "Qual o SLA do cliente Platinum?": {
        "chunks_esperados": ["1"],
        "docs_esperados": ["SLA-2024-tabela-sla-clientes.md"],
        "armadilha": "Tier inexistente — resposta correta é informar que Platinum não existe"
    },
    "Quanto custa o frete para 300kg para Salvador?": {
        "chunks_esperados": [],
        "docs_esperados": [],
        "armadilha": "Sem cobertura — resposta correta é dizer que não encontrou"
    },
    "Quais cargas não podem ser devolvidas?": {
        "chunks_esperados": ["3.2"],
        "docs_esperados": ["POL-001-politica-devolucao.md"],
        "armadilha": "Inversão de regra — deve citar explicitamente cargas perigosas como NÃO elegíveis"
    }
}

def avaliar_retrieval(chunks_retornados, gabarito):
    """
    Métrica ajustada: chunk correto deve estar no top 2.
    Sem cobertura esperada = verifica se modelo disse que não encontrou.
    """
    # Caso especial: pergunta sem cobertura documental
    if not gabarito["docs_esperados"]:
        return "⚠️  SEM COBERTURA — verificar se modelo respondeu 'não encontrei'"

    docs_top2 = [c["source"] for c in chunks_retornados[:2]]
    secoes_top2 = [c["section"] for c in chunks_retornados[:2]]

    doc_no_top2 = any(
        doc in docs_top2
        for doc in gabarito["docs_esperados"]
    )

    secao_no_top2 = any(
        any(esperado in secao for secao in secoes_top2)
        for esperado in gabarito["chunks_esperados"]
    )

    if doc_no_top2 and secao_no_top2:
        return "✅ CORRETO — doc e seção corretos no top 2"
    elif doc_no_top2:
        return "⚠️  PARCIAL — doc correto no top 2, seção errada"
    else:
        return "❌ INCORRETO — doc correto não está no top 2"

def run_tests():
    print("\n" + "="*60)
    print("RESULTADOS DOS 8 TESTES — PIPELINE RAG NOVATECH")
    print("(métrica: chunk correto deve estar no top 2)")
    print("="*60)

    prompts_gerados = []

    for pergunta, gabarito in GABARITO.items():
        print(f"\n{'─'*60}")
        print(f"PERGUNTA: {pergunta}")
        if gabarito["armadilha"]:
            print(f"⚠️  ARMADILHA: {gabarito['armadilha']}")
        print(f"Esperado: {gabarito['docs_esperados']} | "
              f"Seções: {gabarito['chunks_esperados']}")
        print()

        chunks = search(pergunta, n_results=5)

        for i, chunk in enumerate(chunks):
            marcador = "→" if i < 2 else " "
            print(f"  {marcador}[{i+1}] Score: {chunk['score']:.4f} | "
                  f"{chunk['source']} | {chunk['section'][:50]}")

        resultado = avaliar_retrieval(chunks, gabarito)
        print(f"\n  Avaliação retrieval: {resultado}")

        prompt = build_prompt(pergunta, chunks[:3])
        prompts_gerados.append({
            "pergunta": pergunta,
            "armadilha": gabarito["armadilha"],
            "prompt": prompt,
            "resultado": resultado
        })

    # Salva prompts
    with open("prompts_para_claude.txt", "w", encoding="utf-8") as f:
        for item in prompts_gerados:
            f.write(f"\n{'='*60}\n")
            f.write(f"PERGUNTA: {item['pergunta']}\n")
            if item["armadilha"]:
                f.write(f"ARMADILHA: {item['armadilha']}\n")
            f.write(f"AVALIAÇÃO RETRIEVAL: {item['resultado']}\n")
            f.write(f"{'─'*60}\n")
            f.write(item["prompt"])
            f.write("\n")

    print(f"\n{'='*60}")
    print("Prompts salvos em: prompts_para_claude.txt")

if __name__ == "__main__":
    run_tests()