"""
visualize.py — 工程④: Open3D 表示 & PLY 保存

工程③で作った xyz / seg_arr / colors を Open3D の LineSet に組み込み、
インタラクティブビューワーで表示する。
同時に点群（PointCloud）として PLY ファイルに保存する。

LineSet と PointCloud を両方使う理由
─────────────────────────────────
・LineSet  → 道路の「線」として視覚的に正確に表示できる
・PointCloud → Open3D の PLY 書き出し API が PointCloud に対応しているため。
              LineSet を直接 PLY に保存する公式 API がない。
              保存した PLY は MeshLab / CloudCompare でも開ける。

座標軸（TriangleMesh.create_coordinate_frame）
─────────────────────────────────
X=赤, Y=緑, Z=青 の矢印を原点付近に表示し、
空間の向きを把握しやすくする。
サイズはデータの広がりに対して 5% に設定している。
"""

import numpy as np
import open3d as o3d
from . import build_3d   # 頂点色の生成に使う


def save_ply(xyz: np.ndarray, vertex_colors: np.ndarray, output_path: str):
    """点群として PLY に保存する"""
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)
    pcd.colors = o3d.utility.Vector3dVector(vertex_colors)
    o3d.io.write_point_cloud(output_path, pcd)
    print(f"[visualize] PLY 保存: {output_path}  ({len(xyz):,} 点)")


def show(
    xyz: np.ndarray,
    seg_arr: np.ndarray,
    colors: np.ndarray,
    output_ply: str,
    color_by_height: bool = True,
):
    # ── LineSet（表示用）──────────────────────────
    line_set = o3d.geometry.LineSet()
    line_set.points = o3d.utility.Vector3dVector(xyz)
    line_set.lines  = o3d.utility.Vector2iVector(seg_arr)
    line_set.colors = o3d.utility.Vector3dVector(colors)

    # ── PLY 保存（点群として）──────────────────────
    vertex_colors = build_3d.get_vertex_colors(xyz, color_by_height)
    save_ply(xyz, vertex_colors, output_ply)

    # ── 座標軸（向きの目安）──────────────────────
    axis_size = max(xyz[:, 0].max() - xyz[:, 0].min(),
                    xyz[:, 1].max() - xyz[:, 1].min()) * 0.05
    axis = o3d.geometry.TriangleMesh.create_coordinate_frame(
        size=axis_size,
        origin=[xyz[:, 0].min(), xyz[:, 1].min(), xyz[:, 2].min()],
    )

    # ── ビューワー起動 ────────────────────────────
    print("[visualize] Open3D ビューワーを起動します（ウィンドウを閉じると終了）")
    o3d.visualization.draw_geometries(
        [line_set, axis],
        window_name="Road 3D Viewer",
        width=1280,
        height=800,
        zoom=0.5,
        front=[0.0, -1.0, 0.5],
        lookat=[0.0, 0.0, float(xyz[:, 2].mean())],
        up=[0.0, 0.0, 1.0],
    )