import os
from PIL import Image
import numpy as np


def validate_scene(image_filename: str) -> bool:
    """
    Analyse l'image rendue pour valider la scène Blender.
    Vérifie la présence des couleurs vert, bleu, noir,
    que l’image n’est pas uniforme, et que les arbres ne sont pas au-dessus de la rivière.
    """
    if not os.path.isabs(image_filename):
        image_path = os.path.join("renders", image_filename)
    else:
        image_path = image_filename

    if not os.path.exists(image_path):
        print(f"⚠️ Image {image_path} introuvable")
        return False

    img = Image.open(image_path).convert("RGBA")
    pixels = np.array(img)
    height, width, _ = pixels.shape

    # Vérifie que l'image contient du vert
    green_mask = (
        (pixels[:, :, 0] < 100) &   # R faible
        (pixels[:, :, 1] > 150) &   # G élevé
        (pixels[:, :, 2] < 100)     # B faible
    )
    if not green_mask.any():
        print("⚠️ Pas de vert détecté.")
        return False

    # Vérifie la présence de bleu (rivière)
    blue_mask = (
        (pixels[:, :, 0] < 80) &
        (pixels[:, :, 1] < 120) &
        (pixels[:, :, 2] > 120)
    )
    if not blue_mask.any():
        print("⚠️ Pas de bleu détecté.")
        return False

    # Vérifie que l'image n'est pas uniforme (pas unie)
    if np.all(pixels == pixels[0, 0, :]):
        print("⚠️ Image uniforme détectée.")
        return False

    # Vérifie qu'il y a du noir (troncs d'arbre)
    black_mask = (
        (pixels[:, :, 0] < 40) &
        (pixels[:, :, 1] < 40) &
        (pixels[:, :, 2] < 40)
    )
    if not black_mask.any():
        print("⚠️ Pas de noir (troncs) détecté.")
        return False

    # Vérifie que les troncs ne sont pas dans la zone bleue (rivière)
    black_coords = np.column_stack(np.where(black_mask))
    blue_coords = np.column_stack(np.where(blue_mask))
    if black_coords.size == 0 or blue_coords.size == 0:
        print("⚠️ Pas assez de données pour valider la position des troncs.")
        return False

    blue_x_min = blue_coords[:, 1].min()
    blue_x_max = blue_coords[:, 1].max()

    # Pour chaque tronc, vérifier que son x n'est pas dans la plage bleue (rivière)
    for y, x in black_coords:
        if blue_x_min <= x <= blue_x_max:
            print(f"⚠️ Tronc détecté au-dessus de la rivière en pixel x={x}, y={y}.")
            return False

    print("✅ Image validée.")
    return True


def analyze_script(script_path: str) -> dict:
    """
    Analyse sommaire du script pour détecter erreurs potentielles
    ou incohérences (exemple : positions mal définies).
    """
    result = {"issue": None}
    with open(script_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Recherche positions des arbres
    positions_lines = [l for l in lines if "positions" in l]
    if not positions_lines:
        result["issue"] = "La variable 'positions' n'est pas définie."
        return result

    # Exemple d’analyse simplifiée
    # Peut être étendue selon besoin

    return result
