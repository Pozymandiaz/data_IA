import os
import requests
from dotenv import load_dotenv

# Charger .env
load_dotenv()

def prompt_to_blender_code(prompt: str) -> str:
    mistral_api_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_api_key:
        raise ValueError("❌ Clé API Mistral manquante. Vérifie ton fichier .env")

    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {mistral_api_key}",
        "Content-Type": "application/json"
    }

    system_message = (
        "Tu es un expert Blender. Génére uniquement un script Python utilisable directement dans Blender. "
        "Ne mets pas de ``` ni de commentaires ni de texte explicatif."
    )

    data = {
        "model": "mistral-medium",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise RuntimeError(f"Erreur API : {response.status_code} - {response.text}")

    content = response.json()["choices"][0]["message"]["content"]
    return clean_code(content)

def clean_code(code: str) -> str:
    # Supprime les balises Markdown comme ```python ou ```
    lines = code.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines)

def save_script(script: str, filename="generated_scene.py"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"✅ Script Blender enregistré dans {filename}")

if __name__ == "__main__":
    default_prompt = (
        "Crée une scène avec un sol vert, trois arbres en cônes marrons avec feuillage sphérique vert, "
        "une rivière bleue au centre, et une lumière naturelle. Place une caméra pour voir toute la scène."
    )

    try:
        print("🎨 Génération d'une scène Blender via Mistral...")
        blender_code = prompt_to_blender_code(default_prompt)
        save_script(blender_code)
    except Exception as e:
        print(str(e))
