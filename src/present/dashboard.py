#!/usr/bin/env python3
"""
[LAYER: L6 PRESENT]
職責：Dashboard HTML 全量重建（不打補丁）：3-Tab（主分析/47詞彙表/學習狀態）、JS 動態時效、EMH 勝負標記、T 欄小數顯示。
"""
import os, json, math
from datetime import datetime, timezone, date
from core.timeutil import parse_days_to_expiry

def generate_html(data, uft_result, collision, snapshot_num):
    import math, os as _os2
    from datetime import datetime, timezone, date

    spot=float(data.get('spot') or 0); fr=float(data.get('fr') or 0)*100
    oi=float(data.get('oi') or 0); dvol=float(data.get('dvol') or 0)
    ts=str(data.get('timestamp',''))[:16].replace('T',' ')
    expiries=data.get('expiries',['3JUL26','31JUL26','25SEP26'])
    exp0=expiries[0] if expiries else 'N/A'
    exp1=expiries[1] if len(expiries)>1 else 'N/A'
    exp2=expiries[2] if len(expiries)>2 else 'N/A'
    uft_med=float(uft_result.get('uft_median') or spot)
    uft_mode=float(uft_result.get('uft_mode') or spot)
    sigma=float(uft_result.get('sigma') or 0)
    contra=bool(uft_result.get('behavior_contradiction',False))
    comps=uft_result.get('components',{})
    regime=uft_result.get('regime','POS')
    gf_main=int(uft_result.get('gamma_flip',uft_mode) or uft_mode)
    weights=uft_result.get('uft_weights',{'gbm':0.30,'gex':0.18,'behavior':0.28,'bayesian':0.12,'timedecay':0.12})
    def ms(kf,kn):
        m=data.get(kf) or data.get('macd',{}).get(kn,{})
        dif=float(m.get('dif',0)); dea=float(m.get('dea',0)); mac=float(m.get('macd',0))
        b=dif>dea
        return ('BULL X' if b else 'BEAR X'),('#10b981' if b else '#ef4444'),dif,dea,mac
    s15,c15,d15,e15,m15=ms('macd_15m','15m')
    s4h,c4h,d4h,e4h,m4h=ms('macd_4h','4h')
    s1d,c1d,d1d,e1d,m1d=ms('macd_1d','1d')
    frc='#10b981' if fr>=0 else '#ef4444'; frs='+' if fr>=0 else ''
    rc='#10b981' if regime=='POS' else '#ef4444'
    r15t='Rule#15 CLEARED' if not contra else 'Rule#15 TRIGGERED - x0.5'
    r15c='#10b981' if not contra else '#f59e0b'
    ot=collision.get('oracle_verdict','N/A') if collision else 'N/A'
    it=collision.get('key_insight','Claude API not configured') if collision else 'Claude API not configured'
    nt=collision.get('next_trigger','') if collision else ''
    opts=data.get('options',{}); sk=data.get('skew',{}); gfmap=data.get('gamma_flip',{})
    def os2(exp):
        o=opts.get(exp,{})
        if not o: return 0,0,0,0,0
        tc=sum(float(v.get('call_oi',0)) for v in o.values())
        tp=sum(float(v.get('put_oi',0)) for v in o.values())
        mc=max(o.items(),key=lambda x:x[1].get('call_oi',0),default=(0,{}))
        mp=max(o.items(),key=lambda x:x[1].get('put_oi',0),default=(0,{}))
        return tc,tp,round(tp/tc,3) if tc>0 else 0,int(mc[0]),int(mp[0])
    tc0,tp0,pcr0,cw0,pw0=os2(exp0)
    tc1,tp1,pcr1,cw1,pw1=os2(exp1)
    tc2,tp2,pcr2,cw2,pw2=os2(exp2)
    sk0=sk.get(exp0); sk1=sk.get(exp1); sk2=sk.get(exp2)
    s0s=f'{sk0:+.1f}%' if sk0 is not None else 'N/A'
    s1s=f'{sk1:+.1f}%' if sk1 is not None else 'N/A'
    s2s=f'{sk2:+.1f}%' if sk2 is not None else 'N/A'
    s0c='#ef4444' if (sk0 or 0)>2 else ('#10b981' if (sk0 or 0)<-2 else 'var(--mut)')
    s1c='#ef4444' if (sk1 or 0)>2 else ('#10b981' if (sk1 or 0)<-2 else 'var(--mut)')
    s2c='#ef4444' if (sk2 or 0)>2 else ('#10b981' if (sk2 or 0)<-2 else 'var(--mut)')
    gf0=gfmap.get(exp0,gf_main); gf1=gfmap.get(exp1,0); gf2=gfmap.get(exp2,0)
    if sigma>0:
        def nc(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
        pA=round((1-nc((uft_med+sigma*.5-spot)/sigma))*100,1)
        pB=round((nc((uft_med+sigma*.5-spot)/sigma)-nc((uft_med-sigma*.5-spot)/sigma))*100,1)
        pC=round((nc((uft_med-sigma*.5-spot)/sigma)-nc((uft_med-sigma-spot)/sigma))*100,1)
        pD=round(nc((uft_med-sigma-spot)/sigma)*100,1)
    else: pA,pB,pC,pD=20,50,20,10
    dl = parse_days_to_expiry(exp0)
    cd = f'T-{dl}d' if dl > 0 else 'TODAY'
    try:
        now=datetime.now(timezone.utc)
        nxt=min((h for h in [0,8,16] if h>now.hour),default=24)
        # 剩餘時間 = 下一結算點 − 現在（原版 bug：直接顯示當前分鐘數，11:59 顯示 5h59m 實為 4h01m）
        _rem_min=(nxt*60)-(now.hour*60+now.minute)
        fns=f'{_rem_min//60}h{_rem_min%60:02d}m'
        _elapsed_h=8-(_rem_min/60)          # 本 8h 週期已經過時數
        facc=round(fr*_elapsed_h,6)
    except: facc=0; fns='N/A'
    st=''; stc='var(--mut)'; st3=''
    try:
        if _os2.path.exists('data/skew_history.json'):
            import json as j3
            with open('data/skew_history.json') as f3: shd=j3.load(f3)
            if len(shd)>=2:
                sp2=shd[-2].get('skew',{}).get(exp0); sc2=shd[-1].get('skew',{}).get(exp0)
                if sp2 and sc2:
                    dd=sc2-sp2
                    st=(f'^{abs(dd):.1f}%' if dd>0 else f'v{abs(dd):.1f}%') if abs(dd)>0.5 else 'stable'
                    stc='#ef4444' if dd>0 else '#10b981'
            if len(shd)>=3:
                sv=[h.get('skew',{}).get(exp0) for h in shd[-3:] if h.get('skew',{}).get(exp0)]
                st3=f'{sv[0]:.1f}->{sv[1]:.1f}->{sv[2]:.1f}%' if len(sv)==3 else ''
    except: pass
    gfd=abs(spot-gf_main); gfs=gfd/sigma if sigma>0 else 0
    gfss='STABLE' if gfs>0.3 else 'UNSTABLE'; gfsc='#10b981' if gfs>0.3 else '#f59e0b'
    pd2=abs(spot-uft_mode); mpv=int(data.get(f'max_pain_{exp0}',uft_mode) or uft_mode)
    psc=max(0,100-pd2/10-abs(spot-mpv)/20)
    pr='HIGH' if psc>70 else ('MEDIUM' if psc>40 else 'LOW')
    prc='#ef4444' if psc>70 else ('#f59e0b' if psc>40 else '#10b981')
    cla=False; cli=[]; dcl=dl
    if 0<dl<=7:
        cla=True
        cli=[
            ('FR stable','OK' if abs(fr)>0.002 else '?','#10b981' if abs(fr)>0.002 else '#f59e0b'),
            ('Put Wall holding','OK' if spot>pw0 else 'X','#10b981' if spot>pw0 else '#ef4444'),
            ('Spot above GF','OK' if regime=="POS" else 'X','#10b981' if regime=="POS" else '#ef4444'),
            ('GEX Pin stable','OK' if pd2<500 else '?','#10b981' if pd2<500 else '#f59e0b'),
            ('Skew not expanding','OK' if '^' not in st else '!','#10b981' if '^' not in st else '#ef4444'),
            (f'GF POS (${gf_main:,})','OK' if regime=="POS" else 'X','#10b981' if regime=="POS" else '#ef4444'),
        ]
    try:
        ts2=data.get('timestamp','')
        if ts2: age=int((datetime.now(timezone.utc)-datetime.fromisoformat(ts2.replace('Z','+00:00'))).total_seconds()/60)
        else: age=0
        ags=f'{age}m ago' if age<60 else f'{age//60}h{age%60:02d}m ago'
        agc='var(--green)' if age<30 else ('var(--yel)' if age<120 else 'var(--red)')
    except: ags='unknown'; agc='var(--mut)'
    ru=[]
    if contra: ru.append('R#15 Contradictory signal')
    if regime=='NEG': ru.append('R#10 NEG Regime - MM Amplifier')
    if regime=='POS': ru.append(f'R#10 POS Regime (GF ${gf_main:,})')
    if fr>0.005: ru.append('R#5 FR bullish (>0.005%)')
    elif fr<-0.005: ru.append('R#5 FR bearish (<-0.005%)')
    _skd0=float(uft_result.get('skew_demeaned',0) or 0); _skb0=uft_result.get('skew_baseline')
    if _skb0 is not None:
        if _skd0>3: ru.append(f'R#Skew 恐慌偏離 {_skd0:+.1f}% (raw {sk0:+.1f}% vs 基線 {_skb0:+.1f}%)')
        elif _skd0<-3: ru.append(f'R#Skew 緩和偏離 {_skd0:+.1f}% (raw {sk0:+.1f}% vs 基線 {_skb0:+.1f}%)')
    elif (sk0 or 0)>5: ru.append(f'R#Skew Strong bearish +{sk0:.1f}% (無基線)')
    dif1=float((data.get('macd_1d') or data.get('macd',{}).get('1d',{})).get('dif',0))
    if dif1<-1000: ru.append(f'R#2 1D DIF deeply negative ({dif1:.0f})')
    aiv=float(data.get(f'atm_iv_{exp0}',dvol) or dvol); ivp=aiv-dvol
    if abs(ivp)>8: ru.append(f'R#IV ATM-DVOL divergence: {ivp:+.1f}%')
    patm=float(data.get(f'pcr_atm_{exp0}',0) or 0); potm=float(data.get(f'pcr_otm_{exp0}',0) or 0)
    if patm>1.0 and potm<0.5: ru.append(f'R#PCR ATM({patm:.2f}) vs OTM({potm:.2f}) mixed')
    if abs(mpv-uft_mode)>1000: ru.append(f'R#MaxPain-GEXPin ${abs(mpv-uft_mode):,.0f}')
    ruh=''.join(f'<div class="row"><span>{x}</span></div>' for x in ru) if ru else '<div style="font-size:9px;color:var(--mut)">None</div>'
    sr=''
    o0=opts.get(exp0,{})
    if o0:
        t8=sorted(o0.items(),key=lambda x:x[1].get('call_oi',0)+x[1].get('put_oi',0),reverse=True)[:8]
        for stk,v in sorted(t8,key=lambda x:x[0]):
            co=float(v.get('call_oi',0)); po=float(v.get('put_oi',0))
            ci=float(v.get('call_iv',0)); pi=float(v.get('put_iv',0))
            ps=round(po/co,2) if co>0 else 0
            ivs=f'{ci:.0f}/{pi:.0f}' if ci>0 or pi>0 else '-'
            ivc='#ef4444' if max(ci,pi)>60 else ('var(--yel)' if max(ci,pi)>45 else 'var(--mut)')
            at=' style="background:rgba(59,130,246,.08)"' if abs(int(stk)-spot)<1500 else ''
            gm=' *GF*' if abs(int(stk)-gf_main)<500 else ''
            mm=' *MP*' if abs(int(stk)-mpv)<500 else ''
            sr+=f'<tr{at}><td>${int(stk):,}{gm}{mm}</td><td>{co:.0f}</td><td>{po:.0f}</td><td>{ps}</td><td style="color:{ivc}">{ivs}</td></tr>'
    slh=''
    try:
        if _os2.path.exists('data/settlement_log.json'):
            import json as j4
            with open('data/settlement_log.json') as f4: lg=j4.load(f4)
            rs=lg.get('records',[])[-8:]; rws=''
            for rec in reversed(rs):
                sn=rec.get('snapshot_num','?'); ex=rec.get('expiry','')
                prv=rec.get('predicted_median',0); ac=rec.get('actual_settlement'); es=rec.get('error_sigma')
                if ac:
                    es2=f'${abs(ac-prv):,.0f} ({es:.2f}s)' if es else f'${abs(ac-prv):,.0f}'
                    be=rec.get('beats_emh')
                    if be is True: es2+=' ✓'
                    elif be is False: es2+=' ✗'
                    ec='#10b981' if (es or 99)<0.5 else ('#f59e0b' if (es or 99)<1.0 else '#ef4444')
                    as2=f'${ac:,.0f}'
                else: es2='pending'; ec='var(--mut)'; as2='-'
                td_v=rec.get('t_days_at_record')
                if td_v is None: td_s='-'
                elif abs(td_v-round(td_v))<0.05: td_s=f'T-{round(td_v)}d'
                else: td_s=f'T-{td_v:.1f}d'
                rws+=f'<tr><td>S{sn}</td><td>{ex}</td><td style="color:var(--mut);font-size:9px">{td_s}</td><td>${prv:,.0f}</td><td>{as2}</td><td style="color:{ec}">{es2}</td></tr>'
            nd=len([x for x in lg.get('records',[]) if x.get('actual_settlement')])
            _emh_rs=[x for x in lg.get('records',[]) if x.get('beats_emh') is not None]
            _emh_w=len([x for x in _emh_rs if x['beats_emh']])
            _emh_s=f' | vs EMH: {_emh_w}/{len(_emh_rs)}勝' if _emh_rs else ''
            _ncyc=len(set(x.get('expiry') for x in lg.get('records',[]) if x.get('actual_settlement') and not x.get('corrupted_gex')))
            slh=(f'<div style="padding:0 10px 10px"><div class="card"><div class="ct">SETTLEMENT LOG - UFT ACCURACY TRACKER</div>'
                 f'<table><thead><tr><th>S#</th><th>Expiry</th><th>T</th><th>Predicted</th><th>Actual</th><th>Error</th></tr></thead>'
                 f'<tbody>{rws}</tbody></table>'
                 f'<div style="font-size:9px;color:var(--mut);margin-top:4px">Optimizer: {nd} samples / {_ncyc}週期 (需≥3週期){_emh_s} | ✓=贏EMH ✗=輸EMH</div></div></div>')
    except: pass
    clh=''
    if cla:
        cr=''.join(f'<div class="row"><span>{i}</span><span style="color:{c}">{s}</span></div>' for i,s,c in cli)
        clh=(f'<div style="padding:0 10px 10px"><div class="card" style="border-color:#f59e0b">'
             f'<div class="ct" style="color:#f59e0b">T-{dcl}d PRE-SETTLEMENT CHECKLIST ({exp0})</div>{cr}</div></div>')
    bw=float(weights.get('behavior',0.28))*(0.5 if contra else 1.0)
    sw0=f'{min(abs(sk0 or 0)*4,100):.0f}%'; sw1=f'{min(abs(sk1 or 0)*4,100):.0f}%'; sw2=f'{min(abs(sk2 or 0)*4,100):.0f}%'
    css='<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><meta name="google" content="notranslate">'
    css+=f'<title>GEX Oracle S{snapshot_num}</title>'
    css+=('<style>:root{--bg:#0a0e17;--panel:#111827;--border:#1e293b;--acc:#3b82f6;--green:#10b981;--red:#ef4444;'
          '--yel:#f59e0b;--pur:#8b5cf6;--cyan:#06b6d4;--txt:#e2e8f0;--mut:#64748b}'
          '*{box-sizing:border-box;margin:0;padding:0}body{background:var(--bg);color:var(--txt);font-family:Consolas,monospace;font-size:12px}'
          '.hdr{background:linear-gradient(135deg,#0f172a,#1e1b4b);border-bottom:2px solid var(--acc);padding:12px 16px;display:flex;justify-content:space-between;align-items:flex-start}'
          '.ht{font-size:16px;color:var(--acc);letter-spacing:2px;font-weight:bold}.hs{color:var(--mut);font-size:10px;margin-top:2px}'
          '.spot{font-size:24px;font-weight:bold;color:var(--yel)}'
          '.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:10px}'
          '.g2{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:0 10px 10px}'
          '.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;padding:0 10px 10px}'
          '.card{background:var(--panel);border:1px solid var(--border);border-radius:6px;padding:10px}'
          '.ct{font-size:9px;color:var(--mut);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;padding-bottom:4px;border-bottom:1px solid var(--border)}'
          '.kv{font-size:18px;font-weight:bold;text-align:center;padding:6px 0}.kl{font-size:9px;color:var(--mut);text-align:center;letter-spacing:1px}'
          '.al{border-radius:5px;padding:7px 10px;margin:0 10px 8px;font-size:11px}'
          '.row{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border);font-size:10px}.row:last-child{border-bottom:none}'
          '.big{font-size:20px;font-weight:bold;color:var(--yel);text-align:center;padding:6px 0}.sm{color:var(--mut);font-size:9px;text-align:center}'
          '.pb{height:8px;background:var(--border);border-radius:4px;overflow:hidden;margin:2px 0 4px}.pf{height:100%;border-radius:4px}'
          'table{width:100%;border-collapse:collapse;font-size:10px}'
          'th{color:var(--mut);text-align:right;padding:3px 5px;font-size:9px;border-bottom:1px solid var(--border)}th:first-child{text-align:center}'
          'td{padding:3px 5px;text-align:right;border-bottom:1px solid rgba(30,41,59,.5)}td:first-child{text-align:center;font-weight:bold;color:var(--cyan)}'
          '.foot{text-align:center;padding:8px;color:var(--mut);font-size:9px}</style></head><body>')
    # Tab導航欄放在 body 最開頭
    _tab_js2=('function showTab(n){["main","glossary","learning"].forEach(function(t){var e=document.getElementById(t);var b=document.getElementById("tab-"+t);if(e)e.style.display=(t===n?"block":"none");if(b){b.style.background=(t===n?"var(--acc)":"var(--panel)");b.style.color=(t===n?"#fff":"var(--mut)");}});}')
    _ta2='background:var(--acc);color:#fff;border:none'
    _ti2='background:var(--panel);color:var(--mut);border:1px solid var(--border);border-bottom:none'
    _tb2='padding:6px 12px;border-radius:4px 4px 0 0;font-size:10px;cursor:pointer;font-family:inherit'
    css+=(
        f'<div style="display:flex;gap:4px;padding:8px 10px 0;background:var(--bg);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100">'
        f'<button onclick="showTab(\'main\')" id="tab-main" style="{_ta2};{_tb2}">主要分析</button>'
        f'<button onclick="showTab(\'glossary\')" id="tab-glossary" style="{_ti2};{_tb2}">📖 名詞解釋</button>'
        f'<button onclick="showTab(\'learning\')" id="tab-learning" style="{_ti2};{_tb2}">🧠 學習狀態</button>'
        f'</div><script>{_tab_js2}</script>'
        f'<div id="main">'
    )
    css+=f'<div class="hdr"><div><div class="ht">GEX ORACLE AUTO S{snapshot_num}</div>'
    css+=f'<div class="hs">UFT v2.0 | {ts} UTC | 6h | <span style="color:{agc}">updated <span id="ago">{ags}</span></span></div>'
    # JS 動態刷新 "updated Xm ago"（原為生成時烙死的靜態文字，永遠顯示 0m ago）
    _gen_iso = data.get("timestamp", "")
    css+=("<script>var _GEN='" + str(_gen_iso) + "';"
          "function _ago(){var g=new Date(_GEN);if(isNaN(g.getTime()))return;"
          "var m=Math.floor((Date.now()-g.getTime())/60000);if(m<0)m=0;"
          "var t=(m<60)?(m+'m ago'):(Math.floor(m/60)+'h'+(m%60)+'m ago');"
          "var e=document.getElementById('ago');if(e)e.textContent=t;}"
          "_ago();setInterval(_ago,60000);</script>")
    css+=f'<div class="hs">FR next: <span style="color:var(--cyan)">{fns}</span> | Acc: <span style="color:{frc}">{facc:+.5f}%</span> | Pin Risk: <span style="color:{prc};font-weight:bold">{pr}</span></div>'
    css+='</div>'
    css+=f'<div style="text-align:right"><div style="font-size:9px;color:var(--mut)">BTC/USDT PERP | Regime: <span style="color:{rc};font-weight:bold">{regime}</span> | GF: ${gf_main:,} | {cd}</div>'
    css+=f'<div class="spot">${spot:,.0f}</div>'
    css+=f'<div style="font-size:10px;color:{frc}">FR {frs}{fr:.5f}% | DVOL {dvol:.2f}%</div>'
    css+=f'<div style="font-size:9px;color:var(--mut)">OI {oi:.2f}w'
    if data.get('oi_change') is not None: css+=f' ({data.get("oi_change",0):+.3f}w {data.get("oi_change_pct",0):+.1f}%)'
    css+=' | Basis'
    if data.get('perp_basis') is not None: css+=f' ${data.get("perp_basis",0):+.0f} ({data.get("perp_basis_pct",0):+.3f}%)'
    else: css+=' N/A'
    css+='</div></div></div>'
    css+=f'<div class="al" style="background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.4);margin-top:8px">Oracle: <strong>{ot}</strong> | sigma=${sigma:,.0f} | UFT Median=<strong>${uft_med:,.0f}</strong></div>'
    css+=f'<div class="al" style="background:rgba(245,158,11,.08);border:1px solid {r15c}">{r15t}</div>'
    css+=(f'<div class="g4">'
          f'<div class="card"><div class="kv" style="color:var(--yel)">${spot:,.0f}</div><div class="kl">SPOT</div></div>'
          f'<div class="card"><div class="kv" style="color:{frc}">{frs}{fr:.5f}%</div><div class="kl">FUNDING RATE</div></div>'
          f'<div class="card"><div class="kv" style="color:{s0c}">{s0s}</div><div class="kl">SKEW ({exp0})</div></div>'
          f'<div class="card"><div class="kv" style="color:var(--mut)">{oi:.2f}w</div><div class="kl">OPEN INTEREST</div></div></div>')
    css+=f'<div class="g3">'
    css+=(f'<div class="card"><div class="ct">MACD (3 Timeframes)</div>'
          f'<div class="row"><span style="color:var(--cyan)">15m (30%)</span><span style="color:{c15}">{s15} {m15:+.2f}</span><span style="color:var(--mut)">{d15:+.0f}</span></div>'
          f'<div class="row"><span style="color:var(--cyan)">4h (62%)</span><span style="color:{c4h}">{s4h} {m4h:+.2f}</span><span style="color:var(--mut)">{d4h:+.0f}</span></div>'
          f'<div class="row"><span style="color:var(--cyan)">1D (70%)</span><span style="color:{c1d}">{s1d} {m1d:+.2f}</span><span style="color:var(--mut)">{d1d:+.0f}</span></div>'
          f'<div style="border-top:1px solid var(--border);margin-top:4px;padding-top:4px">'
          f'<div class="row"><span style="color:var(--mut)">ATM IV ({exp0})</span><span style="color:var(--pur)">{data.get(f"atm_iv_{exp0}",dvol) or dvol:.2f}%</span></div>'
          f'<div class="row"><span style="color:var(--mut)">DVOL Index</span><span style="color:var(--pur)">{dvol:.2f}%</span></div>'
          f'<div class="row"><span style="color:var(--mut)">IV Premium</span><span style="color:var(--pur)">{(data.get(f"atm_iv_{exp0}",dvol) or dvol)-dvol:+.2f}%</span></div>'
          f'</div></div>')
    css+=(f'<div class="card"><div class="ct">UFT v2.0 Equation</div>'
          f'<div class="row"><span>GBM (x{weights.get("gbm",0.40):.2f})</span><span>${comps.get("gbm",0):,.0f}</span></div>'
          f'<div class="row"><span>GEX (x{weights.get("gex",0.10):.2f})</span><span>${comps.get("gex",0):,.0f}</span></div>'
          f'<div class="row"><span>Behavior (x{bw:.2f})</span><span>${comps.get("behavior",0):,.0f}</span></div>'
          f'<div class="row"><span>Bayesian (x{weights.get("bayesian",0.12):.2f})</span><span>${comps.get("bayesian",0):,.0f}</span></div>'
          f'<div class="row"><span>TimeDecay (x{weights.get("timedecay",0.10):.2f})</span><span>${comps.get("timedecay",0):,.0f}</span></div>'
          f'<div class="big">${uft_med:,.0f}</div><div class="sm">Mode=${uft_mode:,.0f} | EMH=${spot:,.0f}</div></div>')
    css+=(f'<div class="card"><div class="ct">Scenario Probability ({exp0})</div>'
          f'<div style="font-size:10px;display:flex;justify-content:space-between"><span style="color:var(--green)">A: Bounce &gt;+0.5s</span><span style="color:var(--green)">{pA}%</span></div>'
          f'<div class="pb"><div class="pf" style="width:{min(pA,100):.0f}%;background:var(--green)"></div></div>'
          f'<div style="font-size:10px;display:flex;justify-content:space-between"><span style="color:var(--yel)">B: Core range</span><span style="color:var(--yel)">{pB}%</span></div>'
          f'<div class="pb"><div class="pf" style="width:{min(pB,100):.0f}%;background:var(--yel)"></div></div>'
          f'<div style="font-size:10px;display:flex;justify-content:space-between"><span style="color:var(--red)">C: Put Wall test</span><span style="color:var(--red)">{pC}%</span></div>'
          f'<div class="pb"><div class="pf" style="width:{min(pC,100):.0f}%;background:var(--red)"></div></div>'
          f'<div style="font-size:10px;display:flex;justify-content:space-between"><span style="color:var(--red)">D: Tail &lt;-1s</span><span style="color:var(--red)">{pD}%</span></div>'
          f'<div class="pb"><div class="pf" style="width:{min(pD,100):.0f}%;background:#7f1d1d"></div></div></div>')
    css+='</div>'
    css+='<div class="g2">'
    css+=(f'<div><div class="card" style="margin-bottom:10px"><div class="ct">GEX Structure + Regime</div>'
          f'<div class="row"><span>Regime ({exp0})</span><span style="color:{rc};font-weight:bold">{regime}</span></div>'
          f'<div class="row"><span>Gamma Flip ({exp0})</span><span style="color:var(--yel)">${gf0:,}</span></div>'
          f'<div class="row"><span>Spot vs GF</span><span style="color:{rc}">{spot-gf_main:+,.0f} ({abs(spot-gf_main)/gf_main*100:.1f}%)</span></div>'
          f'<div class="row"><span>GF Stability</span><span style="color:{gfsc}">{gfss} ({gfs:.2f}s)</span></div>'
          f'<div class="row"><span>Pin Risk</span><span style="color:{prc};font-weight:bold">{pr} ({psc:.0f})</span></div>'
          f'<div class="row"><span>Spot vs Put Wall</span><span style="color:var(--red)">+${spot-pw0:,.0f} (+{(spot-pw0)/pw0*100 if pw0 else 0:.1f}%)</span></div>'
          f'<div class="row"><span>Spot vs Call Wall</span><span style="color:var(--green)">-${cw0-spot:,.0f} (-{(cw0-spot)/cw0*100 if cw0 else 0:.1f}%)</span></div>'
          f'<div class="row"><span>Max Pain ({exp0})</span><span style="color:var(--pur)">${mpv:,}</span></div>'
          f'<div class="row"><span>GEX Pin ({exp0})</span><span style="color:var(--yel)">${uft_mode:,.0f}</span></div>'
          f'<div class="row"><span>OI Concentration</span><span>{data.get(f"oi_concentration_{exp0}",0) or 0:.1f}% in top3</span></div>'
          f'<div class="row"><span>PCR {exp0} ATM</span><span style="color:var(--cyan)">{data.get(f"pcr_atm_{exp0}",pcr0) or pcr0:.3f}</span></div>'
          f'<div class="row"><span>PCR {exp0} OTM</span><span>{data.get(f"pcr_otm_{exp0}",0) or 0:.3f}</span></div>'
          f'<div class="row"><span>PCR {exp1}</span><span>{pcr1:.3f}</span></div>'
          f'<div class="row"><span>PCR {exp2}</span><span>{pcr2:.3f}</span></div>'
          f'<div class="row"><span>Call Wall {exp0}</span><span style="color:var(--green)">${cw0:,}</span></div>'
          f'<div class="row"><span>Put Wall {exp0}</span><span style="color:var(--red)">${pw0:,}</span></div>'
          f'<div class="row"><span>Call Wall {exp1}</span><span style="color:var(--green)">${cw1:,}</span></div>'
          f'<div class="row"><span>Put Wall {exp1}</span><span style="color:var(--red)">${pw1:,}</span></div></div>')
    css+=(f'<div class="card"><div class="ct">Cross-Expiry Skew</div>'
          f'<div class="row"><span>{exp0} ({cd})</span><span><span style="color:{s0c}">{s0s}</span> <span style="color:{stc}">{st}</span></span></div>'
          f'<div style="font-size:9px;color:var(--mut);margin-bottom:2px">{st3}</div>'
          f'<div style="background:var(--border);height:6px;border-radius:3px;margin:2px 0 6px;overflow:hidden"><div style="height:100%;width:{sw0};background:{s0c};border-radius:3px"></div></div>'
          f'<div class="row"><span>{exp1}</span><span style="color:{s1c}">{s1s}</span></div>'
          f'<div style="background:var(--border);height:6px;border-radius:3px;margin:2px 0 6px;overflow:hidden"><div style="height:100%;width:{sw1};background:{s1c};border-radius:3px"></div></div>'
          f'<div class="row"><span>{exp2}</span><span style="color:{s2c}">{s2s}</span></div>'
          f'<div style="background:var(--border);height:6px;border-radius:3px;margin:2px 0 6px;overflow:hidden"><div style="height:100%;width:{sw2};background:{s2c};border-radius:3px"></div></div>'
          f'<div style="font-size:9px;color:var(--mut);margin-top:4px">Positive skew = bearish (market pays for downside protection)</div></div></div>')
    css+=(f'<div><div class="card" style="margin-bottom:10px"><div class="ct">Options Chain {exp0} (Top by OI)</div>'
          f'<table><thead><tr><th>Strike</th><th>Call OI</th><th>Put OI</th><th>PCR</th><th>IV C/P%</th></tr></thead><tbody>{sr}</tbody></table></div>'
          f'<div class="card" style="margin-bottom:10px"><div class="ct">Active Rules</div>{ruh}</div>'
          f'<div class="card" style="border-color:var(--acc)"><div class="ct">Oracle Insight</div>'
          f'<div style="font-size:10px;line-height:1.7">{it}</div>')
    if nt: css+=f'<div style="font-size:9px;color:var(--cyan);margin-top:6px">Next: {nt}</div>'
    css+='</div></div></div>'
    # Oracle Conclusion區塊
    coh=""
    if collision or True:
        _ov=ot; _ki=it; _nt=nt
        _regime_txt="POS Regime (造市商穩定器)" if regime=="POS" else "NEG Regime (造市商放大器)"
        _skew_txt=f"全期限偏空（{s0s}/{s1s}/{s2s}）" if (sk0 or 0)>5 else (f"全期限偏多（{s0s}/{s1s}/{s2s}）" if (sk0 or 0)<-5 else f"混合（{s0s}/{s1s}/{s2s}）")
        _pin_txt=f"GEX Pin ${uft_mode:,.0f} vs Max Pain ${mpv:,}，差距 ${abs(mpv-uft_mode):,.0f}"
        _settle_txt=f"T-{dl}d 進入結算收斂期" if dl<=7 else f"T-{dl}d 結算仍遠"
        coh=(
            f'<div style="padding:0 10px 10px"><div class="card" style="border-color:#8b5cf6">'
            f'<div class="ct" style="color:#8b5cf6">ORACLE CONCLUSION — S{snapshot_num}</div>'
            f'<div style="font-size:10px;line-height:1.9;color:var(--txt)">'
            f'<div class="row"><span style="color:var(--mut)">Regime</span><span style="color:{rc};font-weight:bold">{_regime_txt}</span></div>'
            f'<div class="row"><span style="color:var(--mut)">Skew結構</span><span style="color:{s0c}">{_skew_txt}</span></div>'
            f'<div class="row"><span style="color:var(--mut)">Pin博弈</span><span style="color:var(--yel)">{_pin_txt}</span></div>'
            f'<div class="row"><span style="color:var(--mut)">結算倒數</span><span style="color:var(--cyan)">{_settle_txt}</span></div>'
            f'<div class="row"><span style="color:var(--mut)">UFT中位</span><span style="color:var(--yel)">${uft_med:,.0f} | Mode=${uft_mode:,.0f} | σ=${sigma:,.0f}</span></div>'
            f'<div class="row"><span style="color:var(--mut)">情境分布</span><span>A={pA}% B={pB}% C={pC}% D={pD}%</span></div>'
            f'<div class="row"><span style="color:var(--mut)">Active Rules</span><span style="color:#f59e0b">{len(ru)}個觸發</span></div>'
            f'<div style="margin-top:8px;padding-top:6px;border-top:1px solid var(--border)">'
            f'<div style="font-size:9px;color:var(--mut);margin-bottom:4px">ORACLE VERDICT</div>'
            f'<div style="font-size:11px;color:var(--acc);font-weight:bold">{_ov}</div>'
            f'</div>'
            f'<div style="margin-top:6px;padding-top:6px;border-top:1px solid var(--border)">'
            f'<div style="font-size:9px;color:var(--mut);margin-bottom:4px">KEY INSIGHT</div>'
            f'<div style="font-size:10px;line-height:1.7;color:var(--txt)">{_ki}</div>'
            f'</div>'
            f'<div style="margin-top:6px;padding-top:6px;border-top:1px solid var(--border)">'
            f'<div style="font-size:9px;color:var(--mut);margin-bottom:4px">NEXT TRIGGER</div>'
            f'<div style="font-size:10px;color:var(--cyan)">{_nt if _nt else "Monitor FR/Skew/Spot vs Pin"}</div>'
            f'</div></div></div></div>'
        )
    # coh+slh+clh+footer 在 #main div 內
    css += coh + slh + clh
    css += f'<div class="foot">GEX Oracle v2.0 | S{snapshot_num} | 6h auto | Not investment advice</div>'
    css += '</div>'  # close #main

    # ── Glossary Tab ─────────────────────────────────────────────
    glossary_terms = [
        ("UFT (Unified Field Theory)", "統一場論", "GEX Oracle 核心預測框架。P(X)=0.30×GBM+0.18×GEX+0.28×行為信號+0.12×貝葉斯+0.12×時間衰減。五個分量加權合成結算價中位估計。"),
        ("GBM", "幾何布朗運動", "金融標準隨機遊走。假設 BTC 以 Spot 為起點按 DVOL 定義的波動率做隨機擴散。GBM 中心=Spot，是最保守的 EMH 基準。權重 0.30。"),
        ("GEX", "Gamma 暴露", "造市商被迫對沖的 Delta 方向。GEX>0：MM 持有正 Gamma，價格偏離 Pin 時反向買賣→穩定化。GEX<0：MM 放大波動。權重 0.18。"),
        ("BehaviorSignal", "行為信號", "FR方向×強度(35%)+Skew偏態(25%)+PCR(20%)+OI變化(10%)+Basis(5%)+鯨魚鏈上(5%)。範圍[-1,+1]，+1=極度多頭行為。權重 0.28。"),
        ("Bayesian", "貝葉斯分量", "基於 Regime 方向和 Skew 的先驗估計。T越小越往 GEX Pin 收斂（結算吸引力）。POS Regime 時偏 Spot 上方，NEG 時偏下方。權重 0.12。"),
        ("TimeDecay", "時間衰減分量", "臨近結算時 GEX Pin 吸引力增強效應。T→0 時 Gamma 極度集中於 Pin 附近，Pin 磁鐵效應最強。中心估計=GEX Pin。權重 0.12。"),
        ("UFT Median", "UFT 中位數", "五個分量加權合成的結算價中位估計。歷史誤差：26MAR26=0.41σ，27MAR26=0.02σ，3APR26≈0σ。"),
        ("UFT Mode", "UFT 眾數", "概率分布峰值，等同於 GEX Pin（最大 Gamma 集中點）。結算前 T-3d 內 Pin 磁鐵效應最強。"),
        ("σ (Sigma)", "一個標準差", "σ=Spot×(DVOL/100)×√T。BTC 有 68% 概率在到期日停留在 [Spot-σ, Spot+σ]。"),
        ("EMH", "效率市場假說基準", "EMH 下最優預測=當前現貨價。UFT 框架 alpha 在條件概率分布形狀和風控邊界識別，而非點預測精度。"),
        ("Gamma Flip (GF)", "Gamma 翻轉點", "造市商 Gamma 暴露從正轉負的臨界價位。Spot>GF→POS Regime（穩定器）；Spot<GF→NEG Regime（放大器）。最重要的 Regime 邊界。"),
        ("POS Regime", "正向 Gamma 機制", "現貨在 GF 以上。MM 持正 Gamma：下跌時買入、上漲時賣出→均值回歸、低波動、Pin 磁鐵有效。"),
        ("NEG Regime", "負向 Gamma 機制", "現貨跌破 GF。MM 持負 Gamma：下跌時追賣→放大下跌。趨勢延伸、高波動、Pin 磁鐵失效。"),
        ("GEX Pin", "Gamma 磁鐵點", "Put OI 最集中的行使價（ATM 附近）。造市商在此 Gamma 對沖需求最大，傾向把現貨固定在此附近，尤其結算前 48h。"),
        ("Max Pain", "最大痛苦點", "使期權買方總虧損最大的行使價。理論上造市商有動力把現貨推向此點。GEX Pin 通常比 Max Pain 更有實際吸引力。"),
        ("Pin Risk", "Pin 風險", "現貨被 Pin 在某行使價附近的風險。對空頭 Gamma 持有者有爆炸性損失風險。本系統用 GEX Pin 距 Spot 距離量化。"),
        ("Call Wall", "看漲阻力牆", "Call OI 最集中的行使價。MM 在此附近空 Gamma，上漲過此點需大量買入對沖→形成自然阻力，突破可能加速（Gamma Squeeze）。"),
        ("Put Wall", "看跌支撐牆", "Put OI 最集中的行使價。三態：OTM=支撐弱；ATM（Spot≈PW）=最強支撐；ITM（Spot<PW）=MM 轉為買入=動態支撐。"),
        ("PCR", "Put/Call 比率", "Put OI÷Call OI。>1.3：空頭防禦主導；<0.6：多頭進攻主導。ATM PCR 比全域 PCR 更能反映即時方向，OTM PCR 反映尾部風險需求。"),
        ("OI Concentration", "OI 集中度", "最大3個行使價的 OI 佔總 OI 比例。集中度越高→Pin 效應越強。通常結算前 OI 向 ATM 集中。"),
        ("Cross-Expiry Skew", "跨期 Skew 結構", "近端 Skew > 遠端為正常。倒掛（遠端>近端）→市場預期中長期尾部風險更高，可能為機構對沖需求。"),
        ("IV (Implied Volatility)", "隱含波動率", "從期權市場價格反推的未來波動率預期。ATM IV 最能反映市場共識，OTM IV 反映尾部風險定價。"),
        ("DVOL Index", "Deribit 波動率指數", "Deribit 官方 BTC 期權市場整體 IV 指數（類似 VIX）。30天期限年化波動率，多行使價加權合成。上升=市場恐慌/對沖需求增加。"),
        ("ATM IV", "平值隱含波動率", "最接近當前 Spot 的期權 IV。ATM IV - DVOL = IV Premium，正值表示近端比市場整體更貴。"),
        ("Skew", "波動率偏態", "Put IV - Call IV（OTM）。正值：市場為下行保護付更高溢價，空頭情緒主導（BTC 通常正 Skew）。"),
        ("Gamma", "期權 Gamma", "Delta 對 Spot 的二階導數。衡量 MM Delta 對沖需求隨 Spot 變化的速度。ATM Gamma 最大，結算前 Gamma 最集中。"),
        ("Delta", "期權 Delta", "期權價值對標的物價格的一階導數。Call Delta∈[0,1]，Put Delta∈[-1,0]。MM 通常 Delta 中性但 Gamma 暴露無法消除。"),
        ("FR (Funding Rate)", "資金費率", "永續合約每 8h 結算一次。FR>0：多方付費給空方（現貨溢價/多頭主導）；FR<0：空方付費（反向溢價/空頭主導）。觸發閾值±0.005%。"),
        ("Perp Basis", "永續基差", "永續合約價格-現貨價格。正值=合約溢價（多頭情緒）；負值=折價（空頭情緒）。是 FR 的即時領先指標。"),
        ("L/S Ratio", "多空比", "大戶帳戶多頭/空頭持倉比例。>2.0=大戶明顯偏多，<1.0=偏空。FR正+L/S上升=全權重確認；矛盾=行為信號×0.7懲罰。"),
        ("OI (Open Interest)", "未平倉量", "市場上未平倉合約總量（萬張）。OI增加+FR正→新多頭進場；OI增加+FR負→新空頭進場；OI下降=舊倉位平倉（趨勢末段）。"),
        ("MACD (12,26,9)", "移動平均匯聚背離", "DIF=EMA12-EMA26；DEA=DIF的EMA9；MACD=(DIF-DEA)×2。DIF>DEA=金叉（多）；DIF<DEA=死叉（空）。金叉在DIF<0領域→信號×0.5。"),
        ("DIF", "MACD 快慢線差", "DIF=EMA12-EMA26。DIF>0且上升=上升動能加速；DIF<0且下降=下跌動能加速。1D DIF<-1000觸發Rule#2深度負值警告。"),
        ("RSI", "相對強弱指數", "範圍[0,100]。RSI<30=超賣（潛在反彈），>70=超買（潛在回調）。需區分真實超賣（RSI隨Spot下跌>1根K棒）和機械滾動（效果×0.5）。"),
        ("EMA", "指數移動平均", "近期價格權重更高的移動平均。本系統使用 EMA5/10/30/200。Spot 在所有 EMA 下方=全線空頭排列。"),
        ("Rule#5 v2b", "FR 確認規則", "FR 須持續正值 16h 以上（=兩個完整 8h 結算週期）才算多頭確認。單週期正 FR 可能是噪音。"),
        ("Rule#14", "FR 最小分析單位", "FR 是每 8h 結算機制，sub-8h 的 FR 分析在方法論上無效。最小有效單位=一個 8h 結算週期。"),
        ("Rule#15 矛盾懲罰", "行為信號矛盾檢測", "FR>+0.005%且Skew>+5%（FR偏多但Skew偏空），behavior_penalty=0.7×。基礎權重0.28不變，信號強度縮減。"),
        ("Regime 分層", "POS/NEG 機制分離", "POS：Layer1+Layer2合併分析，造市商提供自然支撐。NEG：兩層嚴格分離，造市商變放大器，每個信號需更高確信度。"),
        ("Pin 博弈", "結算日 Pin 動態", "結算前 T-3d 進入結算收斂期。GEX Pin 和 Max Pain 爭奪現貨落點。兩點差距越小，Pin 效應越確定；差距>$2000時不確定性高。"),
        ("UFT Optimizer L1-L5", "五層迭代學習", "L1:梯度下降(滾動衰減) L2:信號貢獻度分析 L3:Regime分層(POS/NEG各自最優) L4:貝葉斯更新(防過擬合) L5:收斂偵測(error<0.3σ凍結，>0.8σ解凍)。"),
        ("Signal Direction Accuracy", "信號方向準確率", "每個信號預測方向與實際結算偏差的一致率。>60%=有效；<40%=反向有效；≈50%=無效（隨機）。"),
        ("Rolling Decay Weight", "滾動衰減", "梯度下降計算損失時，越近期結算給越高損失權重（half-life=10條）。公式：w=exp(-0.693×age/10)。防止過度依賴遠期歷史。"),
        ("Convergence", "收斂狀態", "收斂：均方誤差<0.3σ（絕對）或連續3次優化改善<1%（相對）→凍結權重。解凍：新樣本均誤>0.8σ（市場結構變化，重新學習）。"),
        ("Settlement Log", "結算記錄", "每次 UFT 計算記錄預測，到期日後自動從 Deribit 拉取結算價並計算誤差。誤差<0.5σ=綠；0.5-1.0σ=黃；>1.0σ=紅。累積10筆啟動首次優化。"),
    ]

    categories = [
        ("UFT 方程式分量", ["UFT (Unified Field Theory)", "GBM", "GEX", "BehaviorSignal", "Bayesian", "TimeDecay", "UFT Median", "UFT Mode", "σ (Sigma)", "EMH"]),
        ("GEX 結構與 Regime", ["Gamma Flip (GF)", "POS Regime", "NEG Regime", "GEX Pin", "Max Pain", "Pin Risk", "Call Wall", "Put Wall", "PCR", "OI Concentration", "Cross-Expiry Skew"]),
        ("期權基礎概念", ["IV (Implied Volatility)", "DVOL Index", "ATM IV", "Skew", "Gamma", "Delta"]),
        ("行為信號", ["FR (Funding Rate)", "Perp Basis", "L/S Ratio", "OI (Open Interest)"]),
        ("K線技術分析", ["MACD (12,26,9)", "DIF", "RSI", "EMA"]),
        ("框架規則", ["Rule#5 v2b", "Rule#14", "Rule#15 矛盾懲罰", "Regime 分層", "Pin 博弈"]),
        ("迭代學習系統", ["UFT Optimizer L1-L5", "Signal Direction Accuracy", "Rolling Decay Weight", "Convergence", "Settlement Log"]),
    ]
    term_dict = {t[0]: (t[1], t[2]) for t in glossary_terms}

    glos_html = f'<div id="glossary" style="display:none;padding:0 10px 20px">'
    glos_html += f'<div style="font-size:10px;color:var(--mut);padding:8px 0 12px">共 {len(glossary_terms)} 個術語 | 按類別排列 | 點擊展開</div>'
    for cat_name, cat_terms in categories:
        glos_html += f'<div style="font-size:11px;color:var(--acc);font-weight:bold;margin:16px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--border)">{cat_name}</div>'
        for term in cat_terms:
            if term not in term_dict: continue
            cn, desc = term_dict[term]
            glos_html += (
                f'<details style="margin-bottom:6px;background:var(--panel);border:1px solid var(--border);border-radius:4px">'
                f'<summary style="padding:8px 10px;cursor:pointer;list-style:none;display:flex;justify-content:space-between">'
                f'<span><span style="color:var(--yel);font-weight:bold;font-size:11px">{term}</span>'
                f'<span style="color:var(--mut);font-size:10px;margin-left:8px">{cn}</span></span>'
                f'<span style="color:var(--mut);font-size:9px">&#9660;</span></summary>'
                f'<div style="padding:8px 10px 10px;font-size:10px;line-height:1.8;color:var(--txt);border-top:1px solid var(--border)">{desc}</div>'
                f'</details>'
            )
    glos_html += '</div>'
    css += glos_html

    # ── 學習狀態 Tab ─────────────────────────────────────────────
    learn_html = '<div id="learning" style="display:none;padding:0 10px 20px">'
    try:
        if _os2.path.exists('data/settlement_log.json'):
            import json as _jl2
            with open('data/settlement_log.json') as _fl2:
                _ll2 = _jl2.load(_fl2)
            _cw2 = _ll2.get('current_weights', {"gbm":0.30,"gex":0.18,"behavior":0.28,"bayesian":0.12,"timedecay":0.12})
            _rw2 = _ll2.get('regime_weights', {})
            _cv2 = _ll2.get('convergence', {})
            _sc2 = _ll2.get('signal_contributions', {})
            _wh2 = _ll2.get('weight_history', [])
            _cn2 = len([r for r in _ll2.get('records',[]) if r.get('actual_settlement')])
            _tn2 = len(_ll2.get('records',[]))
            _frozen2 = _cv2.get('frozen', False)
            _ncyc2 = len(set(r.get('expiry') for r in _ll2.get('records',[]) if r.get('actual_settlement') and not r.get('corrupted_gex')))
            _conv_s = '已收斂凍結' if _frozen2 else f'學習中 ({_cn2}樣本/{_ncyc2}週期, 需≥3週期)'
            _conv_c2 = '#10b981' if _frozen2 else '#f59e0b'
            _err_h2 = _cv2.get('avg_error_sigma_history', [])
            learn_html += f'<div class="card" style="margin-bottom:10px"><div class="ct">學習系統狀態</div>'
            learn_html += f'<div class="row"><span>收斂狀態</span><span style="color:{_conv_c2};font-weight:bold">{_conv_s}</span></div>'
            learn_html += f'<div class="row"><span>已結算樣本</span><span>{_cn2} / {_tn2} 筆</span></div>'
            learn_html += f'<div class="row"><span>優化次數</span><span>{len(_wh2)} 次</span></div>'
            if _err_h2:
                learn_html += f'<div class="row"><span>誤差σ趨勢</span><span style="color:var(--cyan)">{" → ".join(f"{v:.3f}" for v in _err_h2[-5:])}</span></div>'
            learn_html += '</div>'
            learn_html += '<div class="card" style="margin-bottom:10px"><div class="ct">全局最優權重 (L1+L4 Fusion)</div>'
            for k2, v2 in _cw2.items():
                bw2 = f'{min(v2*100*4,100):.0f}%'
                learn_html += f'<div class="row"><span>{k2}</span><span style="color:var(--yel)">{v2:.4f} ({v2*100:.1f}%)</span></div>'
                learn_html += f'<div style="background:var(--border);height:4px;border-radius:2px;margin:1px 0 4px;overflow:hidden"><div style="height:100%;width:{bw2};background:var(--yel);border-radius:2px"></div></div>'
            learn_html += '</div>'
            if _rw2:
                learn_html += '<div class="card" style="margin-bottom:10px"><div class="ct">Regime 分層權重 (L3)</div>'
                for _rn2, _rd2 in _rw2.items():
                    _rc3 = '#10b981' if _rn2 == 'POS' else '#ef4444'
                    learn_html += f'<div style="font-size:10px;color:{_rc3};font-weight:bold;margin:6px 0 3px">{_rn2} Regime</div>'
                    for k3, v3 in _rd2.items():
                        learn_html += f'<div class="row"><span style="color:var(--mut)">{k3}</span><span style="color:{_rc3}">{v3:.4f}</span></div>'
                learn_html += '</div>'
            if _sc2:
                learn_html += '<div class="card" style="margin-bottom:10px"><div class="ct">信號方向準確率 (L2)</div>'
                learn_html += '<div style="font-size:9px;color:var(--mut);margin-bottom:6px">&gt;60%=有效 | &lt;40%=反向有效 | ≈50%=無效</div>'
                for sg2, sv2 in sorted(_sc2.items(), key=lambda x: x[1].get('direction_accuracy',0), reverse=True):
                    ac2 = sv2.get('direction_accuracy', 0)
                    ns2 = sv2.get('n', 0)
                    ac2c = '#10b981' if ac2 > 0.6 else ('#ef4444' if ac2 < 0.4 else 'var(--mut)')
                    ac2b = f'{ac2*100:.0f}%'
                    learn_html += f'<div class="row"><span>{sg2}</span><span style="color:{ac2c}">{ac2*100:.0f}% (n={ns2})</span></div>'
                    learn_html += f'<div style="background:var(--border);height:4px;border-radius:2px;margin:1px 0 4px;overflow:hidden"><div style="height:100%;width:{ac2b};background:{ac2c};border-radius:2px"></div></div>'
                learn_html += '</div>'
            if _wh2:
                learn_html += '<div class="card"><div class="ct">最近優化記錄 (最多5次)</div>'
                _wh2v=[h for h in _wh2 if 'note' not in h]
                for h2 in _wh2v[-5:][::-1]:
                    _ts_h = str(h2.get('timestamp',''))[:16]
                    _frz2 = '🔒' if h2.get('frozen') else '🔄'
                    learn_html += (f'<div style="font-size:9px;padding:4px 0;border-bottom:1px solid var(--border)">'
                                   f'{_frz2} {_ts_h} | n={h2.get("samples",0)} | '
                                   f'err=${h2.get("avg_error_usd",0):,.0f} ({h2.get("avg_error_sigma",0):.3f}σ) | '
                                   f'改善{h2.get("improvement_pct",0):+.1f}%</div>')
                learn_html += '</div>'
        else:
            learn_html += '<div class="card"><div style="font-size:10px;color:var(--mut);padding:12px">尚無 settlement_log.json，首次結算後自動建立</div></div>'
    except Exception as _le2:
        learn_html += f'<div class="card"><div style="font-size:10px;color:var(--red);padding:12px">載入錯誤: {_le2}</div></div>'
    learn_html += '</div>'
    css += learn_html
    css += '</body></html>'
    return css
