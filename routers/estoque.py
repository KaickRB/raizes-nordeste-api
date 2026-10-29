# Rotas para entrada e consulta de estoque
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import models, schemas, security, services
from database import get_db
from erros import erro

router = APIRouter(prefix="/estoque", tags=["Estoque"])
P = models.Perfil


# Adiciona a quantidade de um produto no estoque da unidade (Função disponível apenas para o gerente)
@router.post("/entrada")
def entrada_de_estoque(dados: schemas.EstoqueEntrada, db: Session = Depends(get_db),
                       gerente=Depends(security.exige_perfis(P.GERENTE))):
    if not db.get(models.Unidade, dados.unidade_id) or not db.get(models.Produto, dados.produto_id):
        raise erro(404, "NAO_ENCONTRADO", "Unidade ou produto não existe.")
    estoque = services.buscar_estoque(db, dados.unidade_id, dados.produto_id)
    # Se a unidade ainda não tiver o produto, um estoque zerado será criado para que o produto fique registrado e novas adições possam ser feitas futuramente
    if not estoque:
        estoque = models.Estoque(unidade_id=dados.unidade_id, produto_id=dados.produto_id, quantidade_disponivel=0)
        db.add(estoque)
    estoque.quantidade_disponivel += dados.quantidade
    # Guarda a entrada no log da auditoria
    services.registrar_log(db, gerente.id, "ENTRADA_ESTOQUE", f"+{dados.quantidade} do produto {dados.produto_id} na unidade {dados.unidade_id}")
    db.commit()
    return {"unidade_id": dados.unidade_id, "produto_id": dados.produto_id, "quantidade_disponivel": estoque.quantidade_disponivel}


# Mostra a quantidade de cada produto existente na unidade (Função liberada para gerentes e atendentes)
@router.get("/{unidade_id}")
def saldo_da_unidade(unidade_id: int, db: Session = Depends(get_db),
                     usuario=Depends(security.exige_perfis(P.GERENTE, P.ATENDENTE))):
    if not db.get(models.Unidade, unidade_id):
        raise erro(404, "NAO_ENCONTRADO", "Unidade não existe.")
    estoques = db.query(models.Estoque).filter_by(unidade_id=unidade_id).all()
    return [{"produto_id": e.produto_id, "nome": e.produto.nome, "quantidade_disponivel": e.quantidade_disponivel} for e in estoques]
