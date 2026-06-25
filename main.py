from dotenv import load_dotenv
import os

from src.loader import load_las
from src.preprocess import downsample, estimate_normals
from src.mesh import create_mesh
from src.visualize import show

load_dotenv()
LAS_FILE = os.getenv("LAS_FILE")
MESH_OUTPUT = os.getenv("MESH_OUTPUT")

pcd = load_las(LAS_FILE)
pcd = downsample(pcd, voxel_size=0.05)
pcd = estimate_normals(pcd)
mesh = create_mesh(pcd)
show(mesh)