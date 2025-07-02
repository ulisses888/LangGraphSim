# simulacao.py (Corrigido)

from langgraph.graph import StateGraph, END
from agentes import inicializar_agentes
from estado import SimulacaoEstado
from ferramentas import FerramentasSimulacao
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import re

# --- Configuração do LLM ---
llm = ChatOpenAI(
    model="local-model",
    openai_api_base="http://localhost:1234/v1",
    temperature=0.7,
    api_key="lm-studio"
)


# --- Definição do Estado do Grafo ---
class GraphState(dict):
    messages: list[BaseMessage]
    next_fazendeiro_idx: int
    current_fazendeiro_id: str
    simulacao_estado: SimulacaoEstado
    negociacao_ativa: bool
    next_action: str = ""
    iteracoes_negociacao: int = 0  # Contador de iterações por negociação


# --- Função Auxiliar para Limpar Saída ---
def _limpar_saida_agente(texto_original: str) -> str:
    """Remove o bloco de pensamento <think> da saída do agente, retornando apenas a resposta final."""
    match = re.search(r"</think>(.*)", texto_original, re.DOTALL)
    if match:
        # Pega o texto após a última tag </think> e remove espaços em branco
        return match.group(1).strip()
    return texto_original.strip()


# --- Funções dos Nós do Grafo ---

def empresario_node(state: GraphState):
    sim_estado = state["simulacao_estado"]
    faz_id = state["current_fazendeiro_id"]

    input_text = (
        f"Sua vez de negociar com o Fazendeiro {faz_id}. "
        f"Lembre-se: você tem R${sim_estado.dinheiro_empresario:.2f} e ele tem {sim_estado.fazendeiros[faz_id]['soja']:.2f}kg."
    )
    executor = agentes["Empresario"]
    result = executor.invoke({
        "input": input_text,
        "chat_history": state["messages"]
    })
    # Limpa a saída antes de adicionar ao histórico
    resp_limpa = _limpar_saida_agente(result.get("output", ""))
    state["messages"].append(AIMessage(content=resp_limpa, name="Empresario"))

    # Log detalhado
    print(f"\n[EMPRESARIO] Iteração: {state['iteracoes_negociacao']}")
    print(f"Entrada: {input_text[:100]}...")
    print(f"Saída: {resp_limpa[:100]}...")

    return state


def fazendeiro_node(state: GraphState):
    sim_estado = state["simulacao_estado"]
    faz_id = state["current_fazendeiro_id"]

    last_message = state["messages"][-1].content
    input_text = (
        f"O empresário disse: '{last_message}'. Responda como Fazendeiro {faz_id}. "
        f"Lembre-se: você tem {sim_estado.fazendeiros[faz_id]['soja']:.2f}kg."
    )
    executor = agentes[f"Fazendeiro {faz_id}"]
    result = executor.invoke({
        "input": input_text,
        "chat_history": state["messages"]
    })
    # Limpa a saída antes de adicionar ao histórico
    resp_limpa = _limpar_saida_agente(result.get("output", ""))
    state["messages"].append(AIMessage(content=resp_limpa, name=faz_id))

    # Log detalhado
    print(f"\n[FAZENDEIRO {faz_id}] Iteração: {state['iteracoes_negociacao']}")
    print(f"Entrada: {input_text[:100]}...")
    print(f"Saída: {resp_limpa[:100]}...")

    return state


def decide_proxima_acao(state: GraphState):
    # CORREÇÃO: Contador de iteração é simplesmente incrementado.
    state["iteracoes_negociacao"] += 1
    print(f"\n[DECISÃO] Iteração: {state['iteracoes_negociacao']}")

    # Verificar limite de iterações
    if state["iteracoes_negociacao"] > 10:
        print(f"--- Limite de iterações excedido com {state['current_fazendeiro_id']} ---")
        state["negociacao_ativa"] = False
        state["next_action"] = "finalizar_ou_proximo"
        state["iteracoes_negociacao"] = 0  # Reseta para a próxima negociação
        return state

    last_agent_message = ""
    # Garante que a mensagem seja uma string antes de chamar .lower()
    if state["messages"] and isinstance(state["messages"][-1], AIMessage):
        last_agent_message = state["messages"][-1].content.lower()

    if "transação de compra/venda registrada com sucesso" in last_agent_message:
        print(f"--- Transação concluída! ---")
        state["negociacao_ativa"] = False
        state["next_action"] = "finalizar_ou_proximo"
    elif "desisto da negociação" in last_agent_message:
        print(f"--- Desistência de negociação. ---")
        state["negociacao_ativa"] = False
        state["next_action"] = "finalizar_ou_proximo"
    else:
        last_sender = state["messages"][-1].name
        if last_sender == "Empresario":
            state["next_action"] = "resposta_fazendeiro"
        else:
            state["next_action"] = "resposta_empresario"

    print(f"Próxima ação: {state['next_action']}")
    return state


def verificar_proximo_fazendeiro(state: GraphState):
    sim_estado = state["simulacao_estado"]
    ids = list(sim_estado.fazendeiros.keys())
    idx = state["next_fazendeiro_idx"]

    if idx < len(ids):
        curr = ids[idx]
        print(f"\n--- Iniciando negociação com {curr} ({idx + 1}/{len(ids)}) ---")
        initial_message = HumanMessage(content=f"Iniciando negociação com {curr}")
        return {
            "messages": [initial_message],
            "next_fazendeiro_idx": idx + 1,
            "current_fazendeiro_id": curr,
            "simulacao_estado": sim_estado,
            "negociacao_ativa": True,
            "next_action": "iniciar_negociacao",
            "iteracoes_negociacao": 0,  # Reset do contador para a nova negociação
        }
    else:
        return {"next_action": "fim"}


# --- Inicialização ---
est_inicial = SimulacaoEstado(
    dinheiro_empresario_inicial=10000.0,
    fazendeiros_info={"Fz1": {"soja": 500.0, "dinheiro": 0.0}, "Fz2": {"soja": 700.0, "dinheiro": 0.0},
                      "Fz3": {"soja": 300.0, "dinheiro": 0.0}}
)
ferramentas = FerramentasSimulacao(est_inicial)
agentes = {}
emp_ag, faz_ag = inicializar_agentes(ferramentas, llm, list(est_inicial.fazendeiros.keys()))
agentes["Empresario"] = emp_ag
agentes.update(faz_ag)

# --- Configuração do Grafo ---
workflow = StateGraph(GraphState)
workflow.add_node("verificar_proximo_fazendeiro", verificar_proximo_fazendeiro)
workflow.add_node("empresario_node", empresario_node)
workflow.add_node("fazendeiro_node", fazendeiro_node)
workflow.add_node("decide_proxima_acao", decide_proxima_acao)

workflow.set_entry_point("verificar_proximo_fazendeiro")

# Transições
workflow.add_conditional_edges(
    "verificar_proximo_fazendeiro",
    lambda state: state["next_action"],
    {"iniciar_negociacao": "empresario_node", "fim": END}
)
workflow.add_edge("empresario_node", "decide_proxima_acao")
workflow.add_edge("fazendeiro_node", "decide_proxima_acao")
workflow.add_conditional_edges(
    "decide_proxima_acao",
    lambda state: state["next_action"],
    {"resposta_empresario": "empresario_node", "resposta_fazendeiro": "fazendeiro_node",
     "finalizar_ou_proximo": "verificar_proximo_fazendeiro"}
)

app = workflow.compile(checkpointer=None)

# --- Execução ---
print("--- Iniciando Simulação de Negociação ---")
print(est_inicial)

# --- Estado inicial ---
initial_graph_state = {
    "next_fazendeiro_idx": 0,
    "simulacao_estado": est_inicial,
    "messages": [],
    "iteracoes_negociacao": 0,
}

# Loop de execução com tratamento de erros
try:
    for s in app.stream(initial_graph_state, config={'recursion_limit': 100}):
        if "__end__" in s:
            break

        # Tratamento de erros críticos
        current_state = s[list(s.keys())[0]]
        if current_state and "error" in current_state:
            print(f"ERRO CRÍTICO: {current_state['error']}")
            print("Reiniciando negociação com próximo fazendeiro...")
            current_state["next_action"] = "finalizar_ou_proximo"
except Exception as e:
    print(f"ERRO GRAVE: {str(e)}")
    print("Finalizando simulação prematuramente...")

print("\n--- Fim da Simulação ---")
print(est_inicial)