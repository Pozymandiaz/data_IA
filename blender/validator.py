import os
from PIL import Image
import numpy as np


def validate_scene(image_path: str) -> bool:
    """
    Analyse l'image rendue pour valider la scène Blender :
    - Présence de vert, bleu, noir (ombres)
    - Image non vide, non monochrome
    - Seuils simplifiés pour validation plus facile
    - Si un arbre est au dessus de l'eau, scène non validée et déplace l'arbre au dessus de l'herbe
    """
    # Si chemin relatif, chercher dans dossier "renders"
    if not os.path.isabs(image_path):
        image_path = os.path.join("renders", image_path)

    if not os.path.exists(image_path):
        print(f"❌ Aucune image de rendu trouvée à {image_path}.")
        return False

    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            data = np.array(img)
            pixels = data.reshape((-1, 3))

            # Vérifie que l’image n’est pas trop uniforme (échec de rendu typique)
            std_devs = np.std(pixels, axis=0)
            if np.mean(std_devs) < 5:
                print("⚠️ Image trop uniforme, probablement vide ou mal éclairée.")
                return False

            # Compte des pixels verts, bleus, noirs
            green = count_color_range(pixels, (25, 80, 25), (110, 210, 110))
            blue = count_color_range(pixels, (20, 40, 100), (100, 130, 255))
            black = count_color_range(pixels, (0, 0, 0), (40, 40, 40))  # noir sombre pour ombres

            total = len(pixels)
            g_ratio = green / total
            b_ratio = blue / total
            bl_ratio = black / total

            print(f"🟩 Vert: {g_ratio:.2%} | 🟦 Bleu: {b_ratio:.2%} | ⚫ Noir: {bl_ratio:.2%}")

            # Seuils simplifiés
            if g_ratio < 0.005:
                print("⚠️ Trop peu de vert : sol ou arbres manquants ?")
                return False

            if b_ratio < 0.002:
                print("⚠️ Trop peu de bleu : rivière absente ou trop discrète ?")
                return False

            if bl_ratio < 0.005:
                print("⚠️ Trop peu de noir : ombres (troncs) absentes ou invisibles ?")
                return False

            # Vérifie une diversité minimale plus simple
            if g_ratio + b_ratio + bl_ratio < 0.03:
                print("⚠️ Scène trop vide : peu de contenu identifiable.")
                return False
            blue_mask = get_color_mask(data, (20, 40, 100), (100, 130, 255))

           
            green_mask = get_color_mask(data, (25, 80, 25), (110, 210, 110))
            brown_mask = get_color_mask(data, (60, 30, 0), (150, 90, 40))  

            
            tree_mask = green_mask | brown_mask

            overlap = np.logical_and(tree_mask, blue_mask)

            if np.any(overlap):
                print("🚫 Un ou plusieurs arbres détectés au-dessus de la rivière !")
                return False

            print("✅ La scène semble visuellement cohérente.")
            return True
            

    except Exception as e:
        print("❌ Erreur lors de l'analyse de l'image :", e)
        return False


def count_color_range(pixels, lower, upper):
    """Compte le nombre de pixels dans une plage de couleurs (RGB)"""
    lower = np.array(lower, dtype=np.uint8)
    upper = np.array(upper, dtype=np.uint8)
    mask = np.all((pixels >= lower) & (pixels <= upper), axis=1)
    return np.count_nonzero(mask)

def get_color_mask(data, lower, upper):
    """Renvoie un masque booléen des pixels dans la plage"""
    lower = np.array(lower, dtype=np.uint8)
    upper = np.array(upper, dtype=np.uint8)
    mask = np.all((data >= lower) & (data <= upper), axis=2)
    return mask

def is_river_wide_enough(blue_mask, min_width_pixels=30):
    # Mesure la largeur max de la rivière sur chaque ligne
    max_width = 0
    for row in blue_mask:
        row_width = np.count_nonzero(row)
        max_width = max(max_width, row_width)
    return max_width >= min_width_pixels

import re

def analyze_script(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    # Extraction brutale (améliorable)
    tree_positions = re.findall(r'create_tree\((-?\d+),\s*(-?\d+)\)', code)
    river_scale = re.search(r'scale=\((\d+\.?\d*),\s*(\d+\.?\d*),', code)
    river_center = re.search(r'location=\(([\d\.\-]+),\s*([\d\.\-]+),', code)

    feedback = {}

    if tree_positions:
        positions = [(int(x), int(y)) for x, y in tree_positions]
        feedback['tree_positions'] = positions

    if river_scale and river_center:
        rx, ry = float(river_scale.group(1)), float(river_scale.group(2))
        cx, cy = float(river_center.group(1)), float(river_center.group(2))
        feedback['river'] = {
            'scale': (rx, ry),
            'center': (cx, cy),
            'bounds_y': (cy - ry * 1, cy + ry * 1)  # grossière estimation Y
        }

        # Détection d’arbres dans la rivière
        in_river = [
            (x, y) for x, y in positions
            if feedback['river']['bounds_y'][0] <= y <= feedback['river']['bounds_y'][1]
        ]
        if in_river:
            feedback['issue'] = f"{len(in_river)} arbre(s) dans la rivière : {in_river}"
        else:
            feedback['issue'] = None

    return feedback
