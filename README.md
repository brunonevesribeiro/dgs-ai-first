# DGS AI First - Entregas de Cenarios

## Visao geral
Este repositorio foi criado para registrar e entregar as praticas da formacao **DGS AI First**.

As praticas aplicam os conceitos da trilha em atividades estruturadas por cenario, com base comum para todos os papeis e execucao especifica por papel.

## Materiais da trilha
O documento **Trilha de Formacao - DGS AI First.pdf** concentra os links de todos os materiais da trilha (video e texto).

- Fonte unica dos conteudos da formacao
- Nao havera novo material alem do que ja consta no PDF

## Cronograma de entrega
- **Cenario 1:** 06/06
- **Cenario 2:** 18/06
- **Cenario 3:** 27/06

## Pos-formacao
Apos o periodo de formacao, havera uma prova de certificacao baseada nos conhecimentos trabalhados nos cenarios.

Objetivo: aferir prontidao para o novo **SDLC AI First**.

## Estrategia de branches
Cada cenario deve ser desenvolvido e entregue em sua propria branch:

- `cenario-1`
- `cenario-2`
- `cenario-3`

## Fluxo recomendado de trabalho
Para cada cenario:

1. Atualize a branch principal local.
2. Crie a branch do cenario.
3. Desenvolva as atividades do cenario.
4. Faça commit das entregas.
5. Envie para o remoto.
6. Abra PR da branch do cenario para revisao.

### Exemplo de comandos Git
```bash
git checkout main
git pull

git checkout -b cenario-1
# ... desenvolver atividades ...
git add .
git commit -m "Entrega cenario 1"
git push --set-upstream origin cenario-1
```

Repita o mesmo fluxo para `cenario-2` e `cenario-3`.

## Estrutura de conteudo
Organize os arquivos de cada entrega de forma clara, mantendo rastreabilidade do que foi produzido por cenario.

Sugestao:
- separar artefatos por cenario
- manter instrucoes e contexto junto das entregas
- registrar decisoes tecnicas relevantes no proprio repositorio

## Responsabilidade de entrega
Cada pessoa deve garantir que:
- o conteudo entregue corresponde ao cenario correto
- o prazo oficial do cenario foi atendido
- a branch de entrega esta atualizada e publicada no remoto
