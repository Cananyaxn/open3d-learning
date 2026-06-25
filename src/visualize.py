import open3d as o3d

def show(geometry):
    o3d.visualization.draw_geometries([geometry])