# estado.py

class SimulacaoEstado:
    """
    Define o estado global da simulação, modelado a partir dos conceitos do Jogo Gorim.
    """
    def __init__(self, dinheiro_empresario_inicial: float, agricultores_info: dict):
        self.dinheiro_empresario = dinheiro_empresario_inicial
        self.agricultores = {}
        for agr_id, info in agricultores_info.items():
            self.agricultores[agr_id] = {
                "dinheiro": info.get("dinheiro", 0.0),
                "inventario": {"semente": [], "fertilizante": [], "agrotoxico": [], "maquina_alugada": []},
                "parcelas": {parcela_id: None for parcela_id in info.get("parcelas", [])},
                "produtividade_total": 0.0,
                "poluicao_gerada": 0
            }
        self.transacoes_registradas = []
        self.historico_negociacao = {}
        self.negociacao_em_andamento = {
            "oferta_ativa": False,
            "agricultor_id": None,
            "item": None,
            "quantidade": 0,
            "preco_proposto": 0.0,
            "ultimo_ofertante": None
        }

    def __repr__(self):
        status = "\n"
        status += "================================================\n"
        status += "=== ESTADO ATUAL DA SIMULAÇÃO (MODELO GORIM) ===\n"
        status += "================================================\n"
        status += f"\n[EMPRESÁRIO]\n"
        status += f"  - Dinheiro: R${self.dinheiro_empresario:.2f}\n"
        status += f"\n[NEGOCIAÇÃO EM ANDAMENTO]\n"
        status += f"  - {self.negociacao_em_andamento}\n"
        status += "\n[AGRICULTORES]\n"
        if not self.agricultores:
            status += "  Nenhum agricultor na simulação.\n"
        else:
            for agr_id, info in self.agricultores.items():
                status += f"  - Agricultor ID: {agr_id}\n"
                status += f"    - Dinheiro: R${info['dinheiro']:.2f}\n"
                status += f"    - Inventário: {info['inventario']}\n"
                status += f"    - Estado das Parcelas: {info['parcelas']}\n"
                status += f"    - Produtividade Total: R${info['produtividade_total']:.2f}\n"
                status += f"    - Poluição Total Gerada: {info['poluicao_gerada']}\n"
        status += f"\n[GERAL]\n"
        status += f"  - Total de Transações Registradas: {len(self.transacoes_registradas)}\n"
        status += "================================================\n"
        return status