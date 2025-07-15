import os
import re
import subprocess
import requests
import time
from dotenv import load_dotenv
from validator import validate_scene

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SCRIPT_FILENAME = "generated_scene.py"
RENDER_FILENAME = "render.png"
MAX_ATTEMPTS = 6

PROMPT_STRUCTURE = (
    "Crée une scène Blender compatible Blender 4.4 avec :\n"
    "- Un sol\n"
    "- Trois arbres composés d’un tronc (cylindre ou cône) et de feuillage (sphère ou cône)\n"
    "- Une rivière au centre\n"
    "- Une lumière naturelle\n"
    "- Une caméra bien placée pour voir toute la scène\n\n"
    "Le script Python doit :\n"
    "- Être directement exécutable dans Blender\n"
    "- Utiliser le moteur de rendu 'BLENDER_EEVEE_NEXT'\n"
    "- Aucune couleur ni matériau n’est nécessaire à ce stade\n"
    "- Ne jamais inclure de backticks Markdown ni commentaires"
)

PROMPT_COLORIZE = (
    "Améliore ce script Blender en ajoutant des couleurs et matériaux compatibles Blender 4.4. Utilise :\n\n"
    "- Sol vert clair (RGBA 0.1, 0.7, 0.1, 1)\n"
    "- Troncs marron foncé (RGBA 0.2, 0.1, 0.0, 1)\n"
    "- Feuillage vert (RGBA 0.0, 0.5, 0.0, 1)\n"
    "- Rivière bleue translucide (RGBA 0.0, 0.3, 0.7, 0.8)\n\n"
    "Le script modifié doit :\n"
    "- Créer les matériaux avec 'Principled BSDF' de manière robuste\n"
    "- Affecter les matériaux à chaque objet correspondant\n"
    "- Utiliser 'BLENDER_EEVEE_NEXT'\n"
    "- Générer un fichier 'render.png' dans le même dossier\n"
    "- Ne jamais inclure de backticks Markdown ni commentaires"
)


def prompt_to_blender_code(prompt: str) -> str:
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistral-medium",
        "messages": [
            {"role": "system", "content": "Tu es un expert Blender Python. Génère un script compatible Blender 4.4."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
    }
    while True:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 429:
            print("⚠️ Limite API atteinte, attente 30 secondes...")
            time.sleep(30)
            continue
        elif response.status_code != 200:
            raise RuntimeError(f"Erreur API : {response.status_code} - {response.text}")
        break
    return clean_code(response.json()["choices"][0]["message"]["content"])

def clean_code(code: str) -> str:
    lines = code.strip().splitlines()

    # On extrait uniquement les lignes de code à partir de "import bpy"
    code_start = next((i for i, line in enumerate(lines) if "import bpy" in line), 0)
    code_lines = lines[code_start:]

    # On coupe tout après le "main()" final pour éviter les descriptions parasites
    for i, line in enumerate(code_lines):
        if 'main()' in line and '__name__' in code_lines[i - 1]:
            return "\n".join(code_lines[:i + 1])

    return "\n".join(code_lines)

def save_script(script: str, filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(script)

def run_blender_script(script_path: str):
    blender_exec = "blender"
    subprocess.run([blender_exec, "--background", "--python", script_path], check=True)

if __name__ == "__main__":
    attempt = 0
    while attempt < MAX_ATTEMPTS:
        print(f"\n🎯 Étape 1 : Génération structure ({attempt + 1})...")
        try:
            base_code = prompt_to_blender_code(PROMPT_STRUCTURE)
            save_script(base_code, SCRIPT_FILENAME)
            run_blender_script(SCRIPT_FILENAME)

            print("\n🎯 Étape 2 : Application des matériaux...")
            enhanced_prompt = f"{PROMPT_COLORIZE}\n\nVoici le code de base :\n{base_code}"
            colored_code = prompt_to_blender_code(enhanced_prompt)
            save_script(colored_code, SCRIPT_FILENAME)
            run_blender_script(SCRIPT_FILENAME)

            if validate_scene(RENDER_FILENAME):
                print("✅ Scène validée !")
                break
        except Exception as e:
            print(f"❌ Erreur : {e}")
        print("🔁 Nouvelle tentative...")
        attempt += 1
