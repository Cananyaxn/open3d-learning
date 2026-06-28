"""
load_road.py — 工程①: GeoJSON 読み込み

GeoJSON の LineString / MultiLineString フィーチャーを走査し、
「全頂点リスト」と「線分インデックスのペアリスト」を返す。

なぜ頂点と線分を別々に持つのか
─────────────────────────────────
Open3D の LineSet は
  ・points  : 頂点座標の配列  (N, 3)
  ・lines   : 線分を表す頂点インデックスのペア配列  (M, 2)
という構造を持つ。そのため、この段階から同じ形式で持っておくと
後工程での変換が不要になる。

返り値
─────────────────────────────────
points   : list[tuple[float, float]]   (lon, lat) の順
segments : list[tuple[int, int]]       (始点インデックス, 終点インデックス)
"""

import json


def load(geojson_path: str):
    with open(geojson_path, encoding="utf-8") as f:
        data = json.load(f)

    points: list[tuple[float, float]] = []
    segments: list[tuple[int, int]] = []

    def add_linestring(coords):
        """1本のラインを頂点リストと線分リストに追加する"""
        base = len(points)           # 追加前の末尾インデックスを記憶
        points.extend(coords)        # 頂点を末尾に追加
        for i in range(len(coords) - 1):
            segments.append((base + i, base + i + 1))   # 隣り合う頂点をペアにする

    for feature in data.get("features", []):
        geom = feature.get("geometry") or {}
        gtype = geom.get("type", "")

        if gtype == "LineString":
            add_linestring(geom["coordinates"])

        elif gtype == "MultiLineString":
            # MultiLineString は複数のラインを持つため、それぞれ処理する
            for line in geom["coordinates"]:
                add_linestring(line)

    print(f"[load_road] 頂点数: {len(points):,}  線分数: {len(segments):,}")
    return points, segments