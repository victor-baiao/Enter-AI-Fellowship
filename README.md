# Take-Home Project: ENTER AI Fellowship

## 1. Visão Geral da Solução

O objetivo deste projeto é criar um sistema de extração de dados de PDFs que seja rápido (menos de 10 segundos por requisição), preciso (acima de 80%), e de baixo custo.

A solução proposta é um **Sistema Híbrido de Extração com Aprendizado Contínuo**. Esta arquitetura evita chamar o LLM (nosso maior custo) em todas as requisições. O LLM é tratado não como o extrator principal, mas como um "professor" que ensina nosso sistema a extrair dados de layouts que ele nunca viu antes.

O sistema armazena conhecimento sobre cada `label` que processa.

1.  **Primeira Vez (Modo "Professor"):** Na primeira vez que um `label` é visto, o sistema não sabe como extrair os dados. Ele envia o texto do PDF e o `extraction_schema` para o LLM (`gpt-5 mini`). O LLM faz a extração "lenta e cara".
2.  **Aprendizado:** O sistema armazena o resultado do LLM. Mais importante, ele também analisa o texto do PDF e tenta gerar **regras heurísticas** (como RegEx ou "âncoras" de texto) para encontrar aqueles dados no futuro.
3.  **Vezes Futuras (Modo "Aluno Rápido"):** Na próxima vez que o mesmo `label` é recebido, o sistema **não** chama o LLM. Ele primeiro aplica suas regras heurísticas e de cache. Esta extração local é quase instantânea e tem custo zero.
4.  **Auto-Correção:** Se as heurísticas falharem (ex: o layout mudou levemente), o sistema recorre ao LLM (Modo "Professor") e atualiza suas regras.

## 2. Desafios Mapeados e Soluções Propostas

Conforme solicitado, esta seção detalha os desafios e as soluções aplicadas.

### Desafio 1: Custo e Tempo (Balanceamento Custo vs. Precisão)

- **Problema:** Chamadas de LLM são lentas e caras. Não podemos chamar o LLM para cada um dos "milhares de documentos". Otimizar o custo é essencial.
- **Solução:** Implementação de um **"Knowledge Base" (KB)** por `label`.
  - **Cache de Heurísticas:** O KB (um simples banco de dados local) armazena heurísticas (RegEx, padrões) aprendidas. Por exemplo, para o `label: "carteira_oab"`, ele pode aprender que o campo `inscricao` corresponde ao RegEx.
  - **Redução de Custo:** A chamada ao LLM só ocorre se (a) o `label` é novo ou (b) as heurísticas salvas falham na extração do `extraction_schema` solicitado. Isso está alinhado com as estratégias sugeridas para reduzir chamadas ao LLM.

### Desafio 2: Variabilidade de Layout e Schemas Parciais

- **Problema:** O mesmo `label` pode ter layouts levemente diferentes. Além disso, não conhecemos o `schema` completo de antemão, apenas partes dele.
- **Solução:** O KB é projetado para "acumular conhecimento".
  - Quando um `label: "RG"` é visto pela primeira vez com `schema: {nome, nome_mae}`, o sistema aprende as regras para `nome` e `nome_mae`.
  - Quando o `label: "RG"` aparece de novo com `schema: {nome, nome_pai}`, o sistema já sabe como extrair `nome` (usando heurística) e só precisa usar o LLM para aprender a extrair `nome_pai`.
  - Isso otimiza o _contexto_ enviado ao LLM, pedindo apenas os campos que "faltam" em nosso KB, minimizando ainda mais o custo.

### Desafio 3: Requisitos de Desempenho (<10s, >80% Acc)

- **Problema:** O sistema precisa ser rápido e preciso.
- **Solução:**
  - **Tempo (<10s):** A extração baseada em heurística/cache é síncrona e leva milissegundos. A chamada ao LLM (o "pior caso") é a única que se aproxima do limite de 10 segundos. Como isso só acontece na _primeira_ visualização de um `label`, o tempo _médio_ de resposta será extremamente baixo.
  - **Precisão (>80%):** O LLM atua como a fonte da verdade para a precisão. Nossas heurísticas são geradas para replicar exatamente a saída do LLM. Se um campo não é encontrado pela heurística, ele é marcado como `null`, e o sistema pode "escalar" para o LLM se a taxa de acerto cair.

## 3. Como Utilizar a Solução

Esta solução é entregue como um endpoint de API construído com FastAPI, o que permite fácil interação e testes.

### Dependências

- `fastapi`: Para a criação da API.
- `uvicorn`: Para executar o servidor.
- `openai`: Para se comunicar com o modelo `gpt-5 mini`.
- `pypdf`: Para extrair o texto do PDF (já que o OCR está pronto).
- `tinydb`: Para o "Knowledge Base" local de heurísticas.

### Executando a API

1.  **Clone o repositório:**

    ```bash
    git clone [https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git](https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git)
    cd SEU_REPOSITORIO
    ```

2.  **Instale as dependências:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure sua API Key da OpenAI:**
    (Você receberá uma API key com limite de budget)

    ```bash
    export OPENAI_API_KEY="SUA_API_KEY_AQUI"
    ```

4.  **Inicie o servidor:**
    ```bash
    uvicorn main:app --reload
    ```
    O servidor estará rodando em `http://127.0.0.1:8000`.

### Endpoint de Extração

`POST /extract`

A requisição deve ser `multipart/form-data` e conter os seguintes campos:

1.  `label` (string)
2.  `extraction_schema` (string JSON)
3.  `pdf` (arquivo PDF)

**Exemplo de Requisição (usando `curl`):**

```bash
curl -X POST "[http://127.0.0.1:8000/extract](http://127.0.0.1:8000/extract)" \
-F "label=carteira_oab" \
-F "extraction_schema={\"nome\": \"Nome do profissional\", \"inscricao\": \"Número de inscrição\"}" \
-F "pdf=@/caminho/para/exemplo1.pdf"
```
