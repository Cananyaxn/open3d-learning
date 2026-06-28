"""
sample_dem.py — 工程②: DEM から標高をサンプリング

GeoTIFF 形式の DEM（数値標高モデル）を rasterio で開き、
工程①で得た各頂点の座標に対応する標高値を読み取る。

CRS（座標参照系）の変換について
─────────────────────────────────
GeoJSON の座標系と DEM の座標系が異なる場合、
座標をそのまま DEM に渡してもピクセル範囲外を指してしまい
nodata（= 0）が返り続ける。

GeoJSON は crs 属性で座標系を宣言している。
  例: { "type": "name", "properties": { "name": "urn:ogc:def:crs:EPSG::6668" }}
  例: { "type": "name", "properties": { "name": "EPSG:4326" }}
  省略時は WGS84 (EPSG:4326) が GeoJSON の仕様上のデフォルト。

この関数では:
  1. GeoJSON の crs から EPSG コードを取り出す
  2. DEM の CRS と異なれば rasterio.warp.transform で座標を変換
  3. 変換後の座標で DEM をサンプリングする

nodata の扱い
─────────────────────────────────
DEM には「測定できなかった領域」を示す特殊値 (nodata) がある。
そのまま使うと標高として巨大な外れ値になるため、
config で指定した nodata_fill 値（デフォルト 0.0）に置き換える。

返り値
─────────────────────────────────
elevations : np.ndarray  shape=(N,)  dtype=float64  単位: メートル
"""

import json
import re
import numpy as np
import rasterio
from rasterio.warp import transform as warp_transform
from pyproj import CRS


def _epsg_from_geojson_crs(geojson_path: str) -> str | None:
    """
    GeoJSON の crs 属性から EPSG コード文字列を取り出す。
    見つからなければ None を返す（呼び出し元が WGS84 をデフォルトにする）。

    対応フォーマット例:
      "urn:ogc:def:crs:EPSG::6668"  → "EPSG:6668"
      "urn:ogc:def:crs:OGC:1.3:CRS84" → None（WGS84 相当なので変換不要）
      "EPSG:4326"                    → "EPSG:4326"
    """
    with open(geojson_path, encoding="utf-8") as f:
        # crs は先頭付近にあるので全体を読まず先頭 4KB だけ見る
        head = f.read(4096)

    # JSON として crs ブロックだけ取り出す
    try:
        data = json.loads(head + ']}')   # 切り捨て部分を閉じて雑にパース
    except Exception:
        try:
            with open(geojson_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None

    crs_obj = data.get("crs")
    if not crs_obj:
        return None

    name = (crs_obj.get("properties") or {}).get("name", "")

    # "urn:ogc:def:crs:EPSG::XXXX" 形式
    m = re.search(r"EPSG::?(\d+)", name, re.IGNORECASE)
    if m:
        return f"EPSG:{m.group(1)}"

    # すでに "EPSG:XXXX" 形式
    if re.match(r"EPSG:\d+", name, re.IGNORECASE):
        return name.upper()

    return None


def sample(
    dem_path: str,
    points: list[tuple[float, float]],
    nodata_fill: float = 0.0,
    geojson_path: str | None = None,
    dem_crs_override: str | None = None,   # DEMにCRSが埋め込まれていない場合に指定（例: "EPSG:4326"）
):
    # ── GeoJSON の CRS を取得 ────────────────────────
    road_crs_str = None
    if geojson_path:
        road_crs_str = _epsg_from_geojson_crs(geojson_path)

    if road_crs_str:
        print(f"[sample_dem] 道路CRS  : {road_crs_str}")
    else:
        road_crs_str = "EPSG:4326"
        print(f"[sample_dem] 道路CRS  : {road_crs_str}（crs属性なし → WGS84と仮定）")

    with rasterio.open(dem_path) as src:
        dem_crs = src.crs

        # DEMにCRSが埋め込まれていない場合はconfigで指定した値を使う
        # それもなければWGS84を仮定する
        if dem_crs is None:
            dem_crs_str = dem_crs_override or "EPSG:4326"
            dem_crs = CRS.from_string(dem_crs_str)
            print(f"[sample_dem] DEM CRS  : {dem_crs_str}（DEMにCRS情報なし → 設定値を使用）")
        else:
            print(f"[sample_dem] DEM CRS  : {dem_crs}")

        print(f"[sample_dem] 解像度   : {src.res[0]:.6f} × {src.res[1]:.6f}")
        print(f"[sample_dem] nodata   : {src.nodata}")

        # ── 座標変換が必要か判定 ──────────────────────
        road_crs = CRS.from_string(road_crs_str)
        need_transform = not road_crs.equals(dem_crs)

        if need_transform:
            print(f"[sample_dem] CRS変換  : {road_crs_str} → {dem_crs}")
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            xs_t, ys_t = warp_transform(road_crs_str, dem_crs, xs, ys)
            xy = list(zip(xs_t, ys_t))
        else:
            print("[sample_dem] CRS変換  : 不要（同一CRS）")
            xy = [(p[0], p[1]) for p in points]

        # ── DEMの範囲（BBox）を取得 ──────────────────
        # DEMがカバーしていない頂点には NaN を入れる。
        # rasterio.sample() はBBox外の座標にもnodata値を返すため、
        # 事前にBBoxチェックして明示的にNaNを立てる。
        left, bottom, right, top = src.bounds

        # ── DEMをサンプリング ─────────────────────────
        elevations = []
        for (x, y), val in zip(xy, src.sample(xy, indexes=1)):
            # DEMのBBox外 → NaN（後工程でこの線分をスキップ）
            if not (left <= x <= right and bottom <= y <= top):
                elevations.append(float("nan"))
                continue
            elev = float(val[0])
            # nodataもNaNにする（BBox内だがデータなし）
            if src.nodata is not None and elev == src.nodata:
                elevations.append(float("nan"))
                continue
            elevations.append(elev)

    result = np.array(elevations, dtype=np.float64)
    # DEMのCRS（メートル系）に変換済みのXY座標を配列として返す
    # build_3d.py はこれをそのまま使うため、経度緯度への再変換が不要になる
    xy_transformed = np.array(xy, dtype=np.float64)  # shape (N, 2)

    valid = int(np.isfinite(result).sum())
    total_pts = len(result)
    print(f"[sample_dem] 標高範囲 : {np.nanmin(result):.1f} m 〜 {np.nanmax(result):.1f} m")
    print(f"[sample_dem] 有効点数 : {valid:,} / {total_pts:,}  "
          f"（DEMカバー率 {valid/total_pts*100:.1f}%）")
    if valid == 0:
        print("[sample_dem] ⚠️  有効な標高が0点です。diagnose.py で範囲・CRSを確認してください。")
    return result, xy_transformed