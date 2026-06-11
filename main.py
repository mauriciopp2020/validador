from fastapi import FastAPI, UploadFile, File
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko_certvalidator import ValidationContext
from pyhanko.sign.validation import validate_pdf_signature
import io

app = FastAPI(title="Validador de Assinaturas ICP-Brasil")

@app.post("/validar-pdf")
async def validar_pdf(file: UploadFile = File(...)):
    try:
        # Lê o arquivo enviado pelo Apps Script na memória
        pdf_content = await file.read()
        pdf_stream = io.BytesIO(pdf_content)
        
        # Configura o contexto de validação (baixa a cadeia de confiança se necessário)
        # Para produção ICP-Brasil, o ideal é carregar as raízes da ITI aqui
        context = ValidationContext(allow_fetching=True)
        
        # Tenta ler o PDF para buscar assinaturas
        reader = IncrementalPdfFileWriter(pdf_stream).prev
        
        if not reader.embedded_signatures:
            return {"assinado": False, "mensagem": "Nenhuma assinatura digital encontrada no documento."}
        
        # Pega a assinatura mais recente (ou itera por todas se houver mais de uma)
        ultima_assinatura = reader.embedded_signatures[-1]
        
        # Valida a assinatura criptográfica e a integridade do arquivo
        status_validacao = await validate_pdf_signature(ultima_assinatura, vc=context)
        
        # Extrai os dados do assinante (Common Name do certificado)
        cert_info = status_validacao.signer_cert
        nome_assinante = cert_info.subject.human_friendly if cert_info else "Desconhecido"
        
        # Verifica a integridade do documento (se foi alterado após ser assinado)
        integro = status_validacao.intact and status_validacao.valid
        
        if integro:
            return {
                "assinado": True,
                "status": "VALIDO",
                "assinante": nome_assinante,
                "mensagem": "Assinatura válida e documento íntegro."
            }
        else:
            return {
                "assinado": True,
                "status": "INVALIDO",
                "assinante": nome_assinante,
                "mensagem": "Assinatura encontrada, mas o documento foi alterado ou o certificado é inválido."
            }
            
    except Exception as e:
        return {"assinado": False, "status": "ERRO", "mensagem": f"Erro ao processar o PDF: {str(e)}"}
