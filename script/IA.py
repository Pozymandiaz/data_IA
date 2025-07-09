import requests
import json
import subprocess
import os
import re

# === Paramètres API ===
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("MISTRAL_API_KEY")
API_URL = "https://api.mistral.ai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# === Historique de la conversation ===
history = [
    {"role": "system", "content": (
        "Tu as accès à trois fonctions Python :\n"
        "- writeFile(path: str, content: str)\n"
        "- launchPythonFile(path: str)\n"
        "- stop()\n"
        "Tu dois répondre uniquement avec une liste JSON d'instructions à exécuter.\n"
        "Chaque instruction doit être un objet avec les clés 'function_name' et 'arguments'.\n"
        "Tu peux appeler stop() quand tu as terminé."
    )}
]

# === Fonctions disponibles pour l'agent ===
def writeFile(path, content):
    with open(path, "w") as f:
        f.write(content)
    print(f"[OK] Fichier écrit : {path}")

def launchPythonFile(path):
    print(f"[INFO] Exécution de : {path}")
    subprocess.run(["python", path], check=True)

def stop():
    print("[AGENT] Arrêt demandé.")
    return "STOP"

# === Envoi d’un prompt à Mistral ===
def generateText(prompt: str) -> str:
    history.append({"role": "user", "content": prompt})
    response = requests.post(API_URL, headers=HEADERS, json={
        "model": "mistral-small",
        "messages": history
    })
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    history.append({"role": "assistant", "content": content})
    return content

# === Analyse + exécution de la réponse JSON ===
def execute_instructions(response: str):
    response = response.replace("\\_", "_")
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', response, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError("Impossible de parser la réponse du LLM.")

    for action in data:
        func_name = action["function_name"]
        args = action["arguments"]

        match func_name:
            case "writeFile":
                writeFile(**args)
            case "launchPythonFile":
                launchPythonFile(**args)
            case "stop":
                return stop()
            case _:
                print(f"[WARN] Fonction inconnue : {func_name}")

# === Agent multi-étapes avec boucle ===
def run_agent(initial_prompt: str, max_step: int = 5):
    print("[AGENT] Démarrage de l’agent...\n")
    user_prompt = initial_prompt

    for step in range(max_step):
        print(f"[STEP {step + 1}] Prompt envoyé à Mistral...")
        response = generateText(user_prompt)
        print("[LLM RESPONSE] ", response)
        result = execute_instructions(response)

        if result == "STOP":
            print("[AGENT] Exécution terminée.")
            break

        user_prompt = "Continue. Si tu as terminé, appelle la fonction stop()."

    else:
        print("[AGENT] Nombre d'étapes maximum atteint.")

# === Entrée principale ===
if __name__ == "__main__":
    run_agent("""
Tu dois créer un fichier Python nommé hello.py qui contient le code :
print("hello world")

Puis exécuter ce fichier. Quand tu as terminé, appelle stop().
""", max_step=3)
