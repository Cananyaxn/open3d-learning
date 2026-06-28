"""
build_3d.py — 工程③: 座標変換・幅付きメッシュ組み立て

経度・緯度（度）をメートル単位の平面座標 (x, y) に変換し、
幅員クラスをもとに各線分を「幅を持つ四角形（三角形2枚）」に展開して
Open3D の TriangleMesh を構築する。

なぜ LineSet から TriangleMesh に変わるのか
─────────────────────────────────
LineSet は「幅のない線」しか表現できない。
道路の幅を表現するには、線分を左右にオフセットして
4頂点の短冊（クワッド）を作り、それを三角形2枚に分割する必要がある。

  始点 ──────────── 終点
    |  ← 幅/2 →  |
  v0  ──────────── v1    ← 左側オフセット頂点
  v3  ──────────── v2    ← 右側オフセット頂点

  三角形① : v0, v1, v2
  三角形② : v0, v2, v3

法線ベクトルの計算
─────────────────────────────────
線分の進行方向ベクトル d = (dx, dy) に対して
水平面上の垂直方向は n = (-dy, dx) を正規化したもの。
これを左右に幅/2 スケールして頂点をオフセットする。
高さ（z）は左右の頂点とも線分の標高をそのまま使う（坂道の傾きは無視）。

幅員クラス → 実メートル変換
─────────────────────────────────
N13_006 の各クラスに対してデフォルト代表幅を定義しており、
config の width_map で上書き可能にしている。

返り値
─────────────────────────────────
mesh : open3d.geometry.TriangleMesh   幅付き道路の3Dメッシュ
xyz  : np.ndarray  shape=(N_orig, 3) 元の中心線頂点座標（PLY保存・座標軸サイズ計算に使用）
"""

import numpy as np
import open3d as o3d

# N13_006 クラス → 代表幅 (m) のデフォルト対応表
DEFAULT_WIDTH_MAP = {
    1: 2.0,   # 3m 未満
    2: 4.0,   # 3m 〜 5.5m 未満
    3: 9.0,   # 5.5m 〜 13m 未満
    4: 16.0,  # 13m 〜 19.5m 未満
    5: 22.0,  # 19.5m 以上
    6: 2.0,   # 不明 → 最小幅でフォールバック
}


def _jet_colormap(t: np.ndarray) -> np.ndarray:
    """
    0〜1 に正規化されたスカラー値 t を Jet 配色の RGB に変換する。
    低値=青、中値=緑、高値=赤。
    """
    r = np.clip(1.5 - np.abs(4 * t - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * t - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * t - 1), 0, 1)
    return np.stack([r, g, b], axis=1)


def _lonlat_to_meters(lons, lats, origin_lon, origin_lat):
    """経度・緯度をメートル平面座標に変換（球面余弦近似）"""
    R = 6_371_000.0
    lat_rad = np.radians(origin_lat)
    x = (lons - origin_lon) * np.radians(1) * R * np.cos(lat_rad)
    y = (lats - origin_lat) * np.radians(1) * R
    return x, y


def build(
    points: list[tuple[float, float]],
    elevations: np.ndarray,
    segments: list[tuple[int, int]],
    width_classes: list[int],
    xy_meters: np.ndarray,        # sample_dem で変換済みのメートルXY座標 shape=(N,2)
    z_scale: float = 1.0,
    color_by_height: bool = True,
    width_map: dict[int, float] | None = None,
):
    wmap = {**DEFAULT_WIDTH_MAP, **(width_map or {})}

    # sample_dem で変換済みのメートル座標をそのまま使う。
    # 重心移動はしない。絶対座標を維持することで
    # CloudCompare 等で元の点群と位置が一致する。
    x = xy_meters[:, 0]
    y = xy_meters[:, 1]
    z = elevations * z_scale

    # 中心線頂点の XYZ（PLY 保存・座標軸サイズ計算に流用）
    xyz_center = np.stack([x, y, z], axis=1).astype(np.float64)

    # ── 線分ごとに幅付き四角形（三角形2枚）を生成 ──────
    all_verts = []   # 頂点座標を積み上げる
    all_tris  = []   # 三角形インデックスを積み上げる
    all_colors = []  # 頂点色を積み上げる

    # 色付けに使う標高の正規化値（中心線頂点ベース）
    # NaN を除いた min/max で正規化し、NaN 頂点は 0 扱いにする
    z_valid_min = np.nanmin(z)
    z_valid_max = np.nanmax(z)
    z_norm = (z - z_valid_min) / (z_valid_max - z_valid_min + 1e-9)
    z_norm = np.where(np.isfinite(z_norm), z_norm, 0.0)

    for seg_idx, (i0, i1) in enumerate(segments):
        p0 = xyz_center[i0]   # 始点 (x, y, z)
        p1 = xyz_center[i1]   # 終点 (x, y, z)

        # 始点・終点どちらかがDEM範囲外（NaN）なら線分をスキップ
        if np.isnan(p0[2]) or np.isnan(p1[2]):
            continue

        # 進行方向ベクトル（XY 平面のみ。Z は法線計算に不要）
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        length = np.hypot(dx, dy)
        if length < 1e-9:
            # 始点と終点が同座標の縮退線分はスキップ
            continue

        # 水平面上の法線ベクトル（進行方向に直交、単位ベクトル）
        nx, ny = -dy / length, dx / length

        half_w = wmap.get(width_classes[seg_idx], 2.0) / 2.0

        # 4頂点を生成（左右 × 始終点）
        #   v0: 始点・左   v1: 終点・左
        #   v3: 始点・右   v2: 終点・右
        v0 = [p0[0] + nx * half_w, p0[1] + ny * half_w, p0[2]]
        v1 = [p1[0] + nx * half_w, p1[1] + ny * half_w, p1[2]]
        v2 = [p1[0] - nx * half_w, p1[1] - ny * half_w, p1[2]]
        v3 = [p0[0] - nx * half_w, p0[1] - ny * half_w, p0[2]]

        base = len(all_verts)
        all_verts.extend([v0, v1, v2, v3])

        # クワッドを三角形2枚に分割
        all_tris.append([base,     base + 1, base + 2])
        all_tris.append([base,     base + 2, base + 3])

        # 頂点色：始点・終点の標高平均で4頂点を統一着色
        if color_by_height:
            t = float((z_norm[i0] + z_norm[i1]) / 2)
            # _jet_colormap は (N,) 配列を受け取る設計のため np.array で包む
            c = _jet_colormap(np.array([t]))[0]   # shape (3,)
        else:
            c = np.array([1.0, 1.0, 1.0])
        all_colors.extend([c, c, c, c])

    if not all_verts:
        raise RuntimeError('有効な線分が1本もありませんでした。データを確認してください。')

    verts  = np.array(all_verts,  dtype=np.float64)   # (N*4, 3)
    tris   = np.array(all_tris,   dtype=np.int32)     # (N*2, 3)
    colors = np.array(all_colors, dtype=np.float64)   # (N*4, 3)

    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices       = o3d.utility.Vector3dVector(verts)
    mesh.triangles      = o3d.utility.Vector3iVector(tris)
    mesh.vertex_colors  = o3d.utility.Vector3dVector(colors)
    mesh.compute_vertex_normals()   # シェーディング用法線を自動計算

    print(f"[build_3d] 頂点数(メッシュ): {len(verts):,}  三角形数: {len(tris):,}")
    print(f"[build_3d] x範囲: {x.min():.1f} 〜 {x.max():.1f} m")
    print(f"[build_3d] y範囲: {y.min():.1f} 〜 {y.max():.1f} m")
    print(f"[build_3d] z範囲: {np.nanmin(z):.1f} 〜 {np.nanmax(z):.1f} m  (z_scale={z_scale})")
    return mesh, xyz_center