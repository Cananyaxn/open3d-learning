#!/usr/bin/env python3
"""
GeoJSON道路データ バウンディングボックス フィルタリングツール

使い方:
    python filter_geojson.py -i 道路データ.geojson --min-lon 137.6 --max-lon 137.8 --min-lat 34.6 --max-lat 34.8

オプション:
    --input   / -i       入力GeoJSONファイル（道路データ）
    --min-lon            経度の最小値（西端）
    --max-lon            経度の最大値（東端）
    --min-lat            緯度の最小値（南端）
    --max-lat            緯度の最大値（北端）
    --output  / -o       出力GeoJSONファイル（省略時: filtered_<入力ファイル名>）
    --mode    / -m       フィルタリングモード（省略時: intersects）
                           intersects : 範囲と少しでも重なるフィーチャーを抽出
                           contains   : 全頂点が範囲内に収まるフィーチャーのみ抽出
"""

import json
import argparse
import sys
import os


def flatten_coords(geometry):
    """GeoJSONジオメトリからすべての座標を [(lon, lat), ...] で返す"""
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
        # 全頂点がBBox内に収まるか
        return all(
            min_lon <= c[0] <= max_lon and min_lat <= c[1] <= max_lat
            for c in coords
        )
    else:  # intersects
        # 少なくとも1頂点がBBox内にあるか
        return any(
            min_lon <= c[0] <= max_lon and min_lat <= c[1] <= max_lat
            for c in coords
        )


def filter_geojson(input_path, output_path, min_lon, max_lon, min_lat, max_lat, mode):
    print(f"[読み込み] {input_path}")
    with open(input_path, encoding="utf-8") as f:
        road_data = json.load(f)

    print(f"[範囲] 経度 {min_lon} 〜 {max_lon}, 緯度 {min_lat} 〜 {max_lat}")

    features = road_data.get("features", [])
    total = len(features)
    print(f"[情報] 入力フィーチャー数: {total:,}")

    filtered = []
    for i, feature in enumerate(features):
        if i % 10000 == 0 and i > 0:
            print(f"  処理中... {i:,} / {total:,}")
        geom = feature.get("geometry")
        if geom and check_feature(geom, min_lon, max_lon, min_lat, max_lat, mode):
            filtered.append(feature)

    print(f"[結果] 抽出フィーチャー数: {len(filtered):,} / {total:,} ({len(filtered)/total*100:.1f}%)")

    output = {"type": "FeatureCollection", "features": filtered}
    for key in ("crs", "name", "bbox"):
        if key in road_data:
            output[key] = road_data[key]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"[完了] 出力: {output_path} ({size_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(
        description="GeoJSON道路データをバウンディングボックスでフィルタリングします"
    )
    parser.add_argument("-i", "--input",   required=True, help="入力GeoJSONファイル")
    parser.add_argument("--min-lon", type=float, required=True, help="経度の最小値（西端）")
    parser.add_argument("--max-lon", type=float, required=True, help="経度の最大値（東端）")
    parser.add_argument("--min-lat", type=float, required=True, help="緯度の最小値（南端）")
    parser.add_argument("--max-lat", type=float, required=True, help="緯度の最大値（北端）")
    parser.add_argument("-o", "--output",  default=None,  help="出力GeoJSONファイル（省略可）")
    parser.add_argument("-m", "--mode",    default="intersects",
                        choices=["intersects", "contains"],
                        help="フィルタリングモード（デフォルト: intersects）")
    args = parser.parse_args()

    if args.min_lon >= args.max_lon:
        print("エラー: min-lon は max-lon より小さい値にしてください")
        sys.exit(1)
    if args.min_lat >= args.max_lat:
        print("エラー: min-lat は max-lat より小さい値にしてください")
        sys.exit(1)

    if args.output is None:
        base = os.path.splitext(os.path.basename(args.input))[0]
        args.output = f"filtered_{base}.geojson"

    filter_geojson(args.input, args.output,
                   args.min_lon, args.max_lon, args.min_lat, args.max_lat,
                   args.mode)


if __name__ == "__main__":
    main()