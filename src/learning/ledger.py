#!/usr/bin/env python3
"""
[LAYER: L5 LEARNING]
職責：結算帳本：預測記錄（T 窗口去重 + EMH 埋點 spot_at_record）、Deribit 結算價自動回填（ISO 日期解析）、誤差計算（USD/σ/beats_emh）。
"""
import json, os, re, requests
from datetime import datetime, date, timezone
from config.settings import (DEFAULT_WEIGHTS, DEFAULT_REGIME_WEIGHTS, MONTHS,
                             SETTLEMENT_LOG_PATH as LOG_PATH, TARGET_T, T_TOLERANCE)

def load_log():
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            log = json.load(f)
        # 向後相容：補充新欄位
        if "regime_weights" not in log:
            log["regime_weights"] = DEFAULT_REGIME_WEIGHTS.copy()
        if "signal_contributions" not in log:
            log["signal_contributions"] = {}
        if "convergence" not in log:
            log["convergence"] = {"converged": False, "frozen": False, "consecutive_no_improve": 0}
        if "optimization_history" not in log:
            log["optimization_history"] = []
        return log
    return {
        "records": [],
        "current_weights": DEFAULT_WEIGHTS.copy(),
        "regime_weights": DEFAULT_REGIME_WEIGHTS.copy(),
        "signal_contributions": {},   # {signal_name: {accuracy, avg_contribution}}
        "weight_history": [],
        "optimization_history": [],
        "last_optimized": None,
        "convergence": {
            "converged": False,
            "frozen": False,
            "consecutive_no_improve": 0,
            "avg_error_sigma_history": [],
        }
    }

def save_log(log):
    os.makedirs("data", exist_ok=True)
    with open(LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)

def record_prediction(snapshot_num, expiry, predicted_median, predicted_mode,
                       components, weights, signals, sigma, regime=None, t_days=None,
                       spot_at_record=None):
    """
    記錄預測。
    t_days：記錄時距結算的剩餘天數（固定T值快照核心字段）。
    固定T值設計：每個到期日只在 T=7/3/1/0d 各記一筆，
    跨週期誤差對比才有學習意義。
    去重邏輯：同一 expiry + 同一 T 窗口（±0.3d）只記一次。
    """
    log = load_log()

    # 去重：同一 snapshot_num + expiry 不重複記
    if any(r["snapshot_num"] == snapshot_num and r["expiry"] == expiry
           for r in log["records"]):
        print(f"[SKIP-DUP] S{snapshot_num} {expiry} 同快照同到期已存在")
        return

    # 固定T值去重：同一 expiry + 相近 t_days（±0.3d）不重複記（硬觸發除外）
    if t_days is not None:
        TARGET_T = [7, 3, 1, 0]
        for r in log["records"]:
            if (r.get("expiry") == expiry and
                r.get("t_days_at_record") is not None):
                # 同一 T 窗口內已有記錄
                if (any(abs(r["t_days_at_record"] - t) <= 0.3 for t in TARGET_T) and
                    any(abs(t_days - t) <= 0.3 for t in TARGET_T) and
                    any(abs(r["t_days_at_record"] - t) <= 0.3 and abs(t_days - t) <= 0.3
                        for t in TARGET_T)):
                    print(f"[SKIP-DUP] {expiry} T={t_days:.1f}d 此窗口已有 S{r['snapshot_num']} T={r['t_days_at_record']:.1f}d")
                    return

    record = {
        "snapshot_num":        snapshot_num,
        "expiry":              expiry,
        "timestamp":           datetime.now(timezone.utc).isoformat(),
        "t_days_at_record":    round(t_days, 2) if t_days is not None else None,
        "predicted_median":    round(predicted_median, 2),
        "predicted_mode":      round(predicted_mode, 2),
        "sigma":               round(sigma, 2),
        "regime_at_prediction":regime,
        "spot_at_record":      round(spot_at_record, 2) if spot_at_record else None,  # EMH基準
        "actual_settlement":   None,
        "components":  {k: round(float(v), 2) for k, v in components.items()},
        "weights_used":{k: round(float(v), 5) for k, v in weights.items()},
        "signals":     {k: (round(float(v), 5) if v is not None else None)
                        for k, v in signals.items()},
        "error_sigma": None,
        "error_usd":   None,
    }
    log["records"].append(record)
    save_log(log)
    print(f"Recorded S{snapshot_num} {expiry} T={t_days:.1f}d: ${predicted_median:,.0f} (regime={regime})")

def record_settlement(expiry, actual_price):
    """結算後填入實際價格並計算誤差"""
    log = load_log()
    updated = 0
    for record in log["records"]:
        if record["expiry"] == expiry and record["actual_settlement"] is None:
            record["actual_settlement"] = actual_price
            error_usd = abs(actual_price - record["predicted_median"])
            sigma = record.get("sigma", 4000)
            record["error_usd"] = round(error_usd, 2)
            record["error_sigma"] = round(error_usd / sigma if sigma > 0 else 0, 4)
            # EMH 基準：直接用記錄時 Spot 當預測的誤差（模型必須贏這個才有 alpha）
            spot_rec = record.get("spot_at_record")
            if spot_rec:
                emh_err = abs(actual_price - spot_rec)
                record["emh_error_usd"] = round(emh_err, 2)
                record["beats_emh"] = bool(error_usd < emh_err)
            updated += 1
            print(f"Settlement S{record['snapshot_num']} {expiry}: "
                  f"pred=${record['predicted_median']:,.0f}, actual=${actual_price:,.0f}, "
                  f"err=${error_usd:,.0f} ({record['error_sigma']:.2f}σ)")
    if updated:
        save_log(log)
    return updated

def check_and_record_settlement():
    """自動從 Deribit 拉取結算價"""
    today = date.today()
    log = load_log()
    pending = set(r["expiry"] for r in log["records"] if r["actual_settlement"] is None)
    if not pending:
        return

    for expiry_str in pending:
        try:
            m = re.match(r"(\d+)([A-Z]+)(\d+)", expiry_str.upper())
            if not m:
                continue
            expiry_date = date(2000 + int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
            if today < expiry_date:
                continue
            r_api = requests.get(
                "https://www.deribit.com/api/v2/public/get_delivery_prices"
                "?index_name=btc_usd&offset=0&count=10",
                timeout=10
            )
            deliveries = r_api.json().get("result", {}).get("data", [])
            for d in deliveries:
                # Deribit date 格式：字串 "YYYY-MM-DD"（非 timestamp）
                raw = d.get("date")
                if isinstance(raw, str):
                    d_date = date.fromisoformat(raw[:10])
                else:
                    d_date = date.fromtimestamp(float(raw) / 1000)
                if d_date == expiry_date:
                    n = record_settlement(expiry_str, float(d["delivery_price"]))
                    print(f"Auto-settlement {expiry_str}: ${float(d['delivery_price']):,.2f} ({n}筆)")
                    break
        except Exception as e:
            print(f"Settlement check {expiry_str}: {e}")
