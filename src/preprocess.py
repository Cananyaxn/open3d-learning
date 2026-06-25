import open3d as o3d

def downsample(pcd: o3d.geometry.PointCloud, voxel_size: float = 0.05):
    return pcd.voxel_down_sample(voxel_size=voxel_size)

def estimate_normals(pcd: o3d.geometry.PointCloud, radius: float = 0.1):
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=30)
    )
    return pcd