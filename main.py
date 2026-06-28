"""
main.py — エントリポイント

各工程モジュールを順番に呼び出すだけのファイル。
処理の中身はそれぞれのモジュールに書いてある。

    ① load_road.py  : GeoJSON → 頂点・線分インデックス
    ② sample_dem.py : DEM → 標高配列
    ③ build_3d.py   : 座標変換・色付け → Open3D 用配列
    ④ visualize.py  : 表示 & PLY 保存

使い方:
    python main.py -c config_3d.yaml
"""

import argparse
import sys
import os

try:
    import yaml
except ImportError:
    print("エラー: pip install pyyaml")
    sys.exit(1)

from src import load_road, sample_dem, build_3d, visualize

def main():
    parser = argparse.ArgumentParser(description="道路 GeoJSON + DEM → Open3D 3D 表示")
    parser.add_argument("-c", "--config", required=True, help="設定 YAML ファイル")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    road_path       = cfg["road"]
    dem_path        = cfg["dem"]
    output_ply      = cfg.get("output_ply",      "road_3d.ply")
    z_scale         = float(cfg.get("z_scale",         1.0))
    nodata_fill     = float(cfg.get("nodata_fill",     0.0))
    color_by_height = bool(cfg.get("color_by_height",  True))

    print("\n[1/4] 道路データ読み込み")
    points, segments = load_road.load(road_path)

    print("\n[2/4] DEM から標高サンプリング")
    elevations = sample_dem.sample(dem_path, points, nodata_fill)

    print("\n[3/4] 3D データ構築")
    xyz, seg_arr, colors = build_3d.build(
        points, elevations, segments,
        z_scale=z_scale,
        color_by_height=color_by_height,
    )

    print("\n[4/4] Open3D 表示 & PLY 保存")
    visualize.show(xyz, seg_arr, colors, output_ply, color_by_height)

    print("\n完了!")


if __name__ == "__main__":
    main()