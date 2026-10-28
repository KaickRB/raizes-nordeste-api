from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import models, schemas, security, services
from database import get_db
from erros import erro

router = APIRouter(prefix="/auth", tags=["Autenticação"])


# Ao fazer login, confere e-mail e senha e retorna o token
@router.post("/login")
def login(dados: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter_by(email=dados.email).first()
    # Será exibida a mesma mensagem pros dois erros, assim ninguém descobre quais e-mails já estão cadastrados
    if not usuario or not security.conferir_senha(dados.senha, usuario.senha_hash):
        raise erro(401, "NAO_AUTORIZADO", "E-mail ou senha incorretos.")
    # Guarda o login no log de auditoria
    services.registrar_log(db, usuario.id, "LOGIN", f"Login de {usuario.email}")
    db.commit()
    return {"access_token": security.criar_token(usuario), "token_type": "bearer"}
