from src.loader import load_las
from src.preprocess import downsample, estimate_normals
from src.mesh import create_mesh
from src.visualize import show

pcd = load_las("../../research/src/las/after/experiment1.las")
pcd = downsample(pcd, voxel_size=0.05)
pcd = estimate_normals(pcd)
mesh = create_mesh(pcd)
show(mesh)