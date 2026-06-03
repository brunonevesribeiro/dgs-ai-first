# Interação com o Assistente de Atendimento NovaTech

**Data:** 2026-06-03  
**Contexto:** Simulação de uso do Assistente de Atendimento da NovaTech por um atendente de suporte ao cliente.

---

## Configuração do Sistema

O assistente foi configurado com as seguintes regras e documentação:

### Documentação disponível (chunks):

- **Chunk A — POL-001, seção 3.2:** Política de devolução (7 dias úteis, exceto cargas perigosas classes 1 a 6 ANTT)
- **Chunk B — SLA-2024:** SLAs por categoria de cliente (Gold, Silver, Standard)
- **Chunk C — PROC-042-v2, seção 2:** Multiplicadores regionais de frete para cargas acima de 500kg
- **Chunk D — PROC-042 v1, seção 2.1:** Multiplicadores regionais (versão anterior — adicionado durante a interação)

### Guardrails configurados:
1. Sempre citar a fonte
2. Nunca inventar valores ou prazos
3. Exceções têm prioridade sobre regras gerais
4. Quando não encontrar resposta, informar e escalar
5. Informar conflito entre fontes e apresentar ambas as versões

---

## Registro das Interações

---

### Pergunta 1
**Atendente:** Qual o prazo de devolução para carga perigosa?

**Assistente:**

**Resposta:** Cargas classificadas como perigosas (classes 1 a 6 da ANTT) **não são elegíveis para devolução**. A política de devolução em 7 dias úteis expressamente exclui esse tipo de carga.

**Fonte:** POL-001, seção 3.2

**Atenção:** Esta é uma exceção à regra geral de devolução. Oriente o cliente que, para cargas perigosas, não há prazo de devolução previsto na política — o caso deve ser escalado ao supervisor para tratamento específico.

---

### Pergunta 2
**Atendente:** Meu cliente é Gold, qual o SLA de resolução?

**Assistente:**

**Resposta:** Para clientes Gold, o SLA de resolução é de **até 24 horas**, com resposta inicial em até 2 horas.

**Fonte:** SLA-2024

---

### Pergunta 3
**Atendente:** Quanto custa o frete para 600kg para Manaus?

**Assistente:**

**Resposta:** Para 600kg com destino a Manaus (região Norte), aplica-se frete especial com o seguinte cálculo:

**Valor base × 1,8** (multiplicador regional Norte)

Porém, o **valor base** não consta nos chunks disponíveis para esta consulta. Não é possível informar o valor final sem esse dado.

**Fonte:** PROC-042-v2, seção 2

**Atenção:** Para obter o valor base e calcular o custo exato, consulte a tabela de tarifas vigente ou escale para o supervisor antes de repassar o valor ao cliente.

---

### Evento: Adição de novo chunk

**Atendente adicionou o Chunk D:**

> **Chunk D — PROC-042 v1, seção 2.1:**
> "Multiplicadores regionais: Sul 1.2, Sudeste 1.0, Centro-Oeste 1.3, Nordeste 1.4, Norte 1.6."

**Assistente:** Chunk D registrado. Identificou conflito entre documentos sobre os multiplicadores regionais:

| Região | PROC-042-v2, seção 2 | PROC-042 v1, seção 2.1 |
|---|---|---|
| Sul | 1,3 | 1,2 |
| Sudeste | 1,1 | 1,0 |
| Norte | 1,8 | 1,6 |
| Nordeste | 1,5 | 1,4 |
| Centro-Oeste | 1,4 | 1,3 |

**Orientação emitida:** Não repassar nenhum multiplicador ao cliente sem confirmar com o supervisor qual versão está vigente.

---

### Pergunta 6
**Atendente:** Qual o multiplicador de frete para a região Norte?

**Assistente:**

**Resposta:** Há **conflito entre documentos** para o multiplicador da região Norte:

- **1,8** — conforme PROC-042-v2, seção 2 (versão mais recente)
- **1,6** — conforme PROC-042 v1, seção 2.1 (versão anterior)

**Fonte:** PROC-042-v2, seção 2 e PROC-042 v1, seção 2.1

**Atenção:** Não repasse nenhum valor ao cliente antes de confirmar com o supervisor qual versão do documento está vigente.

---

### Pergunta 7
**Atendente:** Qual a política para carga danificada em trânsito?

**Assistente:**

Não encontrei essa informação na documentação disponível.

Os chunks fornecidos (POL-001, SLA-2024, PROC-042-v2 e PROC-042 v1) não contêm nenhuma política referente a carga danificada em trânsito.

**Orientação:** Escale o caso ao supervisor antes de repassar qualquer informação ao cliente.

---

## Observações sobre o Comportamento do Assistente

| Guardrail | Situação testada | Comportamento observado |
|---|---|---|
| Citar fonte | Todas as respostas | Fonte sempre informada |
| Não inventar valores | Pergunta sobre custo do frete (valor base ausente) | Informou apenas o multiplicador disponível e orientou escalada |
| Exceções têm prioridade | Prazo de devolução para carga perigosa | Apresentou a exceção antes da regra geral |
| Informar ausência de dados | Política para carga danificada em trânsito (2x) | Declarou explicitamente não ter a informação e orientou escalada |
| Conflito entre fontes | Adição do Chunk D com multiplicadores divergentes | Identificou, tabelou e alertou sobre o conflito; orientou confirmação com supervisor |
