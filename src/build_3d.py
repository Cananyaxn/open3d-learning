"""
build_3d.py — 工程③: 座標変換と 3D データ組み立て

経度・緯度（度）をメートル単位の平面座標 (x, y) に変換し、
標高 (z) と合わせて Open3D が扱える形式に整える。

なぜ度からメートルに変換するのか
─────────────────────────────────
Open3D は単位を持たない XYZ 空間を扱う。
経度・緯度のままだと x と z（標高）のスケールが大きく違い
（1度 ≈ 111km に対して標高は高くても数百メートル）、
3D 表示したときに道路が紙のように薄く見えてしまう。
メートルに統一することでスケールが揃い、z_scale による誇張も直感的になる。

座標変換の方式（平面近似）
─────────────────────────────────
本格的には UTM 投影や平面直角座標系（JGD2011）を使うべきだが、
数十 km 以内の範囲なら球面余弦近似で十分な精度が得られる。
  x = (lon - origin_lon) × cos(origin_lat) × π/180 × R
  y = (lat - origin_lat)                   × π/180 × R
  R = 6,371,000 m（地球半径）
原点は全頂点の重心（平均緯度・平均経度）に置く。

返り値
─────────────────────────────────
xyz      : np.ndarray  shape=(N, 3)  [x_m, y_m, z_m]
segments : np.ndarray  shape=(M, 2)  int32  （工程①の segments をそのまま配列化）
colors   : np.ndarray  shape=(M, 3)  float  各線分の RGB（0〜1）
"""

import numpy as np


def _jet_colormap(t: np.ndarray) -> np.ndarray:
    """
    0〜1 に正規化されたスカラー値 t を Jet 配色の RGB に変換する。
    低値=青、中値=緑、高値=赤。
    """
    r = np.clip(1.5 - np.abs(4 * t - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * t - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * t - 1), 0, 1)
    return np.stack([r, g, b], axis=1)


def build(
    points: list[tuple[float, float]],
    elevations: np.ndarray,
    segments: list[tuple[int, int]],
    z_scale: float = 1.0,
    color_by_height: bool = True,
):
    lons = np.array([p[0] for p in points])
    lats = np.array([p[1] for p in points])

    # ── 平面近似でメートル座標へ変換 ──────────────────
    R = 6_371_000.0
    origin_lon = lons.mean()
    origin_lat = lats.mean()
    lat_rad = np.radians(origin_lat)

    x = (lons - origin_lon) * np.radians(1) * R * np.cos(lat_rad)
    y = (lats - origin_lat) * np.radians(1) * R
    z = elevations * z_scale   # z_scale で高さを誇張

    xyz = np.stack([x, y, z], axis=1).astype(np.float64)  # (N, 3)
    seg_arr = np.array(segments, dtype=np.int32)           # (M, 2)

    # ── 各線分の色を決定 ──────────────────────────────
    if color_by_height:
        # 線分の色 = 始点・終点の標高の平均で決める
        z_norm = (z - z.min()) / (z.max() - z.min() + 1e-9)
        t_seg = (z_norm[seg_arr[:, 0]] + z_norm[seg_arr[:, 1]]) / 2
        colors = _jet_colormap(t_seg)
    else:
        colors = np.ones((len(segments), 3), dtype=np.float64)   # 全線分を白に

    print(f"[build_3d] x範囲: {x.min():.1f} 〜 {x.max():.1f} m")
    print(f"[build_3d] y範囲: {y.min():.1f} 〜 {y.max():.1f} m")
    print(f"[build_3d] z範囲: {z.min():.1f} 〜 {z.max():.1f} m  (z_scale={z_scale})")
    return xyz, seg_arr, colors


def get_vertex_colors(xyz: np.ndarray, color_by_height: bool) -> np.ndarray:
    """
    PLY 保存用に頂点単位の色を返す。
    線分単位の colors とは別に必要になるため、独立した関数として切り出している。
    """
    if color_by_height:
        z = xyz[:, 2]
        t = (z - z.min()) / (z.max() - z.min() + 1e-9)
        return _jet_colormap(t)
    return np.ones((len(xyz), 3), dtype=np.float64)