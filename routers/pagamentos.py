from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import schemas, security, services
from database import get_db

# Rota que realiza pagamentos simulados
router = APIRouter(prefix="/pagamentos", tags=["Pagamentos (mock)"])


# Registra o pagamento do pedido (como tudo é simulado, o resultado "APROVADO" ou "RECUSADO" é enviado no body)
@router.post("/", status_code=201)
def solicitar_pagamento(dados: schemas.PagamentoIn, db: Session = Depends(get_db), usuario=Depends(security.usuario_logado)):
    return services.pagar_pedido(db, dados, usuario)
