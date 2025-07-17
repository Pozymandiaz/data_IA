import os
import subprocess
import requests
import time
from dotenv import load_dotenv
from validator import validate_scene, analyze_script

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SCRIPT_FILENAME = "generated_scene.py"
RENDER_FILENAME = "render.png"
MAX_ATTEMPTS = 6

# Prompt simplifié et sans options qui n'existent pas
PROMPT = (
    "Crée un script Python pour Blender 4.4 qui génère une scène naturelle cohérente :\n"
    "- Un sol vert (plane de 50x50 unités, couleur RGBA 0.1, 0.7, 0.1, 1), centré à l'origine (0, 0, 0)\n"
    "- Une rivière rectangulaire (plane bleue RGBA 0.0, 0.3, 0.7, 0.8), de 4 unités de large (axe X) et 50 unités de long (axe Y), légèrement surélevée (Z=0.01), positionnée au centre du sol (location : (0, 0, 0.01))\n"
    "  * La géométrie doit être réellement rectangulaire (pas juste un plane avec scale visuel)\n"
    "- Une forêt : génère automatiquement une quinzaine d'arbres répartis aléatoirement sur le sol en évitant la zone de la rivière (c'est-à-dire à plus de 2 unités en X du centre)\n"
    "  * Chaque arbre se compose de :\n"
    "    - un tronc (cône, couleur marron RGBA 0.2, 0.1, 0.0, 1)\n"
    "    - un feuillage (sphère verte RGBA 0.0, 0.5, 0.0, 1), placé au-dessus du tronc\n"
    "- Une lumière de type 'SUN' placée en hauteur\n"
    "- Trois caméras à activer successivement, avec rendu PNG pour chacune :\n"
    "    1. Vue 3/4 depuis le coin nord-ouest (exemple : location (-20, -20, 20), rotation adaptée)\n"
    "    2. Vue du dessus (exemple : location (0, 0, 60), orientée vers le bas)\n"
    "    3. Vue ras du sol, centrée sur la rivière (exemple : location (0, -10, 1.5), regardant vers (0, 0, 1))\n"
    "- Pour chaque caméra : définis-la comme active, effectue le rendu, puis sauvegarde l'image PNG dans un dossier 'renders' situé à côté du script\n"
    "- Nomme les fichiers 'render_1.png', 'render_2.png' et 'render_3.png'\n"
    "Ne génère que du code Python sans commentaires ni balises Markdown."
)

blender_exec = r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"

def prompt_to_blender_code(prompt: str) -> str:
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "mistral-medium",
        "messages": [
            {"role": "system", "content": (
                "Tu es un assistant expert Blender 4.4. Génère un script Python prêt à exécuter. "
                "Ne mets aucun commentaire ni balise Markdown."
            )},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
    }

    while True:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 429:
            print("⚠️ API saturée, nouvelle tentative dans 30s...")
            time.sleep(60)
            continue
        elif response.status_code != 200:
            raise RuntimeError(f"Erreur API : {response.status_code} - {response.text}")
        break

    return clean_code(response.json()["choices"][0]["message"]["content"])


def clean_code(code: str) -> str:
    lines = code.strip().splitlines()
    # On enlève les balises markdown, commentaires et lignes vides
    lines = [line for line in lines if not line.strip().startswith("```") and not line.strip().startswith("#")]
    lines = [line.rstrip() for line in lines if line.strip()]
    return "\n".join(lines)


def patch_script(script: str) -> str:
    import re

    # Supprimer lignes dangereuses comme 'inputs["Specular"]' ou 'inputs["Roughness"]'
    script = re.sub(r".*inputs\[['\"](Specular|Roughness)['\"]\].*?\n", "", script)

    # Assurer moteur de rendu correct
    script = script.replace("'BLENDER_EEVEE'", "'BLENDER_EEVEE_NEXT'")

    # Corriger chemin de rendu pour éviter C:\render.png
    render_path_code = (
        "import bpy\n"
        "import os\n"
        "output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'renders')\n"
        "os.makedirs(output_dir, exist_ok=True)\n"
        "filepath = os.path.join(output_dir, 'render.png')\n"
        "bpy.context.scene.render.filepath = filepath\n"
    )

    # Remplacer ou ajouter la ligne du filepath de rendu
    # On remplace toute ligne qui set bpy.context.scene.render.filepath
    if "bpy.context.scene.render.filepath" in script:
        script = re.sub(r"bpy\.context\.scene\.render\.filepath\s*=.*\n", render_path_code, script)
    else:
        # Sinon on insère le code en début de script (après import)
        lines = script.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("import bpy"):
                lines.insert(i + 1, render_path_code)
                break
        script = "\n".join(lines)

    return script


def save_script(script: str, filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(script)


def run_blender_script(script_path: str):
    blender_exec = "blender"  # ou chemin complet si besoin
    subprocess.run([blender_exec, "--background", "--python", script_path], check=True)


if __name__ == "__main__":
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n🎯 Tentative {attempt}...")
        try:
            code = prompt_to_blender_code(PROMPT)
            code = patch_script(code)
            save_script(code, SCRIPT_FILENAME)
            run_blender_script(SCRIPT_FILENAME)

            feedback = analyze_script(SCRIPT_FILENAME)
            print("📄 Analyse du script :", feedback)

            if validate_scene(RENDER_FILENAME):
                print("✅ Scène validée !")
                break
            else:
                print("🔁 Nouvelle tentative...")
        except Exception as e:
            print(f"❌ Erreur : {e}")
            time.sleep(5)
