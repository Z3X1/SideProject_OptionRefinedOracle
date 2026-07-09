#!/usr/bin/env python3
"""
[LAYER: L0 CONFIG]
職責：全系統常數單一真實來源。任何魔術數字禁止散落他處。
上游依賴僅允許指向更低層（config → core → data → signals → model → engine/learning → present → pipeline）。
"""

# ── 檔案路徑 ──────────────────────────────────────────────────
DATA_DIR            = "data"
MARKET_DATA_PATH    = "data/oracle_market_data.json"
SETTLEMENT_LOG_PATH = "data/settlement_log.json"
COUNTER_PATH        = "data/snapshot_counter.json"
PREV_DATA_PATH      = "data/oracle_prev_data.json"
SKEW_HISTORY_PATH   = "data/skew_history.json"
OUTPUT_DIR_DEFAULT  = "docs/oracle"

# ── UFT 權重（v2.0 基準，sum=1.00）───────────────────────────
DEFAULT_WEIGHTS = {"gbm": 0.30, "gex": 0.18, "behavior": 0.28,
                   "bayesian": 0.12, "timedecay": 0.12}
DEFAULT_REGIME_WEIGHTS = {
    "POS": {"gbm": 0.28, "gex": 0.20, "behavior": 0.28, "bayesian": 0.12, "timedecay": 0.12},
    "NEG": {"gbm": 0.25, "gex": 0.15, "behavior": 0.32, "bayesian": 0.16, "timedecay": 0.12},
}
UFT_KEYS = ["gbm", "gex", "behavior", "bayesian", "timedecay"]

# ── 固定 T 值快照 ─────────────────────────────────────────────
TARGET_T    = [7, 3, 1, 0]   # 每週期四個學習窗口
T_TOLERANCE = 0.3            # ±0.3 天 = ±7.2h

# ── S++ 硬觸發 ────────────────────────────────────────────────
FR_THRESHOLDS   = [-0.01, -0.005, 0.0, 0.005, 0.01]  # 百分比
FR_HYSTERESIS   = 0.002      # 重新武裝距離
SPOT_SIGMA_TRIG = 0.5        # |ΔSpot| > 0.5σ
OI_JUMP_TRIG    = 300        # 張
LS_THRESHOLDS   = [1.5, 2.0, 2.5, 3.0]

# ── 守門排程 ──────────────────────────────────────────────────
SLOTS_UTC = [2, 8, 14, 20]   # 台灣 10/16/22/04

# ── 優化器 ────────────────────────────────────────────────────
OPT_MIN_SAMPLES   = 10
OPT_MIN_CYCLES    = 3        # 統計效力以「不同結算週期」計
DECAY_HALF_LIFE   = 10
BAYES_PRIOR_STR   = 3.0
CONV_ABS_SIGMA    = 0.3      # 絕對收斂
CONV_UNFREEZE     = 0.8      # 解凍
FUSION            = {"l1": 0.50, "l4": 0.30, "current": 0.20}

# ── 去均值基線 ────────────────────────────────────────────────
BASELINE_MIN_N    = 8
SKEW_DEV_TRIG     = 3.0      # 去均值偏離 ±3 才算方向信號
PCR_DEV_TRIG      = 0.3

# ── 到期日月份表 ──────────────────────────────────────────────
MONTHS = {"JAN":1,"FEB":2,"MAR":3,"APR":4,"MAY":5,"JUN":6,
          "JUL":7,"AUG":8,"SEP":9,"OCT":10,"NOV":11,"DEC":12}
