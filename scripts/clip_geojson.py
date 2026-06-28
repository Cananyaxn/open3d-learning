#!/usr/bin/env python3
"""
GeoJSON道路データ バウンディングボックス フィルタリングツール

使い方:
    python filter_geojson.py -c config.yaml          # YAMLで複数範囲を一括処理
    python filter_geojson.py -c config.yaml -n 浜松市中心部  # 特定の範囲のみ実行

YAMLの書き方は config.yaml を参照してください。
"""

import json
import argparse
import sys
import os

try:
    import yaml
except ImportError:
    print("エラー: PyYAML が必要です。pip install pyyaml でインストールしてください。")
    sys.exit(1)


# ────────────────────────────────────────────────
# ジオメトリユーティリティ
# ────────────────────────────────────────────────

def flatten_coords(geometry):
    gtype = geometry["type"]
    coords = geometry["coordinates"]
    if gtype == "Point":
        return [coords]
    elif gtype in ("MultiPoint", "LineString"):
        return coords
    elif gtype in ("MultiLineString", "Polygon"):
        return [c for ring in coords for c in ring]
    elif gtype == "MultiPolygon":
        return [c for poly in coords for ring in poly for c in ring]
    elif gtype == "GeometryCollection":
        return [c for g in geometry["geometries"] for c in flatten_coords(g)]
    return []


def check_feature(geometry, min_lon, max_lon, min_lat, max_lat, mode):
    coords = flatten_coords(geometry)
    if not coords:
        return False
    if mode == "contains":
        return all(min_lon <= c[0] <= max_lon and min_lat <= c[1] <= max_lat for c in coords)
    else:  # intersects
        return any(min_lon <= c[0] <= max_lon and min_lat <= c[1] <= max_lat for c in coords)


# ────────────────────────────────────────────────
# フィルタリング本体
# ────────────────────────────────────────────────

def filter_geojson(road_data, region):
    name    = region.get("name", "（名前なし）")
    output  = region["output"]
    min_lon = float(region["min_lon"])
    max_lon = float(region["max_lon"])
    min_lat = float(region["min_lat"])
    max_lat = float(region["max_lat"])
    mode    = region.get("mode", "intersects")

    if min_lon >= max_lon or min_lat >= max_lat:
        print(f"  [スキップ] {name}: 緯度・経度の範囲が不正です")
        return

    print(f"\n{'─'*50}")
    print(f"  範囲名 : {name}")
    print(f"  経度   : {min_lon} 〜 {max_lon}")
    print(f"  緯度   : {min_lat} 〜 {max_lat}")
    print(f"  モード : {mode}")

    features = road_data.get("features", [])
    total = len(features)
    filtered = []

    for i, feature in enumerate(features):
        if i % 50000 == 0 and i > 0:
            print(f"    処理中... {i:,} / {total:,}")
        geom = feature.get("geometry")
        if geom and check_feature(geom, min_lon, max_lon, min_lat, max_lat, mode):
            filtered.append(feature)

    # 元データのメタ属性を引き継ぐ（crs / name / xy_coordinate_resolution など）
    # "type" と "features" 以外のトップレベルキーをすべてコピーする
    result = {}
    for key, val in road_data.items():
        if key != "features":
            result[key] = val
    result["features"] = filtered

    # 出力フォーマット:
    #   トップレベルは改行あり、feature は1行にまとめてファイルを見やすくする
    with open(output, "w", encoding="utf-8") as f:
        f.write('{\"type\": \"FeatureCollection\"'  )
        for key, val in result.items():
            if key in ("type", "features"):
                continue
            f.write(",\n" + json.dumps({key: val}, ensure_ascii=False)[1:-1])
        f.write(",\n\"features\": [\n")
        for i, feature in enumerate(filtered):
            comma = "," if i < len(filtered) - 1 else ""
            f.write("  " + json.dumps(feature, ensure_ascii=False, separators=(", ", ": ")) + comma + "\n")
        f.write("]}\n")

    size_kb = os.path.getsize(output) / 1024
    pct = len(filtered) / total * 100 if total else 0
    print(f"  抽出数 : {len(filtered):,} / {total:,} ({pct:.1f}%)")
    print(f"  出力   : {output} ({size_kb:.1f} KB)")


# ────────────────────────────────────────────────
# エントリポイント
# ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GeoJSON道路データをYAML設定でフィルタリングします")
    parser.add_argument("-c", "--config", required=True, help="設定YAMLファイル")
    parser.add_argument("-n", "--name",   default=None,  help="実行する範囲名（省略時は全範囲）")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    input_path = config.get("input")
    if not input_path:
        print("エラー: config.yaml に input が指定されていません")
        sys.exit(1)
    if not os.path.exists(input_path):
        print(f"エラー: 入力ファイルが見つかりません: {input_path}")
        sys.exit(1)

    regions = config.get("regions", [])
    if not regions:
        print("エラー: config.yaml に regions が1件もありません")
        sys.exit(1)

    # 特定の範囲名が指定された場合は絞り込む
    if args.name:
        regions = [r for r in regions if r.get("name") == args.name]
        if not regions:
            print(f"エラー: 範囲名 '{args.name}' が config.yaml に見つかりません")
            sys.exit(1)

    print(f"[読み込み] {input_path}")
    with open(input_path, encoding="utf-8") as f:
        road_data = json.load(f)
    print(f"[情報] 入力フィーチャー数: {len(road_data.get('features', [])):,}")
    print(f"[情報] 処理する範囲数: {len(regions)}")

    for region in regions:
        filter_geojson(road_data, region)

    print(f"\n{'─'*50}")
    print("すべての処理が完了しました。")


if __name__ == "__main__":
    main()