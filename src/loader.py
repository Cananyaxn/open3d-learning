import laspy
import open3d as o3d
import numpy as np

def load_las(filepath: str) -> o3d.geometry.PointCloud:
    las = laspy.read(filepath)
    points = np.vstack([las.x, las.y, las.z]).T
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    # RGB対応
    try:
        colors = np.vstack([las.red, las.green, las.blue]).T / 65535.0
        pcd.colors = o3d.utility.Vector3dVector(colors)
    except Exception:
        pass
    return pcd