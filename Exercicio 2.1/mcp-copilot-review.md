# Revisão do Output do Copilot — .mcp/mcp.json

## O que o Copilot gerou
Estrutura básica com 5 servers identificados corretamente, 
mas usando formato incorreto (`"type": "github"` em vez do 
protocolo MCP real).

## O que precisou ser ajustado

| Item | Gerado pelo Copilot | Correto |
|---|---|---|
| Formato de server público | `"type": "github"` | `"type": "stdio"` com `command` e `args` |
| Servers customizados | `"type": "custom"` com `endpoint` | `"type": "url"` com `headers` para auth |
| Variáveis de ambiente | Ausentes | Todas as credenciais via `${VAR}` |
| Autenticação | Não configurada | `x-functions-key` para Azure Functions |

## Conclusão
O Copilot acertou a estrutura de quais servers incluir, mas não 
conhece o protocolo MCP real — gerou um formato inventado. 
O arquivo final foi corrigido manualmente seguindo a especificação 
MCP e o exemplo do Anexo C do projeto.