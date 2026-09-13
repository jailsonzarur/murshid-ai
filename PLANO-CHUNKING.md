# Plano — Chunking e embedding dos documentos de matéria

Continuação do `RESUMO-GUIADO.md`. O passo 2 daquele documento (matérias + upload +
ingestão) está concluído. Este plano cobre do fim dele até ter os chunks embedados e
ligados à matéria.

Busca por similaridade e resumo guiado ficam de fora, de propósito: o `RESUMO-GUIADO.md`
separa os passos 3 e 4 justamente para validar a recuperação isoladamente antes de
escrever qualquer prompt.

## Estratégia escolhida

Duas camadas, não duas alternativas:

```
PDF
 │
 ├─ document-based   detecta títulos por fonte/negrito → SEÇÕES
 │
 └─ recursive        subdivide seção grande respeitando
                     parágrafo → frase → corte duro     → CHUNKS
```

Regra que faz as duas conviverem: **o recursive nunca atravessa fronteira de seção.**

Semantic chunking foi descartado. O artigo do NAACL 2025 ("Is Semantic Chunking Worth the
Computational Cost?") mostra que em documentos reais fixed-size frequentemente vai melhor,
e o custo não se justifica. O método depende de saltos de assunto, que livro didático não
tem — o texto flui continuamente.

Late chunking fica na prateleira: resolveria melhor que semantic se as fronteiras vierem
ruins, mas amarra a um fornecedor específico de embedding.

## Medições que fundamentam o plano

Feitas nos documentos reais do usuário.

| documento | páginas | sumário embutido | detecção por fonte |
|---|---|---|---|
| Murray - Microbiologia Médica | 1.363 | não | excelente, 3 níveis |
| e-book Engenharia de Produção | 302 | não | boa, precisa do negrito |
| Segurança no Desenvolvimento | 43 | sim | boa |
| Steve Jobs | 670 | não | falha — livro escaneado |

O sumário embutido do PDF **não é confiável**: falta em 4 de 10 documentos, incluindo os
dois maiores livros. E quando existe é achatado em nível 1 com front matter
("Folha de rosto", "Copyright"). A premissa original do `RESUMO-GUIADO.md` de pendurar o
chunking no `get_toc()` não se sustenta.

Murray, que é o melhor caso:

```
corpo   10pt   77,5% do texto
        13pt    0,5%   ← seção
        16pt    0,3%   ← seção maior
        29pt    0,1%   ← capítulo

texto extraído      4.003.688 chars (~1M tokens)
extração            4,8s
seções detectadas   1.336
seção mediana       1.819 chars
já cabem em 1 chunk 601 (44%)
chunks finais       ~2.433
custo               $0,02
```

---

## Passo 0 — Correções que precisam vir antes

**0.1 Tirar a ingestão da fila do ffmpeg.** `ingest_subject_document_task` não está no
`task_routes`, cai na fila `celery` e é consumida pelo `worker_media` — dois slots prefork
que também rodam transcodificação de áudio.

Criar a fila `documents`, rotear a task, adicionar `worker_documents` no
`supervisord.conf` (prefork, concorrência 2). Prefork porque extração de PDF é CPU.

**0.2 Comprimir o PDF na ingestão.** `MAX_DOCUMENT_BYTES` é 50 MB e o Murray tem 355 MB —
hoje não sobe.

Medido no Murray: **98% do arquivo são imagens** — 722 imagens somando 346 MB, contra 4 MB
de texto. Compressão sem perda não resolve (355,1 → 355,4 MB), porque elas já estão
comprimidas. Recomprimir resolve:

```
imagens em no máximo 1600px, JPEG q80
346 MB  →  50 MB  (15%)  em 26s
```

O PDF inteiro cairia para ~59 MB. Roda com o PyMuPDF que já está no projeto, na mesma task
que já baixa o arquivo. O limite sobe para aceitar o upload original, e o que se guarda é
o comprimido.

Ressalva: medido só no Murray. Livro escaneado (Steve Jobs) pode degradar mais, porque ali
a imagem **é** o texto. Medir nele antes de aplicar a todos.

**Armazenamento — decidido ficar no MinIO por enquanto.** O R2 é 10× mais barato por GB
($0,015 contra $0,15 do volume do Railway) e tem egress zero, e a migração é quase só
variável de ambiente porque o `bucket_service.py` já aceita `BUCKET_ENDPOINT_URL` e chaves
genéricas. Fica registrado para depois; a compressão sozinha já corta 6× o volume.

## Passo 1 — pgvector

Trocar `postgres:16-alpine` por `pgvector/pgvector:pg16`. Mesma versão do Postgres, mesmo
diretório de dados, o volume continua valendo — **mas fazer backup antes**, é troca de
imagem em banco com dado real.

Migração: `CREATE EXTENSION IF NOT EXISTS vector;`

Verificação: `SELECT '[1,2,3]'::vector;` responde sem erro.

## Passo 2 — Tabela de chunks

```sql
CREATE TABLE subject_document_chunks (
    id            uuid PRIMARY KEY,
    document_id   uuid NOT NULL REFERENCES subject_documents(id) ON DELETE CASCADE,
    subject_id    uuid NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    sequence      integer NOT NULL,
    text          text NOT NULL,
    heading_path  text NOT NULL,
    page_start    integer,
    page_end      integer,
    embedding     vector(1536) NOT NULL,
    UNIQUE (document_id, sequence)
);

CREATE INDEX ON subject_document_chunks (subject_id);
CREATE INDEX ON subject_document_chunks USING hnsw (embedding vector_cosine_ops);
```

`subject_id` é desnormalizado de propósito: o filtro por matéria roda em toda consulta e
sem a coluna exige join antes da busca vetorial.

**Dimensão 1536 (`text-embedding-3-small`), decidido.** O `3-large` (3072) custa 6,5× mais
e entrega ganho pequeno de qualidade. A dimensão fica fixa no schema, então trocar depois
exige migração de coluna e reembedar tudo — barato ($0,13 pelo Murray), mas é trabalho.

Tabela de imagens, separada:

```sql
CREATE TABLE subject_document_images (
    id           uuid PRIMARY KEY,
    document_id  uuid NOT NULL REFERENCES subject_documents(id) ON DELETE CASCADE,
    chunk_id     uuid REFERENCES subject_document_chunks(id) ON DELETE SET NULL,
    page         integer NOT NULL,
    bbox         jsonb NOT NULL,
    caption      text
);
```

Tabela e não coluna no chunk porque **184 páginas do Murray têm 2 ou mais imagens** — a
relação é um-para-muitos de verdade.

Na `subject_documents`, duas colunas novas:

```
index_status   NONE | REQUESTED | PROCESSING | DONE | FAILED
chunk_count    integer
```

Separado do `status` existente: a capa precisa aparecer em segundos para o card renderizar;
o embedding leva minuto. Travar um no outro piora a UI sem motivo.

## Passo 3 — Extração de texto com layout

`subjects/ai/text_extraction.py`. Lê com `get_text("dict")` e devolve linhas planas:

Devolve **texto e imagem num único fluxo ordenado**, na ordem de leitura da página. É esse
detalhe que faz o vínculo imagem↔chunk cair sozinho no passo 5.

```python
@dataclass(frozen=True)
class Line:
    text: str
    size: float
    bold: bool
    page: int

@dataclass(frozen=True)
class Image:
    page: int
    bbox: tuple[float, float, float, float]
    caption: str | None
```

**Detecção de legenda:** o bloco de texto imediatamente abaixo da imagem, com sobreposição
horizontal, começando por `Figura|Fig.|Tabela|Quadro|Box` seguido de número. Medido no
Murray: **526 de 557 imagens relevantes (94%)** têm legenda detectável dessa forma.
Imagens com menos de 60px de lado são descartadas — são logo e ícone.

## Passo 4 — Detecção de títulos

`subjects/ai/heading_detection.py`.

1. Histograma de tamanhos ponderado por volume de texto → o mais frequente é o corpo
2. Cada tamanho acima do corpo vira um nível, do maior para o menor
3. Negrito no tamanho do corpo entra como o nível mais baixo

Filtros que a medição mostrou serem necessários:

- descartar linha com 5+ pontos seguidos — são linhas de sumário (`CAPÍTULO 1......`),
  que criariam dezenas de seções fantasma
- descartar linha com menos de 3 ou mais de 120 caracteres
- limitar a 3 níveis. No Murray o quarto (11pt) tinha 1.657 ocorrências misturando
  subtítulo real com bullet e "8ª EDIÇÃO"

**O primeiro nível do `heading_path` é sempre o nome do documento:**

```
Murray - Microbiologia Médica > Esterilização, Desinfecção e Antissepsia
  > Mecanismos de Ação > Calor Úmido
```

Resolve dois problemas de uma vez: distingue de qual documento da matéria veio o trecho, e
dá o fallback natural quando nenhum título é detectado — aí o `heading_path` é só o nome do
documento, que é o caso do Steve Jobs.

## Passo 5 — Chunking recursivo

`subjects/ai/chunking.py`. Para cada seção do passo 4:

- se couber no alvo, vira um chunk só (44% das seções do Murray)
- se não couber, corta em parágrafo; se um parágrafo estourar, cai para frase; só em
  último caso corta duro
- nunca atravessa fronteira de seção

| | valor | por quê |
|---|---|---|
| alvo | 1.600 chars | deu 2.433 chunks no Murray |
| mínimo | 300 chars | abaixo disso o `heading_path` domina o vetor |
| overlap | 150 chars | só entre chunks da mesma seção |

Seção abaixo do mínimo é fundida com a vizinha em vez de virar chunk sozinha.

**Vínculo com as imagens.** Como o fluxo do passo 3 traz texto e imagem juntos, o chunker
só precisa anotar quais marcadores de imagem ficaram dentro de cada chunk:

```
fluxo:  linha  linha  [IMG 3]  legenda  linha  linha  [IMG 4]  legenda  linha
        └────────── chunk 12 ──────────┘└────────── chunk 13 ──────────┘
```

Não existe etapa separada de casamento. Duas regras:

- a fronteira do chunk nunca cai entre a imagem e a sua legenda — o corte é empurrado
- a legenda **fica no `text` do chunk** (é conteúdo, e ajuda a busca: "FIGURA 2-1
  Distribuição topográfica de bactérias na pele" tem termos que o aluno procura) **e** é
  copiada para a linha da imagem, para exibição

**O recorte da imagem não é gerado agora.** Guarda-se só `page` + `bbox`, que é tudo o que
`page.get_pixmap(clip=bbox)` precisa — a mesma chamada que o `_render_square_icon` já faz.

Gerar os 557 recortes do Murray daria ~45 MB por livro, quase o tamanho do PDF comprimido,
para imagens que em sua maioria nunca serão exibidas (um resumo guiado mostra duas ou
três). Quando chegar a hora, recorta sob demanda e guarda só as usadas.

O que importa é **registrar o `bbox` desde já**: extrair posição depois significaria
reprocessar todos os PDFs.

## Passo 6 — Embedding e gravação

Task `index_subject_document_task`, fila `documents`.

```python
entrada = f"{chunk.heading_path}\n{chunk.text}"
```

Lotes de 100, `text-embedding-3-small` (1536 dimensões). No Murray são 25 requisições.

Grava `text` **limpo**, sem o prefixo. O prefixo existe só para o vetor; o `text` vai ser
lido depois pelo LLM do resumo guiado e não deve carregar o cabeçalho.

Idempotência, mesmo padrão do mapa mental: claim atômico movendo `NONE`/`FAILED` para
`REQUESTED`, e apagar os chunks existentes do documento antes de inserir. Reprocessar nunca
duplica.

Encadeamento: `ingest_document` (capa, já existe) dispara `index_subject_document_task` ao
terminar.

## Passo 7 — Verificação

Sem busca ainda, a validação é inspeção. Um comando que, dado um documento, imprime:

- número de chunks, distribuição de tamanho, quantos caíram no fallback de `heading_path`
- 10 chunks amostrados com o `heading_path` completo

Critério de aceite no Murray:

| métrica | esperado |
|---|---|
| chunks | ~2.400 |
| com heading de 3 níveis | maioria |
| com heading só do documento | poucos, concentrados em índice remissivo |
| chunk cortado no meio de frase | raro |
| custo | ~$0,02 |

Se o Murray passar, os outros passam.

## Custo total

```
Murray (1.363 pgs)      $0,020
Engenharia (302 pgs)    $0,005
Metodologia (124 pgs)   $0,002
```

Uma matéria com bibliografia completa fica abaixo de 3 centavos, pagos uma vez. Menos que
transcrever uma aula.

## O que isso já habilita

Com `chunk_id` + `bbox` + `caption` gravados, o resumo guiado ganha as figuras de graça:
quando ele citar um trecho, basta olhar se aquele chunk tem imagem e mostrar a figura junto
da citação. Sem modelo de visão e sem embedding multimodal.

Se a legenda se mostrar pobre demais, o próximo degrau é descrever a imagem com modelo de
visão e embedar a descrição — ~$0,20 pelo Murray inteiro, e continua tudo num índice só.

Embedding multimodal de verdade (imagem e texto no mesmo espaço vetorial) fica como último
recurso: muda o modelo, muda a dimensão do vetor, e obriga a reembedar tudo.

## Fora de escopo, de propósito

Busca por similaridade, resumo guiado, recorte de imagem, e OCR para livro escaneado. O
último é problema de ingestão, não de chunking — misturar os dois confunde o diagnóstico.

## Ordem de execução

Passos 0 e 1 são independentes e podem ir juntos. Do 2 ao 6 é sequencial. O 7 acompanha o
4, 5 e 6 — vale inspecionar a saída de cada um isoladamente antes de encadear, senão um
chunk ruim no fim não diz se o problema foi a detecção de título ou o corte.
