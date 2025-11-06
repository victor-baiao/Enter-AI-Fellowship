import os
import json
from openai import OpenAI


class LlmClient:
    def __init__(self, model: str):
        try:
            self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        except TypeError:
            raise EnvironmentError("OPENAI_API_KEY não encontrada nas variáveis de ambiente.")

        self.model = model  # "gpt-5-mini" ou o nome real fornecido

    def _build_prompt(self, schema: dict, pdf_text: str) -> str:
        """
        Cria o prompt dinâmico para extração.
        """
        schema_str = json.dumps(schema, indent=2, ensure_ascii=False)

        prompt = f"""
        Você é um assistente de extração de dados altamente preciso.
        Extraia as informações do texto do documento fornecido.

        O formato de saída DEVE ser um JSON válido que obedece ao schema.
        Se uma informação não for encontrada, retorne 'null' para o campo.

        SCHEMA (com descrições):
        {schema_str}

        TEXTO DO DOCUMENTO:
        ---
        {pdf_text}
        ---

        JSON EXTRAÍDO:
        """
        return prompt

    def extract_with_llm(self, schema: dict, pdf_text: str) -> dict:
        """
        Chama a API da OpenAI e formata a resposta.
        """
        prompt = self._build_prompt(schema, pdf_text)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um extrator de dados JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )

            raw_output = response.choices[0].message.content
            json_output = json.loads(raw_output)

            final_result = {}
            for key in schema.keys():
                final_result[key] = json_output.get(key)

            return final_result

        except Exception as e:
            print(f"Erro na chamada do LLM: {e}")
            return {key: None for key in schema.keys()}
