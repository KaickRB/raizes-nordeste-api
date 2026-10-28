# Rotas de cadastro, perfil e pontos do usuário
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import models, schemas, security, services
from database import get_db
from erros import erro

router = APIRouter(prefix="/usuarios", tags=["Usuários e Fidelidade"])
VALOR_DO_PONTO = 0.10  # Cada ponto vale 10 centavos no resgate


# Cadastra um novo cliente
@router.post("/", status_code=201, response_model=schemas.UsuarioResposta)
def cadastrar(dados: schemas.UsuarioCadastro, db: Session = Depends(get_db)):
    # Se o cliente não aceitar o termo da LGPD, a conta não é criada
    if not dados.consentimento_lgpd:
        raise erro(422, "ERRO_DE_VALIDACAO", "É necessário aceitar o consentimento da LGPD.")
    # Impede que o mesmo e-mail seja cadastrado duas vezes
    if db.query(models.Usuario).filter_by(email=dados.email).first():
        raise erro(409, "CONFLITO", "Este e-mail já está em uso.")
    # Quem se cadastra por aqui, sempre irá entrar como cliente
    usuario = models.Usuario(
        nome=dados.nome, email=dados.email, senha_hash=security.gerar_hash(dados.senha),
        perfil=models.Perfil.CLIENTE, consentimento_lgpd=True, consentimento_em=datetime.now(timezone.utc),
    )
    db.add(usuario)
    db.commit()
    return usuario


# Exibe os dados do usuário que está logado
@router.get("/me", response_model=schemas.UsuarioResposta)
def meu_perfil(usuario=Depends(security.usuario_logado)):
    return usuario


# Exclui os dados pessoais da conta, mas mantém os pedidos salvos no banco de dados
@router.delete("/me")
def anonimizar_minha_conta(db: Session = Depends(get_db), usuario=Depends(security.usuario_logado)):
    usuario.nome = "Anônimo"
    usuario.email = f"anonimo{usuario.id}@anonimo.com"
    usuario.senha_hash = security.gerar_hash(uuid.uuid4().hex)  # Senha aleatória, para que ninguém mais consiga acessar a conta
    usuario.consentimento_lgpd = False
    services.registrar_log(db, usuario.id, "ANONIMIZACAO", "Conta anonimizada a pedido do titular")
    db.commit()
    return {"message": "Seus dados pessoais foram anonimizados."}


# Mostra quantos pontos o usuário tem
@router.get("/me/pontos")
def ver_pontos(usuario=Depends(security.usuario_logado)):
    return {"usuario": usuario.nome, "pontos_fidelidade": usuario.pontos_fidelidade}


# Troca pontos por desconto
@router.post("/me/resgatar-pontos")
def resgatar_pontos(dados: schemas.ResgatePontos, db: Session = Depends(get_db), usuario=Depends(security.usuario_logado)):
    if dados.pontos > usuario.pontos_fidelidade:
        raise erro(409, "PONTOS_INSUFICIENTES", "Você não tem pontos suficientes.")
    usuario.pontos_fidelidade -= dados.pontos
    desconto = round(dados.pontos * VALOR_DO_PONTO, 2)
    services.registrar_log(db, usuario.id, "RESGATE_PONTOS", f"{dados.pontos} pontos = R$ {desconto}")
    db.commit()
    return {"pontos_resgatados": dados.pontos, "desconto_gerado": desconto, "pontos_restantes": usuario.pontos_fidelidade}
