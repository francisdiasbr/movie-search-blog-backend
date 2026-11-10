# Diretores (`directors`)

Arquivos: `directors/routes.py`, `directors/controller.py`. Prefixo: `/api/directors`. Coleção:
`directors`. Serviços externos: OpenAI (biografia e tradução) e IMDB (foto).

## O que faz

Entrega nome, biografia e foto de um diretor. Na primeira vez em que um diretor é pedido, a biografia
é gerada pela OpenAI em português e gravada. Dali em diante, a resposta vem do banco. A foto é
procurada nas páginas públicas do IMDB quando a requisição informa o `tconst` de um filme do diretor.

## Rotas

### `GET /api/directors/<nome>`

| Parâmetro | Onde | Padrão | Descrição |
|---|---|---|---|
| `nome` | caminho | | Nome do diretor, exatamente como deve ser gravado. Vários nomes separados por vírgula são tratados como vários diretores. |
| `tconst` | query | nenhum | `tconst` de um filme do diretor. Sem ele, a foto não é procurada. |
| `language` | query | `pt` | `pt` ou `en`. Qualquer outro valor vira `pt`. |

```bash
curl "http://localhost:5001/api/directors/Jean-Luc%20Godard?tconst=tt0053472&language=pt"
```

Resposta `200`, diretor gravado:

```json
{
  "_id": "66f0c0ffee0000000000abcd",
  "name": "Jean-Luc Godard",
  "bio": "Jean-Luc Godard foi um dos nomes centrais da Nouvelle Vague...",
  "photo": "https://m.media-amazon.com/images/M/....jpg"
}
```

Resposta `200`, biografia genérica (nada foi gravado):

```json
{
  "name": "Jean-Luc Godard",
  "bio": "Diretor de cinema conhecido por Jean-Luc Godard.",
  "photo": null,
  "placeholder": true
}
```

Resposta `200`, vários diretores (`/api/directors/Joel Coen, Ethan Coen`):

```json
{
  "name": "Joel Coen, Ethan Coen",
  "bio": "Joel Coen: ...\n\nEthan Coen: ...",
  "photo": "https://m.media-amazon.com/images/M/....jpg",
  "directors": [
    {"_id": "...", "name": "Joel Coen", "bio": "...", "photo": "..."},
    {"_id": "...", "name": "Ethan Coen", "bio": "...", "photo": null}
  ]
}
```

| Código | Quando |
|---|---|
| `200` | Diretor encontrado, gerado, ou respondido com biografia genérica. |
| `404` | O nome só tem vírgulas e espaços: `{"error": "Nenhum diretor encontrado"}`. |
| `500` | Banco indisponível ou erro inesperado: `{"error": "Erro ao buscar informações do diretor"}`. |

### `GET /api/directors/all`

Devolve todos os diretores gravados, sem o campo `_id`.

| Código | Corpo |
|---|---|
| `200` | `{"directors": [{"name": "...", "bio": "...", "photo": "..."}]}` |
| `500` | `{"error": "Erro ao buscar diretores"}` |

### `DELETE /api/directors/<nome>`

Remove o documento cujo `name` é igual ao nome informado.

| Código | Corpo |
|---|---|
| `200` | `{"message": "Diretor Jean-Luc Godard removido com sucesso"}` |
| `404` | `{"message": "Diretor Jean-Luc Godard não encontrado"}` |
| `500` | `{"error": "Erro ao deletar diretor"}` |

## Passo a passo interno

### Um diretor

1. Se o banco está indisponível, responde `500`.
2. Se o nome tem vírgula, segue para o fluxo de vários diretores.
3. Procura na coleção `directors` por `name` igual ao nome.
4. **Se achou:**
   1. Se o documento não tem foto e a requisição trouxe `tconst`, procura a foto no IMDB. Se achar,
      grava no documento.
   2. Se `language` não é `pt` e há biografia, traduz a biografia só para a resposta.
   3. Responde `200`.
5. **Se não achou:**
   1. Pede a biografia à OpenAI, em português.
   2. Se a requisição trouxe `tconst`, procura a foto no IMDB.
   3. Se a OpenAI não devolveu texto, responde `200` com a biografia genérica e
      `placeholder: true`, sem gravar.
   4. Se devolveu, grava `name`, `bio` e `photo`. Se `language` não é `pt`, traduz a biografia só
      para a resposta. Responde `200`.

### Vários diretores

1. Separa o texto por vírgula e remove espaços nas pontas. Nomes vazios são descartados.
2. Resolve cada nome pelo fluxo de um diretor, um de cada vez.
3. Se um nome falhar, entra na lista com a biografia genérica.
4. Monta a resposta combinada:
   - `name`: o texto original, com todos os nomes.
   - `bio`: `Nome: biografia` de cada diretor, separados por linha em branco.
   - `photo`: a foto do primeiro diretor da lista.
   - `directors`: a lista dos resultados individuais.
   - `placeholder: true`, se algum dos diretores veio com biografia genérica.
5. A resposta combinada não é gravada. O que fica no banco são os documentos individuais.

### Foto pelo IMDB

1. Baixa `https://www.imdb.com/title/<tconst>/` com um cabeçalho `User-Agent` de navegador e tempo
   limite de 3 segundos.
2. Procura no HTML um link `/name/nm<dígitos>/` cujo texto seja exatamente o nome do diretor, sem
   diferenciar maiúsculas.
3. Baixa `https://www.imdb.com/name/<id>/`, também com tempo limite de 3 segundos.
4. Procura a primeira URL de imagem em `m.media-amazon.com/images/M/` com o formato de miniatura
   (`_V1_UX..._CR0,0,...,..._AL_.jpg`). Se não houver, aceita a primeira URL `.jpg` desse domínio.

Qualquer falha em qualquer passo resulta em diretor sem foto. A resposta da rota não muda de status.

## Regras de negócio

### `placeholder: true`

A biografia genérica é o texto `Diretor de cinema conhecido por <nome>.` (ou
`Film director known for <nome>.` em inglês). Ela aparece quando não há `OPENAI_API_KEY`, quando a
chamada à OpenAI falha ou passa do tempo limite, ou quando a resposta vem vazia.

- A resposta traz `placeholder: true` e não tem `_id`.
- **Nada é gravado.** A próxima consulta ao mesmo diretor tenta gerar a biografia de novo. É isso que
  impede uma falha momentânea de virar o texto definitivo do diretor.
- A foto do IMDB, se foi encontrada, vai na resposta, mas também não é gravada nesse caso.
- O [cache de detalhe](movie-detail-cache.md) e a [pré-população](prepopulate.md) tratam
  `placeholder` como dado provisório: o primeiro não grava o cache, a segunda não conta como sucesso.

### Idioma

- A biografia gravada é sempre a canônica, em português. O prompt de geração pede português
  brasileiro, independentemente de `language`.
- Para `language=en`, a tradução é feita a cada requisição e não é guardada.
- Se a tradução falha ou não há chave, a resposta sai com a biografia em português, sem aviso.

### Foto

- A busca da foto só acontece quando há `tconst`.
- Para um diretor já gravado sem foto, a busca é repetida a cada requisição com `tconst`, até dar
  certo. Isso custa até duas requisições ao IMDB por chamada.
- Uma foto já gravada nunca é trocada por esta rota.

## Casos de borda

- **O nome é a chave.** A busca é por igualdade exata de `name`. `Jean-Luc Godard` e
  `jean-luc godard` são diretores diferentes e geram dois documentos.
- **Nome com vírgula sempre vira lista.** Não há como consultar um diretor cujo nome contenha vírgula.
- **Banco indisponível com vários diretores** responde `500`, porque a checagem vem antes da
  separação dos nomes.
- **Um diretor chamado `all`** não pode ser consultado: `/api/directors/all` é a rota de listagem.
- **O `DELETE` não trata vírgula.** Ele apaga o documento cujo `name` é o texto inteiro.
- **A biografia combinada** é montada da mesma forma em português e em inglês; o código tem dois
  ramos iguais.
- **O modelo `Director` do Swagger** lista `name`, `bio` e `photo`. Os campos `_id`, `placeholder` e
  `directors` não aparecem nele.
- **Não há índice único em `name` criado pelo código.** Duas requisições simultâneas para um diretor
  novo podem gravar dois documentos.

Os prompts, parâmetros e tempos limite das chamadas à OpenAI estão em
[integracoes.md](../integracoes.md).
