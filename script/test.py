import requests
import json
import subprocess
import os
import re
from dotenv import load_dotenv

# === Chargement de la clé API ===
load_dotenv()
API_KEY = os.getenv("MISTRAL_API_KEY")
API_URL = "https://api.mistral.ai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# === Historique conversationnel ===
history = [
    {"role": "system", "content": (
        "Tu es un agent Python intelligent. Tu peux créer du code, écrire des tests unitaires, exécuter les tests, "
        "et décider quand t'arrêter. Tu dois renvoyer un JSON au format : "
        '{ "functions": [ {"name": ..., "code": ...} ], "tests": [...], "run_tests": true, "stop": true }'
    )}
]

# === Fonctions utilitaires ===
def writeFile(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Fichier écrit : {path}")

def runTests(path="."):
    print(f"[INFO] Lancement des tests avec pytest dans {path}")
    # On capture la sortie pour plus de clarté si besoin, mais ici simple run
    subprocess.run(["pytest", path], check=False)

def stop():
    print("[AGENT] Arrêt demandé par l'agent.")
    return "STOP"

def cleanup_old_generated_files():
    # Supprime les anciens fichiers tests et fonctions générés (test_generated*.py, *.py générés)
    removed = False
    for f in os.listdir():
        if re.match(r"test_generated(_\d+)?\.py", f) or re.match(r"[a-zA-Z0-9_]+\.py", f) and f not in ["run_agent.py"]:
            try:
                os.remove(f)
                print(f"[CLEANUP] {f} supprimé.")
                removed = True
            except Exception as e:
                print(f"[WARN] Impossible de supprimer {f} : {e}")
    if not removed:
        print("[CLEANUP] Aucun fichier à supprimer.")

# === Appel à l’API LLM ===
def generateText(user_prompt: str) -> str:
    history.append({"role": "user", "content": user_prompt})
    response = requests.post(API_URL, headers=HEADERS, json={
        "model": "mistral-small",
        "messages": history
    })
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    history.append({"role": "assistant", "content": content})
    return content

# === Interprétation du JSON généré par le LLM ===
def execute_instructions(response: str):
    response = response.replace("\\_", "_")

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError("Impossible de parser la réponse du LLM.")

    cleanup_old_generated_files()

    function_names = []
    for func in data.get("functions", []):
        name = func.get("name", "generated_function")
        code = func.get("code") or func.get("definition") or ""
        writeFile(f"{name}.py", code)
        function_names.append(name)

    # === Regroupement des tests dans un seul fichier
    test_code = ""
    if len(function_names) == 1:
        # Import explicite pour pytest
        test_code += f"from {function_names[0]} import {function_names[0]}\n\n"

    for test in data.get("tests", []):
        if isinstance(test, dict):
            test_code += (test.get("code") or test.get("definition") or "") + "\n"
        elif isinstance(test, str):
            # On vérifie que c'est bien du test (fonction ou assertions)
            if any(kw in test for kw in ["def test_", "assert ", "test_"]):
                test_code += test.strip() + "\n"
            else:
                print(f"[SKIP] Chaîne ignorée (pas un test) : {test[:30]}...")
        else:
            print(f"[WARN] Format de test non reconnu : {test}")

    if test_code:
        writeFile("test_generated.py", test_code)

    if data.get("run_tests"):
        runTests()

    if data.get("stop"):
        return stop()

# === Agent multi-étapes ===
def run_agent(initial_prompt: str, max_step: int = 5):
    print(f"[AGENT] Démarrage de l'agent pour {max_step} étapes maximum.")
    user_prompt = initial_prompt

    for step in range(max_step):
        print(f"\n[STEP {step + 1}] Prompt envoyé à Mistral...")
        response = generateText(user_prompt)
        print("[LLM RESPONSE] ", response)

        result = execute_instructions(response)
        if result == "STOP":
            print("[AGENT] Fin de l'exécution.")
            break

        user_prompt = "Tu peux continuer. Si tu as terminé, appelle la fonction stop()."
    else:
        print("[AGENT] Nombre d'étapes maximum atteint sans arrêt explicite.")

# === Point d’entrée principal ===
if __name__ == "__main__":
    run_agent("""
Crée une fonction Python nommée `add(a, b)` qui retourne leur somme.
Écris un test unitaire associé, exécute-le, puis arrête-toi quand c'est bon.
""", max_step=5)
