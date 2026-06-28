"""
load_road.py — 工程①: GeoJSON 読み込み

GeoJSON の LineString / MultiLineString フィーチャーを走査し、
「全頂点リスト」「線分インデックスのペアリスト」「線分ごとの幅リスト」を返す。

なぜ頂点と線分を別々に持つのか
─────────────────────────────────
Open3D の LineSet / TriangleMesh は
  ・points  : 頂点座標の配列  (N, 3)
  ・lines   : 線分を表す頂点インデックスのペア配列  (M, 2)
という構造を持つ。そのため、この段階から同じ形式で持っておくと
後工程での変換が不要になる。

幅員クラス (N13_006) の扱い
─────────────────────────────────
国土数値情報の道路データでは N13_006 属性が幅員区分を表す整数で格納されている。
この段階では整数値をそのまま保持し、実メートル値への変換は build_3d.py で行う。
こうすることで、代表幅の変更が build_3d.py だけで済む。

返り値
─────────────────────────────────
points        : list[tuple[float, float]]   (lon, lat) の順
segments      : list[tuple[int, int]]       (始点インデックス, 終点インデックス)
width_classes : list[int]                   線分ごとの N13_006 値（不明は 6）
"""

import json


def load(geojson_path: str, width_property: str = "N13_006"):
    with open(geojson_path, encoding="utf-8") as f:
        data = json.load(f)

    points: list[tuple[float, float]] = []
    segments: list[tuple[int, int]] = []
    width_classes: list[int] = []

    def add_linestring(coords, wclass: int):
        """1本のラインを頂点リスト・線分リスト・幅クラスリストに追加する"""
        base = len(points)
        points.extend(coords)
        for i in range(len(coords) - 1):
            segments.append((base + i, base + i + 1))
            # 線分ごとに同じ幅クラスを紐づける
            width_classes.append(wclass)

    for feature in data.get("features", []):
        geom = feature.get("geometry") or {}
        gtype = geom.get("type", "")
        # N13_006 が存在しない場合は 6（不明）として扱う
        wclass = int(feature.get("properties", {}).get(width_property, 6) or 6)

        if gtype == "LineString":
            add_linestring(geom["coordinates"], wclass)

        elif gtype == "MultiLineString":
            for line in geom["coordinates"]:
                add_linestring(line, wclass)

    print(f"[load_road] 頂点数: {len(points):,}  線分数: {len(segments):,}")
    return points, segments, width_classes