#!/usr/bin/env python3
"""
[LAYER: L1 CORE]
職責：時間原語：到期日解析（整數/精確小數雙軌）。零業務邏輯。
上游依賴僅允許指向更低層（config → core → data → signals → model → engine/learning → present → pipeline）。
"""
import re as _re_exp
from config.settings import MONTHS as _MONTHS_EXP

def parse_days_to_expiry(expiry_str):
    """'3JUL26' → 剩餘天數(int)，最小1天"""
    from datetime import date as _date_exp
    try:
        m = _re_exp.match(r"(\d+)([A-Z]+)(\d+)", expiry_str.upper())
        if m:
            d = _date_exp(2000 + int(m.group(3)), _MONTHS_EXP[m.group(2)], int(m.group(1)))
            return max(1, (d - _date_exp.today()).days)
    except Exception:
        pass
    return 7

def exact_days_to_expiry(expiry_str):
    """距結算時刻（到期日 08:00 UTC）的精確剩餘天數（float，可為 0.x）。
    與 parse_days_to_expiry 的差異：後者 max(1,) 保護 σ 計算，
    此函數供固定 T 值快照記錄使用，讓 T=0 窗口（結算日晨間）可達。"""
    from datetime import datetime as _dt_e, timezone as _tz_e
    try:
        m = _re_exp.match(r"(\d+)([A-Z]+)(\d+)", expiry_str.upper())
        if m:
            settle = _dt_e(2000 + int(m.group(3)), _MONTHS_EXP[m.group(2)],
                           int(m.group(1)), 8, 0, tzinfo=_tz_e.utc)
            return max(0.0, (settle - _dt_e.now(_tz_e.utc)).total_seconds() / 86400.0)
    except Exception:
        pass
    return 7.0
