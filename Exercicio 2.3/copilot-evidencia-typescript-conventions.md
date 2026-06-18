# Evidencia de Geracao com Copilot - typescript-conventions

## Contexto
- Data: 2026-06-18
- Ferramenta: GitHub Copilot Chat (modelo GPT-5.3-Codex)
- Artefato alvo: Exercicio 2.3/skills/foundation/typescript-conventions.md

## Prompt recebido no chat
"Leia o arquivo Exercicio 2.3/skills-strategy.md para entender a estrategia de skills do projeto NovaTech Assistant.

Com base nisso, crie o arquivo Exercicio 2.3/skills/foundation/typescript-conventions.md

Esta e a skill Foundation mais importante - base para todas as outras.
O arquivo deve conter:
1. CONTEXTO: quando esta skill se aplica
2. REGRAS PRESCRITIVAS (DEVE/NAO DEVE) para TypeScript strict mode,
   imports, naming, null safety, async/await, logging e env vars
3. EXEMPLOS concretos DO/DON'T com codigo real
4. ANTI-PADROES: 3 coisas que LLMs geram errado sem este guidance
5. DEPENDENCIAS: outras skills que devem ser lidas antes"

## Evidencia de iteracao real (tooling)
1. Leitura de contexto do repositorio:
   - read_file em Exercicio 2.3/skills-strategy.md (linhas 1-260).
   - list_dir em Exercicio 2.3/skills/foundation (pasta vazia no momento).
2. Geracao do artefato:
   - create_file em Exercicio 2.3/skills/foundation/typescript-conventions.md.
3. Verificacao posterior de consistencia:
   - hash SHA256 calculado do arquivo gerado.
   - contagem de linhas/palavras/caracteres.

## Saida documentada
- Arquivo gerado: Exercicio 2.3/skills/foundation/typescript-conventions.md
- Hash SHA256: 56514D31199BB913E7D0FF29CCB3A6FE48A76C68C47564B2483BC1A161E2762F
- Estatisticas: 221 linhas, 1180 palavras, 8413 caracteres

## Resultado
A skill foi criada via interacao real com Copilot, com prompt explicito, iteracao registrada e saida verificavel por hash.
