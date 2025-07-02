# ferramentas.py (Versão Final Corrigida e Robusta)

from langchain_core.tools import Tool
from typing import Dict, Any
from estado import SimulacaoEstado
import re


class FerramentasSimulacao:
    """
    Coleção de ferramentas que os agentes LLM podem usar para interagir com o estado da simulação.
    """

    def __init__(self, estado: SimulacaoEstado):
        self.estado = estado

    # MÉTODOS INTERNOS (não expostos diretamente como ferramentas)

    def verificar_dinheiro_empresario(self) -> float:
        """
        Retorna o saldo atual do empresário.
        """
        print(f"\nFerramenta: Empresário verificou dinheiro: R${self.estado.dinheiro_empresario:.2f}")
        return self.estado.dinheiro_empresario

    def verificar_estoque_fazendeiro(self, fazendeiro_id: str) -> float:
        """
        Retorna a quantidade de soja disponível de um fazendeiro.
        """
        estoque = self.estado.fazendeiros.get(fazendeiro_id, {}).get("soja", 0)
        print(f"\nFerramenta: Fazendeiro {fazendeiro_id} verificou estoque: {estoque:.2f}kg de soja")
        return estoque

    def registrar_transacao(self, comprador_id: str, vendedor_id: str, item: str, quantidade: float,
                            preco_total: float) -> str:
        """
        Lógica interna para registro de transação.
        """
        # Validação de IDs
        if comprador_id.lower() != "empresario":
            return "ERRO: Apenas o Empresario pode comprar"

        if vendedor_id not in self.estado.fazendeiros:
            return f"ERRO: Fazendeiro {vendedor_id} não existe"

        # Validação de recursos
        if self.estado.dinheiro_empresario < preco_total:
            return f"ERRO: Empresário não tem dinheiro suficiente (tem R${self.estado.dinheiro_empresario:.2f}, precisa R${preco_total:.2f})"

        if self.estado.fazendeiros[vendedor_id]["soja"] < quantidade:
            return f"ERRO: Fazendeiro não tem soja suficiente (tem {self.estado.fazendeiros[vendedor_id]['soja']:.2f}kg, precisa {quantidade:.2f}kg)"

        # Executa a transação
        self.estado.dinheiro_empresario -= preco_total
        self.estado.fazendeiros[vendedor_id]["soja"] -= quantidade
        self.estado.fazendeiros[vendedor_id]["dinheiro"] += preco_total

        self.estado.transacoes_registradas.append({
            "comprador": comprador_id,
            "vendedor": vendedor_id,
            "item": item,
            "quantidade": quantidade,
            "preco_total": preco_total
        })
        print(f"Ferramenta: Transação registrada com SUCESSO. Empresário: R${self.estado.dinheiro_empresario:.2f}")
        return "Transação de compra/venda registrada com SUCESSO."

    def obter_historico_negociacao(self, fazendeiro_id: str) -> str:
        """
        Retorna o histórico de negociação com o fazendeiro.
        """
        hist = self.estado.historico_negociacao.get(fazendeiro_id, "Nenhum histórico ainda.")
        print(f"\nFerramenta: Histórico para {fazendeiro_id}: {hist}")
        return hist

    # WRAPPERS PARA AS FERRAMENTAS COM TOOL

    # CORREÇÃO FINAL: Adicionado *args e **kwargs para ignorar argumentos extras que o agente possa passar
    def verificar_dinheiro_empresario_tool(self, *args, **kwargs) -> float:
        """
        Wrapper para verificar dinheiro do empresário. Ignora quaisquer argumentos recebidos.
        """
        return self.verificar_dinheiro_empresario()

    def verificar_estoque_fazendeiro_tool(self, fazendeiro_id: str) -> float:
        """
        Wrapper para verificar estoque de um fazendeiro. Recebe o fazendeiro_id como string.
        """
        return self.verificar_estoque_fazendeiro(fazendeiro_id)

    def registrar_transacao_tool(self, comando: str) -> str:
        """
        Espera comando no formato:
        Comprador: <id>, Vendedor: <id>, Item: <nome>, Quantidade: <valor>kg, Preço Total: <valor>
        Faz o parsing e chama registrar_transacao interna.
        """
        pattern = (
            r"(?i)comprador\s*:\s*(?P<comprador>\w+)[,;\s]*"
            r"vendedor\s*:\s*(?P<vendedor>\w+)[,;\s]*"
            r"item\s*:\s*(?P<item>\w+)[,;\s]*"
            r"quantidade\s*:\s*(?P<quantidade>[\d\.,]+)\s*kg[,;\s]*"
            r"pre[cç]o\s*total\s*:\s*[R\$\s]*(?P<preco>[\d\.,]+)"
        )

        m = re.search(pattern, comando)
        if not m:
            return "ERRO: formato inválido. Use 'Comprador: <id>, Vendedor: <id>, Item: <nome>, Quantidade: <valor>kg, Preço Total: <valor>'."

        comprador = m.group('comprador').strip()
        vendedor = m.group('vendedor').strip()
        item = m.group('item').strip().lower()

        try:
            quantidade_str = m.group('quantidade').replace(',', '.')
            quantidade = float(quantidade_str)

            preco_str = m.group('preco').replace(',', '.')
            preco_total = float(preco_str)
        except ValueError:
            return "ERRO: Valores numéricos inválidos. Use números com ponto ou vírgula como separador decimal."

        return self.registrar_transacao(comprador, vendedor, item, quantidade, preco_total)

    def obter_historico_negociacao_tool(self, comando: str) -> str:
        """
        Wrapper para obter histórico. Recebe fazendeiro_id como comando.
        """
        return self.obter_historico_negociacao(comando)

    def as_tool_list(self):
        return [
            Tool.from_function(
                name="verificar_dinheiro_empresario",
                description="Use para verificar seu saldo de dinheiro atual. Não requer argumentos.",
                func=self.verificar_dinheiro_empresario_tool,
            ),
            Tool.from_function(
                name="verificar_estoque_fazendeiro",
                description="Use para verificar o estoque de soja de um fazendeiro específico. Argumento: ID do fazendeiro (ex: 'Fz1').",
                func=self.verificar_estoque_fazendeiro_tool,
            ),
            Tool.from_function(
                name="registrar_transacao",
                description="Use para finalizar e registrar uma compra APÓS um acordo. O argumento DEVE estar no formato: 'Comprador: <id>, Vendedor: <id>, Item: Soja, Quantidade: <valor>kg, Preço Total: <valor>' (Ex: 'Comprador: Empresario, Vendedor: Fz1, Item: Soja, Quantidade: 500kg, Preço Total: 9500.00').",
                func=self.registrar_transacao_tool,
            ),
            Tool.from_function(
                name="obter_historico_negociacao",
                description="Use para ver o histórico da conversa com um fazendeiro. Argumento: ID do fazendeiro (ex: 'Fz1').",
                func=self.obter_historico_negociacao_tool,
            ),
        ]