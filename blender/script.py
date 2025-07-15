import bpy
import random
import math

# Supprimer tous les objets existants
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Fonction pour ajouter une couleur
def add_material(obj, name, color):
    mat = bpy.data.materials.new(name=name)
    mat.diffuse_color = color
    obj.data.materials.append(mat)

# Fonction pour positionner un objet de manière aléatoire
def random_position(range_xy=10, height=0):
    x = random.uniform(-range_xy, range_xy)
    y = random.uniform(-range_xy, range_xy)
    z = height
    return (x, y, z)

# Créer un sol
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
ground = bpy.context.active_object
add_material(ground, "GroundMaterial", (0.1, 0.5, 0.1, 1))  # Vert

# Liste des types d'objets à ajouter
object_types = ['CUBE', 'SPHERE', 'CYLINDER', 'CONE', 'TORUS']

for i in range(10):
    obj_type = random.choice(object_types)
    pos = random_position(height=1)

    if obj_type == 'CUBE':
        bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    elif obj_type == 'SPHERE':
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.7, location=pos)
    elif obj_type == 'CYLINDER':
        bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=2, location=pos)
    elif obj_type == 'CONE':
        bpy.ops.mesh.primitive_cone_add(radius1=0.6, depth=2, location=pos)
    elif obj_type == 'TORUS':
        bpy.ops.mesh.primitive_torus_add(location=pos)

    obj = bpy.context.active_object
    color = (random.random(), random.random(), random.random(), 1)
    add_material(obj, f"Mat_{i}", color)

# Ajouter une lumière
bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
light = bpy.context.active_object

# Ajouter une caméra
bpy.ops.object.camera_add(location=(15, -15, 10), rotation=(math.radians(60), 0, math.radians(45)))
cam = bpy.context.active_object
bpy.context.scene.camera = cam
