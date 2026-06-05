# Análise de Problemas — Pipeline RAG NovaTech

## Resultados dos 8 Testes
(métrica: chunk correto deve estar no top 2)

| # | Pergunta | Retrieval | Resposta | Armadilha |
|---|---|---|---|---|
| 1 | Prazo de devolução | ⚠️ Parcial | ⚠️ Valor correto, fonte errada | — |
| 2 | Carga perigosa | ❌ Incorreto | ❌ FAQ como fonte principal | Inversão de regra |
| 3 | SLA Gold | ⚠️ Parcial | ⚠️ Valores corretos, fonte errada | — |
| 4 | Frete Manaus | ✅ Correto | ⚠️ Parcial — perdeu multiplicador | — |
| 5 | Multiplicador Sudeste | ❌ Incorreto | ❌ Valor errado (v1 em vez de v2) | — |
| 6 | SLA Platinum | ✅ Correto | ✅ Informou que tier não existe | Tier inexistente |
| 7 | Frete 300kg Salvador | ⚠️ Sem cobertura | ✅ Disse que não encontrou | Sem cobertura |
| 8 | Cargas não devolvíveis | ❌ Incorreto | ⚠️ Orientou consultar POL-001 | Inversão de regra |

---

## Problema 1 — FAQ domina retrieval para perguntas críticas

**Afetou:** testes 2, 3 e 8

**O que aconteceu:** para perguntas sobre devolução de carga
perigosa e SLA, o pipeline retornou chunks do FAQ-atendimento
no topo, suprimindo os documentos normativos (POL-001 e SLA-2024).
No teste 8, o retrieval falhou completamente — POL-001 seção 3.2
não chegou nos chunks, impedindo o modelo de citar a regra explícita.

**Causa:** o modelo all-MiniLM-L6-v2 foi treinado
predominantemente em inglês. Ele alinha melhor com a linguagem
coloquial do FAQ ("cliente perguntou se pode devolver") do que
com a linguagem formal dos documentos normativos ("não são
elegíveis para devolução pelo processo padrão").

**Impacto:** respostas baseadas em fonte informal com aparência
de confiança alta. Para SLA, isso é crítico — SLA é compromisso
contratual, não pode ser referenciado a partir de FAQ.
Para regras de exceção (carga perigosa), a inversão da regra
pode causar orientação incorreta ao cliente.

**Proposta de correção:**
1. Adicionar metadado `tipo` em cada chunk durante a ingestão:
   - `normativo` → POL-XXX
   - `procedimento` → PROC-XXX
   - `sla` → SLA-XXXX
   - `faq` → FAQ-Atendimento
2. No retrieval, buscar primeiro em chunks com tipo `normativo`,
   `procedimento` e `sla`. Usar FAQ apenas como fallback quando
   nenhum documento formal cobrir a pergunta.
3. Substituir o modelo de embedding por
   `paraphrase-multilingual-MiniLM-L12-v2`, treinado em 50
   idiomas incluindo português — melhora o alinhamento com
   linguagem formal dos documentos normativos.

---

## Problema 2 — Versão antiga prevalece sobre versão nova

**Afetou:** teste 5

**O que aconteceu:** para a pergunta sobre multiplicador do
Sudeste, o pipeline retornou o chunk do PROC-042 v1 (posição 3,
score 0.0126) antes do PROC-042 v2 (posição 4, score 0.0107).
O modelo usou o chunk que veio primeiro — valor 1.0 (errado)
em vez de 1.1 (correto).

**Causa:** v1 e v2 têm conteúdo semanticamente idêntico
(mesma estrutura, mesmos campos, só valores diferentes).
O modelo de embedding não consegue distinguir versões por
similaridade semântica — os scores ficam quase idênticos e
a ordem é arbitrária.

**Impacto:** atendente recebe multiplicador desatualizado
e pode repassar valor errado ao cliente.

**Proposta de correção:**
1. Adicionar metadados `versao` e `data_emissao` nos chunks
   durante a ingestão.
2. No retrieval, quando dois chunks do mesmo procedimento
   forem recuperados, descartar automaticamente o de
   `data_emissao` mais antiga.
3. Alternativamente: no pipeline de ingestão, não indexar
   documentos marcados como obsoletos — exige processo de
   curadoria da documentação antes da ingestão.

---

## Avaliação das Armadilhas Intencionais do Anexo B

### Armadilha 1 — Tier inexistente (Platinum)
**Resultado:** ✅ Tratada corretamente
O modelo informou que o tier Platinum não existe, listou os
tiers corretos (Gold, Silver, Standard) e não inventou SLA.
O chunk do FAQ item 15 foi suficiente para tratar este caso.

### Armadilha 2 — Pergunta sem cobertura (frete < 500kg)
**Resultado:** ✅ Tratada corretamente
O modelo disse explicitamente que a documentação disponível
não cobre fretes abaixo de 500kg e orientou escalar ao
supervisor. Guardrail 4 funcionou conforme esperado.

### Armadilha 3 — Inversão de regra (cargas não devolvíveis)
**Resultado:** ⚠️ Parcial
O modelo não inverteu a regra (não disse que cargas perigosas
podem ser devolvidas), mas também não pôde citar a regra
explícita porque o POL-001 seção 3.2 não chegou nos chunks.
Orientou corretamente consultar o POL-001, mas a resposta
depende do atendente buscar manualmente — não resolve o
atendimento em tempo real.
Raiz do problema: falha de retrieval (Problema 1).

---

## Conclusão

O pipeline é funcional para casos simples, mas apresenta
fragilidades estruturais que precisam ser resolvidas antes
de ir para produção:

- Sem priorização por tipo de fonte, documentos informais
  contaminam respostas críticas.
- Sem controle de versão no retrieval, versões antigas
  competem com versões novas com scores equivalentes.
- O modelo de embedding em inglês prejudica o alinhamento
  com documentos formais em português.

Ambos os problemas principais são de **engenharia de dados**,
não de modelo — confirmando que RAG é um sistema de pipeline,
não apenas uma chamada de API.