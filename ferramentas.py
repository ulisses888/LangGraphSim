# ferramentas.py (VERSÃO CORRIGIDA)

from langchain_core.tools import tool
from estado import SimulacaoEstado
import traceback

_estado_global = None
_catalogo_global = None


def definir_recursos_globais(estado: SimulacaoEstado):
    global _estado_global, _catalogo_global
    _estado_global = estado
    _catalogo_global = {
        "semente": {"soja": 30, "arroz": 20, "hortalica": 10},
        "fertilizante": {"fertilizante-comum": 30, "fertilizante-premium": 60, "fertilizante-super-premium": 90},
        "agrotoxico": {"agrotoxico-comum": 30, "agrotoxico-premium": 60, "agrotoxico-super-premium": 90},
        "maquina": {"pacote1": 30, "pacote2": 60, "pacote3": 90, "pulverizador": 400}
    }


def _realizar_compra(agricultor_id: str, categoria_item: str, nome_item: str, preco_final: float,
                     quantidade: int = 1) -> str:
    try:
        if agricultor_id not in _estado_global.agricultores: return f"ERRO: Agricultor com ID '{agricultor_id}' não existe."
        dinheiro_agricultor = _estado_global.agricultores[agricultor_id]["dinheiro"]
        if dinheiro_agricultor < preco_final:
            return (f"ERRO: Dinheiro insuficiente. Custo: R${preco_final:.2f}, Saldo: R${dinheiro_agricultor:.2f}")

        _estado_global.agricultores[agricultor_id]["dinheiro"] -= preco_final
        _estado_global.dinheiro_empresario += preco_final

        chave_inventario = "maquina_alugada" if categoria_item == "maquina" else categoria_item
        _estado_global.agricultores[agricultor_id]['inventario'][chave_inventario].append(nome_item)
        transacao = {"comprador": agricultor_id, "vendedor": "Empresario", "item": nome_item, "quantidade": quantidade,
                     "preco_total": preco_final}
        _estado_global.transacoes_registradas.append(transacao)
        print(f"\n[FERRAMENTA] Transação bem-sucedida: {transacao}")
        return f"SUCESSO: Venda de {quantidade} de {nome_item} para {agricultor_id} por R${preco_final:.2f} concluída."
    except Exception:
        return f"ERRO INESPERADO NA FERRAMENTA: {traceback.format_exc()}"


@tool
def consultar_inventario(agricultor_id: str) -> dict:
    """Use para verificar os itens que você possui atualmente E as parcelas de terra sob sua responsabilidade, indicando quais estão vazias. É sua primeira ação em todo turno."""
    if agricultor_id in _estado_global.agricultores:
        inventario_e_parcelas = {
            "inventario": _estado_global.agricultores[agricultor_id]['inventario'],
            "parcelas": _estado_global.agricultores[agricultor_id]['parcelas']
        }
        return inventario_e_parcelas
    return {"erro": "Agricultor não encontrado."}


@tool
def fazer_oferta(agricultor_id: str, tipo_item: str, quantidade: int, preco_proposto: float) -> str:
    """Use esta ferramenta para iniciar uma negociação, propondo um preço para um insumo."""
    _estado_global.negociacao_em_andamento = {
        "oferta_ativa": True,
        "agricultor_id": agricultor_id,
        "item": tipo_item,
        "quantidade": quantidade,
        "preco_proposto": preco_proposto,
        "ultimo_ofertante": "Agricultor"
    }
    return f"OFERTA ENVIADA. Sua proposta de R${preco_proposto:.2f} pelo item '{tipo_item}' foi enviada. AGUARDE A RESPOSTA DO EMPRESÁRIO."


@tool
def plantar_semente(agricultor_id: str, parcela_id: str, tipo_semente: str, pacote_maquina: str,
                    tipo_fertilizante: str = None, tipo_agrotoxico: str = None) -> str:
    """Ação final para plantar. Requer uma semente e um pacote de máquina. Opcionalmente, pode-se usar fertilizante e agrotóxico (que requer um pulverizador)."""
    try:
        if agricultor_id not in _estado_global.agricultores: return f"ERRO: Agricultor com ID '{agricultor_id}' não existe."
        inventario = _estado_global.agricultores[agricultor_id]["inventario"]
        parcelas_agricultor = _estado_global.agricultores[agricultor_id]["parcelas"]
        if parcela_id not in parcelas_agricultor: return f"ERRO: Parcela '{parcela_id}' não pertence ao agricultor '{agricultor_id}'."
        if tipo_semente not in inventario[
            "semente"]: return f"ERRO: Semente '{tipo_semente}' não encontrada no inventário."
        if pacote_maquina not in inventario[
            "maquina_alugada"]: return f"ERRO: Pacote de máquina '{pacote_maquina}' não encontrado no inventário. Alugue um primeiro."
        if tipo_agrotoxico and "pulverizador" not in inventario[
            "maquina_alugada"]: return f"ERRO: Para usar agrotóxico, você precisa alugar um 'pulverizador'."
        if tipo_fertilizante and tipo_fertilizante not in inventario[
            "fertilizante"]: return f"ERRO: Fertilizante '{tipo_fertilizante}' não encontrado no inventário."
        if tipo_agrotoxico and tipo_agrotoxico not in inventario[
            "agrotoxico"]: return f"ERRO: Agrotóxico '{tipo_agrotoxico}' não encontrado no inventário."
        if parcelas_agricultor[parcela_id] is not None: return f"ERRO: A parcela '{parcela_id}' já está plantada."

        inventario["semente"].remove(tipo_semente)
        if tipo_fertilizante: inventario["fertilizante"].remove(tipo_fertilizante)
        if tipo_agrotoxico: inventario["agrotoxico"].remove(tipo_agrotoxico)

        produtividade = 50
        poluicao = {"soja": 30, "arroz": 20, "hortalica": 10}.get(tipo_semente, 15)
        produtividade += {"pacote1": 25, "pacote2": 60, "pacote3": 150}.get(pacote_maquina, 0)
        produtividade += {"fertilizante-comum": 50, "fertilizante-premium": 120, "fertilizante-super-premium": 250}.get(
            tipo_fertilizante, 0)
        if tipo_agrotoxico:
            bonus_agro = {"agrotoxico-comum": 200, "agrotoxico-premium": 500, "agrotoxico-super-premium": 1000}.get(
                tipo_agrotoxico, 0)
            produtividade += bonus_agro
            if tipo_semente == 'soja':
                produtividade *= 3
            elif tipo_semente == 'arroz':
                produtividade *= 2
            poluicao += {"agrotoxico-comum": 100, "agrotoxico-premium": 150, "agrotoxico-super-premium": 250}.get(
                tipo_agrotoxico, 50)
            if "pulverizador" in inventario["maquina_alugada"]: poluicao /= 2

        _estado_global.agricultores[agricultor_id]["produtividade_total"] += produtividade
        _estado_global.agricultores[agricultor_id]["poluicao_gerada"] += int(poluicao)
        _estado_global.agricultores[agricultor_id]["parcelas"][parcela_id] = f"{tipo_semente}"
        print(f"\n[FERRAMENTA] Plantio bem-sucedido na parcela {parcela_id}.")
        return f"SUCESSO: Você plantou {tipo_semente}. Produtividade desta colheita: R${produtividade:.2f}. Poluição gerada: {int(poluicao)}."
    except Exception:
        return f"ERRO INESPERADO: {traceback.format_exc()}"


@tool
def aceitar_oferta() -> str:
    """Use esta ferramenta para aceitar la oferta atual feita pelo agricultor. Isso finalizará a transação."""
    try:
        negociacao = _estado_global.negociacao_em_andamento
        if not negociacao['oferta_ativa']: return "ERRO: Não há nenhuma oferta ativa para aceitar."

        agr_id = negociacao['agricultor_id']
        preco_final = negociacao['preco_proposto']
        item_nome = negociacao['item']
        quantidade = negociacao['quantidade']

        categoria_item = None
        for cat, itens in _catalogo_global.items():
            if item_nome in itens:
                categoria_item = cat
                break
        if not categoria_item: return f"ERRO: Item '{item_nome}' não encontrado no catálogo."

        resultado_compra = _realizar_compra(agr_id, categoria_item, item_nome, preco_final, quantidade)

        _estado_global.negociacao_em_andamento = {"oferta_ativa": False, "ultimo_ofertante": None,
                                                  "agricultor_id": None, "item": None, "quantidade": 0,
                                                  "preco_proposto": 0.0}
        return resultado_compra
    except Exception:
        return f"ERRO INESPERADO: {traceback.format_exc()}"


@tool
def rejeitar_oferta() -> str:
    """Use esta ferramenta para rejeitar e descartar la oferta atual do agricultor."""
    if not _estado_global.negociacao_em_andamento[
        'oferta_ativa']: return "ERRO: Não há nenhuma oferta ativa para rejeitar."

    agr_id = _estado_global.negociacao_em_andamento['agricultor_id']
    msg = f"Sua oferta foi rejeitada pelo empresário. A negociação sobre o item '{_estado_global.negociacao_em_andamento['item']}' foi encerrada."

    _estado_global.negociacao_em_andamento = {"oferta_ativa": False, "ultimo_ofertante": "Empresario",
                                              "agricultor_id": agr_id, "item": None, "quantidade": 0,
                                              "preco_proposto": 0.0}
    print(f"\n[FERRAMENTA] Oferta REJEITADA.")
    return msg


@tool
def fazer_contra_oferta(novo_preco: float) -> str:
    """Use esta ferramenta para rejeitar la oferta do agricultor e propor um novo preço."""
    try:
        negociacao = _estado_global.negociacao_em_andamento
        if not negociacao['oferta_ativa']: return "ERRO: Não há oferta ativa para fazer uma contra-proposta."
        if negociacao[
            'ultimo_ofertante'] == 'Empresario': return "ERRO: Você já fez uma contra-proposta. Aguarde a resposta do agricultor."

        negociacao['preco_proposto'] = novo_preco
        negociacao['ultimo_ofertante'] = 'Empresario'

        print(f"\n[FERRAMENTA] Contra-oferta feita pelo Empresário: novo preço R${novo_preco:.2f}.")
        return f"SUCESSO: Sua contra-oferta de R${novo_preco:.2f} foi enviada ao agricultor."
    except Exception:
        return f"ERRO INESPERADO: {traceback.format_exc()}"