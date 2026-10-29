from datetime import datetime, timezone
from fastapi import FastAPI, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
import models, security
from database import engine, Base, get_db
from routers import auth, usuarios, unidades, estoque, pedidos, pagamentos, auditoria

# Cria as tabelas no banco de dados caso elas ainda não existam
Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Raízes do Nordeste", description="Projeto Multidisciplinar - Back-end", version="2.0.0")

# Adiciona na aplicação as rotas que estão na pasta routers
for rota in (auth, usuarios, unidades, estoque, pedidos, pagamentos, auditoria):
    app.include_router(rota.router)


# Monta a resposta de erro no mesmo formato para a API inteira
def resposta_de_erro(request, status, codigo, mensagem, detalhes=()):
    return JSONResponse(status_code=status, content={
        "error": codigo, "message": mensagem, "details": list(detalhes),
        "timestamp": datetime.now(timezone.utc).isoformat(), "path": request.url.path,
    })


# Trata os erros de dados que são inválidos ou estão faltando (erro 422) e mostra qual campo está incorreto
@app.exception_handler(RequestValidationError)
async def erro_de_validacao(request: Request, exc: RequestValidationError):
    detalhes = [{"field": ".".join(str(x) for x in e["loc"]), "issue": e["msg"]} for e in exc.errors()]
    return resposta_de_erro(request, 422, "ERRO_DE_VALIDACAO", "Dados incorretos. Corrija e tente novamente.", detalhes)


# Trata os outros erros: 401, 403,404, 409, etc.
@app.exception_handler(StarletteHTTPException)
async def erro_http(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict):
        return resposta_de_erro(request, exc.status_code, exc.detail["error"], exc.detail["message"])
    return resposta_de_erro(request, exc.status_code, "ERRO_REQUISICAO", str(exc.detail))


# Rota inicial para verificar se a API está rodando
@app.get("/")
def raiz():
    return {"message": "API Raízes do Nordeste rodando!"}


# Coloca dados fictícios para realizar testes no banco se ele estiver vazio (todas as senhas são "senha123")
@app.post("/seed", tags=["Testes"])
def seed(db: Session = Depends(get_db)):
    if db.query(models.Unidade).first():
        return {"message": "Banco já está populado."}
    matriz = models.Unidade(nome="Matriz Recife", endereco="Av. Boa Viagem, 1000")
    filial = models.Unidade(nome="Filial Olinda", endereco="Rua do Amparo, 50")
    tapioca = models.Produto(nome="Tapioca de Carne de Sol", preco=18.50)
    cuscuz = models.Produto(nome="Cuscuz Recheado", preco=14.00)
    db.add_all([matriz, filial, tapioca, cuscuz])
    db.commit()  # Salva para gerar os ids das unidades e dos produtos

    # Cadastra o estoque de cada uma das unidades
    db.add_all([
        models.Estoque(unidade_id=matriz.id, produto_id=tapioca.id, quantidade_disponivel=100),
        models.Estoque(unidade_id=matriz.id, produto_id=cuscuz.id, quantidade_disponivel=50),
        models.Estoque(unidade_id=filial.id, produto_id=tapioca.id, quantidade_disponivel=30),
    ])
    # Cria um usuário de cada perfil para realizar testes (todos com a mesma senha)
    senha = security.gerar_hash("senha123")
    agora = datetime.now(timezone.utc)
    for nome, email, perfil in [("João", "joao@gmail.com", models.Perfil.CLIENTE),
                                ("Chefe", "gerente@raizes.com", models.Perfil.GERENTE),
                                ("Cozinheira", "cozinha@raizes.com", models.Perfil.COZINHA),
                                ("Atendente", "atendente@raizes.com", models.Perfil.ATENDENTE)]:
        db.add(models.Usuario(nome=nome, email=email, senha_hash=senha, perfil=perfil,
                              consentimento_lgpd=True, consentimento_em=agora))
    db.commit()
    return {"message": "Banco populado! Usuários (senha senha123): joao@gmail.com, gerente@raizes.com, cozinha@raizes.com, atendente@raizes.com"}
