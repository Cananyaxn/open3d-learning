import open3d as o3d
import numpy as np

def create_mesh(pcd: o3d.geometry.PointCloud, depth: int = 9):
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=depth
    )
    # ノイズ除去
    vertices_to_remove = densities < np.quantile(densities, 0.05)
    mesh.remove_vertices_by_mask(vertices_to_remove)
    return mesh