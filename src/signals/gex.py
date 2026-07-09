#!/usr/bin/env python3
"""
[LAYER: L3 SIGNALS]
職責：GEX 結構：距離加權 Pin（排除牆效應）、PCR、總 OI。純函數，入參期權鏈出參結構。
"""
def calc_gex_structure(options, spot):
    # 計算GEX Structure:Pin水位,PCR,Gamma Flip
    # 注意：JSON 載入後 strike key 一定是字串，必須轉 float
    if not options:
        return {"pin": spot, "pcr": 1.0, "gamma_flip": spot - 2000}

    opts = {}
    for k, v in options.items():
        try:
            opts[float(k)] = v
        except (ValueError, TypeError):
            continue
    if not opts:
        return {"pin": spot, "pcr": 1.0, "gamma_flip": spot - 2000}

    # PCR(OI加權)
    total_call_oi = sum(float(v.get("call_oi", 0)) for v in opts.values())
    total_put_oi = sum(float(v.get("put_oi", 0)) for v in opts.values())
    pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0

    # GEX Pin：ATM ±8% 內「距離加權總 OI」最大的行使價
    # Gamma 集中度 ∝ OI × ATM鄰近度（ATM Gamma 最大，遠離線性衰減）
    # 純總 OI 會被 Call/Put Wall（牆在邊緣）拉偏，加權後排除
    _band = spot * 0.08
    atm_range = {k: v for k, v in opts.items() if abs(k - spot) < _band}
    if atm_range:
        def _pin_score(k):
            oi_tot = float(atm_range[k].get("call_oi", 0)) + float(atm_range[k].get("put_oi", 0))
            proximity = 1.0 - abs(k - spot) / _band   # ATM=1.0 → 邊緣=0
            return oi_tot * proximity
        pin = max(atm_range, key=_pin_score)
    else:
        pin = round(spot / 1000) * 1000  # 最近千位

    return {
        "pin": int(pin),
        "pcr": pcr,
        "total_call_oi": total_call_oi,
        "total_put_oi": total_put_oi,
    }
