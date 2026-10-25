# define as tabelas do banco e os enums
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


def agora():
    return datetime.now(timezone.utc)


# --------- valores fixos (enums) --------
class Perfil(str, enum.Enum):
    CLIENTE = "CLIENTE"
    ATENDENTE = "ATENDENTE"
    COZINHA = "COZINHA"
    GERENTE = "GERENTE"


class CanalPedido(str, enum.Enum):
    APP = "APP"
    TOTEM = "TOTEM"
    BALCAO = "BALCAO"
    WEB = "WEB"
    PICKUP = "PICKUP"


class StatusPedido(str, enum.Enum):
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    PAGO = "PAGO"
    PREPARANDO = "PREPARANDO"
    PRONTO = "PRONTO"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"


# ---------- tabelas --------
class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    perfil = Column(Enum(Perfil), default=Perfil.CLIENTE)
    consentimento_lgpd = Column(Boolean, default=False)
    consentimento_em = Column(DateTime, nullable=True)  # data e hora em que o usuário aceitou o consentimento
    pontos_fidelidade = Column(Integer, default=0)


class Unidade(Base):
    __tablename__ = "unidades"
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    endereco = Column(String, nullable=False)


class Produto(Base):
    __tablename__ = "produtos"
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    preco = Column(Float, nullable=False)


# guarda a quantidade de cada produto em cada unidade
class Estoque(Base):
    __tablename__ = "estoques"
    __table_args__ = (UniqueConstraint("unidade_id", "produto_id"),)
    id = Column(Integer, primary_key=True)
    unidade_id = Column(Integer, ForeignKey("unidades.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade_disponivel = Column(Integer, default=0)
    produto = relationship("Produto")


class Pedido(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    unidade_id = Column(Integer, ForeignKey("unidades.id"), nullable=False)
    canal_pedido = Column(Enum(CanalPedido), nullable=False)
    status = Column(Enum(StatusPedido), default=StatusPedido.AGUARDANDO_PAGAMENTO)
    total = Column(Float, default=0)
    forma_pagamento = Column(String)
    observacoes = Column(String)
    created_at = Column(DateTime, default=agora)
    cliente = relationship("Usuario")
    itens = relationship("ItemPedido")


class ItemPedido(Base):
    __tablename__ = "itens_pedido"
    id = Column(Integer, primary_key=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False)  # guarda o preço do produto no momento da compra


# registra cada tentativa de pagamento de um pedido
class Pagamento(Base):
    __tablename__ = "pagamentos"
    id = Column(Integer, primary_key=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    valor = Column(Float, nullable=False)
    status = Column(String, nullable=False)  # APROVADO ou RECUSADO
    codigo_transacao = Column(String)
    created_at = Column(DateTime, default=agora)


class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    acao = Column(String, nullable=False)
    detalhes = Column(String)
    created_at = Column(DateTime, default=agora)
