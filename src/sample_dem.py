"""
sample_dem.py — 工程②: DEM から標高をサンプリング

GeoTIFF 形式の DEM（数値標高モデル）を rasterio で開き、
工程①で得た各頂点の (lon, lat) に対応する標高値を読み取る。

サンプリングとは
─────────────────────────────────
DEM はラスター（格子状のピクセル）データ。
各ピクセルが「そのセルの標高値（メートル）」を持っている。
頂点の座標がピクセル境界をまたぐ場合、rasterio はピクセル中心に
最近傍で丸めて値を返す（デフォルト動作）。

nodata の扱い
─────────────────────────────────
DEM には「測定できなかった領域」を示す特殊値 (nodata) がある。
そのまま使うと標高として巨大な外れ値になるため、
config で指定した nodata_fill 値（デフォルト 0.0）に置き換える。

返り値
─────────────────────────────────
elevations : np.ndarray  shape=(N,)  dtype=float64  単位: メートル
"""

import numpy as np
import rasterio


def sample(dem_path: str, points: list[tuple[float, float]], nodata_fill: float = 0.0):
    with rasterio.open(dem_path) as src:
        print(f"[sample_dem] CRS      : {src.crs}")
        print(f"[sample_dem] 解像度   : {src.res[0]:.6f} × {src.res[1]:.6f} m")
        print(f"[sample_dem] nodata   : {src.nodata}")

        # rasterio.DatasetReader.sample() は (lon, lat) のイテラブルを受け取り、
        # 各座標に対応するバンド値を yield する
        xy = [(p[0], p[1]) for p in points]
        elevations = []
        for val in src.sample(xy, indexes=1):
            elev = float(val[0])
            if src.nodata is not None and elev == src.nodata:
                elev = nodata_fill   # nodata を指定値で置換
            elevations.append(elev)

    result = np.array(elevations, dtype=np.float64)
    print(f"[sample_dem] 標高範囲 : {result.min():.1f} m 〜 {result.max():.1f} m")
    return result