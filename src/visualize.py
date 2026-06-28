"""
visualize.py — 工程④: Open3D 表示 & PLY 保存

工程③で作った TriangleMesh を Open3D のビューワーで表示し、
同じメッシュを PLY ファイルとして保存する。

追加 PLY ファイルの重ね合わせ
─────────────────────────────────
extra_ply_files にファイルパスのリストを渡すと、
道路メッシュと一緒に表示できる。
PLY ファイルは TriangleMesh / PointCloud どちらでも自動判別して読み込む。
  ・頂点のみ（PointCloud）→ o3d.io.read_point_cloud()
  ・面データあり（TriangleMesh）→ o3d.io.read_triangle_mesh()
config の extra_ply_files に複数ファイルを列挙するだけで追加できる。
"""

import numpy as np
import open3d as o3d


def _load_ply(path: str) -> o3d.geometry.Geometry3D:
    """
    PLY ファイルを読み込む。
    面データがあれば TriangleMesh、なければ PointCloud として返す。
    """
    mesh = o3d.io.read_triangle_mesh(path)
    if len(mesh.triangles) > 0:
        mesh.compute_vertex_normals()
        print(f"[visualize] 追加PLY（メッシュ）: {path}  "
              f"頂点={len(mesh.vertices):,} 面={len(mesh.triangles):,}")
        return mesh
    else:
        pcd = o3d.io.read_point_cloud(path)
        print(f"[visualize] 追加PLY（点群）  : {path}  点={len(pcd.points):,}")
        return pcd


def show(
    mesh: o3d.geometry.TriangleMesh,
    xyz_center: np.ndarray,
    output_ply: str,
    extra_ply_files: list[str] | None = None,   # 重ね合わせるPLYファイルのリスト
):
    # ── PLY 保存（TriangleMesh のまま書き出せる）──────
    o3d.io.write_triangle_mesh(output_ply, mesh)
    print(f"[visualize] PLY 保存: {output_ply}")

    # ── 追加PLYの読み込み ─────────────────────────────
    extra_geoms = []
    for path in (extra_ply_files or []):
        try:
            extra_geoms.append(_load_ply(path))
        except Exception as e:
            print(f"[visualize] ⚠️  {path} の読み込みに失敗しました: {e}")

    # ── 座標軸（向きの目安）──────────────────────────
    valid = xyz_center[np.isfinite(xyz_center).all(axis=1)]
    axis_size = max(
        valid[:, 0].max() - valid[:, 0].min(),
        valid[:, 1].max() - valid[:, 1].min(),
    ) * 0.05
    axis = o3d.geometry.TriangleMesh.create_coordinate_frame(
        size=axis_size,
        origin=[
            float(valid[:, 0].min()),
            float(valid[:, 1].min()),
            float(valid[:, 2].min()),
        ],
    )

    # ── ビューワー起動 ────────────────────────────────
    geometries = [mesh] + extra_geoms + [axis]
    print(f"[visualize] Open3D ビューワーを起動します（ウィンドウを閉じると終了）")
    o3d.visualization.draw_geometries(
        geometries,
        window_name="Road 3D Viewer",
        width=1280,
        height=800,
        zoom=0.5,
        front=[0.0, -1.0, 0.5],
        lookat=[
            float(np.nanmean(xyz_center[:, 0])),
            float(np.nanmean(xyz_center[:, 1])),
            float(np.nanmean(xyz_center[:, 2])),
        ],
        up=[0.0, 0.0, 1.0],
        mesh_show_back_face=True,
    )