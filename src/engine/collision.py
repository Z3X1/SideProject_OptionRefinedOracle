#!/usr/bin/env python3
"""
[LAYER: L5 ENGINE]
職責：對抗性碰撞裁決：rule-based 主引擎（Claude API 為可選增強，缺 key 自動 fallback）。輸出 verdict/insight/next_trigger。
"""
import os, json, requests
from core.timeutil import parse_days_to_expiry

def generate_rule_based_collision(data, uft_result):
    """當Claude API不可用時，用規則引擎自動生成結論"""
    spot=float(data.get("spot",0))
    fr=float(data.get("fr",0))*100
    dvol=float(data.get("dvol",0))
    regime=uft_result.get("regime","POS")
    uft_med=float(uft_result.get("uft_median",spot))
    sigma=float(uft_result.get("sigma",0))
    contra=uft_result.get("behavior_contradiction",False)
    skew_main=float(uft_result.get("skew_main",0) or 0)
    gf=int(uft_result.get("gamma_flip",spot) or spot)
    expiries=data.get("expiries",["3JUL26"])
    exp0=expiries[0] if expiries else "3JUL26"
    dl = parse_days_to_expiry(exp0)
    opts=data.get("options",{}).get(exp0,{})
    tc=sum(float(v.get("call_oi",0)) for v in opts.values())
    tp=sum(float(v.get("put_oi",0)) for v in opts.values())
    pcr=round(tp/tc,2) if tc>0 else 1.0
    macd_1d=data.get("macd_1d") or data.get("macd",{}).get("1d",{})
    dif_1d=float(macd_1d.get("dif",0))
    macd_4h=data.get("macd_4h") or data.get("macd",{}).get("4h",{})
    dif_4h=float(macd_4h.get("dif",0))
    # 決定Oracle Verdict
    bull_pts=0; bear_pts=0
    if regime=="POS": bull_pts+=2
    else: bear_pts+=2
    if fr>0.005: bull_pts+=1
    elif fr<-0.005: bear_pts+=1
    _skd=float(uft_result.get("skew_demeaned",0) or 0)
    if _skd>3: bear_pts+=2   # 去均值：比自身常態更恐慌才算空方信號
    elif skew_main>5 and uft_result.get("skew_baseline") is None: bear_pts+=2  # 無基線fallback
    elif skew_main<-2: bull_pts+=1
    if dif_1d<-500: bear_pts+=2
    elif dif_1d>500: bull_pts+=1
    if dif_4h>0: bull_pts+=1
    else: bear_pts+=1
    if pcr>1.3: bear_pts+=1
    elif pcr<0.6: bull_pts+=1
    if contra: bear_pts+=1
    total=bull_pts+bear_pts
    bull_pct=round(bull_pts/total,2) if total>0 else 0.5
    if bull_pct>=0.6: verdict=f"BULL {bull_pct:.2f}"
    elif bull_pct<=0.4: verdict=f"BEAR {1-bull_pct:.2f}"
    else: verdict=f"NEUTRAL {bull_pct:.2f}"
    # Key Insight
    insights=[]
    _pin_v=float(uft_result.get("uft_mode",0) or 0)
    if dl<=7: insights.append(f"T-{dl}d結算Pin博弈：GEX Pin ${_pin_v:,.0f} vs Spot ${spot:,.0f}（差${abs(spot-_pin_v):,.0f}）｜UFT中位 ${uft_med:,.0f}")
    if skew_main>15: insights.append(f"Skew {skew_main:+.1f}% 極度偏空，市場為下行付高溢價")
    elif skew_main>5: insights.append(f"Skew {skew_main:+.1f}% 偏空，空方防禦需求主導")
    if regime=="POS" and abs(spot-gf)<sigma*0.3: insights.append(f"Spot距GF僅{abs(spot-gf):,.0f}，Regime轉換風險高")
    elif regime=="POS": insights.append(f"POS Regime穩定，GF ${gf:,} 距Spot {abs(spot-gf):,.0f}（{abs(spot-gf)/gf*100:.1f}%）")
    else: insights.append(f"NEG Regime：造市商放大波動，GF ${gf:,} 為關鍵收復目標")
    if contra: insights.append("FR多/Skew空矛盾（Rule#15觸發），行為信號權重×0.5")
    if dif_1d<-1000: insights.append(f"1D MACD DIF={dif_1d:.0f} 深度負值，中期趨勢偏空")
    key_insight=" | ".join(insights[:3]) if insights else f"UFT Median ${uft_med:,.0f}，σ=${sigma:,.0f}，情境B（核心區間）概率最高"
    # Next Trigger
    triggers=[]
    if dl<=3: triggers.append(f"T-{dl}d結算前最後窗口：監控Pin是否移位")
    if regime=="POS" and spot-gf<sigma*0.5: triggers.append(f"Spot跌破GF ${gf:,} → NEG Regime硬觸發")
    if fr>0: triggers.append("FR穿越0%（多→空成本轉換）")
    else: triggers.append("FR穿越-0.01%（空頭信念加深）或反彈穿越0%")
    if skew_main>10: triggers.append("Skew收縮至+10%以下（空方壓力緩解信號）")
    next_trigger=" | ".join(triggers[:2]) if triggers else "監控FR/Skew/Spot vs Pin"
    return {"oracle_verdict":verdict,"key_insight":key_insight,"next_trigger":next_trigger}

def call_claude_collision(data, uft_result):
    api_key=os.environ.get("ANTHROPIC_API_KEY","")
    # 先嘗試Claude API
    if api_key:
        try:
            import urllib.request as _ur
            spot=float(data.get("spot",0)); fr=float(data.get("fr",0))*100
            dvol=float(data.get("dvol",0)); uft_med=float(uft_result.get("uft_median",0))
            sigma=float(uft_result.get("sigma",0)); regime=uft_result.get("regime","POS")
            exp=data.get("expiries",["3JUL26"])[0]
            sk=data.get("skew",{}).get(exp,0) or 0
            prompt=(
                f"Spot: ${spot:,.0f} | FR: {fr:+.5f}% | DVOL: {dvol:.2f}%\n"
                f"Regime: {regime} | Skew {exp}: {sk:+.1f}%\n"
                f"UFT Median: ${uft_med:,.0f} | Sigma: ${sigma:,.0f}\n"
                "Run 4-layer adversarial collision. Output JSON only: "
                "{""oracle_verdict"":""BULL/BEAR 0.XX"",""key_insight"":""one sentence"",""next_trigger"":""next signal""}"
            )
            body=json.dumps({"model":"claude-haiku-4-5-20251001","max_tokens":300,
                "messages":[{"role":"user","content":prompt}]}).encode()
            req=_ur.Request("https://api.anthropic.com/v1/messages",data=body,
                headers={"x-api-key":api_key,"anthropic-version":"2023-06-01","content-type":"application/json"},method="POST")
            with _ur.urlopen(req,timeout=30) as resp: result=json.loads(resp.read())
            if "error" not in result:
                text="".join(b.get("text","") for b in result.get("content",[]) if b.get("type")=="text").strip()
                if "{" in text: text=text[text.find("{"):text.rfind("}")+1]
                parsed=json.loads(text)
                print("Claude collision OK"); return parsed
        except Exception as e: print(f"Claude API fallback to rules: {e}")
    # Fallback：規則引擎
    print("Using rule-based collision engine")
    return generate_rule_based_collision(data, uft_result)
