from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import models, schemas, security, services
from database import get_db

# Rotas de pedidos usadas para criar, consultar, listar, mudar status e cancelar pedidos
router = APIRouter(prefix="/pedidos", tags=["Pedidos"])
P = models.Perfil


# Cria um novo pedido para o usuário que está logado no sistema
@router.post("/", status_code=201, response_model=schemas.PedidoOut)
def criar_pedido(dados: schemas.PedidoIn, db: Session = Depends(get_db), usuario=Depends(security.usuario_logado)):
    return services.criar_pedido(db, dados, usuario)


# Lista todos os pedidos, com filtro opcional por canal e status do pedido
@router.get("/")
def listar_pedidos(
    canalPedido: Optional[models.CanalPedido] = Query(None, description="APP, TOTEM, BALCAO, WEB ou PICKUP"),
    status: Optional[models.StatusPedido] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    usuario=Depends(security.usuario_logado),
):
    query = db.query(models.Pedido)
    if usuario.perfil == P.CLIENTE:  # Se o usuário for cliente, mostra apenas os pedidos dele
        query = query.filter(models.Pedido.cliente_id == usuario.id)
    if canalPedido:
        query = query.filter(models.Pedido.canal_pedido == canalPedido)
    if status:
        query = query.filter(models.Pedido.status == status)
    # Exibe os pedidos mais recentes primeiro e separa de forma organizada por páginas
    pedidos = query.order_by(models.Pedido.id.desc()).offset((page - 1) * limit).limit(limit).all()
    data = [schemas.PedidoOut.model_validate(p) for p in pedidos]
    return {"total": query.count(), "page": page, "limit": limit, "data": data}


# Mostra um pedido específico
@router.get("/{pedido_id}", response_model=schemas.PedidoOut)
def consultar_pedido(pedido_id: int, db: Session = Depends(get_db), usuario=Depends(security.usuario_logado)):
    return services.buscar_pedido(db, pedido_id, usuario)


# Avança o status do pedido (apenas funcionários possuem acesso a essa opção)
@router.patch("/{pedido_id}/status")
def atualizar_status(pedido_id: int, dados: schemas.StatusIn, db: Session = Depends(get_db),
                     funcionario=Depends(security.exige_perfis(P.COZINHA, P.ATENDENTE, P.GERENTE))):
    return services.mudar_status(db, pedido_id, dados.status, funcionario)


# Cancela o pedido do cliente e devolve os itens ao estoque
@router.post("/{pedido_id}/cancelar")
def cancelar(pedido_id: int, db: Session = Depends(get_db), usuario=Depends(security.usuario_logado)):
    return services.cancelar_pedido(db, pedido_id, usuario)
