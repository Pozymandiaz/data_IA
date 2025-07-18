import os
import subprocess
import requests
import time
import re
from dotenv import load_dotenv

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SCRIPT_FILENAME = "generated_scene.py"
RENDER_FILENAMES = ["render_1.png", "render_2.png", "render_3.png"]
MAX_ATTEMPTS = 6

PROMPT = """
    Crée un script Python pour Blender 4.4 qui génère une scène naturelle cohérente :
    - Un sol vert (plane de 50x50 unités, couleur RGBA 0.1, 0.7, 0.1, 1), centré à l'origine (0, 0, 0)
    - Une rivière rectangulaire (plane bleue RGBA 0.0, 0.3, 0.7, 0.8), de 4 unités de large (axe X) et 50 unités de long (axe Y), légèrement surélevée (Z=0.01), positionnée au centre du sol (location : (0, 0, 0.01))
      * La géométrie doit être réellement rectangulaire (pas juste un plane avec scale visuel)
    - Une forêt : génère automatiquement une quinzaine d'arbres répartis aléatoirement sur le sol en évitant la zone de la rivière (c'est-à-dire à plus de 2 unités en X du centre)
      * Chaque arbre se compose de :
        - un tronc (cône, couleur marron RGBA 0.2, 0.1, 0.0, 1)
        - un feuillage (sphère verte RGBA 0.0, 0.5, 0.0, 1), placé au-dessus du tronc
    - Une lumière de type 'SUN' placée en hauteur
    - Trois caméras à activer successivement, avec rendu PNG pour chacune :
        1. Vue 3/4 depuis le coin nord-ouest (exemple : location (-20, -20, 20), rotation adaptée)
        2. Vue du dessus (exemple : location (0, 0, 80), orientée vers le bas)
        3. Vue ras du sol, centrée sur la rivière (exemple : location (0, -20, 1.5), regardant vers (0, 0, 1))
    - Pour chaque caméra : définis-la comme active, effectue le rendu, puis sauvegarde l'image PNG dans un dossier 'renders' situé à côté du script
    - Nomme les fichiers 'render_1.png', 'render_2.png' et 'render_3.png'
    ⚠️ N’utilise **aucune indentation superflue** en dehors des blocs `for`, `if`, ou des fonctions. Ne décale pas les appels comme `bpy.ops.render.render()` inutilement.
    Ne génère que du code Python sans commentaires ni balises Markdown.
"""

system_prompt = """
GOAL: Generate a Python script for Blender 4.4 to build a 3D scene based on user demand.
The generated script will be executed inside Blender to produce the scene.

GENERAL GUIDELINES:
- Generate ONLY executable Python code — no comments, no explanations, no Markdown tags.
- Use the bpy library.
- The code must be clean and modular, organized with reusable functions.
    - Use primitive functions (e.g., add_plane, add_cube, add_cylinder, etc.)
    - Compose higher-level objects (e.g., add_tree, add_bridge, add_desert) using these primitives.
    - Group complex objects into their own collections for organization.
- Take your time to generate, reflect and reread your code to ensure that it will work.

IMPORTANT RULES:
- NEVER use `bpy.context.object` or `bpy.context.active_object`.
    - Instead, capture created objects via:
        - `obj = bpy.data.objects[-1]` immediately after creation
        - or store the object via naming and retrieve it by name via `bpy.data.objects.get("MyObject")`
    - Use robust access patterns that do not rely on the current selection or active object.

- Handle light setup: create at least one light with appropriate energy and position.
- Apply materials or colors to objects to make the scene visually coherent and rich.
- Ensure realistic proportions and object placements.
- Always name your objects with logical names (tree_1, house_1)

CAMERA & RENDERING:
- Add three cameras to visualize the scene:
    1. Camera 1: 3/4 view from northwest (example: location=(-20, -20, 20), rotation facing scene)
    2. Camera 2: Top-down view (location=(0, 0, 80), rotation looking down)
    3. Camera 3: Ground-level view facing the river (location=(0, -20, 1.5), looking toward (0, 0, 1))
- For each camera:
    - Set it as the active camera
    - Render the scene
    - Save the image in a folder named 'renders' (created next to the script file)
    - Output files must be named 'render_1.png', 'render_2.png', and 'render_3.png'

CONSTRAINTS:
- The generated script must run without manual corrections in Blender 4.4.
- The script must be self-contained: it creates all data, objects, materials, lights, and cameras.
- If the user request lacks detail, assume a rich environment: landscape, vegetation, water, etc.
- Create a plane 100x100 units and place objects logically on it. 

"""

blender_exec = r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"

def clean_code(code: str) -> str:
    lines = code.strip().splitlines()
    lines = [line for line in lines if not line.strip().startswith("```") and not line.strip().startswith("#")]
    lines = [line.rstrip() for line in lines if line.strip()]
    return "\n".join(lines)

def patch_script(script: str) -> str:
    # Nettoyage de certaines erreurs connues
    script = re.sub(r".*inputs\[['\"](Specular|Roughness)['\"]\].*?\n", "", script)
    script = script.replace("'BLENDER_EEVEE'", "'BLENDER_EEVEE_NEXT'")

    if "positions" in script and "positions =" not in script:
        script = "positions = []\n" + script

    # Patch incorrect de plane à géométrie rectangle
    script = script.replace(
        "bpy.ops.mesh.primitive_plane_add(size=1",
        "bpy.ops.mesh.primitive_plane_add(size=1)\nobj = bpy.data.objects[-1]\nbpy.ops.object.editmode_toggle()\nbpy.ops.transform.resize(value=(2, 25, 1))\nbpy.ops.object.editmode_toggle()\n# "
    )

    # Ajout du code pour gérer le répertoire de rendu
    render_header = (
        "import os\n"
        "output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'renders')\n"
        "os.makedirs(output_dir, exist_ok=True)\n"
    )

    # Ajouter le header juste après `import bpy`
    lines = script.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "import bpy":
            lines.insert(i + 1, render_header)
            break
    script = "\n".join(lines)

    # Modifier dynamiquement chaque bloc de rendu
    for idx in range(1, 4):
        render_pattern = rf'bpy\.context\.scene\.render\.filepath\s*=.*?[\'"]render_{idx}\.png[\'"]'
        render_code = (
            f"    bpy.context.scene.render.filepath = os.path.join(output_dir, 'render_{idx}.png')"
        )
        if re.search(render_pattern, script):
            script = re.sub(render_pattern, render_code, script)
        else:
            # Si la ligne n'existe pas, insérer avant chaque `bpy.ops.render.render()`
            render_lines = script.splitlines()
            for i, line in enumerate(render_lines):
                if f"render_{idx}.png" in line or f"render({'' if line.strip().endswith(')') else ')' }" in line:
                    render_lines.insert(i, render_code)
                    break
            script = "\n".join(render_lines)

    return script

def run_blender_script_capture_output(script_path: str) -> str:
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

def check_render_outputs():
    render_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'renders')
    return all(os.path.exists(os.path.join(render_dir, filename)) for filename in RENDER_FILENAMES)

def adapt_prompt_with_console_error(prompt: str, error_output: str, script_feedback: dict = None) -> str:
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
        return prompt
    correction_text = "\n⚠️ Le script précédent a échoué. Apporte les corrections suivantes :\n"
    for c in corrections:
        correction_text += f"- {c}\n"
    return prompt + correction_text

def prompt_to_blender_code(prompt: str, system_prompt: str) -> str:
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "codestral-2501",
        "max_tokens": 10000,
        "messages": [
            {"role": "system", "content": system_prompt},
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
    content = response.json()["choices"][0]["message"]["content"]
    print("\n🧠 Contenu brut renvoyé par Mistral :\n", content[:1000])
    return clean_code(content)

def main():
    user_prompt = input("📝 Que veux-tu générer comme scène Blender ?\n> ").strip()
    prompt = user_prompt
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n🎯 Tentative {attempt}...")
        try:
            code = prompt_to_blender_code(prompt, system_prompt)
            print("\n📤 Script généré par l'API :\n")
            print(code[:3000])
            code = patch_script(code)
            save_script(code, SCRIPT_FILENAME)
            error_output = run_blender_script_capture_output(SCRIPT_FILENAME)
            if error_output:
                print("❌ Erreur Blender détectée :")
                print(error_output)
                continue
            if check_render_outputs():
                print("✅ Scène validée !")
                break
            else:
                print("🔁 Nouvelle tentative (échec validation image)...")
        except Exception as e:
            print(f"❌ Exception inattendue : {e}")
            time.sleep(5)

def indent_lines(code: str, level: int = 1, indent_with="    ") -> str:
    indent = indent_with * level
    return "\n".join(indent + line if line.strip() else line for line in code.splitlines())


if __name__ == "__main__":
    main()
