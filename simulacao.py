# simulacao.py (VERSÃO CORRIGIDA)

from langgraph.graph import StateGraph, END
from agentes import inicializar_agentes
from estado import SimulacaoEstado
from ferramentas import definir_recursos_globais
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import re
import sys


class Tee:
    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for f in self.files: f.write(obj); f.flush()

    def flush(self):
        for f in self.files: f.flush()


llm = ChatOpenAI(model="local-model", openai_api_base="http://localhost:1234/v1", temperature=0.0, api_key="lm-studio")


class GraphState(dict):
    messages: list[BaseMessage]
    next_agricultor_idx: int
    current_agricultor_id: str
    simulacao_estado: SimulacaoEstado
    negociacao_ativa: bool
    next_action: str = ""
    iteracoes_negociacao: int = 0


def _limpar_saida_agente(texto_original: str) -> str:
    match = re.search(r"</think>(.*)", texto_original, re.DOTALL)
    if match: return match.group(1).strip()
    return texto_original.strip()


def empresario_node(state: GraphState):
    sim_estado = state["simulacao_estado"]
    agr_id = state["current_agricultor_id"]
    oferta = sim_estado.negociacao_em_andamento
    input_text = (
        f"Sua vez de negociar com o Agricultor '{agr_id}'. A oferta atual é: {oferta}. Avalie e decida (aceitar, rejeitar, ou contrapropor).")

    executor = agentes["Empresario"]
    result = executor.invoke({"input": input_text, "chat_history": state["messages"]})
    resp_limpa = _limpar_saida_agente(result.get("output", ""))

    state["messages"].append(AIMessage(content=resp_limpa, name="Empresario"))
    print(f"\n[EMPRESARIO] Responde para {agr_id}: {resp_limpa}")
    return state


def agricultor_node(state: GraphState):
    agr_id = state["current_agricultor_id"]
    last_message = state["messages"][-1].content if state["messages"] else "Nenhuma mensagem anterior."

    input_text = (
        f"O empresário respondeu: '{last_message}'.\nSiga seu algoritmo. Verifique seu inventário, seu plano, e decida sua próxima ação: fazer uma oferta, plantar, ou responder a uma contra-proposta.")

    executor = agentes["Agricultores"][agr_id]
    result = executor.invoke({"input": input_text, "chat_history": state["messages"]})
    resp_limpa = _limpar_saida_agente(result.get("output", ""))

    state["messages"].append(AIMessage(content=resp_limpa, name=f"Agricultor {agr_id}"))
    print(f"\n[AGRICULTOR {agr_id}] Ação/Resposta: {resp_limpa}")
    return state


def decide_proxima_acao(state: GraphState):
    print(state["simulacao_estado"])
    state["iteracoes_negociacao"] += 1
    print(f"\n[DECISÃO] Fim da iteração: {state['iteracoes_negociacao']}")

    if state["iteracoes_negociacao"] > 10:
        print(f"--- FIM DA NEGOCIAÇÃO: Limite de iterações excedido com {state['current_agricultor_id']} ---")
        state["next_action"] = "finalizar_ou_proximo"
        return state

    negociacao = state["simulacao_estado"].negociacao_em_andamento
    if negociacao['oferta_ativa']:
        if negociacao['ultimo_ofertante'] == 'Agricultor':
            state["next_action"] = "resposta_empresario"
        else:
            state["next_action"] = "resposta_agricultor"
    else:
        state["next_action"] = "resposta_agricultor"

    print(f"Próxima ação definida: {state['next_action']}")
    return state


def verificar_proximo_agricultor(state: GraphState):
    sim_estado = state["simulacao_estado"]
    ids_agricultores = list(sim_estado.agricultores.keys())
    idx = state["next_agricultor_idx"]
    if idx < len(ids_agricultores):
        curr_id = ids_agricultores[idx]
        print(f"\n\n--- INICIANDO NOVA NEGOCIAÇÃO COM AGRICULTOR: {curr_id} ---")
        initial_message = HumanMessage(content=f"Olá, Agricultor {curr_id}. Sou o Empresário. O que você precisa hoje?")
        return {"messages": [initial_message], "next_agricultor_idx": idx + 1, "current_agricultor_id": curr_id,
                "simulacao_estado": sim_estado, "next_action": "iniciar_negociacao", "iteracoes_negociacao": 0}
    else:
        print("\n--- TODOS OS AGRICULTORES JÁ NEGOCIARAM. ---")
        return {"next_action": "fim"}


original_stdout = sys.stdout
log_file = open("simulacao_log.txt", "w", encoding="utf-8")
sys.stdout = Tee(original_stdout, log_file)
try:
    agricultores_config = {"Agr1": {"dinheiro": 6000.0, "parcelas": ["P1", "P2", "P3"]},
                           "Agr2": {"dinheiro": 8000.0, "parcelas": ["T1", "T2"]}}
    est_inicial = SimulacaoEstado(dinheiro_empresario_inicial=10000.0, agricultores_info=agricultores_config)
    definir_recursos_globais(est_inicial)

    agentes = {}
    emp_ag, agr_ags = inicializar_agentes(llm, list(est_inicial.agricultores.keys()))
    agentes["Empresario"] = emp_ag
    agentes["Agricultores"] = agr_ags

    workflow = StateGraph(GraphState)
    workflow.add_node("verificar_proximo_agricultor", verificar_proximo_agricultor)
    workflow.add_node("empresario_node", empresario_node)
    workflow.add_node("agricultor_node", agricultor_node)
    workflow.add_node("decide_proxima_acao", decide_proxima_acao)
    workflow.set_entry_point("verificar_proximo_agricultor")

    workflow.add_conditional_edges("verificar_proximo_agricultor", lambda state: state["next_action"],
                                   {"iniciar_negociacao": "agricultor_node", "fim": END})

    workflow.add_edge("empresario_node", "decide_proxima_acao")
    workflow.add_edge("agricultor_node", "decide_proxima_acao")

    workflow.add_conditional_edges("decide_proxima_acao", lambda state: state["next_action"],
                                   {"resposta_empresario": "empresario_node",
                                    "resposta_agricultor": "agricultor_node",
                                    "finalizar_ou_proximo": "verificar_proximo_agricultor"})

    app = workflow.compile(checkpointer=None)
    print("--- INICIANDO SIMULAÇÃO DE NEGOCIAÇÃO (MODELO GORIM) ---")
    print(est_inicial)

    initial_graph_state = {"next_agricultor_idx": 0, "simulacao_estado": est_inicial, "messages": [],
                           "iteracoes_negociacao": 0}

    for s in app.stream(initial_graph_state, config={'recursion_limit': 150}):
        if "__end__" in s: break
except Exception as e:
    print(f"\nERRO GRAVE NA EXECUÇÃO DO GRAFO: {str(e)}")
    print("Finalizando simulação prematuramente...")
finally:
    print("\n--- FIM DA SIMULAÇÃO ---")
    print(est_inicial)
    sys.stdout = original_stdout
    log_file.close()
    print("\nLog da simulação salvo em 'simulacao_log.txt'")