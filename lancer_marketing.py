# lancer_marketing.py (Version avec Chemin Externe)
import sys, json, os, google.generativeai as genai

# --- NOUVEAU CHEMIN VERS LE CRM ---
HOME_DIR = os.path.expanduser("~")
CRM_DIR = os.path.join(HOME_DIR, 'Desktop', 'crm')
CRM_FILE = os.path.join(CRM_DIR, 'prospects.json')

API_KEY = "AIzaSyCX5UdsXa9B3QZdXPO1MY8oPbW3A_yCo0Y"

class AgentMarketing:
    # ... (le reste du code de l'agent marketing est inchangé)
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    def charger_prospects(self):
        if not os.path.exists(CRM_FILE):
            print(f"INFO: Le fichier CRM n'existe pas encore.")
            return []
        try:
            with open(CRM_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if data else []
        except:
            print("ERREUR: Le fichier CRM est corrompu.")
            return []
    def lancer_campagne_relance_ia(self):
        print("\n--- Lancement de la Campagne Marketing par IA ---")
        prospects = self.charger_prospects()
        prospects_a_relancer = [p for p in prospects if p.get("prenom")]
        if not prospects_a_relancer:
            print("Aucun prospect qualifié à relancer.")
            return
        print(f"Préparation de messages pour {len(prospects_a_relancer)} prospect(s)...")
        for prospect in prospects_a_relancer:
            prenom = prospect.get('prenom')
            # On utilise le nouveau champ "produit_commande"
            produit = prospect.get('produit_commande', 'votre dernière discussion')
            print(f"\nPréparation du message pour : {prenom}...")
            prompt = f"Tu es un marketeur. Écris un message de relance WhatsApp court et amical pour {prenom} qui a commandé '{produit}'. Signe 'L'équipe ViteFait.sn'."
            reponse = self.model.generate_content(prompt)
            print(f"--- MSG pour {prenom} ---\n{reponse.text.strip()}\n----------------------")
        print("\n--- Campagne terminée. ---")

def main():
    # ... (le reste du code main est inchangé)
    print("="*50 + "\n   OUTIL DE CAMPAGNE MARKETING\n" + "="*50)
    if "VOTRE_CLE" in API_KEY:
        print("\nERREUR : CLÉ API MANQUANTE")
        input("Appuyez sur Entrée pour quitter.")
        return
    try:
        agent = AgentMarketing(api_key=API_KEY)
        agent.lancer_campagne_relance_ia()
    except Exception as e:
        print(f"\nERREUR FATALE: {e}")
    input("\nAppuyez sur Entrée pour fermer.")

if __name__ == "__main__":
    main()