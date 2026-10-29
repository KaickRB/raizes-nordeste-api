from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import models, security
from database import get_db

# Rota do log de auditoria
router = APIRouter(prefix="/auditoria", tags=["Auditoria"])


# Lista os registros de auditoria, separando por páginas (Apenas o gerente possui acesso a esse recurso)
@router.get("/")
def listar_logs(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=50),
                db: Session = Depends(get_db), gerente=Depends(security.exige_perfis(models.Perfil.GERENTE))):
    query = db.query(models.LogAuditoria)
    # Mostra os registros mais recentes primeiro
    logs = query.order_by(models.LogAuditoria.id.desc()).offset((page - 1) * limit).limit(limit).all()
    data = [{"id": l.id, "usuario_id": l.usuario_id, "acao": l.acao, "detalhes": l.detalhes, "created_at": l.created_at} for l in logs]
    return {"total": query.count(), "page": page, "limit": limit, "data": data}
