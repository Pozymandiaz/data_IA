import os
import subprocess
import requests
import time
from dotenv import load_dotenv
from validator import validate_scene, analyze_script
import openai 

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
    "    2. Vue du dessus (exemple : location (0, 0, 80), orientée vers le bas)\n"
    "    3. Vue ras du sol, centrée sur la rivière (exemple : location (0, -20, 1.5), regardant vers (0, 0, 1))\n"
    "- Pour chaque caméra : définis-la comme active, effectue le rendu, puis sauvegarde l'image PNG dans un dossier 'renders' situé à côté du script\n"
    "- Nomme les fichiers 'render_1.png', 'render_2.png' et 'render_3.png'\n"
    "⚠️ N’utilise **aucune indentation superflue** en dehors des blocs `for`, `if`, ou des fonctions. Ne décale pas les appels comme `bpy.ops.render.render()` inutilement.\n"
    "Ne génère que du code Python sans commentaires ni balises Markdown."
)

blender_exec = r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"

def prompt_to_blender_code(prompt: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "Tu es un assistant expert Blender 4.4. Génère un script Python prêt à exécuter. "
                "Ne mets aucun commentaire ni balise Markdown."
            )
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # tu peux aussi essayer "gpt-4o" ou "gpt-3.5-turbo" si performances/moindre coût sont préférés
            messages=messages,
            temperature=0.3,
        )
    except openai.error.OpenAIError as e:
        raise RuntimeError(f"Erreur API OpenAI : {e}")

    code = response.choices[0].message["content"]
    return clean_code(code)

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

    if "positions" in script and "positions =" not in script:
        # Ajoute une initialisation défensive de la variable
        script = "positions = []\n" + script

    # Corrige les soucis de scale visuel au lieu de mesh
    script = script.replace(
        "bpy.ops.mesh.primitive_plane_add(size=1",
        "bpy.ops.mesh.primitive_plane_add(size=1)\nobj = bpy.context.object\nbpy.ops.object.editmode_toggle()\nbpy.ops.transform.resize(value=(2, 25, 1))\nbpy.ops.object.editmode_toggle()\n# "
    )
    
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

def run_blender_script_capture_output(script_path: str) -> str:
    """Exécute Blender et capture la sortie d'erreur (stderr)."""
    result = subprocess.run(
        [blender_exec, "--background", "--python", script_path],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return result.stderr.strip()
    return ""

def save_script(script: str, filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(script)


def run_blender_script(script_path: str):
    blender_exec = "blender"  # ou chemin complet si besoin
    subprocess.run([blender_exec, "--background", "--python", script_path], check=True)

def adapt_prompt_with_console_error(prompt: str, error_output: str, script_feedback: dict = None) -> str:
    """Modifie le prompt en fonction de l'erreur Blender et des feedbacks de script."""
    corrections = []

    if "IndentationError" in error_output:
        corrections.append("Corrige les problèmes d'indentation : aucune indentation superflue, ni oubli de bloc indenté.")
    if "referenced before assignment" in error_output:
        corrections.append("Vérifie que toutes les variables sont bien définies avant d'être utilisées.")
    if "expected an indented block" in error_output:
        corrections.append("Ajoute les blocs indentés attendus après les `for`, `if`, ou `def`.")
    if "No module named" in error_output:
        corrections.append("Utilise uniquement les modules Blender intégrés comme `bpy`, `mathutils`.")

    if script_feedback and script_feedback.get("issue"):
        corrections.append(f"Corrige ceci : {script_feedback['issue']}")

    if not corrections:
        return prompt  # pas d'erreur détectée

    correction_text = "\n⚠️ Le script précédent a échoué. Apporte les corrections suivantes :\n"
    for c in corrections:
        correction_text += f"- {c}\n"

    return prompt + correction_text


if __name__ == "__main__":
    prompt = PROMPT
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n🎯 Tentative {attempt}...")
        try:
            code = prompt_to_blender_code(prompt)
            code = patch_script(code)
            save_script(code, SCRIPT_FILENAME)

            error_output = run_blender_script_capture_output(SCRIPT_FILENAME)
            feedback = analyze_script(SCRIPT_FILENAME)

            if error_output:
                print("❌ Erreur Blender détectée :")
                print(error_output)
                prompt = adapt_prompt_with_console_error(prompt, error_output, feedback)
                continue

            print("📄 Analyse du script :", feedback)

            if validate_scene(RENDER_FILENAME):
                print("✅ Scène validée !")
                break
            else:
                print("🔁 Nouvelle tentative (échec validation image)...")

        except Exception as e:
            print(f"❌ Exception inattendue : {e}")
            time.sleep(5)
