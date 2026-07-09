#!/usr/bin/env python3
"""
[LAYER: L7 PIPELINE]
職責：唯一編排入口。層序：讀數據 → 觸發判定(engine) → UFT(model)
     → 碰撞(engine) → 帳本(learning) → 優化(learning) → HTML(present)。
     任何層內錯誤被隔離，結算回填永不被連坐。
"""
import os, sys, json, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (MARKET_DATA_PATH, COUNTER_PATH, PREV_DATA_PATH,
                             OUTPUT_DIR_DEFAULT, TARGET_T, T_TOLERANCE,
                             OPT_MIN_SAMPLES, OPT_MIN_CYCLES)
from core.timeutil import parse_days_to_expiry, exact_days_to_expiry
from engine.triggers import evaluate_hard_triggers
from model.uft import calc_uft
from engine.collision import generate_rule_based_collision, call_claude_collision
from present.dashboard import generate_html


def main():
    output_dir = os.environ.get("OUTPUT_DIR", OUTPUT_DIR_DEFAULT)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("data", exist_ok=True)

    # 1. 市場數據（L2 產物）
    if not os.path.exists(MARKET_DATA_PATH):
        print(f"ERROR: {MARKET_DATA_PATH} not found"); sys.exit(1)
    with open(MARKET_DATA_PATH) as f:
        data = json.load(f)
    print(f"Spot: ${data.get('spot',0):,.2f}  FR: {data.get('fr',0)*100:+.5f}%")

    # 2. Counter + 硬觸發（L5 engine）
    counter = {}
    if os.path.exists(COUNTER_PATH):
        with open(COUNTER_PATH) as f:
            counter = json.load(f)
    prev_num = max(counter.get("last_snapshot", 0), counter.get("count", 0))

    exp0 = (data.get("expiries") or ["7D"])[0]
    dl_int = parse_days_to_expiry(exp0)
    sigma_trig = data.get("spot",0) * (data.get("dvol",50)/100) * math.sqrt(dl_int/365)
    hard_triggers = evaluate_hard_triggers(counter, data, sigma_trig, dl_int, exp0)
    is_hard = bool(hard_triggers)

    snapshot_num = prev_num + 1 if is_hard else prev_num
    if is_hard:
        print(f"[HARD TRIGGER] {' | '.join(hard_triggers)}")
    else:
        print(f"[NO TRIGGER] snapshot 維持 S{snapshot_num}")
    counter.update({"last_snapshot": snapshot_num, "count": snapshot_num,
                    "hard_triggers": hard_triggers,
                    "last_trigger_ts": data.get("timestamp","")})
    with open(COUNTER_PATH, "w") as f:
        json.dump(counter, f, indent=2)
    print(f"Snapshot: S{snapshot_num}")

    # 3. prev data（行為信號比對用）
    prev_data = None
    if os.path.exists(PREV_DATA_PATH):
        with open(PREV_DATA_PATH) as f:
            prev_data = json.load(f)
    with open(PREV_DATA_PATH, "w") as f:
        json.dump(data, f)

    # 4. UFT（L4 model）
    uft_result = calc_uft(data, prev_data)
    print(f"UFT Median: ${uft_result['uft_median']:,.0f}  Regime: {uft_result['regime']}")

    # 5. 碰撞裁決（L5 engine；Claude API 可選）
    collision = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            collision = call_claude_collision(data, uft_result)
        except Exception as e:
            print(f"claude collision fallback: {e}")
    if not collision:
        collision = generate_rule_based_collision(data, uft_result)

    # 6. 帳本記錄（L5 learning）——固定 T 窗口或硬觸發
    try:
        from learning.ledger import record_prediction
        dl = exact_days_to_expiry(exp0)
        should = any(abs(dl - t) <= T_TOLERANCE for t in TARGET_T) or is_hard
        if should:
            record_prediction(
                snapshot_num=snapshot_num, expiry=exp0,
                predicted_median=uft_result["uft_median"],
                predicted_mode=uft_result["uft_mode"],
                components=uft_result.get("components", {}),
                weights=uft_result.get("uft_weights", {}),
                signals={
                    "fr":            data.get("fr"),
                    "skew":          uft_result.get("skew_demeaned"),
                    "skew_raw":      uft_result.get("skew_main"),
                    "dvol":          data.get("dvol"),
                    "pcr_main":      data.get(f"pcr_atm_{exp0}"),
                    "macd_4h":       (data.get("macd_4h") or {}).get("dif"),
                    "regime_pos":    1.0 if uft_result.get("regime")=="POS" else 0.0,
                    "gamma_flip":    float(uft_result.get("gamma_flip") or 0),
                    "contradiction": 1.0 if uft_result.get("behavior_contradiction") else 0.0,
                },
                sigma=uft_result.get("sigma", 4000),
                regime=uft_result.get("regime", "POS"),
                t_days=dl,
                spot_at_record=data.get("spot"),
            )
        else:
            print(f"[NO RECORD] T={dl:.2f}d 不在窗口且無硬觸發")
    except Exception as e:
        print(f"record error: {e}")

    # 7. 結算回填 + 優化（獨立 try，永不被連坐）
    try:
        from learning.ledger import check_and_record_settlement
        from learning.optimizer import optimize_weights
        check_and_record_settlement()
        optimize_weights(min_samples=OPT_MIN_SAMPLES, min_cycles=OPT_MIN_CYCLES)
    except Exception as e:
        print(f"settlement/optimize error: {e}")

    # 8. HTML（L6 present）
    html = generate_html(data, uft_result, collision, snapshot_num)
    out = os.path.join(output_dir, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML written: {out} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
