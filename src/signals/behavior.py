#!/usr/bin/env python3
"""
[LAYER: L3 SIGNALS]
職責：行為信號合成（FR/OI/L-S legacy 組件）。去均值 Skew/PCR 的消費在 model 層 calc_uft 內，基線讀取見該處註記。
"""
def calc_behavior_signal(fr, ls, oi_change, prev_ls=None):
    # 行為信號計算
    # Rule#15: FR正+L/S同升=全權重;矛盾=×0.5
    fr_direction = 1 if fr > 0 else -1
    ls_direction = 1 if (prev_ls is None or ls > prev_ls) else -1

    # 矛盾檢測
    contradiction = (fr_direction != ls_direction)
    weight = 0.7 if contradiction else 1.0

    # 信號強度
    fr_signal = min(abs(fr) / 0.0001, 1.0) * fr_direction  # 正規化
    ls_signal = (ls - 2.0) / 0.5  # 2.0為中性基準

    raw_signal = (fr_signal * 0.4 + ls_signal * 0.6) * weight
    return raw_signal, contradiction, weight
