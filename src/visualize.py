"""
visualize.py — 工程④: Open3D 表示 & PLY 保存

工程③で作った TriangleMesh を Open3D のビューワーで表示し、
同じメッシュを PLY ファイルとして保存する。

LineSet から TriangleMesh への変更点
─────────────────────────────────
幅付きメッシュは TriangleMesh として渡されるため、
以前の LineSet 表示から差し替えている。
TriangleMesh は o3d.io.write_triangle_mesh() で直接 PLY 保存できるため、
以前のような PointCloud への変換が不要になった。

座標軸（TriangleMesh.create_coordinate_frame）
─────────────────────────────────
X=赤, Y=緑, Z=青 の矢印を原点付近に表示し、
空間の向きを把握しやすくする。
サイズはデータの広がりに対して 5% に設定している。
"""

import numpy as np
import open3d as o3d


def show(
    mesh: o3d.geometry.TriangleMesh,
    xyz_center: np.ndarray,
    output_ply: str,
):
    # ── PLY 保存（TriangleMesh のまま書き出せる）──────
    o3d.io.write_triangle_mesh(output_ply, mesh)
    print(f"[visualize] PLY 保存: {output_ply}")

    # ── 座標軸（向きの目安）──────────────────────────
    axis_size = max(
        xyz_center[:, 0].max() - xyz_center[:, 0].min(),
        xyz_center[:, 1].max() - xyz_center[:, 1].min(),
    ) * 0.05
    axis = o3d.geometry.TriangleMesh.create_coordinate_frame(
        size=axis_size,
        origin=[
            float(xyz_center[:, 0].min()),
            float(xyz_center[:, 1].min()),
            float(xyz_center[:, 2].min()),
        ],
    )

    # ── ビューワー起動 ────────────────────────────────
    print("[visualize] Open3D ビューワーを起動します（ウィンドウを閉じると終了）")
    o3d.visualization.draw_geometries(
        [mesh, axis],
        window_name="Road 3D Viewer",
        width=1280,
        height=800,
        zoom=0.5,
        front=[0.0, -1.0, 0.5],
        lookat=[0.0, 0.0, float(xyz_center[:, 2].mean())],
        up=[0.0, 0.0, 1.0],
        mesh_show_back_face=True,   # 裏面（道路の下側）も描画する
    )