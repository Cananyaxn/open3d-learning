"""
main.py — エントリポイント

各工程モジュールを順番に呼び出すだけのファイル。
処理の中身はそれぞれのモジュールに書いてある。

    ① load_road.py  : GeoJSON → 頂点・線分インデックス・幅クラス
    ② sample_dem.py : DEM → 標高配列
    ③ build_3d.py   : 座標変換・幅付きメッシュ構築
    ④ visualize.py  : 表示 & PLY 保存

使い方:
    python main.py -c config_3d.yaml
"""

import argparse
import sys

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

    road_path        = cfg["road"]
    dem_path         = cfg["dem"]
    output_ply       = cfg.get("output_ply",       "road_3d.ply")
    z_scale          = float(cfg.get("z_scale",          1.0))
    nodata_fill      = float(cfg.get("nodata_fill",      0.0))
    color_by_height  = bool(cfg.get("color_by_height",   True))
    width_property   = cfg.get("width_property",   "N13_006")
    # config で width_map を指定する場合はキーを int に変換する
    width_map_raw    = cfg.get("width_map", {})
    width_map        = {int(k): float(v) for k, v in width_map_raw.items()}

    print("\n[1/4] 道路データ読み込み")
    points, segments, width_classes = load_road.load(road_path, width_property)

    print("\n[2/4] DEM から標高サンプリング")
    dem_crs = cfg.get("dem_crs", None)
    elevations = sample_dem.sample(dem_path, points, nodata_fill, geojson_path=road_path, dem_crs_override=dem_crs)

    print("\n[3/4] 幅付き3Dメッシュ構築")
    mesh, xyz_center = build_3d.build(
        points, elevations, segments, width_classes,
        z_scale=z_scale,
        color_by_height=color_by_height,
        width_map=width_map or None,
    )

    print("\n[4/4] Open3D 表示 & PLY 保存")
    visualize.show(mesh, xyz_center, output_ply)

    print("\n完了!")


if __name__ == "__main__":
    main()