# serveur_api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys, uuid

from agents.agent_principal import AgentPrincipal

# --- CONFIGURATION ---
API_KEY = "AIzaSyCX5UdsXa9B3QZdXPO1MY8oPbW3A_yCo0Y"

app = FastAPI(title="SmartEcom360 API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

if "VOTRE_CLE" in API_KEY:
    print("ERREUR : CLÉ API MANQUANTE"); sys.exit()

conversations_en_cours = {}

class MessageEntrant(BaseModel):
    id_session: str | None = None
    texte: str
class ReponseAgent(BaseModel):
    id_session: str
    texte: str

@app.post("/chat", response_model=ReponseAgent)
async def recevoir_message(message: MessageEntrant):
    id_session = message.id_session
    
    if not id_session or id_session not in conversations_en_cours:
        id_session = str(uuid.uuid4())
        print(f"\n[API] Nouvelle session démarrée : {id_session}")
        conversations_en_cours[id_session] = AgentPrincipal(api_key=API_KEY)
    
    agent_instance = conversations_en_cours[id_session]
    
    print(f"[API] Message de '{id_session}': '{message.texte}'")
    reponse_texte = agent_instance.repondre(message.texte)
    print(f"[API] Réponse pour '{id_session}': '{reponse_texte}'")
    
    return ReponseAgent(id_session=id_session, texte=reponse_texte)

@app.get("/")
def racine(): return {"status": "ok"}