from fastapi import HTTPException


# Cria uma sinalização de erro padronizada sempre no mesmo formato.
# Exemplo: raise erro(404, "NAO_ENCONTRADO", "Pedido não encontrado.")
def erro(status, codigo, mensagem):
    return HTTPException(status_code=status, detail={"error": codigo, "message": mensagem})
