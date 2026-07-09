# SideProject_OptionRefinedOracle

BTC 期權結算價預測系統——藉由 Option 結算迭代不斷優化 Oracle。

## 極致分層架構
```
L0 config/    settings.py      全系統常數單一真實來源
L1 core/      timeutil.py      到期日解析（整數σ用 / 精確小數T窗口用）
L2 data/      acquisition.py   Deribit+Binance 獲取、多源fallback、滾動歷史
L3 signals/   gex.py           距離加權 GEX Pin / PCR / 牆
              behavior.py      行為信號合成
L4 model/     uft.py           UFT 五分量方程式 × Regime 分層權重
L5 engine/    triggers.py      S++ 硬觸發（FR遲滯/0.5σ/OI/T單發）
              collision.py     rule-based 對抗裁決
L5 learning/  ledger.py        結算帳本（T窗口去重、EMH埋點、自動回填）
              optimizer.py     五層迭代（梯度×週期聚類/信號準確率/Regime/貝葉斯/收斂）
L6 present/   dashboard.py     3-Tab HTML 全量重建
              protect.py       base64+Blob 密碼保護
              publisher.py     GitHub API 發佈
L7 pipeline.py                 唯一編排入口，層間錯誤隔離
   run_guard.py                每小時守門（擊敗 GitHub cron 延遲）
```
依賴方向嚴格單向：低層永不 import 高層。

Dashboard: https://z3x1.github.io/SideProject_OptionRefinedOracle/oracle/
