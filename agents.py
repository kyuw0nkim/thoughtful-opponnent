import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain.output_parsers import PydanticOutputParser

from langchain_community.vectorstores import FAISS
from langchain.schema import Document

from prompts import *
from output_parser import *
from world_model import WorldModel
from working_memory import WorkingMemory, Turn
import dotenv
import json
import threading
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv("env_1.env")


# --- App, LLM, Parsers ---
baselinemode = True
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
json_mode = {"response_format": {"type": "json_object"}}
llm1 = ChatOpenAI(model="gpt-4.1-nano-2025-04-14", temperature=0.3, model_kwargs=json_mode)
llm2 = ChatOpenAI(model="gpt-4.1-nano-2025-04-14", temperature=0.3, model_kwargs=json_mode)
llm3 = ChatOpenAI(model="gpt-4.1-nano-2025-04-14", temperature=0.3, model_kwargs=json_mode)
llm4 = ChatOpenAI(model="gpt-4.1-nano-2025-04-14", temperature=0.3, model_kwargs=json_mode)
llm5 = ChatOpenAI(model="gpt-4.1-nano-2025-04-14", temperature=0.3)

parser1 = PydanticOutputParser(pydantic_object=Response1)
parser2 = PydanticOutputParser(pydantic_object=Response2)
parser3 = PydanticOutputParser(pydantic_object=Response3)
parser4 = PydanticOutputParser(pydantic_object=Response4)
parser5 = StrOutputParser()

# --- State Management ---
world_model = WorldModel()
working_memory = WorkingMemory(max_history_len=4)

# --- Logging ---
_LOG_DIR = os.environ.get("LOG_DIR", "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_LOCK = threading.Lock()

def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")

def _safe_jsonable(obj):
    try:
        json.dumps(obj)
        return obj
    except Exception:
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        return str(obj)

def log_event(event: str, channel: str, payload: Dict[str, Any]):
    record = {"ts": _now_iso(), "event": event, "channel": channel or "default", "payload": _safe_jsonable(payload)}
    line = json.dumps(record, ensure_ascii=False)
    with _LOG_LOCK:
        with open(os.path.join(_LOG_DIR, f"{channel or 'default'}.jsonl"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
        with open(os.path.join(_LOG_DIR, "_all.jsonl"), "a", encoding="utf-8") as f:
            f.write(line + "\n")

# --- VectorDB ---
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = None

def add_to_db_from_chain1(chain1_obj, meta=None):
    global vectorstore
    text = str(chain1_obj.model_dump_json() if hasattr(chain1_obj, "model_dump_json") else chain1_obj)
    doc = Document(page_content=text, metadata=meta or {"stage": "chain1"})
    if vectorstore is None:
        vectorstore = FAISS.from_documents([doc], embeddings)
    else:
        vectorstore.add_documents([doc])
    return chain1_obj

def retrieve_context(query_text: str, k: int = 5) -> str:
    if not query_text or vectorstore is None: return ""
    docs = vectorstore.similarity_search(query_text, k=k)
    return "\n\n".join(f"[{i}] {d.page_content}" for i, d in enumerate(docs, start=1))

def map_opinion_strength(strength: float) -> str:
    """Maps a numerical opinion strength to a descriptive string."""
    strength = round(strength)
    if strength >= 5:
        return "very confident"
    if strength == 4:
        return "somewhat confident"
    if strength == 3:
        return "neither confident nor unconfident"
    if strength == 2:
        return "somewhat unconfident"
    return "not confident at all"

# --- Chain I/O Adapters ---
def build_chain1_input(user_utterance: str, wm: WorldModel) -> Dict[str, Any]:
    return {"utterance": user_utterance, "a_position": wm.a_position, "a_opinion_strength": map_opinion_strength(wm.a_opinion_strength), "text": user_utterance}

def normalize_chain1_output(r1_obj) -> Dict[str, Any]:
    u0 = (r1_obj.utterance or [{}])[0]
    head = {
        "interp": str(u0.interp or ""),
        "value": ", ".join(map(str, u0.value or [])),
        "da": ", ".join(map(str, u0.da or [])),
        "persu_reason": str(u0.persu_reason or ""),
        "persu": float(u0.persu or 0.0),
    }
    return {"utterance": [head]}

def build_chain2_input(history: str, chain1_out: Dict[str, Any], wm: WorldModel) -> Dict[str, Any]:
    head = (chain1_out.get("utterance") or [{}])[0]
    return {
        "history": history, "topic": wm.topic,
        "background": wm.background,
        "interp": head.get("interp", ""),
        "value": head.get("value", ""),
        "da": head.get("da", ""),
        "u1_position": wm.u1_position, "u1_opinion_strength": map_opinion_strength(wm.u1_opinion_strength),
        "u2_position": wm.u2_position, "u2_opinion_strength": map_opinion_strength(wm.u2_opinion_strength),
        "a_position": wm.a_position, "a_opinion_strength": map_opinion_strength(wm.a_opinion_strength),
        "value_space": wm.get_mentioned_values(), 
        "text": f'{history}\ninterp={head.get("interp",'')}\nvalue={head.get("value",'')}\nda={head.get("da",'')}'
    }

def build_chain3_input(history: str, retrieved: str, desire: str, wm: WorldModel, chain1_out: Dict[str, Any]) -> Dict[str, Any]:
    head = (chain1_out.get("utterance") or [{}])[0]
    return {
        "history": history,
        "retrieved_thought": retrieved,
        "selected_desire": desire,
        "topic": wm.topic,
        "background": wm.background,
        "interp": head.get("interp", ""),
        "value": head.get("value", ""),
        "da": head.get("da", ""),
        "u1_position": wm.u1_position,
        "u1_opinion_strength": map_opinion_strength(wm.u1_opinion_strength),
        "u2_position": wm.u2_position,
        "u2_opinion_strength": map_opinion_strength(wm.u2_opinion_strength),
        "a_position": wm.a_position,
        "a_opinion_strength": map_opinion_strength(wm.a_opinion_strength),
    }


def build_chain4_input(history: str, desire: str, thoughts: List[Any], wm: WorldModel) -> Dict[str, Any]:
    return {
        "background": wm.background,
        "topic": wm.topic,
        "selected_desire": desire,
        "history": history,
        "thoughts": thoughts,
        "u1_position": wm.u1_position,
        "u1_opinion_strength": map_opinion_strength(wm.u1_opinion_strength),
        "u2_position": wm.u2_position,
        "u2_opinion_strength": map_opinion_strength(wm.u2_opinion_strength),
        "a_position": wm.a_position,
        "a_opinion_strength": map_opinion_strength(wm.a_opinion_strength),
    }

def pick_best_desire(items: List[Any], evals: List[Any], score_key: str = "score") -> Any:
    if not items:
        return None
    if not evals:
        return items[0]

    best_item, best_score = None, float("-inf")
    for item, evaluation in zip(items, evals):
        score = 0.0
        if isinstance(evaluation, dict):
            score = float(evaluation.get(score_key, 0.0))
        else:
            score = float(getattr(evaluation, score_key, 0.0))

        if score > best_score:
            best_item, best_score = item, score

    return best_item

def pick_best_item_by_score(items: List[Any], evals: List[Any], threshold: float = 4.75, score_key: str = "score") -> Any:
    if not items:
        return None
    if not evals:
        return items[0]

    best_item, best_score = None, float("-inf")
    for item, evaluation in zip(items, evals):
        score = 0.0
        if isinstance(evaluation, dict):
            score = float(evaluation.get(score_key, 0.0))
        else:
            score = float(getattr(evaluation, score_key, 0.0))

        if score > best_score:
            best_item, best_score = item, score

    return best_item if best_score >= threshold else None

# --- Persuasion Handling ---
def handle_persuasion(c1_out: Dict[str, Any], wm: WorldModel, channel: str) -> Optional[Dict[str, str]]:
    persu_score = (c1_out.get("utterance", [{}])[0]).get("persu", 0.0)
    
    # Assuming user is 'u1' for simplicity. This needs to be adapted for multi-user.
    user_position = wm.u1_position 
    
    if persu_score >= 4.5 and user_position != wm.a_position:
        new_strength = max(1, wm.a_opinion_strength - 0.5)
        wm.update_agent_opinion_strength(new_strength)
        log_event("persuasion_success", channel, {"old_strength": wm.a_opinion_strength + 0.5, "new_strength": new_strength})
        return {"persuasion_thought": "이 말도 설득력이 있네요."}
    return None

from operator import itemgetter

# --- LCEL Chains ---
template1 = ChatPromptTemplate.from_template(INTENT_ANALYZER + "\n\n{format_instructions}")
template2 = ChatPromptTemplate.from_template(DESIRE_SHAPER)
template3 = ChatPromptTemplate.from_template(THOUGHT_FORMATION)
template4 = ChatPromptTemplate.from_template(THOUGHT_EVALUATION)
template5 = ChatPromptTemplate.from_template(THOUGHT_ARTICULATOR)
template_direct_conversation = PromptTemplate.from_template(DIRECT_CONVERSATION_PROMPT)

chain1 = (
    {
        "format_instructions": lambda _: parser1.get_format_instructions(),
        "utterance": itemgetter("utterance"),
        "a_position": itemgetter("a_position"),
        "a_opinion_strength": itemgetter("a_opinion_strength"),
        "text": itemgetter("text"),
    }
    | template1
    | llm1
    | parser1
)
chain1_with_store = chain1 | RunnableLambda(add_to_db_from_chain1)
chain1_to_schema = RunnableLambda(normalize_chain1_output)

chain2 = template2 | llm2 | parser2
chain3 = template3 | llm3 | parser3
chain4 = template4 | llm4 | parser4
chain5 = template5 | llm5 | parser5
chain_direct_conversation = template_direct_conversation | llm5 | parser5


# --- Pipeline ---
def run_pipeline(latest_user_utterance: str, channel: str, wm: WorldModel, mem: WorkingMemory) -> str:
    history = mem.get_history_string(channel)
    log_event("pipeline_start", channel, {"latest_user_utterance": latest_user_utterance, "history": history})

    c1_input = build_chain1_input(latest_user_utterance, wm)
    log_event("chain1_input", channel, {"input": c1_input})
    c1_raw = chain1_with_store.invoke(c1_input)
    log_event("chain1_raw", channel, {"output": _safe_jsonable(c1_raw)})
    c1_out = chain1_to_schema.invoke(c1_raw)
    log_event("chain1_output", channel, {"output": c1_out})

    head = (c1_out.get("utterance") or [{}])[0]
    mem.add_turn(channel, "user", latest_user_utterance, head.get("interp"), head.get("value"), head.get("da"))
    if head.get("value"): wm.add_value(head["value"])

    persuasion_feedback = handle_persuasion(c1_out, wm, channel)
    log_event("persuasion_feedback", channel, {"feedback": persuasion_feedback})
    if persuasion_feedback:
        persuasion_thought = persuasion_feedback.get("persuasion_thought")
        if persuasion_thought:
            selected_desire = "ENGAGE IN EVERYDAY SOCIAL CONVERSATION"
            c5_input = {
                "selected_thought": persuasion_thought,
                "selected_desire": selected_desire,
                "a_position": wm.a_position,
                "a_opinion_strength": map_opinion_strength(wm.a_opinion_strength),
            }
            log_event("chain5_input_persuasion", channel, {"input": c5_input})
            final_str = chain5.invoke(c5_input)
            log_event("chain5_output_persuasion", channel, {"output": final_str})

            mem.add_turn(channel, "agent", final_str)
            log_event("final_reply_persuasion", channel, {"output": final_str})
            return final_str

    if baselinemode:
        selected_desire = "participate in conversation"
        log_event("selected_desire", channel, {"selected_desire": selected_desire})
    else:
        c2_input = build_chain2_input(history, c1_out, wm)

        log_event("chain2_input", channel, {"input": c2_input})
        c2_out = chain2.invoke(c2_input)
        log_event("chain2_output", channel, {"output": _safe_jsonable(c2_out)})

        desires = c2_out.desires
        best_desire_obj = pick_best_desire(desires, desires, score_key="motivation_score")
        selected_desire = best_desire_obj.desire if best_desire_obj else "INTRODUCE A NEW PERSPECTIVE OR ANGLE"
        log_event("selected_desire", channel, {"selected_desire": selected_desire})

    retrieved = retrieve_context(head.get("interp", ""), k=5)
    log_event("retrieved_context", channel, {"retrieved": retrieved})

    c3_input = build_chain3_input(history, retrieved, selected_desire, wm, c1_out)
    log_event("chain3_input", channel, {"input": c3_input})
    c3_out = chain3.invoke(c3_input)
    log_event("chain3_output", channel, {"output": _safe_jsonable(c3_out)})
    thoughts = c3_out.thoughts
    mem.add_thoughts(channel, thoughts)

    c4_input = build_chain4_input(history, selected_desire, thoughts, wm)
    log_event("chain4_input", channel, {"input": _safe_jsonable(c4_input)})
    c4_out = chain4.invoke(c4_input)
    log_event("chain4_output", channel, {"output": _safe_jsonable(c4_out)})

    selected_thought_obj = pick_best_item_by_score(thoughts, c4_out.thought_eval)
    selected_thought = selected_thought_obj.content if selected_thought_obj else None
    log_event("selected_thought", channel, {"selected": selected_thought})

    if not selected_thought: return ""

    c5_input = {"selected_thought": selected_thought, "selected_desire": selected_desire, "a_position": wm.a_position, "a_opinion_strength": map_opinion_strength(wm.a_opinion_strength)}
    log_event("chain5_input", channel, {"input": c5_input})
    final_str = chain5.invoke(c5_input)
    log_event("chain5_output", channel, {"output": final_str})

    mem.add_turn(channel, "agent", final_str)
    log_event("final_reply", channel, {"output": final_str})
    return final_str

# --- Slack Handler ---
BOT_USER_ID = None

def initialize_bot_id():
    global BOT_USER_ID
    try:
        response = app.client.auth_test()
        BOT_USER_ID = response["user_id"]
        log_event("bot_id_initialized", "system", {"bot_user_id": BOT_USER_ID})
    except Exception as e:
        log_event("error_initializing_bot_id", "system", {"error": repr(e)})
        print("Error getting bot user ID:", e)

channel_user_labels: Dict[str, Dict[str, str]] = defaultdict(dict)
def _assign_label(channel: str, user_id: str) -> str:
    if user_id not in channel_user_labels[channel]:
        label = f"user{len(channel_user_labels[channel]) + 1}"
        channel_user_labels[channel][user_id] = label
    return channel_user_labels[channel][user_id]

@app.message(".*")
def message_handler(message, say, logger):
    try:
        channel = message.get("channel", "default")
        user_text = message.get("text", "")
        user_id = message.get("user", "unknown")
        
        log_event("user_message", channel, {"user_id": user_id, "text": user_text})
        
        if BOT_USER_ID and f"<@{BOT_USER_ID}>" in user_text:
            # Handle direct mention
            log_event("direct_mention", channel, {"user_text": user_text})
            
            history = working_memory.get_history_string(channel)
            
            direct_conversation_input = {
                "history": history,
                "user_question": user_text,
                "a_position": world_model.a_position,
                "a_opinion_strength": map_opinion_strength(world_model.a_opinion_strength)
            }
            log_event("direct_conversation_chain_input", channel, {"input": direct_conversation_input})
            
            response = chain_direct_conversation.invoke(direct_conversation_input)
            
            log_event("direct_conversation_chain_output", channel, {"output": response})
            say(text=response)
        else:
            # Existing logic
            user_label = _assign_label(channel, user_id)
            working_memory.add_turn(channel, user_label, user_text)
            
            output = run_pipeline(user_text, channel, world_model, working_memory)
            
            if output:
                say(text=output)
            
    except Exception as e:
        logger.exception(e)
        log_event("error", message.get("channel", "default"), {"error": repr(e)})
        say(text="An error occurred.")

# --- Main ---
if __name__ == "__main__":
    log_event("boot", "system", {"pid": os.getpid()})
    initialize_bot_id()
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()