import re
from tinydb import TinyDB, Query
from llm_client import LlmClient  # Arquivo separado para chamadas de LLM


class HybridExtractor:
    def __init__(self, llm_model: str):
        # O KB armazena heurísticas (RegEx) aprendidas para cada label
        self.db = TinyDB('knowledge_base.json')
        self.kb = self.db.table('heuristics')
        # Cliente LLM
        self.llm = LlmClient(model=llm_model)

    def extract(self, label: str, schema: dict, pdf_text: str) -> dict:
        """
        Orquestra o processo de extração.
        """
        print(f"Iniciando extração para label: {label}")
        Label = Query()

        # 1. Tentar extrair com heurísticas locais (rápido e barato)
        learned_rules = self.kb.search(Label.label == label)

        if learned_rules:
            print("Knowledge Base hit. Tentando extração local.")
            rules = learned_rules[0].get('rules', {})
            result, success = self._apply_heuristics(schema, pdf_text, rules)

            if success:
                print("Sucesso na extração local.")
                return result
            else:
                print("Extração local falhou. Escalando para LLM.")
        else:
            print(f"Label '{label}' novo. Escalando para LLM.")

        # 2. Se as heurísticas falharem ou não existirem, usar o LLM
        llm_result = self.llm.extract_with_llm(schema, pdf_text)

        # 3. Aprender com o resultado do LLM
        self._learn_heuristics(label, schema, pdf_text, llm_result)

        return llm_result

    def _apply_heuristics(self, schema: dict, pdf_text: str, rules: dict) -> (dict, bool):
        """
        Aplica as regras de RegEx aprendidas.
        """
        extracted_data = {}
        all_found = True

        for field_name in schema.keys():
            if field_name in rules:
                regex_pattern = rules[field_name]
                match = re.search(regex_pattern, pdf_text, re.IGNORECASE | re.DOTALL)
                if match:
                    extracted_data[field_name] = match.group(1) if match.groups() else match.group(0)
                else:
                    extracted_data[field_name] = None
                    all_found = False
            else:
                all_found = False

        return extracted_data, all_found

    def _learn_heuristics(self, label: str, schema: dict, pdf_text: str, llm_result: dict):
        """
        Gera e salva novas heurísticas baseadas na saída do LLM.
        """
        print(f"Aprendendo novas heurísticas para {label}...")
        Label = Query()

        # Busca o registro de regras existente ou cria um novo
        rules_doc = self.kb.get(Label.label == label)
        if not rules_doc:
            self.kb.insert({'label': label, 'rules': {}})
            rules_doc = self.kb.get(Label.label == label)

        new_rules = rules_doc['rules']

        for field_name, extracted_value in llm_result.items():
            if extracted_value:
                # Cria um RegEx simples baseado no valor encontrado
                pattern = f"({re.escape(str(extracted_value))})"
                new_rules[field_name] = pattern

        # Atualiza o KB
        self.kb.update({'rules': new_rules}, Label.label == label)
        print(f"Heurísticas para {label} atualizadas.")
