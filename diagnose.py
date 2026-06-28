"""
diagnose.py — CRS・範囲のミスマッチ診断

sample_dem で標高が全部 0 になる原因を特定するために、
DEM と道路データそれぞれの座標系・範囲を表示して比較する。

使い方:
    python diagnose.py -c config_3d.yaml
"""

import json
import argparse
import sys

try:
    import yaml
except ImportError:
    print("エラー: pip install pyyaml"); sys.exit(1)

try:
    import rasterio
    from rasterio.warp import transform_bounds
except ImportError:
    print("エラー: pip install rasterio"); sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True)
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    road_path = cfg["road"]
    dem_path  = cfg["dem"]

    # ── DEM の情報 ────────────────────────────────
    print("=" * 55)
    print("【DEM】")
    dem_crs_override = cfg.get("dem_crs", None)

    with rasterio.open(dem_path) as src:
        dem_crs    = src.crs
        dem_bounds = src.bounds
        dem_nodata = src.nodata
        dem_res    = src.res

    if dem_crs is None:
        if dem_crs_override:
            dem_crs = dem_crs_override
            print(f"  CRS          : {dem_crs}（DEMにCRS情報なし → config の dem_crs を使用）")
        else:
            # CRSが不明なので座標変換できない。ネイティブ座標のまま表示する
            print( "  CRS          : 不明（config に dem_crs を指定してください）")
            print(f"  解像度       : {dem_res}")
            print(f"  nodata       : {dem_nodata}")
            print(f"  範囲(ネイティブ): left={dem_bounds.left:.4f} right={dem_bounds.right:.4f}")
            print(f"                   bottom={dem_bounds.bottom:.4f} top={dem_bounds.top:.4f}")
            print()
            print("⚠️  DEM の CRS が不明なため範囲比較ができません。")
            print("   config_3d.yaml に以下を追加してから再実行してください:")
            print("     dem_crs: EPSG:4326   # または EPSG:6668 など")
            return
        bounds_wgs84 = transform_bounds(dem_crs, "EPSG:4326", *dem_bounds)
    else:
        bounds_wgs84 = transform_bounds(dem_crs, "EPSG:4326", *dem_bounds)

    print(f"  CRS          : {dem_crs}")
    print(f"  解像度       : {dem_res}")
    print(f"  nodata       : {dem_nodata}")
    print(f"  範囲(ネイティブ): left={dem_bounds.left:.4f} right={dem_bounds.right:.4f}")
    print(f"                   bottom={dem_bounds.bottom:.4f} top={dem_bounds.top:.4f}")
    print(f"  範囲(WGS84)  : lon {bounds_wgs84[0]:.4f} 〜 {bounds_wgs84[2]:.4f}")
    print(f"                  lat {bounds_wgs84[1]:.4f} 〜 {bounds_wgs84[3]:.4f}")

    # ── 道路データの情報 ──────────────────────────
    print()
    print("【道路 GeoJSON】")
    with open(road_path, encoding="utf-8") as f:
        data = json.load(f)

    lons, lats = [], []
    for feature in data.get("features", []):
        geom = feature.get("geometry") or {}
        coords = []
        if geom.get("type") == "LineString":
            coords = geom["coordinates"]
        elif geom.get("type") == "MultiLineString":
            coords = [c for line in geom["coordinates"] for c in line]
        for c in coords:
            lons.append(c[0])
            lats.append(c[1])

    if not lons:
        print("  座標が1点も見つかりません。GeoJSONを確認してください。")
        return

    print(f"  座標系       : GeoJSON は通常 WGS84 (EPSG:4326)")
    print(f"  lon 範囲     : {min(lons):.4f} 〜 {max(lons):.4f}")
    print(f"  lat 範囲     : {min(lats):.4f} 〜 {max(lats):.4f}")

    # ── ミスマッチ判定 ────────────────────────────
    print()
    print("【判定】")
    road_in_dem = (
        bounds_wgs84[0] <= min(lons) and max(lons) <= bounds_wgs84[2] and
        bounds_wgs84[1] <= min(lats) and max(lats) <= bounds_wgs84[3]
    )
    if road_in_dem:
        print("  ✓ 道路データはDEMの範囲内に収まっています。")
        print("    → CRSの不一致が原因の可能性があります。")
        print(f"    → DEMのCRS ({dem_crs}) がWGS84でない場合、")
        print( "       sample_dem.py で座標変換が必要です。")
    else:
        print("  ✗ 道路データがDEMの範囲外です。")
        print("    → フィルタリング範囲とDEMファイルの範囲が合っているか確認してください。")

    if dem_nodata is not None:
        print(f"\n  nodata値 ({dem_nodata}) が標高0と混同されていないか確認してください。")
        print( "  config の nodata_fill を変更することで置換値を調整できます。")


if __name__ == "__main__":
    main()