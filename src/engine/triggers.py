#!/usr/bin/env python3
"""
[LAYER: L5 ENGINE]
職責：S++ 硬觸發判定（含 FR 遲滯狀態機、T 強制單發、優化器觸發旗標）。純函數：入參(counter, data, sigma, dl_int) 出參(triggers, counter更新)。
"""
import math
from config.settings import (FR_THRESHOLDS, FR_HYSTERESIS, SPOT_SIGMA_TRIG,
                             OI_JUMP_TRIG, LS_THRESHOLDS)

def evaluate_hard_triggers(counter, data, sigma, dl_int, expiry):
    """回傳 (hard_triggers: list[str])；counter 就地更新遲滯/單發狀態。"""
    spot = data.get("spot", 0)
    fr   = data.get("fr", 0) * 100
    ls   = data.get("ls") or 0
    oi   = data.get("oi", 0)
    last_spot = counter.get("last_spot", spot)
    last_fr   = counter.get("last_fr", fr)
    last_ls   = counter.get("last_ls", ls)
    last_oi   = counter.get("last_oi", oi)
    hard = []

    # ① FR 穿越（遲滯：觸發解除武裝，遠離 >FR_HYSTERESIS 重新武裝）
    armed = counter.get("fr_armed", {str(t): True for t in FR_THRESHOLDS})
    for thr in FR_THRESHOLDS:
        key = str(thr)
        crossed = (last_fr < thr <= fr) or (last_fr > thr >= fr)
        if crossed and armed.get(key, True):
            hard.append(f"FR穿越{thr:+.3f}%（{last_fr:+.5f}→{fr:+.5f}）")
            armed[key] = False
        elif not armed.get(key, True) and abs(fr - thr) > FR_HYSTERESIS:
            armed[key] = True
    counter["fr_armed"] = armed

    # ② Spot 移動 > 0.5σ
    if sigma > 0 and abs(spot - last_spot) > SPOT_SIGMA_TRIG * sigma:
        hard.append(f"Spot移動{spot-last_spot:+,.0f}（>{SPOT_SIGMA_TRIG*sigma:,.0f}={SPOT_SIGMA_TRIG}σ）")

    # ③ L/S 整數穿越（數據源停用中，保留邏輯）
    if ls > 0 and last_ls > 0:
        for thr in LS_THRESHOLDS:
            if (last_ls < thr <= ls) or (last_ls > thr >= ls):
                hard.append(f"L/S穿越{thr}（{last_ls:.3f}→{ls:.3f}）")

    # ④ OI 跳動 > 300 張
    oi_jump = abs(oi - last_oi) * 10000
    if oi_jump > OI_JUMP_TRIG:
        hard.append(f"OI跳動{oi_jump:+,.0f}張（{last_oi:.2f}→{oi:.2f}萬）")

    # ⑤ T=1/0 強制（每 (expiry, dl) 單發）
    if dl_int in (1, 0):
        fired = counter.get("t_forced_fired", {})
        lst = fired.get(expiry, [])
        if dl_int not in lst:
            hard.append(f"T={dl_int}d強制觸發（結算前最後窗口）")
            lst.append(dl_int); fired[expiry] = lst
            counter["t_forced_fired"] = fired

    counter.update({"last_spot": spot, "last_fr": fr, "last_ls": ls, "last_oi": oi})
    return hard
