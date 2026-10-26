import os
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from database import get_db
from erros import erro
import models

load_dotenv()  # lê o arquivo .env
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("Falta a SECRET_KEY. Copie o .env.example para .env")

# lê o token enviado no cabeçalho Authorization
esquema_bearer = HTTPBearer(auto_error=False)


# ---------- senha ----------
# Converte a senha do usuário em hash antes de salvar (A senha do usuário nunca é registrada no banco de dados)
def gerar_hash(senha):
    return bcrypt.hashpw(senha.encode()[:72], bcrypt.gensalt()).decode()


def conferir_senha(senha, senha_hash):
    return bcrypt.checkpw(senha.encode()[:72], senha_hash.encode())


# ---------- token ----------
def criar_token(usuario):
    expira = datetime.now(timezone.utc) + timedelta(minutes=60)
    return jwt.encode({"sub": str(usuario.id), "perfil": usuario.perfil.value, "exp": expira}, SECRET_KEY, algorithm="HS256")


# ---------- usuário logado ----------
def usuario_logado(credenciais=Depends(esquema_bearer), db: Session = Depends(get_db)):
    if not credenciais:
        raise erro(401, "NAO_AUTORIZADO", "Faça login para acessar.")
    try:
        dados = jwt.decode(credenciais.credentials, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise erro(401, "NAO_AUTORIZADO", "Token inválido ou expirado.")
    usuario = db.get(models.Usuario, int(dados["sub"]))
    if not usuario:
        raise erro(401, "NAO_AUTORIZADO", "Usuário não encontrado.")
    return usuario


# Esta função só libera o acesso à rota se o perfil do usuário logado estiver entre os perfis autorizados, caso contrário, retorna o erro 403
# exemplo: Depends(exige_perfis(models.Perfil.GERENTE))
def exige_perfis(*perfis):
    def verificar(usuario=Depends(usuario_logado)):
        if usuario.perfil not in perfis:
            raise erro(403, "SEM_PERMISSAO", "Seu perfil não tem permissão para acessar este recurso.")
        return usuario
    return verificar
