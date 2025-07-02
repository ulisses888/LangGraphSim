# estado.py

class SimulacaoEstado:
    """
    Define o estado global da simulação, incluindo o dinheiro do empresário,
    informações dos fazendeiros e transações registradas.
    """

    def __init__(self, dinheiro_empresario_inicial: float, fazendeiros_info: dict):
        self.dinheiro_empresario = dinheiro_empresario_inicial
        # fazendeiros_info ex: {"Fz1": {"soja": 500.0, "dinheiro": 0.0}, ...}
        self.fazendeiros = fazendeiros_info
        self.transacoes_registradas = []
        self.historico_negociacao = {}  # Para manter o contexto da conversa com cada fazendeiro

    def __repr__(self):
        """Representação de string do estado atual da simulação."""
        status = (f"Estado Atual:\n"
                  f"  Empresário: R${self.dinheiro_empresario:.2f}\n")

        for faz_id, info in self.fazendeiros.items():
            status += f"  {faz_id}: {info['soja']}kg soja | R${info['dinheiro']:.2f}\n"

        status += f"  Transações: {len(self.transacoes_registradas)}"
        return status