import bpy
import math

bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_ground():
    bpy.ops.mesh.primitive_plane_add(size=50, enter_editmode=False, align='WORLD', location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"

def create_tree(x, y):
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=1, radius2=0.5, depth=3, end_fill_type='NGON', enter_editmode=False, align='WORLD', location=(x, y, 0))
    trunk = bpy.context.active_object
    trunk.name = f"Tree_Trunk_{x}_{y}"

    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=2, radius2=0, depth=3, end_fill_type='NGON', enter_editmode=False, align='WORLD', location=(x, y, 3))
    foliage = bpy.context.active_object
    foliage.name = f"Tree_Foliage_{x}_{y}"

def create_river():
    bpy.ops.mesh.primitive_plane_add(size=2, enter_editmode=False, align='WORLD', location=(0, 0, 0.1))
    river = bpy.context.active_object
    river.name = "River"
    river.scale = (30, 5, 1)

def setup_light():
    bpy.ops.object.light_add(type='SUN', align='WORLD', location=(10, -10, 20))
    light = bpy.context.active_object
    light.data.energy = 2.0
    light.name = "Sun"

def setup_camera():
    bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(20, -20, 20), rotation=(math.radians(60), 0, math.radians(45)))
    camera = bpy.context.active_object
    camera.name = "Camera"
    bpy.context.scene.camera = camera

def main():
    clear_scene()
    create_ground()
    create_tree(5, 5)
    create_tree(-5, 5)
    create_tree(0, -10)
    create_river()
    setup_light()
    setup_camera()

if __name__ == "__main__":
    main()