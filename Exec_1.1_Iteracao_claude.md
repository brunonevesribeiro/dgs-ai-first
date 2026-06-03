# Cenario 1 - Iteracao com Claude

Use este arquivo para registrar cada interação com Claude em blocos padronizados.

## Contexto

- Data: 2026-06-03
- Objetivo: documentar prompts enviados e respostas recebidas

## Interacoes

### Interacao 01

#### Prompt

Você é um desenvolvedor sênior revisando a viabilidade técnica de um pipeline de RAG.

Contexto do projeto:

- Cliente: NovaTech, empresa de logística com 1.200 funcionários
- Objetivo: assistente de IA para equipe de atendimento (45 pessoas) consultar documentação interna em linguagem natural
- Fontes de dados:
	- SharePoint: ~800 documentos PDF e DOCX (atualização mensal)
	- Confluence: ~400 páginas wiki HTML (atualização semanal)
	- Pasta de rede: ~50 planilhas XLSX (atualização mensal)
- Volume: 320 chamados/dia, ~60% envolvem consulta a documentação
- Stack prevista: Azure AI Search + Azure OpenAI (GPT-4o, janela de 128K tokens)

Desafios identificados nos documentos:

- PDFs incluem tabelas complexas (15+ colunas), fluxogramas como imagens, e ~15% escaneados (precisam de OCR)
- Wiki tem links internos e macros customizadas
- Planilhas têm fórmulas interdependentes
- Existem documentos contraditórios (duas versões do mesmo procedimento sem indicação de qual é vigente)

Para cada tipo de fonte (PDFs com tabelas, PDFs escaneados, wiki com links, planilhas), analise:

1. O desafio específico para o pipeline de RAG
2. Como isso afeta a qualidade das respostas
3. Uma estratégia de tratamento concreta

#### Resposta Claude

## Revisao de Viabilidade Tecnica - Pipeline RAG NovaTech

### Visao Geral do Cenario

Antes de entrar nos desafios por fonte, vale contextualizar o perfil de carga: **~192 consultas/dia** com envolvimento de documentacao (60% de 320 chamados). Isso e volume baixo o suficiente para priorizar qualidade de resposta sobre throughput, o que influencia diretamente as escolhas arquiteturais abaixo.

---

### 1. PDFs com Tabelas Complexas (15+ colunas)

#### Desafio para o Pipeline

Parsers de PDF padrao (PyMuPDF, pdfplumber) serializam tabelas linha a linha em texto plano, destruindo a estrutura bidimensional. Uma tabela de frete com 15 colunas - origem, destino, modal, peso, dimensoes, prazo, seguro, etc. - vira um bloco de texto sem relacao semantica entre cabecalho e celula apos chunking.

O problema se agrava com **cell merging**, tabelas que quebram entre paginas, e cabecalhos repetidos em sub-secoes. O chunk resultante e semanticamente opaco para o retriever.

#### Impacto na Qualidade

O modelo recebe contexto como "SP RJ Aereo 10kg 50x40x30 3 dias 1,5%" sem saber o que cada valor representa. Respostas ficam imprecisas ou o modelo alucina relacoes entre colunas. Perguntas do tipo *"qual o prazo para envio aereo de SP para RJ com 10kg?"* tem alta chance de retornar valores trocados.

#### Estrategia de Tratamento

**Extracao estruturada com conversao para Markdown + metadados semanticos:**

```python
import pdfplumber
import pandas as pd

def extract_table_as_markdown(pdf_path: str, page_num: int) -> list[dict]:
	chunks = []
	with pdfplumber.open(pdf_path) as pdf:
		page = pdf.pages[page_num]
		tables = page.extract_tables()

		for table in tables:
			df = pd.DataFrame(table[1:], columns=table[0])

			# Cada linha vira um chunk independente com contexto completo
			for _, row in df.iterrows():
				row_text = " | ".join(
					f"{col}: {val}"
					for col, val in row.items()
					if val and str(val).strip()
				)
				chunks.append({
					"content": row_text,
					"metadata": {
						"source": pdf_path,
						"type": "table_row",
						"table_headers": list(df.columns),
						"page": page_num
					}
				})
	return chunks

# Resultado por linha:
# "origem: SP | destino: RJ | modal: Aereo | peso_max: 10kg | prazo: 3 dias"
```

Para tabelas com **cell merging** (estruturas hierarquicas), usar **Camelot** com `flavor='lattice'` que detecta bordas e preserva a hierarquia. Tabelas multi-pagina devem ser detectadas e reunidas antes do chunking via heuristica de cabecalho repetido.

**Complemento:** indexar tambem uma representacao Markdown completa da tabela como chunk de "visao geral" para queries que precisam comparar multiplas linhas.

---

### 2. PDFs Escaneados (~15% do acervo ~= 120 documentos)

#### Desafio para o Pipeline

PDFs escaneados sao imagens embutidas - sem camada de texto, o parser retorna string vazia ou lixo de metadados. O Azure AI Search nao indexa o conteudo visual por padrao. Sao **~120 documentos invisiveis** para o RAG sem tratamento previo.

O risco adicional e silencioso: o pipeline nao falha, simplesmente ignora o documento e o modelo responde sem aquele contexto, sem nenhum aviso ao usuario.

#### Impacto na Qualidade

Documentos criticos potencialmente ausentes do indice sem qualquer alerta. Se um procedimento importante for um escaneado, o assistente respondera *"nao encontrei informacoes sobre isso"* - ou pior, usara um documento desatualizado que esteja indexado, gerando resposta incorreta com aparencia de confianca.

#### Estrategia de Tratamento

**Pipeline de OCR com deteccao automatica e validacao de qualidade:**

```python
import fitz  # PyMuPDF
from azure.ai.formrecognizer import DocumentAnalysisClient

def classify_and_process_pdf(pdf_path: str) -> dict:
	doc = fitz.open(pdf_path)

	text_density = sum(
		len(page.get_text().strip())
		for page in doc
	) / len(doc)

	# Documentos escaneados tem densidade de texto proxima de zero
	is_scanned = text_density  dict:
	client = DocumentAnalysisClient(
		endpoint=AZURE_FORM_RECOGNIZER_ENDPOINT,
		credential=AzureKeyCredential(KEY)
	)

	with open(pdf_path, "rb") as f:
		poller = client.begin_analyze_document("prebuilt-read", f)

	result = poller.result()

	# Validacao de confianca - rejeitar OCR de baixa qualidade
	avg_confidence = sum(
		word.confidence
		for page in result.pages
		for word in page.words
	) / sum(len(p.words) for p in result.pages)

	return {
		"content": result.content,
		"ocr_confidence": avg_confidence,
		"needs_review": avg_confidence
```

```python
from atlassian import Confluence
from bs4 import BeautifulSoup
import re

class ConfluenceProcessor:
	def __init__(self, confluence_client: Confluence):
		self.client = confluence_client
		self.page_cache = {}

	def process_page(self, page_id: str, depth: int = 0) -> dict:
		if depth > 2:  # Limite para evitar loops
			return None

		page = self.client.get_page_by_id(
			page_id,
			expand='body.storage,metadata.labels,version'
		)

		content = self._clean_confluence_html(page['body']['storage']['value'])
		links = self._extract_internal_links(content)

		# Resolucao de dependencias: incluir resumo das paginas linkadas
		linked_summaries = {}
		for link_id, link_text in links.items():
			linked_page = self.process_page(link_id, depth + 1)
			if linked_page:
				linked_summaries[link_text] = linked_page['content'][:500]

		return {
			"content": content,
			"linked_context": linked_summaries,
			"labels": page['metadata']['labels'],
			"last_modified": page['version']['when'],
			"metadata": {
				"page_id": page_id,
				"type": "confluence_wiki"
			}
		}

	def _clean_confluence_html(self, html: str) -> str:
		soup = BeautifulSoup(html, 'html.parser')

		# Remover macros mas preservar conteudo relevante
		macro_content_map = {
			'ac:structured-macro[ac:name="note"]':
				lambda m: f"[NOTA: {m.get_text()}]",
			'ac:structured-macro[ac:name="warning"]':
				lambda m: f"[ATENCAO: {m.get_text()}]",
			'ac:structured-macro[ac:name="status"]':
				lambda m: f"[STATUS: {m.get('ac:parameter', 'desconhecido')}]",
		}

		for selector, transformer in macro_content_map.items():
			for macro in soup.select(selector):
				macro.replace_with(transformer(macro))

		return soup.get_text(separator='\n', strip=True)
```

**Ponto critico:** labels do Confluence como `deprecado`, `rascunho`, `revisar` devem ser extraidas como metadados e usados como **filtro de boost negativo** no Azure AI Search - documentos com label `deprecado` recebem score penalizado ou sao excluidos do indice de producao.

---

### 4. Planilhas XLSX com Formulas Interdependentes

#### Desafio para o Pipeline

Formulas como `=VLOOKUP(A2, 'Tabela_Fretes'!A:F, 3, FALSE)` nao tem valor - sao referencias que so fazem sentido em tempo de execucao do Excel. Um chunk contendo `"Prazo: =VLOOKUP(A2,'Tabela_Fretes'!A:F,3,FALSE)"` e inutil para o modelo e para o retriever semantico.

Planilhas tambem tem **contexto distribuido**: a aba "Dashboard" mostra KPIs calculados a partir de "Dados_Brutos", que referencia "Parametros". Tratar abas isoladamente perde a semantica do negocio.

#### Impacto na Qualidade

O modelo recebe formulas literais em vez de valores e relacoes de negocio. Incapaz de responder *"qual e o prazo atual para frete internacional acima de 100kg?"* porque o valor esta em uma celula calculada por VLOOKUP referenciando outra aba que foi chunkada separadamente - ou ignorada.

#### Estrategia de Tratamento

**Resolucao de formulas em tempo de ingestao + modelagem de relacoes entre abas:**

```python
import openpyxl
from openpyxl.utils import get_column_letter

def process_xlsx_for_rag(file_path: str) -> list[dict]:
	# xlwings ou openpyxl com data_only=True resolve formulas
	# (requer que o arquivo tenha sido salvo com valores calculados)
	wb = openpyxl.load_workbook(file_path, data_only=True)

	chunks = []
	sheet_summaries = {}

	for sheet_name in wb.sheetnames:
		ws = wb[sheet_name]
		sheet_data = extract_sheet_with_context(ws, sheet_name)
		sheet_summaries[sheet_name] = sheet_data['summary']
		chunks.extend(sheet_data['chunks'])

	# Chunk de metadados da planilha completa
	chunks.append({
		"content": f"Planilha: {file_path}\n" +
				   "\n".join(f"Aba '{k}': {v}"
							 for k, v in sheet_summaries.items()),
		"metadata": {
			"source": file_path,
			"type": "xlsx_overview",
			"sheets": list(wb.sheetnames)
		}
	})

	return chunks

def extract_sheet_with_context(ws, sheet_name: str) -> dict:
	headers = [cell.value for cell in ws[1] if cell.value]
	rows_as_text = []

	for row in ws.iter_rows(min_row=2, values_only=True):
		if not any(row):  # Pular linhas vazias
			continue

		row_text = " | ".join(
			f"{headers[i]}: {val}"
			for i, val in enumerate(row)
			if i
```

```python
from difflib import SequenceMatcher
from datetime import datetime

def detect_duplicate_documents(new_doc: dict, index: list[dict]) -> list[dict]:
	candidates = []

	for existing in index:
		# Similaridade de titulo/nome
		title_similarity = SequenceMatcher(
			None,
			new_doc['title'].lower(),
			existing['title'].lower()
		).ratio()

		if title_similarity > 0.85:
			candidates.append({
				"existing_doc": existing,
				"title_similarity": title_similarity,
				"date_existing": existing['metadata'].get('last_modified'),
				"date_new": new_doc['metadata'].get('last_modified')
			})

	return candidates
```

**Camada 2 - Politica de indexacao com resolucao humana:**

```text
SE documento novo tem similaridade > 85% com documento existente:
	SE data_novo > data_existente E fonte_novo == fonte_existente:
		-> Substituir automaticamente (nova versao da mesma fonte)
	SENAO:
		-> Colocar em quarentena + notificar equipe gestora
		-> Nao indexar ate resolucao humana
		-> SLA de resolucao: 5 dias uteis
```

**Camada 3 - Transparencia para o usuario final:**

Quando o modelo retornar resposta, incluir no prompt de sistema:

```text
Se voce encontrar informacoes contraditorias entre documentos,
NAO escolha uma arbitrariamente. Informe explicitamente:
"Encontrei versoes conflitantes deste procedimento: [Doc A, data X]
e [Doc B, data Y]. Recomendo verificar com o responsavel qual e a vigente."
```

---

### Resumo Executivo - Matriz de Risco e Esforco

FonteRisco sem tratamentoEsforco de implementacaoPrioridade
PDFs com tabelasAlto - respostas imprecisas em dados estruturadosMedio P1
Documentos contraditoriosAlto - respostas incorretas com aparencia de confiancaMedio P1
PDFs escaneadosMedio - documentos invisiveis silenciosamenteAlto P2
Wiki com links/macrosMedio - respostas incompletas em procedimentosMedio P2
Planilhas XLSXMedio-baixo - formulas nao resolvidasBaixo P3

**Veredicto de viabilidade:** o pipeline e tecnicamente viavel dentro do stack Azure proposto, mas requer um **estagio de pre-processamento robusto** antes da indexacao - essa e a camada que determinara 80% da qualidade final das respostas. A ingestao naive direto no Azure AI Search entregara um sistema de baixa confiabilidade.

---

### Interacao 02

#### Prompt

Agora faca a estimativa de tamanho da base em tokens:

- ~800 PDFs com media de 10 paginas cada (media de 300 palavras por pagina)
- ~400 paginas wiki com media de 1.500 palavras cada
- ~50 planilhas (estime 500 palavras de conteudo util cada, apos extrair valores calculados)

Use a regra pratica de 1 token ~= 0,75 palavras.

Depois analise o orcamento de contexto por query:

- Janela total: 128.000 tokens
- System prompt + guardrails: ~2.000 tokens
- Metadados do cliente + pergunta: ~200 tokens
- Historico de conversa (estimativa conservadora): ~2.000 tokens

Com o que sobra: quantos chunks de 500 tokens cabem por query? O que isso implica para a estrategia de retrieval?

#### Resposta Claude

## Estimativa de Tokens e Orcamento de Contexto - NovaTech

### Parte 1 - Tamanho Total da Base

#### Calculo por Fonte

**PDFs**

- 800 documentos x 10 paginas x 300 palavras = **2.400.000 palavras**
- Em tokens: 2.400.000 / 0,75 = **3.200.000 tokens**

**Wiki Confluence**

- 400 paginas x 1.500 palavras = **600.000 palavras**
- Em tokens: 600.000 / 0,75 = **800.000 tokens**

**Planilhas XLSX**

- 50 planilhas x 500 palavras = **25.000 palavras**
- Em tokens: 25.000 / 0,75 = **~33.000 tokens**

#### Consolidacao

FontePalavrasTokens% do totalPDFs2.400.0003.200.00078,4%Wiki Confluence600.000800.00019,6%Planilhas XLSX25.00033.0000,8%Documentos contraditorios25.00033.0000,8%**TOTAL****3.025.000****~4.033.000**100%

> **~4 milhoes de tokens no indice total** - isso e a base bruta antes de qualquer chunking ou filtragem.

---

### Parte 2 - Orcamento de Contexto por Query

#### Decomposicao da Janela de 128.000 tokens

```text
┌─────────────────────────────────────────────────────────────┐
│                  JANELA: 128.000 tokens                     │
├─────────────────────────────────────────────────────────────┤
│  System prompt + guardrails          2.000 t    (1,6%)      │
│  Metadados do cliente + pergunta       200 t    (0,2%)      │
│  Historico de conversa               2.000 t    (1,6%)      │
│  Resposta do modelo (reserva)        2.000 t    (1,6%)      │
├─────────────────────────────────────────────────────────────┤
│  DISPONIVEL PARA CHUNKS            121.800 t   (95,2%)      │
└─────────────────────────────────────────────────────────────┘
```

> Reservar ~2.000 tokens para a resposta do modelo e essencial - ignorar isso e um bug classico que causa truncamento silencioso da resposta em queries complexas.

#### Capacidade de Chunks por Query

```text
121.800 tokens disponiveis / 500 tokens por chunk = 243 chunks
```

**Cabem ate 243 chunks por query** - a primeira vista parece generoso. Mas esse numero precisa ser analisado com cuidado.

---

### Parte 3 - O que 243 Chunks Implicam para a Estrategia de Retrieval

#### O Problema: Tamanho nao e Qualidade

243 chunks de 500 tokens injetados cegamente representam **cobertura de apenas 6% do indice total** (~4.033 chunks totais se tudo fosse dividido em blocos de 500t). A questao real nao e *quantos* cabem, mas *quao bons* sao os que chegam ao modelo.

```text
Base total:   ~4.033.000 tokens / 500 = ~8.066 chunks indexados
Por query:     243 chunks injetados no contexto
Cobertura:     243 / 8.066 = ~3% da base por query
```

Isso impoe uma conclusao direta: **o retriever carrega todo o peso do sistema**. Se ele errar, o modelo nao tem como corrigir - o documento certo simplesmente nao estara no contexto.

#### Implicacao 1 - Retrieval em Dois Estagios e Obrigatorio

Usar apenas busca semantica (embedding cosine similarity) como unico mecanismo e insuficiente para esta base. A estrategia recomendada e **Retrieve -> Rerank**:

```text
					Query do usuario
						  |
			  ┌───────────▼────────────┐
			  │   ESTAGIO 1: RETRIEVE  │
			  │   Busca hibrida:       │
			  │   • Semantica (ANN)    │  -> top-K = 80 chunks
			  │   • BM25 (keyword)     │
			  └───────────┬────────────┘
						  │ 80 candidatos
			  ┌───────────▼────────────┐
			  │   ESTAGIO 2: RERANK    │
			  │   Cross-encoder        │  -> top-N = 20-30 chunks
			  │   (ex: Cohere Rerank   │     para injetar no prompt
			  │   ou Azure AI Search   │
			  │   semantic reranker)   │
			  └───────────┬────────────┘
						  │ 20-30 chunks de alta precisao
					 Prompt do modelo
```

O primeiro estagio prioriza recall (nao perder o documento relevante); o segundo prioriza precision (nao poluir o contexto com chunks irrelevantes).

#### Implicacao 2 - 243 Chunks e um Teto, Nao uma Meta

Injetar os 243 chunks possiveis e um anti-padrao com nome: **context stuffing**. O fenomeno *lost in the middle* (documentado em pesquisas da Stanford/Anthropic) mostra que modelos de linguagem degradam atencao em conteudo posicionado no meio de contextos longos.

Na pratica, o ponto otimo para este caso e bem mais conservador:

```text
┌────────────────────────────────────────────────────────┐
│  Capacidade teorica:    243 chunks  (121.800 tokens)   │
│  Zona de risco:         > 60 chunks (degradacao real)  │
│  Target recomendado:    20-30 chunks (10.000-15.000 t) │
│  Janela usada:          ~10% da capacidade disponivel  │
└────────────────────────────────────────────────────────┘
```

Usar 20-30 chunks de alta qualidade supera consistentemente 100+ chunks mediocres em benchmarks de QA sobre documentos corporativos.

#### Implicacao 3 - Chunking Adaptativo por Tipo de Fonte

Chunk fixo de 500 tokens e subotimo para esta base heterogenea. Cada fonte tem granularidade natural diferente:

FonteEstrategiaTamanho alvoMotivoPDFs - texto corridoSliding window400t + overlap 80tPreservar continuidade entre secoesPDFs - tabelas1 linha = 1 chunk50-150tGranularidade de busca por registroWiki ConfluencePor secao (h2/h3)300-600tRespeitar estrutura do documentoPlanilhas XLSX1 linha = 1 chunk + overview da aba100-200tIdem tabelas de PDF

O overlap de 80 tokens no sliding window e especialmente importante para PDFs: evita que uma resposta seja cortada no meio entre dois chunks adjacentes, o que causaria recuperacao incompleta de qualquer um dos dois.

#### Implicacao 4 - Query Routing Antes do Retrieval

Com 3 fontes de natureza muito distinta, um retriever unico contra o indice completo e ineficiente. Queries tem intencao detectavel:

```python
ROUTING_RULES = {
	"procedimento|processo|como fazer|passo a passo|fluxo":
		["pdfs", "wiki"],       # Documentacao de processos

	"prazo|valor|custo|tabela|frete|peso|dimensao":
		["xlsx", "pdfs"],       # Dados estruturados

	"politica|norma|regra|compliance|aprovacao":
		["pdfs", "wiki"],       # Documentacao normativa

	"o que e|definicao|conceito|glossario":
		["wiki"],                # Conhecimento enciclopedico
}
```

Um classificador leve (ate mesmo regex + embeddings de intencao) reduz o espaco de busca em 60-70% antes do retrieval, aumentando precision sem custo de recall - as fontes ignoradas por tipo raramente contem a resposta para aquele padrao de query.

---

### Sintese Executiva

DimensaoNumeroInterpretacaoBase total indexada~4.033.000 tokensIndexacao completa viavel, sem necessidade de particionamentoCobertura por query~3% da baseRetriever e o componente critico do sistemaChunks disponiveis/query243Teto teorico - nunca usar como alvoTarget operacional20-30 chunksEquilibrio qualidade/atencao do modeloOrcamento de contexto residual~111.800 tokens livresMargem para crescimento da base em ~2,7x sem mudanca arquitetural

A janela de 128K tokens do GPT-4o e confortavel para esta base atual e suporta crescimento organico por anos. O investimento de engenharia deve se concentrar no pipeline de pre-processamento (Parte 1 desta analise) e na qualidade do retrieval - nao na gestao de contexto, que nao e o gargalo aqui.

---

### Interacao 03

#### Prompt

Com base na analise anterior, recomende uma estrategia de chunking considerando:

1. O tipo de pergunta que o atendente vai fazer (ex: "qual o multiplicador de frete para o Norte?", "qual o SLA do cliente Gold?")
2. O efeito lost in the middle - informacao posicionada no meio de contextos longos e processada com menor qualidade
3. O fato de que tabelas de frete tem multiplas colunas interdependentes

Justifique por que chunking de tamanho fixo (512 tokens) seria inadequado para este caso especifico.

#### Resposta Claude

## Estratégia de Chunking para NovaTech — Análise e Recomendações

### Por que Chunking Fixo de 512 Tokens Falha Neste Caso

Antes de prescrever a solução, vale entender o diagnóstico com precisão. O chunking fixo tem um pressuposto implícito: **que a informação relevante tem distribuição uniforme no texto**. Para documentação corporativa heterogênea, esse pressuposto falha em pelo menos quatro dimensões:

#### Problema 1 — Quebra de Unidade Semântica em Tabelas

Considere uma tabela de multiplicadores de frete. Com chunking fixo de 512 tokens, o corte acontece em posição arbitrária determinada pelo contador de tokens, não pela estrutura dos dados:

```
CHUNK 1 (512t) — termina no meio da tabela:
┌─────────────────────────────────────────────────────────────┐
│ Tabela de Multiplicadores Regionais                         │
│ Região | Modal | Peso até | Mult. Base | Mult. Seguro | ... │
│ Norte  | Aéreo | 10kg     | 1.85       | 0.015        | ... │
│ Norte  | Aéreo | 30kg     | 1.72       | 0.015        | ... │
│ Norte  | Rodov | 10kg     | 1.

CHUNK 2 (512t) — começa sem cabeçalho:
45       | 0.012        | ... │
│ Norte  | Rodov | 30kg     | 1.31       | 0.012        | ... │
│ Nordest| Aéreo | 10kg     | 1.62       | 0.014        | ... │
```

O Chunk 2 é semanticamente órfão — sem cabeçalho, o modelo não sabe que `1.45` é um multiplicador de frete rodoviário para a região Norte com peso até 10kg. A query *"qual o multiplicador rodoviário para o Norte até 10kg?"* pode recuperar o Chunk 2 via similaridade semântica e o modelo receberá `1.45 | 0.012` sem contexto de interpretação.

#### Problema 2 — Granularidade Errada para Perguntas Pontuais

A pergunta *"qual o SLA do cliente Gold?"* tem resposta de 15 palavras. Com chunking de 512 tokens, o retriever busca esse dado em chunks que contêm ~380 palavras de contexto adjacente — texto sobre outros tipos de SLA, histórico da política, exceções. Isso gera dois efeitos negativos:

```
Query: "qual o SLA do cliente Gold?"

Chunk retornado (512t):
"...A política de SLA foi revisada em 2023 após análise de mercado.
Clientes Bronze têm SLA de 5 dias úteis para chamados de prioridade normal
e 24h para chamados críticos. Clientes Silver têm SLA de 3 dias úteis e 8h
para críticos, com escalonamento automático após 4h. Clientes Gold têm SLA
de 1 dia útil e 2h para críticos, com gerente dedicado e relatório mensal.
Clientes Platinum têm SLA de 4h e 30min para críticos, com NOC exclusivo..."

Informação útil: ~30 tokens
Ruído contextual: ~482 tokens (94% do chunk)
```

Esse ruído não é inerte — ocupa espaço de contexto e aumenta a probabilidade de o modelo confundir valores entre categorias adjacentes (SLA Silver vs Gold).

#### Problema 3 — Lost in the Middle Amplificado por Chunks Grandes

O efeito lost in the middle é proporcional ao tamanho do contexto injetado. Com chunks de 512 tokens e 20–30 chunks recuperados, o contexto total chega a 10.000–15.000 tokens. A resposta para *"qual o multiplicador Norte?"* pode estar no chunk 14 de 25 — exatamente na região de menor atenção do modelo.

Chunks menores e mais precisos permitem posicionar a informação mais relevante no início ou fim do contexto (as regiões de maior atenção), porque o reranker tem mais controle sobre o que incluir e onde:

```
Atenção relativa do modelo por posição no contexto:

Alta  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░████████████
	  [início]              [meio]               [fim]

Com chunks de 512t (25 chunks = 12.800t):
Chunk relevante em posição 13/25 → zona de baixa atenção

Com chunks menores e precisos (25 chunks = 4.000t):
Chunk relevante pode ser posicionado em 2/25 → zona de alta atenção
```

#### Problema 4 — Overhead de Overlap Ineficiente

O overlap padrão de 10–20% em chunking fixo (50–100 tokens em chunks de 512) existe para compensar quebras semânticas — é um workaround para um problema que estratégias estruturadas resolvem na origem. Para esta base, o overlap fixo gera duplicação de índice sem ganho real de recall para queries pontuais.

---

### Estratégia Recomendada: Chunking Estrutural por Tipo de Conteúdo

#### Tipo 1 — Tabelas de Frete e Dados Estruturados

**Estratégia: 1 linha = 1 chunk com cabeçalho injetado**

Cada linha da tabela vira um chunk independente, mas o cabeçalho completo é prefixado em cada chunk. Isso cria redundância intencional que garante que qualquer chunk recuperado seja autocontido e interpretável:

python

```
def chunk_table_with_headers(df: pd.DataFrame, 
							  table_name: str,
							  source_doc: str) -> list[dict]:
	header_context = (
		f"Tabela: {table_name} | "
		f"Colunas: {' | '.join(df.columns.tolist())}"
	)
    
	chunks = []
	for idx, row in df.iterrows():
		# Cada valor é explicitamente rotulado com seu cabeçalho
		row_content = " | ".join(
			f"{col}: {val}" 
			for col, val in row.items() 
			if pd.notna(val)
		)
        
		chunk_text = f"{header_context}\n{row_content}"
        
		chunks.append({
			"content": chunk_text,
			"tokens": estimate_tokens(chunk_text),  # ~50–150t típico
			"metadata": {
				"type":        "table_row",
				"table_name":  table_name,
				"source":      source_doc,
				"row_index":   idx,
				# Campos indexados para filtros no Azure AI Search
				"regiao":      row.get("Região"),
				"modal":       row.get("Modal"),
				"categoria":   row.get("Categoria"),
			}
		})
    
	# Chunk de overview da tabela inteira para queries comparativas
	# ex: "quais regiões têm multiplicador acima de 1.8?"
	chunks.append({
		"content": (
			f"Visão geral — {table_name}: "
			f"{len(df)} registros. "
			f"Regiões cobertas: {df['Região'].unique().tolist()}. "
			f"Modais: {df['Modal'].unique().tolist()}. "
			f"Faixa de multiplicadores: "
			f"{df['Mult. Base'].min():.2f}–{df['Mult. Base'].max():.2f}."
		),
		"metadata": {"type": "table_overview", "source": source_doc}
	})
    
	return chunks
```

**Resultado para a query *"qual o multiplicador de frete para o Norte?"*:**

```
Chunk recuperado (autocontido, ~80 tokens):
"Tabela: Multiplicadores Regionais | Colunas: Região | Modal | Peso até | 
Mult. Base | Mult. Seguro | Prazo adicional
Região: Norte | Modal: Aéreo | Peso até: 10kg | Mult. Base: 1.85 | 
Mult. Seguro: 0.015 | Prazo adicional: +2 dias"
```

O modelo recebe exatamente o que precisa, sem ruído.

#### Tipo 2 — Documentos de Política e Procedimento (PDFs texto)

**Estratégia: Chunking hierárquico por seção + chunk-pai de resumo**

Documentos de política têm estrutura natural em seções (h1/h2/h3 em HTML, ou detectável por tamanho de fonte em PDFs). Respeitar essa estrutura produz chunks semanticamente coesos:

python

```
def chunk_policy_document(sections: list[dict]) -> list[dict]:
	"""
	sections: lista de {'title': str, 'content': str, 'level': int}
	extraída do PDF via estrutura de headings ou heurísticas de fonte
	"""
	chunks = []
    
	for section in sections:
		content = section["content"]
		token_count = estimate_tokens(content)
        
		# Seção cabe em um chunk: preservar integralmente
		if token_count  400 and window:
					chunk_text = (
						f"[{section['title']}]\n" + 
						"\n\n".join(window)
					)
					chunks.append({
						"content": chunk_text,
						"metadata": {
							"type":          "policy_section_part",
							"section_title": section["title"]
						}
					})
					# Overlap semântico: último parágrafo do
					# chunk anterior inicia o próximo
					window = [window[-1], para]
					window_tokens = (estimate_tokens(window[-2]) + 
									 para_tokens)
				else:
					window.append(para)
					window_tokens += para_tokens
            
			if window:  # Flush do último chunk
				chunks.append({
					"content": f"[{section['title']}]\n" + 
							   "\n\n".join(window),
					"metadata": {"type": "policy_section_part",
								 "section_title": section["title"]}
				})
    
	return chunks
```

O overlap aqui é **semântico** (por parágrafo), não por contagem de tokens. Um parágrafo raramente corta uma ideia pela metade; 100 tokens fixos frequentemente o fazem.

#### Tipo 3 — Wiki Confluence (SLAs, Definições, Procedimentos)

**Estratégia: Chunk por bloco atômico de informação + metadado de categoria**

Páginas wiki do Confluence têm blocos naturais: definições, tabelas internas, listas de critérios, notas. Cada bloco atômico deve ser um chunk, com o título da página e da seção como prefixo:

python

```
ATOMIC_BLOCK_PATTERNS = {
	# SLA: bloco específico com categoria identificável
	"sla": r"(SLA|nível de serviço|tempo de resposta).{0,500}?(?=\n\n|\Z)",
    
	# Critérios de categorização de cliente
	"client_tier": r"(Gold|Silver|Bronze|Platinum).{0,300}?(?=\n\n|\Z)",
    
	# Procedimentos numerados
	"procedure": r"(\d+\.\s.+?)(?=\n\d+\.|\Z)",
}

def chunk_confluence_page(page: dict) -> list[dict]:
	chunks = []
	page_prefix = f"[Wiki: {page['title']}]"
    
	for section in page["sections"]:
		section_text = section["content"]
		section_prefix = f"{page_prefix} > [{section['heading']}]"
        
		# Detectar tipo de conteúdo para chunking especializado
		if is_table(section_text):
			# Tabelas dentro de wiki: mesmo tratamento do Tipo 1
			df = parse_wiki_table(section_text)
			table_chunks = chunk_table_with_headers(
				df, section["heading"], page["title"]
			)
			chunks.extend(table_chunks)
            
		elif is_definition_list(section_text):
			# Listas de definição: 1 definição = 1 chunk
			for term, definition in parse_definition_list(section_text):
				chunks.append({
					"content": (
						f"{section_prefix}\n"
						f"Definição — {term}: {definition}"
					),
					"metadata": {
						"type": "definition",
						"term": term,
						"page": page["title"]
					}
				})
		else:
			# Texto corrido: chunk por seção se Tipo de QueryExemplo RealEstratégia de ChunkTamanho AlvoLookup pontual em tabela*"Multiplicador Norte, aéreo, 10kg?"*1 linha + cabeçalho60–150tAtributo de entidade*"SLA do cliente Gold?"*Bloco atômico de definição80–200tProcedimento multi-etapa*"Como escalar um chamado crítico?"*Seção completa de documento250–450tComparação entre categorias*"Diferença entre SLA Gold e Platinum?"*Overview de tabela + chunks de linha150–300tContexto amplo de política*"Quais exceções se aplicam ao SLA?"*Sliding window por parágrafo350–500t

#### Regra de Ouro para Este Projeto

> **O chunk ideal é o menor fragmento que contém, sozinho, toda a informação necessária para responder à query — nem mais, nem menos.**

Para a NovaTech, isso se traduz em:

```
Tabelas           → chunks de 60–150t   (granularidade de registro)
Definições/SLAs   → chunks de 80–200t   (granularidade de conceito)  
Procedimentos     → chunks de 250–450t  (granularidade de seção)
Políticas longas  → chunks de 350–500t  (sliding window semântico)

Chunking fixo de 512t → inadequado para todos os tipos acima,
						exceto acidentalmente para o último
```

O chunking adaptativo adiciona complexidade ao pipeline de ingestão, mas essa complexidade é paga uma única vez — na indexação mensal/semanal. O retorno é um retriever que entrega precisão cirúrgica para exatamente o tipo de query que o time de atendimento da NovaTech vai fazer centenas de vezes por dia.

---

### Interacao 04

#### Prompt

Agora revise tudo que voce produziu ate aqui como se fosse um tech lead cetico. Identifique:

- Estimativas otimistas demais
- Riscos que nao foram mencionados
- Pontos onde a analise foi generica em vez de especifica para o caso NovaTech
- Qualquer inconsistencia entre as recomendacoes

Seja direto e critico.

#### Resposta Claude

## Revisão Crítica — O que a Análise Anterior Superestimou ou Ignorou

### 1. Estimativas Otimistas Demais

#### OCR com 85% de confiança como threshold aceitável

A análise recomendou rejeitar documentos com confiança de OCR abaixo de 85% e enviá-los para revisão humana. O problema é duplo.

Primeiro, 85% de confiança em OCR não significa 85% de acurácia nas informações críticas. Um documento de 500 palavras com 85% de confiança tem ~75 palavras potencialmente erradas. Se essas palavras incluem valores numéricos — multiplicadores de frete, prazos, limites de peso — o documento indexado é ativamente perigoso, não apenas impreciso. O threshold deveria ser 95%+ para documentos com dados estruturados, e a análise não fez essa distinção.

Segundo, foram estimados ~120 documentos escaneados (15% de 800). Na prática, "15% escaneados" é uma estimativa do cliente sem validação. É comum que clientes subestimem isso por um fator de 2x a 3x quando documentos parcialmente escaneados — PDFs híbridos com algumas páginas como imagem e outras como texto — são contabilizados como "não escaneados". A análise aceitou o número sem questionar.

#### O custo de processamento foi completamente ignorado

A análise inteira não mencionou uma única vez o custo operacional. Azure Document Intelligence custa por página processada. Com 120 documentos escaneados de 10 páginas em média, são 1.200 páginas só na ingestão inicial — mais reprocessamento mensal. Azure AI Search tem custo por unidade de busca e volume de índice. GPT-4o com janela de 128K tokens tem custo por token de input significativamente maior que modelos menores.

Para 192 queries/dia com 15.000 tokens de contexto médio, o custo de input do GPT-4o sozinho pode tornar o projeto inviável sem um cálculo explícito. Isso deveria ter aparecido na análise de viabilidade — é um critério de go/no-go, não um detalhe de implementação.

#### A estimativa de tokens assumiu conteúdo limpo

Os ~4 milhões de tokens foram calculados sobre palavras úteis. PDFs reais de logística incluem cabeçalhos e rodapés repetidos em todas as páginas, marcas d'água, numeração, metadados de versão, texto boilerplate jurídico. É razoável estimar 20–30% de overhead de ruído sobre a base calculada, elevando o índice real para 5–5,2 milhões de tokens — o que não muda a conclusão de viabilidade, mas a margem de crescimento de "2,7x" mencionada no final é otimista.

---

### 2. Riscos Não Mencionados

#### Latência — o elefante na sala

A análise recomendou pipeline de dois estágios: retrieve top-80, rerank para top-20–30. Não foi mencionado em nenhum momento qual é a latência esperada desse pipeline.

Retrieve híbrido (semântico + BM25) no Azure AI Search: 200–500ms. Rerank com cross-encoder ou Cohere: 300–800ms adicionais. Inferência GPT-4o com 15.000 tokens de contexto: 3–8 segundos. Total realista: **4–10 segundos por query**.

Para um atendente com cliente na linha, 8 segundos de espera é tempo suficiente para abandonar a ferramenta e usar o método anterior — seja uma planilha local, seja ligar para um colega. A análise de viabilidade técnica que não endereça latência está incompleta para um caso de uso de atendimento em tempo real.

#### Atualização incremental do índice não foi especificada

Foi dito que PDFs têm atualização mensal e wiki tem atualização semanal. A análise não abordou como o pipeline de ingestão lida com atualizações. Reindexar 800 PDFs mensalmente tem custo e tempo não triviais. Mais importante: no intervalo entre a publicação de um documento novo e sua indexação, o sistema responde com informação desatualizada sem nenhum aviso ao usuário. Para documentos contraditórios — um risco já identificado — esse intervalo é uma janela de falha ativa.

#### O problema de documentos contraditórios foi subestimado na solução

A estratégia proposta para documentos contraditórios dependia de similaridade de título acima de 85% para detecção. Dois procedimentos contraditórios frequentemente têm títulos diferentes: "Política de Frete — Região Norte v2" e "Manual Operacional Norte 2024" podem cobrir o mesmo procedimento com regras conflitantes e ter similaridade de título de 40%. A detecção por título não resolve o problema — precisaria de comparação semântica de conteúdo, que não foi especificada.

Além disso, a resolução foi delegada para "equipe gestora com SLA de 5 dias úteis". Com atualização semanal do Confluence, 5 dias úteis significa que um documento conflitante pode entrar em produção antes da resolução. Isso não foi sinalizado como risco.

#### Ausência total de estratégia de fallback

O que acontece quando o retriever não encontra nada relevante? A análise não menciona. O comportamento padrão do GPT-4o nessa situação é gerar uma resposta plausível com o que tem disponível — que para documentação de logística pode significar valores de frete inventados com aparência de confiança. Para um sistema usado por 45 atendentes em 192 queries/dia, esse é um risco operacional concreto que precisava de tratamento explícito: threshold mínimo de score de relevância, mensagem de fallback clara, escalação para humano.

#### Segurança e controle de acesso foram ignorados

A base inclui SharePoint, Confluence e pasta de rede. Não foi perguntado — e a análise não questionou — se todos os 45 atendentes têm acesso a todos os documentos. Se existem documentos restritos por área ou nível hierárquico, um RAG sem controle de acesso no nível do chunk cria vazamento de informação por design. Esse é um requisito que precisa ser levantado antes de qualquer decisão arquitetural, não depois.

---

### 3. Pontos Genéricos em Vez de Específicos para NovaTech

#### "Query routing" com regex é inadequado para o caso real

A estratégia de routing apresentou padrões como `"procedimento|processo|como fazer"` como se fossem suficientes. Atendentes de logística não perguntam assim. Eles perguntam *"cliente reclamou que o prazo não foi cumprido, o que faço?"* ou *"nota fiscal veio errada, qual o procedimento?"*. Essas queries não casam com nenhum dos padrões propostos e cairiam no retriever geral — que é exatamente o comportamento que o routing deveria evitar.

O routing efetivo para NovaTech exigiria exemplos reais de queries dos atendentes, que a análise nunca pediu. A recomendação foi construída sobre queries hipotéticas genéricas de logística, não sobre o vocabulário e os padrões reais do time de atendimento.

#### A estratégia de chunking para planilhas ignorou a estrutura real do negócio

Foi recomendado "1 linha = 1 chunk" para planilhas. Mas planilhas de frete em logística frequentemente têm estrutura hierárquica: cabeçalhos de grupo, subtotais, linhas de exceção que só fazem sentido em relação à linha de regra geral acima. Uma linha de exceção chunkada isoladamente — *"exceto feriados regionais: +1 dia"* — sem o contexto da regra que ela modifica é não apenas inútil mas potencialmente perigosa se o modelo a apresentar como regra geral.

A análise recomendou chunking por linha sem examinar exemplos reais das planilhas. Para um pipeline de produção, isso precisaria de inspeção manual de pelo menos uma amostra representativa antes de definir a estratégia.

#### Lost in the middle foi tratado como problema de posicionamento, não de seleção

A análise apresentou o efeito lost in the middle como um problema de onde o chunk está no contexto, sugerindo posicionar chunks relevantes no início. Isso é correto mas incompleto para o caso NovaTech. O problema mais provável aqui não é posicionamento — é que para queries como *"qual o SLA do cliente Gold?"*, o retriever provavelmente retorna chunks sobre SLA Bronze, Silver, e Platinum junto com Gold, porque todos têm alta similaridade semântica com a query. O modelo recebe 4 respostas semelhantes e tem que discriminar entre elas — exatamente o cenário onde confusão entre valores adjacentes acontece. A solução não é posicionamento; é filtragem por metadados (`categoria = "Gold"`) antes ou durante o retrieval, que foi mencionada superficialmente mas não desenvolvida como estratégia principal.

---

### 4. Inconsistências Entre Recomendações

#### Rerank para top 20–30 chunks contradiz chunks de 60–150 tokens

A análise recomendou rerank para selecionar 20–30 chunks, e chunks de tabela de 60–150 tokens. Combinados, isso é 1.200–4.500 tokens de contexto para uma query que tem resposta de 20 tokens. O overhead é aceitável, mas a recomendação de "nunca usar 243 chunks como alvo" e depois sugerir 20–30 chunks para todos os tipos de query ignora que para lookup pontual em tabela, **3–5 chunks de alta precisão são suficientes e superiores**. O número 20–30 foi apresentado como target universal quando deveria variar por tipo de query — o que contradiz a própria lógica do chunking adaptativo recomendado logo em seguida.

#### Overlap semântico recomendado mas não implementado para o tipo mais crítico

A análise identificou corretamente que PDFs com tabelas são a fonte de maior risco. Mas a estratégia de chunking para tabelas — 1 linha = 1 chunk — não tem nenhum mecanismo de overlap ou contexto entre linhas adjacentes. Para uma tabela onde a linha 5 é uma exceção à linha 4, esse approach falha exatamente onde foi dito que o chunking fixo falha. A recomendação de overlap semântico foi desenvolvida apenas para texto corrido, que é o tipo de conteúdo onde o problema é menos grave.

#### Metadados de filtragem recomendados sem definir quem os mantém

A estratégia de chunking para tabelas incluiu metadados como `regiao`, `modal`, `categoria` para filtros no Azure AI Search. A estratégia para Confluence incluiu labels como `deprecado` e `rascunho`. Em nenhum momento foi perguntado ou assumido explicitamente quem mantém esses metadados atualizados, como eles são validados, e o que acontece quando um documento entra no pipeline sem os metadados esperados — que é o comportamento padrão para qualquer documento legado.

---

### O que Precisaria ser Feito Antes de Avançar

Para ser direto: a análise produziu uma arquitetura tecnicamente sofisticada sobre premissas não validadas. Os próximos passos reais antes de qualquer implementação são:

**Validação de dados:** amostragem manual de 50 PDFs, 40 páginas wiki e 10 planilhas para verificar se as premissas de estrutura, qualidade e volume são reais.

**Levantamento de queries reais:** entrevistar 5–8 atendentes para coletar 50–100 exemplos de perguntas reais, com vocabulário real. Sem isso, routing e chunking são hipóteses.

**Prova de conceito com dados reais:** pipeline mínimo com 10% da base, medindo latência end-to-end, precisão de retrieval e custo por query antes de comprometer a arquitetura completa.

**Levantamento de requisitos de acesso:** mapa de quem pode ver o quê antes de desenhar qualquer coisa relacionada a indexação.

A análise anterior é um bom ponto de partida para discussão técnica. Não é base suficiente para uma decisão de implementação.

---

### Interacao 05

#### Prompt

Com base na revisao critica que voce forneceu, reescreva a analise
tecnica incorporando os pontos validos. Mantenha o documento em
4 secoes:

1. Desafios por tipo de fonte (com estrategias de tratamento)
2. Estimativa de tokens e orcamento de contexto por query
3. Estrategia de chunking justificada
4. Riscos tecnicos nao triviais (latencia, fallback, documentos
contraditorios, controle de acesso)

Seja especifico para o caso NovaTech. Evite recomendacoes genericas.

#### Resposta Claude

Análise Técnica — Pipeline RAG NovaTech
Documento de Viabilidade v2.0 — Revisado com Ressalvas Explícitas

Nota de escopo: esta análise incorpora revisão crítica da v1.0. Premissas não validadas são sinalizadas explicitamente. Recomendações marcadas com ⚠️ dependem de validação com dados reais antes de implementação.


Seção 1 — Desafios por Tipo de Fonte
1.1 PDFs com Tabelas Complexas
O problema real
Parsers padrão serializam tabelas linha a linha, destruindo a relação entre cabeçalho e célula. Para tabelas de frete com 15+ colunas — origem, destino, modal, faixas de peso, multiplicadores, seguros, prazos adicionais — o resultado após chunking fixo é texto sem estrutura interpretável.
O problema se agrava em dois casos específicos que a análise anterior não detalhou: linhas de exceção que só fazem sentido em relação à linha de regra acima delas ("exceto feriados regionais: +1 dia" sem a regra que ela modifica é ativamente enganosa), e tabelas com cabeçalhos hierárquicos onde a coluna "Prazo" se subdivide em "Normal", "Urgente" e "Crítico" — estrutura que parsers lineares colapsam.
Estratégia de tratamento
pythondef chunk_freight_table(df: pd.DataFrame, 
						 table_name: str,
						 source_doc: str) -&gt; list[dict]:
	chunks = []
	header_context = (
		f"Tabela: {table_name} | "
		f"Colunas: {' | '.join(df.columns.tolist())}"
	)
    
	prev_row = None
	for idx, row in df.iterrows():
		row_content = " | ".join(
			f"{col}: {val}" 
			for col, val in row.items() 
			if pd.notna(val) and str(val).strip()
		)
        
		# Detectar linhas de exceção pelo conteúdo
		# ⚠️ padrão precisa ser calibrado com planilhas reais
		is_exception = any(
			marker in str(row.values).lower() 
			for marker in ["exceto", "exceto", "salvo", "exceto se", "*"]
		)
        
		# Linhas de exceção carregam contexto da linha-pai
		if is_exception and prev_row is not None:
			row_content = (
				f"Regra base — {prev_row}\n"
				f"Exceção — {row_content}"
			)
        
		chunks.append({
			"content": f"{header_context}\n{row_content}",
			"metadata": {
				"type":       "table_row",
				"table_name": table_name,
				"source":     source_doc,
				"row_index":  idx,
				"is_exception": is_exception,
				# Campos para filtro no Azure AI Search
				# ⚠️ nomes das colunas precisam ser confirmados
				# com amostra real das planilhas
				"regiao":    row.get("Região"),
				"modal":     row.get("Modal"),
				"categoria": row.get("Categoria Cliente"),
			}
		})
		prev_row = row_content
    
	# Chunk de overview para queries comparativas
	# ex: "quais regiões têm multiplicador acima de 1.8?"
	chunks.append({
		"content": (
			f"Visão geral — {table_name}: {len(df)} registros. "
			f"Regiões: {df['Região'].unique().tolist()}. "
			f"Modais: {df['Modal'].unique().tolist()}."
		),
		"metadata": {"type": "table_overview", "source": source_doc}
	})
    
	return chunks
Limitação explícita: os metadados de filtragem (regiao, modal, categoria) precisam ser mapeados para os nomes reais de colunas das planilhas da NovaTech. Documentos legados provavelmente não seguem nomenclatura padronizada — esse mapeamento precisa ser feito manualmente antes da implementação.

1.2 PDFs Escaneados
O problema real, sem suavizações
A estimativa de 15% escaneados (~120 documentos) veio do cliente sem validação. PDFs híbridos — com algumas páginas como imagem e outras como texto — são frequentemente contabilizados como "não escaneados" por quem faz o levantamento. O número real pode ser 2–3x maior. A primeira ação do projeto deve ser um script de classificação automática sobre a base completa, antes de qualquer decisão arquitetural.
Sobre threshold de confiança de OCR: 85% não é suficiente para documentos com dados estruturados. Um documento de tabela de frete com 85% de confiança tem potencialmente dezenas de valores numéricos errados. A política deve ser diferenciada por tipo de documento:
Documentos com dados estruturados (tabelas, valores, prazos):
  confiança ≥ 95% → indexar
  85% ≤ confiança &lt; 95% → sinalizar para revisão humana antes de indexar
  confiança &lt; 85% → rejeitar, notificar responsável, NÃO indexar

Documentos de texto corrido (políticas, procedimentos narrativos):
  confiança ≥ 85% → indexar com flag "OCR — verificar se crítico"
  confiança &lt; 85% → rejeitar
Estratégia de tratamento
pythonimport fitz  # PyMuPDF
from azure.ai.formrecognizer import DocumentAnalysisClient
from enum import Enum

class DocType(Enum):
	STRUCTURED = "structured"   # tabelas, dados numéricos
	NARRATIVE  = "narrative"    # políticas, procedimentos em texto

# Thresholds diferenciados por tipo de documento
CONFIDENCE_THRESHOLDS = {
	DocType.STRUCTURED: {"index": 0.95, "review": 0.85},
	DocType.NARRATIVE:  {"index": 0.85, "review": 0.75},
}

def classify_pdf(pdf_path: str) -&gt; tuple[bool, DocType]:
	doc = fitz.open(pdf_path)
	total_chars = sum(len(p.get_text().strip()) for p in doc)
	avg_chars_per_page = total_chars / len(doc)
    
	is_scanned = avg_chars_per_page &lt; 50
    
	# ⚠️ heurística de tipo: precisa ser calibrada com amostra real
	# Assumindo que tabelas têm alta densidade de dígitos
	digit_ratio = sum(
		c.isdigit() for p in doc for c in p.get_text()
	) / max(total_chars, 1)
    
	doc_type = (DocType.STRUCTURED if digit_ratio &gt; 0.15 
				else DocType.NARRATIVE)
    
	return is_scanned, doc_type

def process_with_ocr(pdf_path: str, doc_type: DocType) -&gt; dict:
	client = DocumentAnalysisClient(
		endpoint=AZURE_FORM_RECOGNIZER_ENDPOINT,
		credential=AzureKeyCredential(KEY)
	)
	with open(pdf_path, "rb") as f:
		result = client.begin_analyze_document(
			"prebuilt-layout", f  # layout preserva tabelas
		).result()
    
	words = [w for p in result.pages for w in p.words]
	avg_confidence = (sum(w.confidence for w in words) / len(words)
					  if words else 0)
    
	thresholds = CONFIDENCE_THRESHOLDS[doc_type]
    
	if avg_confidence &gt;= thresholds["index"]:
		status = "ready"
	elif avg_confidence &gt;= thresholds["review"]:
		status = "needs_review"
	else:
		status = "rejected"
    
	return {
		"content":        result.content if status != "rejected" else None,
		"ocr_confidence": avg_confidence,
		"doc_type":       doc_type.value,
		"status":         status,
		"metadata": {
			"source":   pdf_path,
			"type":     "ocr_extracted",
			"ocr_tool": "azure_document_intelligence"
		}
	}
Custo operacional (não ignorar desta vez): Azure Document Intelligence custa por página. ⚠️ Antes de implementar, calcular: volume real de escaneados × páginas médias × preço atual da API. Incluir no TCO do projeto.

1.3 Wiki Confluence
O problema real
Dois problemas distintos que a análise anterior colapsou em um:
Problema A — Macros: macros como {status:colour=Red|title=DEPRECADO} não são apenas ruído — são metadados críticos de vigência. Uma página marcada como deprecada no Confluence que chega ao índice sem esse flag é um documento obsoleto tratado como vigente. A análise anterior mencionou isso mas não o tratou como prioridade.
Problema B — Dependência entre páginas: um procedimento de escalonamento de chamados no Confluence provavelmente referencia a página de "Matriz de Responsabilidades" e a página de "SLA por Categoria de Cliente". Chunked isoladamente, o procedimento fica incompleto. A estratégia de resolver links recursivamente (profundidade máxima 2) está correta, mas tem um risco não mencionado: loops de referência circular entre páginas são comuns em wikis corporativas antigas.
pythonfrom atlassian import Confluence
from bs4 import BeautifulSoup

# Labels que indicam que o documento NÃO deve ser indexado
# ⚠️ lista precisa ser validada com equipe da NovaTech —
# labels customizados variam por empresa
EXCLUSION_LABELS = {"deprecado", "draft", "rascunho", "revisar", 
					 "obsoleto", "archived", "wip"}

# Labels que devem ser preservados como metadados de alerta
WARNING_LABELS = {"beta", "em-revisao", "nao-oficial"}

def process_confluence_page(page_id: str, 
							  client: Confluence,
							  visited: set = None,
							  depth: int = 0) -&gt; dict | None:
	if visited is None:
		visited = set()
    
	# Proteção contra referência circular
	if page_id in visited or depth &gt; 2:
		return None
	visited.add(page_id)
    
	page = client.get_page_by_id(
		page_id,
		expand="body.storage,metadata.labels,version,ancestors"
	)
    
	labels = {
		l["name"] for l in 
		page["metadata"]["labels"].get("results", [])
	}
    
	# Excluir documentos marcados como não vigentes
	if labels &amp; EXCLUSION_LABELS:
		return {
			"status":   "excluded",
			"page_id":  page_id,
			"reason":   f"labels: {labels &amp; EXCLUSION_LABELS}",
			"content":  None
		}
    
	html    = page["body"]["storage"]["value"]
	soup    = BeautifulSoup(html, "html.parser")
	content = extract_and_clean(soup)
	links   = extract_internal_links(soup)
    
	linked_context = {}
	for linked_id, link_text in links.items():
		linked = process_confluence_page(
			linked_id, client, visited, depth + 1
		)
		if linked and linked.get("content"):
			# Incluir apenas resumo das páginas linkadas
			linked_context[link_text] = linked["content"][:400]
    
	return {
		"content":        content,
		"linked_context": linked_context,
		"status":         "active",
		"has_warnings":   bool(labels &amp; WARNING_LABELS),
		"metadata": {
			"page_id":       page_id,
			"title":         page["title"],
			"last_modified": page["version"]["when"],
			"labels":        list(labels),
			"type":          "confluence_wiki"
		}
	}

1.4 Planilhas XLSX
O problema real
data_only=True no openpyxl funciona apenas se o arquivo foi salvo com valores calculados pelo Excel. Planilhas que chegam via pasta de rede após edição sem abertura no Excel retornam None em todas as células com fórmula — falha silenciosa que produz chunks vazios indexados sem erro. A alternativa robusta é pré-processamento via LibreOffice headless para forçar recálculo:
bash# Pré-processamento antes da ingestão Python
# Executa recálculo e salva com valores resolvidos
libreoffice --headless --calc \
  --infilter="Calc MS Excel 2007 XML" \
  --convert-to xlsx \
  --outdir /tmp/processed/ \
  /input/planilha_frete.xlsx
Após esse passo, data_only=True retorna valores reais. Sem ele, o pipeline falha silenciosamente para qualquer planilha não recalculada.

Seção 2 — Estimativa de Tokens e Orçamento de Contexto
2.1 Base Total — Com Overhead de Ruído
A estimativa da v1.0 calculou sobre palavras úteis. PDFs reais de logística têm cabeçalhos e rodapés repetidos em todas as páginas, numeração, metadados de versão, texto boilerplate. Estimativa conservadora de 25% de overhead:
FontePalavras úteisTokens (÷0,75)+25% overheadTotal realPDFs2.400.0003.200.000+800.0004.000.000Wiki600.000800.000+200.0001.000.000Planilhas25.00033.000+8.000~41.000Total~5.041.000
A margem de crescimento de "2,7x sem mudança arquitetural" da v1.0 cai para ~1,9x com essa correção — ainda confortável, mas não tão folgada.
2.2 Orçamento de Contexto por Query
JANELA TOTAL:                          128.000 tokens
─────────────────────────────────────────────────────
System prompt + guardrails:             -2.000 tokens
Metadados do cliente + pergunta:          -200 tokens
Histórico de conversa:                  -2.000 tokens
Reserva para resposta do modelo:        -2.000 tokens
─────────────────────────────────────────────────────
DISPONÍVEL PARA CHUNKS:               121.800 tokens
A reserva de 2.000 tokens para resposta do modelo não é opcional — sem ela, respostas longas são truncadas silenciosamente, o que é particularmente grave para procedimentos multi-etapa onde a última etapa desaparece.
2.3 Capacidade Teórica vs. Target Real
Capacidade teórica:  121.800 ÷ 500 = 243 chunks
Target operacional:  20–30 chunks (10.000–15.000 tokens)
243 chunks é um teto nunca a ser atingido, não um alvo. O número correto de chunks por tipo de query varia:
Tipo de queryExemplo NovaTechChunks alvoTokens de contextoLookup pontual"Multiplicador Norte, aéreo, 10kg?"3–5150–750tAtributo de entidade"SLA do cliente Gold?"5–8400–1.200tProcedimento"Como escalar chamado crítico?"10–153.000–7.500tComparação"Diferença SLA Gold vs Platinum?"8–12600–1.800tContexto amplo"Quais exceções se aplicam ao SLA?"15–257.500–12.500t
2.4 Custo Operacional — Não Ignorar
⚠️ Cálculo que precisa ser feito antes da decisão de arquitetura:
192 queries/dia × 15.000 tokens médios de input × custo/token GPT-4o
= custo diário de inferência

+ custo Azure AI Search (por unidade de busca)
+ custo Azure Document Intelligence (por página, para OCR)
+ custo Cohere Rerank ou equivalente (por query no reranker)

Total mensal → comparar com orçamento disponível antes de avançar
Os valores exatos dependem de negociação de contrato Azure da NovaTech e ficam fora do escopo desta análise — mas o cálculo é um critério de go/no-go, não um detalhe posterior.

Seção 3 — Estratégia de Chunking
3.1 Por que Chunking Fixo de 512 Tokens Falha Aqui
Chunking fixo pressupõe distribuição uniforme de informação no texto. Para a base da NovaTech, esse pressuposto falha em casos concretos:
Caso 1 — Tabela de multiplicadores: corte em posição arbitrária separa células de seus cabeçalhos. O Chunk 2 começa com "1.45 | 0.012 | +2 dias" sem saber que esses são multiplicador base, percentual de seguro e prazo adicional para frete rodoviário Norte até 10kg.
Caso 2 — SLA por categoria: a query "qual o SLA do cliente Gold?" recupera um chunk de 512 tokens com SLA Bronze, Silver, Gold e Platinum juntos. O modelo recebe quatro respostas semelhantes e tem que discriminar entre elas — cenário de alta probabilidade de confusão entre valores adjacentes.
Caso 3 — Linha de exceção isolada: "exceto feriados regionais: +1 dia" em chunk separado da regra que ela modifica é desinformação estruturada.
3.2 Estratégia por Tipo de Conteúdo
Tabelas de frete e dados estruturados — 1 linha = 1 chunk com contexto
Detalhado na Seção 1.1. Tamanho resultante: 60–150 tokens por chunk. Linhas de exceção carregam a linha-pai como contexto. Chunks de overview da tabela completa para queries comparativas.
Documentos de política e procedimento — chunking por seção com overlap semântico
pythondef chunk_policy_document(sections: list[dict]) -&gt; list[dict]:
	chunks = []
    
	for section in sections:
		content     = section["content"]
		token_count = estimate_tokens(content)
        
		# Seção cabe inteira: preservar sem corte
		if token_count &lt;= 400:
			chunks.append({
				"content": f"[{section['title']}]\n{content}",
				"metadata": {
					"type":          "policy_section",
					"section_title": section["title"],
				}
			})
        
		# Seção longa: sliding window por parágrafo
		# Overlap semântico: último parágrafo do chunk anterior
		# inicia o próximo — preserva continuidade sem corte arbitrário
		else:
			paragraphs = content.split("\n\n")
			window, window_tokens = [], 0
            
			for para in paragraphs:
				para_tokens = estimate_tokens(para)
                
				if window_tokens + para_tokens &gt; 400 and window:
					chunks.append({
						"content": (f"[{section['title']}]\n" +
									"\n\n".join(window)),
						"metadata": {
							"type":          "policy_section_part",
							"section_title": section["title"],
						}
					})
					# Overlap: último parágrafo carrega para o próximo chunk
					window       = [window[-1], para]
					window_tokens = (estimate_tokens(window[0]) + 
									 para_tokens)
				else:
					window.append(para)
					window_tokens += para_tokens
            
			if window:
				chunks.append({
					"content": (f"[{section['title']}]\n" +
								"\n\n".join(window)),
					"metadata": {
						"type": "policy_section_part",
						"section_title": section["title"],
					}
				})
    
	return chunks
Tamanho resultante: 250–450 tokens. Overlap é por parágrafo, não por token fixo — um parágrafo raramente corta uma ideia ao meio; 100 tokens fixos frequentemente o fazem.
Wiki Confluence — chunk por bloco atômico com prefixo de localização
pythondef chunk_confluence_page(page: dict) -&gt; list[dict]:
	chunks = []
	page_prefix = f"[Wiki: {page['title']}]"
    
	for section in page["sections"]:
		section_prefix = f"{page_prefix} &gt; [{section['heading']}]"
		content = section["content"]
        
		if is_definition_block(content):
			# Definições: 1 termo = 1 chunk
			for term, definition in parse_definitions(content):
				chunks.append({
					"content": (f"{section_prefix}\n"
								f"Definição — {term}: {definition}"),
					"metadata": {
						"type": "definition",
						"term": term,
						"page": page["title"],
						"has_warning": page.get("has_warnings", False)
					}
				})
        
		elif is_table(content):
			df = parse_wiki_table(content)
			chunks.extend(
				chunk_freight_table(df, section["heading"], 
									page["title"])
			)
        
		else:
			# Texto corrido: mesmo tratamento de política
			chunks.extend(chunk_policy_document([{
				"title":   section["heading"],
				"content": content,
			}]))
    
	return chunks
3.3 Retrieval em Dois Estágios
Retrieve top-80 via busca híbrida (semântica + BM25), rerank para top N variável por tipo de query. O reranker é necessário porque queries como "SLA Gold" têm alta similaridade semântica com chunks sobre SLA Bronze, Silver e Platinum — o retriever semântico sozinho não discrimina entre eles com confiabilidade suficiente.
Filtros por metadados antes do retrieval para queries com entidade identificável:
pythondef build_search_filter(query: str) -&gt; str | None:
	# ⚠️ padrões precisam ser validados com queries reais dos atendentes
	# Esta lista foi construída sobre hipóteses, não sobre dados reais
    
	REGION_KEYWORDS = {
		"norte": "regiao eq 'Norte'",
		"nordeste": "regiao eq 'Nordeste'",
		"sul": "regiao eq 'Sul'",
		"sudeste": "regiao eq 'Sudeste'",
		"centro-oeste": "regiao eq 'Centro-Oeste'",
	}
    
	TIER_KEYWORDS = {
		"gold":     "categoria eq 'Gold'",
		"silver":   "categoria eq 'Silver'",
		"bronze":   "categoria eq 'Bronze'",
		"platinum": "categoria eq 'Platinum'",
	}
    
	query_lower = query.lower()
    
	filters = []
	for keyword, filter_expr in {**REGION_KEYWORDS, 
								   **TIER_KEYWORDS}.items():
		if keyword in query_lower:
			filters.append(filter_expr)
    
	return " and ".join(filters) if filters else None
Filtro por metadados reduz o espaço de busca antes do retriever semântico, aumentando precision sem custo de recall para queries com entidade explícita. Para queries sem entidade identificável, o filtro é None e o retriever busca na base completa.

Seção 4 — Riscos Técnicos Não Triviais
4.1 Latência — Risco Primário para Adoção
Este é o risco com maior probabilidade de matar o projeto silenciosamente. Para atendentes com cliente na linha, o threshold de tolerância é 3–4 segundos. O pipeline recomendado tem latência realista de:
Retrieve híbrido (Azure AI Search):    200–500ms
Rerank (Cohere ou Azure reranker):     300–800ms
Inferência GPT-4o (15.000t contexto):  3–8 segundos
─────────────────────────────────────────────────
Total realista:                        3,5–9,3 segundos
9 segundos por query é inaceitável para atendimento em tempo real. Mitigações a considerar, em ordem de impacto:
Mitigação 1 — Streaming de resposta: o modelo começa a retornar texto antes de terminar a geração. Reduz latência percebida para ~1–2 segundos até o primeiro token, mesmo que a resposta completa demore 6 segundos. É a mitigação de maior impacto com menor custo de implementação.
Mitigação 2 — Cache de queries frequentes: 192 queries/dia com vocabulário de atendimento têm alta repetição. "Qual o SLA do cliente Gold?" provavelmente aparece dezenas de vezes por semana. Cache semântico (similaridade de embedding &gt; 0.95 com query anterior) serve a resposta em ~50ms.
Mitigação 3 — Modelo menor para queries simples: GPT-4o para lookup pontual em tabela é overkill. Um classificador de complexidade de query pode rotear lookups simples para GPT-4o-mini com contexto reduzido, reservando GPT-4o para procedimentos complexos.
⚠️ Ação obrigatória antes de produção: medir latência end-to-end com dados reais em ambiente Azure da NovaTech. Os números acima são estimativas baseadas em benchmarks públicos — latência real depende de região do Azure, tier do serviço e carga concorrente.

4.2 Fallback — Comportamento Quando o Retriever Falha
O comportamento padrão do GPT-4o quando não há contexto relevante é gerar resposta plausível com o que estiver disponível. Para tabelas de frete, isso significa valores inventados com aparência de confiança. É o pior tipo de falha em um sistema de atendimento.
pythonRELEVANCE_THRESHOLD = 0.75  # ⚠️ calibrar com dados reais

def query_with_fallback(query: str, 
						 chunks: list[dict]) -&gt; dict:
    
	if not chunks:
		return {
			"answer": (
				"Não encontrei documentação específica para essa consulta. "
				"Recomendo verificar diretamente com o supervisor ou "
				"consultar o SharePoint em [link]."
			),
			"fallback": True,
			"chunks_used": 0
		}
    
	max_score   = max(c["score"] for c in chunks)
	best_chunks = [c for c in chunks 
				   if c["score"] &gt;= RELEVANCE_THRESHOLD]
    
	if not best_chunks:
		return {
			"answer": (
				f"Encontrei documentos relacionados, mas nenhum com "
				f"confiança suficiente para essa consulta específica "
				f"(melhor score: {max_score:.2f}). "
				f"Documentos próximos: "
				f"{[c['metadata']['source'] for c in chunks[:3]]}. "
				f"Recomendo verificar manualmente."
			),
			"fallback":    True,
			"chunks_used": 0,
			"nearest_docs": [c["metadata"]["source"] 
							 for c in chunks[:3]]
		}
    
	# Proceder com inferência normal
	return generate_response(query, best_chunks)
O fallback deve ser informativo — indicar quais documentos foram encontrados mas não atingiram threshold, com link direto. "Não sei" útil é melhor que resposta confiante incorreta.

4.3 Documentos Contraditórios — Detecção Real
A v1.0 propôs detecção por similaridade de título (&gt;85%). Essa abordagem falha para o caso mais comum na NovaTech: "Política de Frete — Região Norte v2" e "Manual Operacional Norte 2024" cobrem o mesmo procedimento com regras conflitantes e têm similaridade de título de ~40%. Detecção por título não resolve o problema.
Abordagem correta: detecção por similaridade semântica de conteúdo combinada com sobreposição de entidades mencionadas.
pythonfrom sklearn.metrics.pairwise import cosine_similarity

CONTRADICTION_THRESHOLD = 0.88

def detect_contradictions(new_doc: dict, 
						   indexed_docs: list[dict],
						   embed_fn) -&gt; list[dict]:
	new_embedding = embed_fn(new_doc["content"][:2000])
	conflicts     = []
    
	for existing in indexed_docs:
		# Similaridade semântica de conteúdo (não de título)
		sim = cosine_similarity(
			[new_embedding],
			[existing["embedding"]]
		)[0][0]
        
		if sim &gt; CONTRADICTION_THRESHOLD:
			same_source  = (new_doc["source_system"] == 
							existing["source_system"])
			new_is_newer = (new_doc["last_modified"] &gt; 
							existing["last_modified"])
            
			if same_source and new_is_newer:
				# Mesma fonte, documento mais novo:
				# substituir automaticamente
				conflicts.append({
					"action":       "replace",
					"existing_id":  existing["id"],
					"similarity":   sim,
				})
			else:
				# Fontes diferentes ou versões ambíguas:
				# quarentena obrigatória
				conflicts.append({
					"action":      "quarantine",
					"existing_id": existing["id"],
					"similarity":  sim,
					"reason": (
						"Conteúdo similar de fontes diferentes "
						"ou versão ambígua"
					),
				})
    
	return conflicts
Política de quarentena com SLA realista:
Documentos em quarentena não entram no índice. SLA de resolução de 5 dias úteis é incompatível com atualização semanal do Confluence — um documento conflitante publicado segunda-feira entra em quarentena e pode não ser resolvido antes da próxima atualização. O SLA precisa ser 48h, com escalonamento automático se não resolvido.
Comportamento do modelo quando contradição já está no índice (para casos que passaram da detecção):
System prompt — instrução explícita:
"Se você identificar informações contraditórias entre documentos 
recuperados, NÃO escolha uma arbitrariamente. Responda:
'Encontrei versões conflitantes: [Documento A, data X] indica [Y], 
enquanto [Documento B, data Z] indica [W]. Recomendo verificar com 
o supervisor qual versão está vigente antes de informar o cliente.'"

4.4 Controle de Acesso — Requisito que Precisa Ser Levantado Antes de Qualquer Implementação
A análise v1.0 não mencionou controle de acesso. Isso é uma omissão grave para um sistema que agrega SharePoint, Confluence e pasta de rede.
SharePoint e Confluence têm controle de acesso por documento. Se um atendente não tem permissão para ver um documento no SharePoint, ele não deveria receber seu conteúdo via RAG. Um índice flat sem controle de acesso no nível do chunk cria vazamento de informação por design — qualquer atendente pode consultar qualquer documento, independente das permissões originais.
As perguntas que precisam ser respondidas antes de implementar:
1. Todos os 45 atendentes têm acesso a todos os documentos 
   nas três fontes?
   
2. Existem documentos restritos por área (ex: documentos 
   financeiros visíveis apenas para supervisores)?
   
3. A NovaTech tem requisitos de auditoria que exigem log 
   de quais documentos foram acessados por quem?
Se a resposta para (1) for "sim, acesso total para todos", o problema não existe e o índice flat é adequado. Se for "não", a arquitetura precisa de um dos dois modelos:
Modelo A — Índices separados por perfil de acesso (simples, mas com overhead de manutenção):
Índice "atendente_base"   → documentos acessíveis a todos
Índice "atendente_senior" → base + documentos restritos
Índice "supervisor"       → todos os documentos
Modelo B — Filtro de acesso por metadado no Azure AI Search (mais flexível, mais complexo):
pythondef build_access_filter(user_profile: str) -&gt; str:
	ACCESS_LEVELS = {
		"atendente":  ["publico", "atendimento"],
		"senior":     ["publico", "atendimento", "operacional"],
		"supervisor": ["publico", "atendimento", "operacional", "gerencial"],
	}
	allowed = ACCESS_LEVELS.get(user_profile, ["publico"])
	return " or ".join(f"access_level eq '{l}'" for l in allowed)
⚠️ Este levantamento precisa acontecer na semana 1 do projeto. Mudar a arquitetura de indexação após a ingestão inicial tem custo alto.

O que Precisa Acontecer Antes de Implementar
Esta análise é tecnicamente consistente, mas foi construída sobre premissas não validadas. Quatro ações são necessárias antes de qualquer linha de código de produção:
1. Auditoria da base de dados (1 semana): script de classificação automática sobre os 800 PDFs para medir porcentagem real de escaneados, híbridos e com tabelas complexas. Inspecionar manualmente 10% das planilhas para mapear estrutura real de colunas e identificar padrões de exceção.
2. Levantamento de queries reais (3–5 dias): entrevistar 6–8 atendentes e coletar 80–100 exemplos de perguntas reais com vocabulário real. Sem isso, routing e estratégia de chunking são hipóteses sobre comportamento de usuário que pode ser completamente diferente.
3. Levantamento de requisitos de acesso (2 dias): mapa de permissões por perfil antes de qualquer decisão sobre arquitetura de indexação.
4. Prova de conceito com 10% da base (2–3 semanas): pipeline completo em escala reduzida, medindo latência end-to-end real no ambiente Azure da NovaTech, precisão de retrieval com queries reais coletadas no passo 2, e custo por query para validar viabilidade econômica.
A decisão de avançar para implementação completa deve ser tomada após — não antes — dos resultados da PoC.

---

## Observacoes

- Insights principais:
- Ajustes para proxima iteracao:

