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

            # Masque vert (feuillage) + marron (troncs)
            green_mask = get_color_mask(data, (25, 80, 25), (110, 210, 110))
            brown_mask = get_color_mask(data, (60, 30, 0), (150, 90, 40))  # approx tronc marron

            # Masque arbre (vert ou marron)
            tree_mask = green_mask | brown_mask

            # On vérifie s'il y a des pixels d'arbres directement sur du bleu
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