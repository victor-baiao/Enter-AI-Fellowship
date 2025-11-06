import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from typing import Annotated
import pypdf
import io

from extractor import HybridExtractor

app = FastAPI(title="ENTER AI Extraction Service")
extractor = HybridExtractor(llm_model="gpt-5-mini")  # O nome real do modelo seria "gpt-5 mini"


@app.post("/extract")
async def extract_data(
    label: Annotated[str, Form()],
    extraction_schema: Annotated[str, Form()],
    pdf: Annotated[UploadFile, File()]
):
    """
    Recebe um label, um schema JSON e um arquivo PDF para extração de dados.
    """
    try:
        # 1. Validar e carregar o extraction_schema
        try:
            schema = json.loads(extraction_schema)
            if not isinstance(schema, dict):
                raise ValueError("extraction_schema must be a JSON object (dict).")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid extraction_schema JSON.")

        # 2. Ler o conteúdo do PDF
        # O PDF já tem OCR, então só extraímos o texto
        pdf_content = await pdf.read()
        pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_content))

        # Restrição: PDF possui apenas uma página
        if len(pdf_reader.pages) == 0:
            raise HTTPException(status_code=400, detail="PDF is empty or corrupted.")

        pdf_text = pdf_reader.pages[0].extract_text()

        # 3. Chamar o extrator híbrido
        extracted_data = extractor.extract(label, schema, pdf_text)

        return extracted_data

    except Exception as e:
        # Tratar outros erros
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
