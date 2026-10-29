from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import models
from database import get_db
from erros import erro

# Rotas das unidades e do cardápio de cada uma delas
router = APIRouter(prefix="/unidades", tags=["Unidades e Cardápio"])


# Lista todas as unidades cadastradas, separando por páginas
@router.get("/")
def listar_unidades(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    query = db.query(models.Unidade)
    unidades = query.offset((page - 1) * limit).limit(limit).all()
    data = [{"id": u.id, "nome": u.nome, "endereco": u.endereco} for u in unidades]
    return {"total": query.count(), "page": page, "limit": limit, "data": data}


# Monta o cardápio da unidade usando os produtos que ainda estão em estoque
@router.get("/{unidade_id}/cardapio")
def cardapio(unidade_id: int, db: Session = Depends(get_db)):
    unidade = db.get(models.Unidade, unidade_id)
    if not unidade:
        raise erro(404, "NAO_ENCONTRADO", "Unidade não existe.")
    # Busca produtos que ainda estão em estoque na unidade
    estoques = db.query(models.Estoque).filter(
        models.Estoque.unidade_id == unidade_id, models.Estoque.quantidade_disponivel > 0).all()
    itens = [{"produto_id": e.produto.id, "nome": e.produto.nome, "preco": e.produto.preco} for e in estoques]
    return {"unidade": unidade.nome, "cardapio": itens}
