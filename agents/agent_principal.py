# agents/agent_principal.py (Version Finale avec Mémoire Produit Fiable)
import google.generativeai as genai
import json, os, datetime

# --- NOUVEAU CHEMIN VERS LE CRM (en dehors du projet pour éviter le reload) ---
HOME_DIR = os.path.expanduser("~")
CRM_DIR = os.path.join(HOME_DIR, 'Desktop', 'crm')
CRM_FILE = os.path.join(CRM_DIR, 'prospects.json')

def sauvegarder_contact(infos):
    contacts = []
    os.makedirs(os.path.dirname(CRM_FILE), exist_ok=True)
    try:
        with open(CRM_FILE, 'r', encoding='utf-8') as f: contacts = json.load(f)
    except: pass
    contacts.append(infos)
    with open(CRM_FILE, 'w', encoding='utf-8') as f: json.dump(contacts, f, indent=4, ensure_ascii=False)
    print("DEBUG: Prospect sauvegardé dans le CRM.")

def charger_connaissance():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    faq_path = os.path.join(base_dir, 'config', 'faq.txt')
    produits_path = os.path.join(base_dir, 'config', 'produits.json')
    faq, produits = "Aucune FAQ.", []
    try:
        with open(faq_path, 'r', encoding='utf-8') as f: faq = f.read()
    except: pass
    try:
        with open(produits_path, 'r', encoding='utf-8') as f: produits = json.load(f)
    except: pass
    return faq, produits

class AgentPrincipal:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        faq, self.catalogue_produits = charger_connaissance()
        self.produit_contexte = None
        
        self.prompt_systeme = f"""
        Tu es un assistant IA vendeur expert pour 'ViteFait.sn'.
        --- CONNAISSANCE ---
        FAQ: {faq}
        CATALOGUE: {json.dumps(self.catalogue_produits, indent=2, ensure_ascii=False)}
        --- RÈGLES ---
        1.  **Petites Discussions:** Si c'est une salutation/politesse, réponds brièvement.
        2.  **Questions:** Utilise la CONNAISSANCE. Si tu ne sais pas, propose le contact +2250749522365.
        3.  **Hésitation:** Si le client hésite sur le prix, propose la livraison gratuite pour la première commande.
        4.  **Intention d'achat:** Si le client veut commander, passe en mode collecte.
        5.  **Collecte:** Demande NOM, PRÉNOM, TÉLÉPHONE, ADRESSE en une seule fois.
        6.  **Sauvegarde:** Après la réponse du client, analyse-la et réponds UNIQUEMENT avec un JSON.
            - Le JSON doit avoir la structure : {{"action": "sauvegarder_prospect", "data": {{"nom": "...", "prenom": "...", "telephone": "...", "adresse_livraison": "...", "produit_commande": "..."}}}}.
            - **IMPORTANT :** Pour "produit_commande", tu dois mettre le nom du produit dont le client parlait juste avant de vouloir commander.
        """
        self.model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=self.prompt_systeme)
        self.chat = self.model.start_chat(history=[])

    def extraire_json(self, txt):
        try:
            start = txt.find('{'); end = txt.rfind('}')
            if start != -1 and end != -1: return json.loads(txt[start:end+1])
            return None
        except: return None

    def repondre(self, requete_client):
        for produit in self.catalogue_produits:
            if produit["nom"].lower() in requete_client.lower():
                self.produit_contexte = produit["nom"]
                print(f"DEBUG: Produit mis en contexte -> {self.produit_contexte}")

        # On injecte le produit en contexte dans la requête pour que l'IA s'en souvienne
        requete_pour_ia = f"PRODUIT ACTUELLEMENT EN DISCUSSION : {self.produit_contexte}\n\nMESSAGE DU CLIENT : {requete_client}"

        try:
            reponse_api = self.chat.send_message(requete_pour_ia).text
            action_json = self.extraire_json(reponse_api)
            
            if action_json and action_json.get("action") == "sauvegarder_prospect":
                prospect_data = action_json.get("data", {})
                if prospect_data.get("nom") and prospect_data.get("prenom"):
                    prospect_data["date"] = datetime.datetime.now().isoformat()
                    prospect_data["statut"] = "chaud"
                    sauvegarder_contact(prospect_data)
                    self.produit_contexte = None # On réinitialise
                    return "Parfait, merci ! Vos informations ont été enregistrées. Un conseiller vous contactera."
                else:
                    return "Merci. Il manque des informations. Un conseiller essaiera de vous joindre."
            return reponse_api
        except Exception as e:
            print(f"ERREUR [AgentPrincipal]: {e}"); return "Désolé, une erreur technique est survenue."