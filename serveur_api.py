# serveur_api.py (Version mise à jour pour Chat Web et Telegram)

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sys, uuid, os, json
from agents.agent_principal import AgentPrincipal

# Importations pour Telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
import asyncio

# --- CONFIGURATION ---
API_KEY_GOOGLE = os.environ.get("API_KEY") # Clé API Google depuis Render
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") # Token Telegram depuis Render
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL_BASE", "http://127.0.0.1:8000") # Votre URL publique Render + endpoint

# Vérification des clés
if not API_KEY_GOOGLE:
    print("ERREUR : CLÉ API GOOGLE MANQUANTE (vérifier les variables d'environnement Render)")
    # sys.exit() # On commente pour permettre au serveur de démarrer, mais il ne fonctionnera pas sans la clé.
if not TELEGRAM_BOT_TOKEN:
    print("ERREUR : TOKEN BOT TELEGRAM MANQUANT (vérifier les variables d'environnement Render)")
    # sys.exit()

# --- Initialisation de l'IA ---
# Note : L'initialisation de l'agent peut prendre un peu de temps.
# On peut la faire ici ou dans les handlers si on veut que le démarrage soit plus rapide.
# Pour simplifier, on l'initialise globalement pour l'instant.
# Si vous avez beaucoup de conversations, il faudra une gestion plus fine.
agent_ia = None
if API_KEY_GOOGLE:
    try:
        agent_ia = AgentPrincipal(api_key=API_KEY_GOOGLE)
        print("INFO: Agent IA initialisé.")
    except Exception as e:
        print(f"ERREUR lors de l'initialisation de l'Agent IA: {e}")

# --- Gestion des conversations ---
conversations_en_cours_web = {} # Pour le chat web
conversations_en_cours_telegram = {} # Pour Telegram

# --- Classes Pydantic pour les requêtes ---
class MessageEntrant(BaseModel):
    id_session: str | None = None
    texte: str

class ReponseAgent(BaseModel):
    id_session: str
    texte: str

# --- API générale ---
app = FastAPI(title="SmartEcom360 API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def racine():
    return {"status": "ok", "message": "API Ecom active"}

# --- Endpoint pour le Chat Web ---
@app.post("/chat", response_model=ReponseAgent)
async def recevoir_message_web(message: MessageEntrant):
    if not API_KEY_GOOGLE:
        return ReponseAgent(id_session="", texte="Erreur interne : Clé API Google non configurée.")
    if not agent_ia:
         return ReponseAgent(id_session="", texte="Erreur interne : L'agent IA n'a pas pu être initialisé.")
         
    id_session = message.id_session
    if not id_session or id_session not in conversations_en_cours_web:
        id_session = str(uuid.uuid4())
        print(f"\n[API] Nouvelle session chat web démarrée : {id_session}")
        conversations_en_cours_web[id_session] = AgentPrincipal(api_key=API_KEY_GOOGLE)
        
    agent_instance = conversations_en_cours_web[id_session]
    print(f"[API] Message chat web de '{id_session}': '{message.texte}'")
    reponse_texte = agent_instance.repondre(message.texte)
    print(f"[API] Réponse chat web pour '{id_session}': '{reponse_texte}'")
    return ReponseAgent(id_session=id_session, texte=reponse_texte)

# --- Logique Telegram ---

# Dictionnaire pour stocker les instances de AgentPrincipal par chat_id Telegram
telegram_sessions = {}

# Fonction pour obtenir ou créer un agent pour un chat_id Telegram donné
def get_or_create_telegram_agent(chat_id: int):
    if not API_KEY_GOOGLE:
        return None # Impossible de créer sans clé API Google

    if chat_id not in telegram_sessions:
        print(f"[Telegram] Création nouvelle session pour chat_id: {chat_id}")
        try:
            telegram_sessions[chat_id] = AgentPrincipal(api_key=API_KEY_GOOGLE)
        except Exception as e:
            print(f"[Telegram] Erreur création agent pour {chat_id}: {e}")
            return None
    return telegram_sessions[chat_id]

# Fonction asynchrone pour envoyer un message à Telegram via son API Bot
# Nécessite la librairie 'httpx' pour les appels asynchrones
# Vous devrez l'ajouter à requirements.txt: pip install httpx
async def send_telegram_message(bot_token: str, chat_id: int, text: str):
    import httpx
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}) # parse_mode pour formater le texte si nécessaire
            response.raise_for_status() # Lève une exception pour les codes d'erreur HTTP
            print(f"[Telegram] Message envoyé à chat_id {chat_id}. Statut: {response.status_code}")
        except httpx.RequestError as exc:
            print(f"[Telegram] Erreur de requête pour envoyer message à {chat_id}: {exc}")
        except httpx.HTTPStatusError as exc:
            print(f"[Telegram] Erreur HTTP pour envoyer message à {chat_id}: {exc.response.status_code} - {exc.response.text}")
        except Exception as e:
            print(f"[Telegram] Erreur inattendue lors de l'envoi de message à {chat_id}: {e}")


# Handler pour la commande /start sur Telegram
async def start_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    agent = get_or_create_telegram_agent(chat_id)
    if not agent:
        await send_telegram_message(TELEGRAM_BOT_TOKEN, chat_id, "Désolé, je ne peux pas démarrer pour le moment. Contactez l'administrateur.")
        return
    
    response = agent.repondre("Bonjour") # Ou un message de bienvenue spécifique
    await send_telegram_message(TELEGRAM_BOT_TOKEN, chat_id, response)

# Handler pour les messages texte sur Telegram
async def handle_message_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = update.message.text
    
    agent = get_or_create_telegram_agent(chat_id)
    if not agent:
        await send_telegram_message(TELEGRAM_BOT_TOKEN, chat_id, "Désolé, je ne peux pas traiter votre message pour le moment.")
        return

    response = agent.repondre(user_text)
    await send_telegram_message(TELEGRAM_BOT_TOKEN, chat_id, response)

# --- Endpoint Webhook pour Telegram ---
# FastAPI ne peut pas exécuter directement les handlers de python-telegram-bot
# Il faut utiliser un endpoint qui reçoit les données JSON de Telegram et appelle les handlers
# Cela nécessite une librairie pour transformer les Updates JSON en objets Update de python-telegram-bot.
# Ou bien, on fait un traitement manuel comme dans le post précédent.
# Pour garder la structure, nous allons faire un traitement manuel simple ici.

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    if not TELEGRAM_BOT_TOKEN:
        print("ERREUR: TOKEN TELEGRAM NON CONFIGURÉ DANS LES VARIABLES D'ENVIRONNEMENT")
        raise HTTPException(status_code=500, detail="Telegram bot token not configured")
    
    try:
        update_data = await request.json()
        # print(f"[Telegram Webhook] Reçu: {json.dumps(update_data, indent=2)}") # Attention: Peut être très verbeux

        # On crée un objet Update pour pouvoir utiliser les méthodes comme .effective_chat.id etc.
        # C'est un peu une simulation pour pouvoir réutiliser la logique d'AgentPrincipal
        # Une intégration plus propre utiliserait directement la librairie python-telegram-bot
        
        if 'message' in update_data:
            message = update_data['message']
            chat_id = message['chat']['id']
            user_text = message.get('text', '')
            
            # On détecte si c'est une commande ou un message texte
            if 'text' in message:
                if user_text.startswith('/'): # C'est une commande
                    command = user_text.split(' ')[0]
                    if command == '/start':
                        agent = get_or_create_telegram_agent(chat_id)
                        if agent:
                            response = agent.repondre("Bonjour")
                            await send_telegram_message(TELEGRAM_BOT_TOKEN, chat_id, response)
                        else:
                            await send_telegram_message(TELEGRAM_BOT_TOKEN, chat_id, "Désolé, problème d'initialisation de l'IA.")
                    else: # Autres commandes non gérées ici
                        agent = get_or_create_telegram_agent(chat_id)
                        if agent:
                             response = agent.repondre(f"Commande : {user_text}")
                             await send_telegram_message(TELEGRAM_BOT_TOKEN, chat_id, response)
                        else:
                             await send_telegram_message(TELEGRAM_BOT_TOKEN, chat_id, "Désolé, problème d'initialisation de l'IA.")
                else: # C'est un message texte normal
                    agent = get_or_create_telegram_agent(chat_id)
                    if agent:
                        response = agent.repondre(user_text)
                        await send_telegram_message(TELEGRAM_BOT_TOKEN, chat_id, response)
                    else:
                        await send_telegram_message(TELEGRAM_BOT_TOKEN, chat_id, "Désolé, problème d'initialisation de l'IA.")

            # Gérer d'autres types de messages (photos, documents, etc.) si nécessaire

        return {"status": "received", "message": "Update processed"}

    except json.JSONDecodeError:
        print("[Telegram Webhook] Erreur: Payload JSON invalide.")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except TelegramError as e:
        print(f"[Telegram Webhook] Erreur Telegram: {e}")
        raise HTTPException(status_code=500, detail=f"Telegram API error: {e}")
    except Exception as e:
        print(f"[Telegram Webhook] ERREUR GÉNÉRALE dans le webhook : {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")