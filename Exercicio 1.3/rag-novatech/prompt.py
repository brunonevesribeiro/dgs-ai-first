# Montagem do prompt completo para o LLM
# Combina system prompt (v2) + chunks recuperados + pergunta

def build_prompt(query, chunks):
    """
    Monta o prompt completo pronto para colar no Claude.
    """

    system_prompt = """# IDENTIDADE
Você é o Assistente de Atendimento da NovaTech, empresa de logística.
Seu papel é apoiar os atendentes respondendo perguntas sobre 
procedimentos, políticas, SLAs e regras de frete com base 
exclusivamente na documentação oficial fornecida.

# REGRAS
1. CITE SEMPRE A FONTE: nome do documento e seção de origem.
2. NUNCA INVENTE VALORES OU PRAZOS: se não estiver nos chunks, não mencione.
3. EXCEÇÕES TÊM PRIORIDADE: verifique exceções antes de responder a regra geral.
4. QUANDO NÃO ENCONTRAR: diga explicitamente e oriente escalar ao supervisor.
5. CONFLITO ENTRE FONTES: apresente ambas as versões e oriente confirmação.
6. HISTÓRICO: priorize chunks sobre histórico de conversa.

# FORMATO DE RESPOSTA
**Resposta:** [resposta direta]
**Fonte:** [documento + seção]
**Atenção:** [exceção, limitação ou contradição, se houver]"""

    # Monta bloco de chunks
    chunks_block = "\n\n# DOCUMENTAÇÃO DISPONÍVEL\n"
    for i, chunk in enumerate(chunks):
        chunks_block += f"""
[Chunk {i+1}]
Fonte: {chunk['source']} | Seção: {chunk['section']}
Conteúdo: {chunk['text'][:500]}
"""

    # Monta prompt final
    prompt = f"{system_prompt}{chunks_block}\n# PERGUNTA DO ATENDENTE\n{query}"

    return prompt


def print_prompt(query, chunks):
    prompt = build_prompt(query, chunks)
    print("\n" + "="*60)
    print("PROMPT MONTADO:")
    print("="*60)
    print(prompt)
    print("="*60)
    return prompt


if __name__ == "__main__":
    # Teste com chunks simulados
    test_chunks = [
        {
            "text": "O cliente pode solicitar devolução em até 7 dias úteis.",
            "source": "POL-001-politica-devolucao.md",
            "section": "### 3.1. Prazo geral"
        }
    ]
    print_prompt("Qual o prazo de devolução?", test_chunks)