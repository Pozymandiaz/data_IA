import os
from PIL import Image
import numpy as np


def validate_scene(image_path: str) -> bool:
    """
    Analyse l'image rendue pour valider la scène Blender :
    - Présence de vert, bleu, marron
    - Image non vide, non monochrome
    - Ratios équilibrés entre les couleurs attendues
    """
    if not os.path.exists(image_path):
        print("❌ Aucune image de rendu trouvée.")
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

            # Compte des pixels verts, bleus, bruns
            green = count_color_range(pixels, (25, 80, 25), (110, 210, 110))
            blue = count_color_range(pixels, (20, 40, 100), (100, 130, 255))
            brown = count_color_range(pixels, (60, 30, 0), (160, 110, 60))

            total = len(pixels)
            g_ratio = green / total
            b_ratio = blue / total
            br_ratio = brown / total

            print(f"🟩 Vert: {g_ratio:.2%} | 🟦 Bleu: {b_ratio:.2%} | 🟫 Marron: {br_ratio:.2%}")

            # Seuils minimums absolus
            if g_ratio < 0.01:
                print("⚠️ Trop peu de vert : sol ou arbres manquants ?")
                return False

            if b_ratio < 0.003:
                print("⚠️ Trop peu de bleu : rivière absente ou trop discrète ?")
                return False

            if br_ratio < 0.002:
                print("⚠️ Trop peu de marron : troncs d’arbres absents ou invisibles ?")
                return False

            # Vérifie une diversité minimale
            if g_ratio + b_ratio + br_ratio < 0.05:
                print("⚠️ Scène trop vide : peu de contenu identifiable.")
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
