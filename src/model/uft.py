#!/usr/bin/env python3
"""
[LAYER: L4 MODEL]
職責：UFT 統一場方程式組裝：五分量（GBM/GEX/Behavior/Bayesian/TimeDecay）×Regime 分層權重 → 中位/眾數/σ。去均值基線（skew/pcr 滾動歷史）在此消費。
"""
import os, json, math
from core.timeutil import parse_days_to_expiry
from signals.gex import calc_gex_structure
from signals.behavior import calc_behavior_signal

def calc_uft(data, prev_data=None):
    # UFT統一場方程計算
    spot = data["spot"]
    dvol = data["dvol"] / 100
    T = 7 / 365  # 暫時，後面動態覆蓋
    sigma = spot * dvol * math.sqrt(T)

    # GEX成分：用主到期日的實際期權鏈（動態 key，非硬碼）
    _exps_early = data.get("expiries", ["3JUL26","31JUL26","25SEP26"])
    _exp_main_early = _exps_early[0] if _exps_early else "3JUL26"
    opts_main = (data.get("options", {}) or {}).get(_exp_main_early) \
                or data.get(f"options_{_exp_main_early}", {})
    gex = calc_gex_structure(opts_main, spot)
    gex_center = gex["pin"]

    # BehaviorSignal成分(L/S已移除,用FR+PCR+Skew)
    expiries = data.get("expiries", ["3JUL26","31JUL26","25SEP26"])
    _exp0 = data.get("expiries", ["3JUL26","31JUL26","25SEP26"])[0]
    _dl = parse_days_to_expiry(_exp0)   # 單一真實來源
    T = _dl / 365                       # 動態T覆蓋
    sigma = spot * dvol * math.sqrt(T)  # 重算sigma
    fr = data.get("fr", 0)
    oi_change = (data.get("oi",0) - prev_data.get("oi",0)) if prev_data else 0
    skew_main = data.get("skew", {}).get(expiries[0] if expiries else "3JUL26", 0) or 0
    # ── Skew 去均值：BTC Skew 結構性長期為正（下行保護永遠有溢價），
    # 絕對值不是方向信號；有效信號 = 當前值相對自身滾動基線的偏離
    skew_baseline = None
    try:
        if os.path.exists("data/skew_history.json"):
            with open("data/skew_history.json") as _fsk:
                _sk_hist = json.load(_fsk)
            _exp0_sk = expiries[0] if expiries else None
            _vals = [e["skew"].get(_exp0_sk) for e in _sk_hist
                     if e.get("skew", {}).get(_exp0_sk) is not None]
            # 跨到期日 fallback：主到期切換後歷史不足時，用所有到期日的值
            if len(_vals) < 8:
                _vals = [v for e in _sk_hist for v in e.get("skew", {}).values() if v is not None]
            if len(_vals) >= 8:
                skew_baseline = sum(_vals) / len(_vals)
    except Exception:
        pass
    skew_demeaned = (skew_main - skew_baseline) if skew_baseline is not None else 0.0
    # FR信號方向
    fr_signal = 1 if fr > 0 else -1
    fr_strength = min(abs(fr) / 0.0001, 1.0)
    # Skew信號：用去均值Skew（相對滾動基線的偏離），非絕對值
    # 偏離>+2%=比常態更恐慌(偏空)；<-2%=比常態更貪婪(偏多)；基線缺失時信號=0
    skew_signal = -1 if skew_demeaned > 2 else (1 if skew_demeaned < -2 else 0)
    # T≤7d時Skew信號衰減（結算前Skew多為hedge非方向）
    _skew_decay=0.5 if _dl<=7 else 1.0
    skew_signal=skew_signal*_skew_decay
    # PCR ATM信號(更精確:用ATM PCR而非全局PCR)
    exp_main = expiries[0] if expiries else "3JUL26"
    pcr_atm = data.get(f"pcr_atm_{exp_main}", 0)
    pcr_otm = data.get(f"pcr_otm_{exp_main}", 0)
    # ATM PCR更能反映即時方向
    pcr_use = pcr_atm if pcr_atm > 0 else (pcr_ratio := sum(float(v.get("put_oi",0)) for v in data.get("options",{}).get(exp_main,{}).values()) / max(sum(float(v.get("call_oi",0)) for v in data.get("options",{}).get(exp_main,{}).values()), 1))
    # PCR 去均值：與 Skew 同理，絕對閾值(1.3/0.6)僅在無基線時使用
    pcr_baseline = None
    try:
        if os.path.exists("data/skew_history.json"):
            with open("data/skew_history.json") as _fp:
                _p_hist = json.load(_fp)
            _pvals = [e.get("pcr", {}).get(exp_main) for e in _p_hist
                      if e.get("pcr", {}).get(exp_main)]
            if len(_pvals) >= 8:
                pcr_baseline = sum(_pvals) / len(_pvals)
    except Exception:
        pass
    if pcr_baseline:
        _pcr_dev = pcr_use - pcr_baseline
        pcr_signal = -1 if _pcr_dev > 0.3 else (1 if _pcr_dev < -0.3 else 0)
    else:
        pcr_signal = -1 if pcr_use > 1.3 else (1 if pcr_use < 0.6 else 0)

    # OI變化方向(新增信號)
    oi_change = float(data.get("oi_change", 0) or 0)
    oi_signal = 0
    if abs(oi_change) > 0.1:  # 顯著變化
        oi_signal = -1 if oi_change > 0 else 1  # OI增加+FR正=空頭主導(已處理FR方向)

    # Perp Basis(新增信號)
    basis_pct = float(data.get("perp_basis_pct", 0) or 0)
    basis_signal = 1 if basis_pct > 0.05 else (-1 if basis_pct < -0.05 else 0)

    whale_signal = 0
    try:
        import os as _osw, sqlite3 as _sq
        _db = "data/whale_tracker.db"
        if _osw.path.exists(_db):
            _conn = _sq.connect(_db)
            _sql = ("SELECT SUM(CASE WHEN direction='in' THEN amount ELSE -amount END)"
                   " FROM transfers WHERE timestamp > datetime('now', '-24 hours') AND amount > 100")
            _row = _conn.execute(_sql).fetchone()
            _conn.close()
            if _row and _row[0]:
                _net = float(_row[0])
                whale_signal = -1 if _net > 500 else (1 if _net < -500 else 0)
    except: pass
    raw_signal = (fr_signal * fr_strength * 0.35 + skew_signal * 0.25
                + pcr_signal * 0.20 + oi_signal * 0.10
                + basis_signal * 0.05 + whale_signal * 0.05)
    behavior_signal = max(-1, min(1, raw_signal))
    contradiction = bool(fr > 0.005 and skew_demeaned > 5)  # FR多 vs Skew異常恐慌（去均值後）
    # behavior 懲罰因子（不縮減權重，縮減信號強度）
    behavior_penalty = 0.7 if contradiction else 1.0
    import math as _m2
    exp_main = expiries[0] if expiries else "3JUL26"
    T_main = _dl / 365
    sigma_main = spot * (data.get("dvol", 50) / 100) * _m2.sqrt(T_main)
    gf_dict = data.get("gamma_flip", {})
    # 精確查找 → 找不到時取最近到期日的 GF（避免 fallback 到 Spot）
    if exp_main in gf_dict and gf_dict[exp_main]:
        gamma_flip_main = int(gf_dict[exp_main])
    elif gf_dict:
        # 取第一個有效 GF（最近到期日）
        gamma_flip_main = int(next(v for v in gf_dict.values() if v))
    else:
        gamma_flip_main = int(gex_center) if gex_center != spot else int(spot * 0.95)
    regime = "POS" if spot > gamma_flip_main else "NEG"
    # Bayesian 動態收斂：T 越小越往 GEX Pin 收斂
    _t_factor = max(0.0, min(1.0, _dl / 30))
    _skew_factor = min(1.0, abs(skew_main) / 10) if skew_main != 0 else 0.3
    _regime_signal = 1 if regime == "POS" else -1
    _bayes_offset = _regime_signal * _skew_factor * _t_factor * 0.4
    bayes_center = spot + _bayes_offset * sigma_main
    # ── 權重取得：優先用 Regime 分層最優權重（L3）─────────────
    # 嘗試從 optimizer 取 regime-specific 最優權重
    try:
        import sys as _sys_uft
        _sys_uft.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from learning.optimizer import get_regime_weights as _grw
        bw = _grw(regime)  # POS/NEG 各自最優
    except Exception:
        bw = {"gbm": 0.30, "gex": 0.18, "behavior": 0.28, "bayesian": 0.12, "timedecay": 0.12}
    # 允許 data["uft_weights"] 覆蓋（human override）
    _override = data.get("uft_weights", {})
    if _override and abs(sum(_override.values()) - 1.0) < 0.02:
        bw = dict(_override)
    # 最終歸一（防止浮點誤差）
    _total = sum(bw.values())
    bw = {k: v / _total for k, v in bw.items()}
    # ── UFT 方程式（所有項結構統一：weight × center_estimate）────
    # behavior 信號縮減在 center_estimate 內（signal * penalty），不縮減 weight
    behavior_center = spot + behavior_signal * behavior_penalty * sigma_main
    uft = (bw["gbm"] * spot
           + bw["gex"] * gex_center
           + bw["behavior"] * behavior_center
           + bw["bayesian"] * bayes_center
           + bw["timedecay"] * gex_center)
    return {
        "uft_median": round(uft, 2), "uft_mode": gex_center, "uft_emh": spot,
        "sigma": round(sigma_main, 2), "regime": regime, "gamma_flip": gamma_flip_main,
        "behavior_contradiction": contradiction, "behavior_penalty": behavior_penalty,
        "skew_main": skew_main, "skew_demeaned": round(skew_demeaned, 2),
        "skew_baseline": round(skew_baseline, 2) if skew_baseline is not None else None,
        "uft_weights": bw,
        "components": {
            "gbm":       round(bw["gbm"] * spot, 2),
            "gex":       round(bw["gex"] * gex_center, 2),
            "behavior":  round(bw["behavior"] * behavior_center, 2),
            "bayesian":  round(bw["bayesian"] * bayes_center, 2),
            "timedecay": round(bw["timedecay"] * gex_center, 2),
        }
    }
