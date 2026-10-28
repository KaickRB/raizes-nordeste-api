# funções contendo todas as regras dos pedidos: criar, pagar, mudar status e cancelar
import uuid
from sqlalchemy.orm import Session
import models
from erros import erro

FUNCIONARIOS_BALCAO = (models.Perfil.ATENDENTE, models.Perfil.GERENTE)

# Responsável por definir o próximo status do pedido permitido a partir do status atual
PROXIMO_STATUS = {
    models.StatusPedido.PAGO: models.StatusPedido.PREPARANDO,
    models.StatusPedido.PREPARANDO: models.StatusPedido.PRONTO,
    models.StatusPedido.PRONTO: models.StatusPedido.ENTREGUE,
}


# ---------- funções auxiliares ---------
def registrar_log(db: Session, usuario_id, acao, detalhes):
    db.add(models.LogAuditoria(usuario_id=usuario_id, acao=acao, detalhes=detalhes))


def buscar_estoque(db: Session, unidade_id, produto_id):
    return db.query(models.Estoque).filter_by(unidade_id=unidade_id, produto_id=produto_id).first()

# busca o pedido pelo id e bloqueia o acesso de quem não possui permissão para acessá-lo
def buscar_pedido(db: Session, pedido_id, usuario=None):
    pedido = db.get(models.Pedido, pedido_id)
    if not pedido:
        raise erro(404, "NAO_ENCONTRADO", "Pedido não encontrado.")
    # se o usuário não for o dono do pedido, atendente ou gerente, retorna o erro 403
    if usuario and pedido.cliente_id != usuario.id and usuario.perfil not in FUNCIONARIOS_BALCAO:
        raise erro(403, "SEM_PERMISSAO", "Você não tem permissão para acessar este pedido.")
    return pedido


def devolver_estoque(db: Session, pedido):
    for item in pedido.itens:
        estoque = buscar_estoque(db, pedido.unidade_id, item.produto_id)
        estoque.quantidade_disponivel += item.quantidade


# ---------- criar pedido --------
def criar_pedido(db: Session, dados, usuario):
    if not db.get(models.Unidade, dados.unidade_id):
        raise erro(404, "NAO_ENCONTRADO", "Unidade não existe.")

    # o pedido fica com quem está logado(a não ser que um atendente ou o gerente informe outro cliente)
    cliente_id = usuario.id
    if dados.clienteId and dados.clienteId != usuario.id:
        if usuario.perfil not in FUNCIONARIOS_BALCAO:
            raise erro(403, "SEM_PERMISSAO", "Só o atendente ou o gerente podem criar um pedido para outro cliente.")
        if not db.get(models.Usuario, dados.clienteId):
            raise erro(404, "NAO_ENCONTRADO", "Cliente não encontrado.")
        cliente_id = dados.clienteId

    total = 0
    itens = []
    for item in dados.itens:
        produto = db.get(models.Produto, item.produto_id)
        if not produto:
            raise erro(404, "NAO_ENCONTRADO", f"Produto {item.produto_id} não encontrado.")
        estoque = buscar_estoque(db, dados.unidade_id, item.produto_id)
        if not estoque or estoque.quantidade_disponivel < item.quantidade:
            raise erro(409, "ESTOQUE_INSUFICIENTE", f"Produto {item.produto_id} sem estoque nesta unidade.")
        estoque.quantidade_disponivel -= item.quantidade  # desconta a quantidade do estoque
        total += produto.preco * item.quantidade
        itens.append(models.ItemPedido(produto_id=produto.id, quantidade=item.quantidade, preco_unitario=produto.preco))

    pedido = models.Pedido(
        cliente_id=cliente_id, unidade_id=dados.unidade_id, canal_pedido=dados.canalPedido,
        total=round(total, 2), forma_pagamento=dados.formaPagamento, observacoes=dados.observacoes, itens=itens,
    )
    db.add(pedido)
    db.flush()  # envia o pedido ao banco de dados para gerar o id que é usado no log
    registrar_log(db, usuario.id, "CRIACAO_PEDIDO", f"Pedido {pedido.id} criado pelo canal: {pedido.canal_pedido.value}")
    db.commit()  # salva o pedido, os itens, o estoque e o log de uma vez só
    return pedido


# -------- pagamento (mock) ----------
def pagar_pedido(db: Session, dados, usuario):
    pedido = buscar_pedido(db, dados.pedido_id, usuario)
    # só aceita o pagamento de pedidos que estão aguardando pagamento(pedidos com pagamento aprovado ou cancelado não podem ser pagos novamente)
    if pedido.status != models.StatusPedido.AGUARDANDO_PAGAMENTO:
        raise erro(409, "PEDIDO_JA_PROCESSADO", f"Pedido com status {pedido.status.value} não aceita pagamento.")

    pagamento = models.Pagamento(
        pedido_id=pedido.id, valor=pedido.total, status=dados.resultado,
        codigo_transacao="MOCK-" + uuid.uuid4().hex[:8].upper(),
    )
    db.add(pagamento)

    if dados.resultado == "APROVADO":
        pedido.status = models.StatusPedido.PAGO
        pedido.cliente.pontos_fidelidade += int(pedido.total)  # soma 1 ponto a cada real gasto
        mensagem = "Pagamento aprovado. Pedido enviado para a cozinha."
    else:
        pedido.status = models.StatusPedido.CANCELADO
        devolver_estoque(db, pedido)
        mensagem = "Pagamento recusado. Pedido cancelado e estoque devolvido."

    registrar_log(db, usuario.id, "PAGAMENTO", f"Pedido {pedido.id}: {dados.resultado} (R$ {pedido.total})")
    db.commit()
    db.refresh(pagamento)
    return {
        "pagamento_id": pagamento.id, "pedido_id": pedido.id, "status_pagamento": pagamento.status,
        "status_pedido": pedido.status.value, "valor": pagamento.valor,
        "codigo_transacao": pagamento.codigo_transacao, "message": mensagem,
    }


# ---------- mudança de status ---------
def mudar_status(db: Session, pedido_id, novo_status, usuario):
    pedido = buscar_pedido(db, pedido_id)  # busca o pedido sem conferir o dono, porque esta rota já é restrita aos funcionários da lanchonete
    if PROXIMO_STATUS.get(pedido.status) != novo_status:
        raise erro(409, "TRANSICAO_INVALIDA", f"Não é possível mudar o status de {pedido.status.value} para {novo_status.value}, .")
    antigo = pedido.status.value
    pedido.status = novo_status
    registrar_log(db, usuario.id, "MUDANCA_STATUS", f"Pedido {pedido.id}: {antigo} -> {novo_status.value}")
    db.commit()
    return {"pedido_id": pedido.id, "status": pedido.status.value}


# ---------- cancelar ---------
# Cancela pedidos já pagos, ou que ainda estão aguardando pagamento
def cancelar_pedido(db: Session, pedido_id, usuario):
    pedido = buscar_pedido(db, pedido_id, usuario)
    if pedido.status not in (models.StatusPedido.AGUARDANDO_PAGAMENTO, models.StatusPedido.PAGO):
        raise erro(409, "CANCELAMENTO_INVALIDO", f"Pedido {pedido.status.value} não pode mais ser cancelado.")
    if pedido.status == models.StatusPedido.PAGO:  # remove os pontos de fidelidade que o cliente ganhou quando fez o pagamento anteriormente
        pedido.cliente.pontos_fidelidade = max(0, pedido.cliente.pontos_fidelidade - int(pedido.total))
    devolver_estoque(db, pedido)
    pedido.status = models.StatusPedido.CANCELADO
    registrar_log(db, usuario.id, "CANCELAMENTO_PEDIDO", f"Pedido {pedido.id} cancelado")
    db.commit()
    return {"pedido_id": pedido.id, "status": pedido.status.value}
