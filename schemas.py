from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field
from models import Perfil, CanalPedido, StatusPedido


# ---------- usuário ---------
class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str
    model_config = {"json_schema_extra": {"example": {"email": "joao@gmail.com", "senha": "senha123"}}}


class UsuarioCadastro(BaseModel):
    nome: str = Field(..., min_length=2)
    email: EmailStr
    senha: str = Field(..., min_length=6, max_length=72)
    consentimento_lgpd: bool  # o cadastro só é aceito se vier true
    model_config = {"json_schema_extra": {"example": {
        "nome": "Maria", "email": "maria@gmail.com", "senha": "senha123", "consentimento_lgpd": True}}}


# define os dados do usuário devolvidos na resposta (sem a senha_hash)
class UsuarioResposta(BaseModel):
    id: int
    nome: str
    email: EmailStr
    perfil: Perfil
    pontos_fidelidade: int
    model_config = {"from_attributes": True}


class ResgatePontos(BaseModel):
    pontos: int = Field(..., gt=0)


# --------- pedido ----------
class ItemIn(BaseModel):
    produto_id: int
    quantidade: int = Field(..., gt=0)  # aceita só valores maiores que zero


class PedidoIn(BaseModel):
    unidade_id: int
    canalPedido: CanalPedido # se o canal do pedido não for informado ou for inválido, o FastAPI irá recusar e retornar o erro 422
    itens: List[ItemIn] = Field(..., min_length=1)
    formaPagamento: str
    observacoes: Optional[str] = None
    clienteId: Optional[int] = None  # essa opção é usada quando o gerente ou um atendente fazem o pedido para um cliente
    model_config = {"json_schema_extra": {"example": {
        "unidade_id": 1, "canalPedido": "TOTEM", "itens": [{"produto_id": 1, "quantidade": 2}],
        "formaPagamento": "PIX", "observacoes": "Sem cebola"}}}


class ItemOut(BaseModel):
    produto_id: int
    quantidade: int
    preco_unitario: float
    model_config = {"from_attributes": True}


class PedidoOut(BaseModel):
    id: int
    cliente_id: int
    unidade_id: int
    canal_pedido: CanalPedido
    status: StatusPedido
    total: float
    forma_pagamento: Optional[str] = None
    observacoes: Optional[str] = None
    created_at: datetime
    itens: List[ItemOut]
    model_config = {"from_attributes": True}


class StatusIn(BaseModel):
    status: StatusPedido


# ---------- pagamento (mock) ---------
# O resultado define se o pagamento simulado foi aprovado ou recusado
class PagamentoIn(BaseModel):
    pedido_id: int
    resultado: Literal["APROVADO", "RECUSADO"]
    model_config = {"json_schema_extra": {"example": {"pedido_id": 1, "resultado": "APROVADO"}}}


# -------- estoque --------
class EstoqueEntrada(BaseModel):
    unidade_id: int
    produto_id: int
    quantidade: int = Field(..., gt=0)
