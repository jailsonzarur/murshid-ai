# Resumo Guiado por Matéria — Avaliação

Avaliação da ideia de criar um sistema de matérias com base documental (RAG) para gerar
resumos guiados das aulas. Não é planejamento de implementação — é o registro do porquê
vale a pena e do que pode dar errado.

## A ideia

Cada matéria pode ter vários documentos anexados (artigos, livros base, slides). Essa base
alimenta um RAG que, além do resumo normal e do mapa mental já existentes, gera um resumo
mais detalhado e guiado: explica pontos da aula puxando trechos do próprio material e
sinaliza quando a aula diverge da bibliografia.

No futuro, a mesma base serve para outras funcionalidades.

## Veredito

Valor alto, viável, e barato — nessa ordem de confiança.

## Por que tem valor

Transcrição + resumo + mapa mental é commodity. Qualquer ferramenta faz, e o diferencial
vira preço.

Resumo ancorado no material da própria disciplina não é commodity. Atende uma dor real e
específica de estudante: *"foi eu que entendi errado ou o professor falou diferente do
livro?"*

O ponto mais importante é que **isso acumula**. A base de conhecimento da matéria é um
ativo que fica. Depois ela alimenta geração de questões, tira-dúvidas, revisão pré-prova,
comparação entre aulas. Cada documento que o usuário sobe aumenta o valor de tudo que veio
antes.

É o oposto do módulo de provas, onde cada prova era um evento isolado e caro.

Isso também cria retenção de um jeito que transcrição pura não cria: quem montou a base de
quatro matérias não migra para outro app.

## Custo

O ponto que fecha o argumento: a transcrição, que já é paga hoje, é a parte cara. O RAG é
troco.

Estimativas em ordem de grandeza (preços de provedor mudam):

| Item | Custo |
|---|---|
| Embedar um livro de ~400 páginas | menos de 1 centavo, uma vez só |
| Armazenar os vetores | zero — pgvector no Postgres que já roda |
| Um resumo guiado (aula de 1h) | ~1 a 3 centavos |
| *Transcrever essa mesma aula (Whisper)* | *~$0.36* |

O resumo guiado custa em torno de 5% do que já se gasta transcrevendo a aula.

## Infraestrutura

Não é necessário Pinecone, Qdrant nem Weaviate. Postgres + extensão pgvector resolve com
folga em qualquer volume previsível para os próximos anos.

A mudança no `docker-compose.yml` é trocar a imagem `postgres:16-alpine` por
`pgvector/pgvector:pg16`. Uma linha.

## O que já existe e é reaproveitado

O quanto reaproveita é o que dá confiança na viabilidade:

- **MinIO** já montado para upload de arquivo (feature `files`)
- **PyMuPDF** está nas dependências e foi preservado no corte. Ressalva: o único uso que
  existia era rasterizar páginas em imagem para o modelo de visão das provas, não extrair
  texto. Extração de texto (`page.get_text()`) e leitura do sumário do PDF ainda são
  código a escrever — a dependência está pronta, o pipeline não
- **Celery** já existe para processamento assíncrono (embedar um livro leva minutos, tem
  que ser task)
- **Postgres** só precisa da extensão
- O padrão de feature (`models` + `services` + `routes` + `tasks`) já está estabelecido

Código realmente novo: chunking, geração de embedding, busca por similaridade, e o prompt
do resumo guiado.

## Riscos a desenhar agora, não depois

### 1. Chunking é onde a feature ganha ou perde

Não é detalhe de implementação — é *a* variável de qualidade.

Cortar o livro em pedaços fixos de N caracteres dá recuperação medíocre: traz meio
parágrafo sem contexto e o modelo alucina em cima. Livro didático tem estrutura (capítulo →
seção → subseção) e o PyMuPDF expõe o sumário do PDF.

Chunk respeitando a estrutura, guardando de qual capítulo/seção veio, muda o resultado de
"mais ou menos" para "bom". Se for economizar esforço, economizar em outro lugar.

### 2. "Corrigir o professor" é a parte perigosa

É o recurso mais atraente e o mais fácil de destruir confiança.

Quando o sistema disser "o professor errou" e estiver errado — porque a recuperação trouxe
o trecho errado, porque o livro está desatualizado, ou porque é divergência legítima de
abordagem — o usuário para de acreditar em tudo, inclusive no que estava certo.

Enquadramento sugerido: **"divergência encontrada"**, mostrando os dois lados com a citação
do livro (página e seção), deixando o estudante julgar. Mesmo valor prático, sem o app
bancar árbitro — e protege o produto de estar errado.

### 3. Direito autoral, se um dia isso for compartilhado

Usuário subir o PDF do livro para estudo pessoal é uma coisa. Matéria compartilhada entre
alunos vira distribuição de obra protegida.

Não é bloqueador agora, mas decide se "matéria" nasce pessoal ou compartilhável — e isso é
bem mais barato de decidir antes do que depois.

### 4. Cold start

Matéria sem documento anexado faz a funcionalidade não entregar nada. Precisa degradar com
graça: cair no resumo normal, e deixar claro que anexar material melhora o resultado.

## Matéria é a `categories` evoluída — confirmado no código

Essa era a questão em aberto, e a resposta veio na remoção do módulo de provas.

`LectureModel` já tem `category_id` e o relacionamento `category` (`lectures/models.py`).
A tabela `categories` já existe, com CRUD completo e quatro rotas.

Ou seja: **o vínculo aula → matéria já está pronto.** Não é preciso criar entidade nova.
O caminho é renomear/estender `categories` para o conceito de matéria e pendurar os
documentos nela.

Detalhe do histórico: `categories` tinha também um relacionamento com `questions`, que caiu
junto com o módulo de provas. Hoje ela serve exclusivamente às aulas — o que deixa o
caminho livre para virar matéria sem conviver com uma semântica antiga.

O que falta no modelo de dados é só a parte nova: documento (pertence a uma matéria) e
chunk com embedding (pertence a um documento).

## Sequência sugerida

1. Cortar provas (tag antes, preservando o pipeline de PDF)
2. Matérias + upload de documentos + ingestão, **sem RAG ainda** — só anexar e listar
3. Chunking + embedding + busca, validando a recuperação isoladamente
4. O resumo guiado em cima de uma recuperação que já se sabe que funciona

O passo 3 separado do 4 importa: construindo os dois juntos, se o resultado vier ruim não
dá para saber se o problema é a recuperação ou o prompt.
