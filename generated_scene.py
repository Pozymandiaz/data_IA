import bpy
import os
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.mesh.primitive_plane_add(size=20, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
sol = bpy.context.active_object
mat_sol = bpy.data.materials.new(name="Mat_Sol")
mat_sol.diffuse_color = (0.1, 0.7, 0.1, 1)
sol.data.materials.append(mat_sol)
bpy.ops.mesh.primitive_plane_add(size=10, enter_editmode=False, align='WORLD', location=(0, 0, 0.01), scale=(0.5, 2, 1))
riviere = bpy.context.active_object
mat_riviere = bpy.data.materials.new(name="Mat_Riviere")
mat_riviere.diffuse_color = (0.0, 0.3, 0.7, 0.8)
riviere.data.materials.append(mat_riviere)
def create_tree(x, y):
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.3, radius2=0.1, depth=1, end_fill_type='NGON', enter_editmode=False, align='WORLD', location=(x, y, 0.5), scale=(1, 1, 1))
    tronc = bpy.context.active_object
    mat_tronc = bpy.data.materials.new(name="Mat_Tronc")
    mat_tronc.diffuse_color = (0.2, 0.1, 0.0, 1)
    tronc.data.materials.append(mat_tronc)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.7, enter_editmode=False, align='WORLD', location=(x, y, 1.5), scale=(1, 1, 1))
    feuillage = bpy.context.active_object
    mat_feuillage = bpy.data.materials.new(name="Mat_Feuillage")
    mat_feuillage.diffuse_color = (0.0, 0.5, 0.0, 1)
    feuillage.data.materials.append(mat_feuillage)
create_tree(-2, 0)
create_tree(0, 0)
create_tree(2, 0)
bpy.ops.object.light_add(type='SUN', align='WORLD', location=(5, 5, 10), scale=(1, 1, 1))
soleil = bpy.context.active_object
soleil.data.energy = 2.0
bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(5, -5, 5), rotation=(1.0, 0.0, 0.7), scale=(1, 1, 1))
camera = bpy.context.active_object
bpy.context.scene.camera = camera
import bpy
import os
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'renders')
os.makedirs(output_dir, exist_ok=True)
filepath = os.path.join(output_dir, 'render.png')
bpy.context.scene.render.filepath = filepath
bpy.ops.render.render(write_still=True)