from fastapi import FastAPI, Request
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko_certvalidator import ValidationContext
from pyhanko.sign.validation import validate_pdf_signature
import io

app = FastAPI(title="Validador de Assinaturas ICP-Brasil")

@app.post("/validar-pdf")
async def validar_pdf(request: Request):
    try:
        # Lê os bytes puros enviados diretamente no corpo da requisição
        pdf_content = await request.body()
        
        if not pdf_content:
            return {"assinado": False, "status": "ERRO", "mensagem": "Nenhum conteúdo de arquivo recebido."}
            
        pdf_stream = io.BytesIO(pdf_content)
        
        # Configura o contexto de validação
        context = ValidationContext(allow_fetching=True)
        
        # Tenta ler o PDF para buscar assinaturas
        reader = IncrementalPdfFileWriter(pdf_stream).prev
        
        if not reader.embedded_signatures:
            return {"assinado": False, "status": "SEM_ASSINATURA", "mensagem": "Nenhuma assinatura digital encontrada no documento."}
        
        # Pega a assinatura mais recente
        ultima_assinatura = reader.embedded_signatures[-1]
        
        # Valida a assinatura criptográfica e a integridade
        status_validacao = await validate_pdf_signature(ultima_assinatura, vc=context)
        
        cert_info = status_validacao.signer_cert
        nome_assinante = cert_info.subject.human_friendly if cert_info else "Desconhecido"
        
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
