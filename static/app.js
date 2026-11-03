const $=id=>document.getElementById(id);
let pairs=[];
let deferredInstallPrompt=null;
const installButton=$("install");
window.addEventListener("beforeinstallprompt", event=>{event.preventDefault();deferredInstallPrompt=event;installButton.hidden=false;});
installButton.addEventListener("click",async()=>{if(!deferredInstallPrompt)return;deferredInstallPrompt.prompt();await deferredInstallPrompt.userChoice;deferredInstallPrompt=null;installButton.hidden=true;});
window.addEventListener("appinstalled",()=>{installButton.hidden=true;});
if("serviceWorker" in navigator){window.addEventListener("load",()=>navigator.serviceWorker.register("/static/sw.js").catch(()=>{}));}
document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{
 document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));b.classList.add("active");
 ["scanner","strategy","data"].forEach(id=>$(id).classList.toggle("hidden",id!==b.dataset.tab));
});
async function init(){
 try{const r=await fetch("/api/pairs");pairs=(await r.json()).pairs;
 $("pair").innerHTML=pairs.map(p=>`<option value="${p}">${p.replace("USDT","/USDT")}</option>`).join("");
 $("pairs").innerHTML=pairs.map((p,i)=>`<div class="pair">${String(i+1).padStart(2,"0")} · ${p.replace("USDT","/USDT")}</div>`).join("");
 }catch(e){$("signal").textContent="Could not load pairs. Check server connection."}
}
function strategy(){return {name:$("sname").value,fast_ema:+$("fast").value,slow_ema:+$("slow").value,rsi_period:+$("rsi").value,rsi_long_max:+$("rmax").value,stop_pct:+$("stop").value,target_pct:+$("target").value}}
$("analyze").onclick=async()=>{
 $("signal").textContent="Loading one year of candle data and analyzing…";
 const s=strategy(),q=new URLSearchParams({symbol:$("pair").value,interval:$("tf").value});
 Object.entries(s).forEach(([k,v])=>q.set(k,v));
 try{const r=await fetch("/api/analyze?"+q,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(s)});const d=await r.json();if(!r.ok)throw Error(d.detail||"Request failed");
 const x=d.result;let html=`<div class="big ${x.signal==="LONG"?"good":x.signal==="SHORT"?"bad":""}">${x.signal}</div><p>Pair: <b>${d.symbol.replace("USDT","/USDT")}</b> · ${d.interval} · ${d.candles_used} candles</p>`;
 if(x.signal==="LONG"||x.signal==="SHORT"){html+=`<p>Last close: <b>${x.last_close.toFixed(6)}</b><br>Entry zone: ${x.entry_range.map(v=>v.toFixed(6)).join(" – ")}<br>Take profit: ${x.take_profit.toFixed(6)}<br>Stop loss: ${x.stop_loss.toFixed(6)}<br>RSI: ${x.rsi.toFixed(2)}</p>`}
 html+=`<small class="muted">${x.note||""}</small>`;$("signal").innerHTML=html;
 }catch(e){$("signal").textContent="Analysis error: "+e.message}
};
$("backtest").onclick=async()=>{
 $("bt").textContent="Downloading historical candles and running backtest…";
 const s=strategy(),q=new URLSearchParams({symbol:$("pair").value,interval:$("tf").value,fast_ema:s.fast_ema,slow_ema:s.slow_ema,stop_pct:s.stop_pct,target_pct:s.target_pct});
 try{const r=await fetch("/api/backtest?"+q);const d=await r.json();if(!r.ok)throw Error(d.detail||"Backtest failed");
 $("bt").innerHTML=`<b>${d.symbol.replace("USDT","/USDT")} · ${d.interval}</b><p>Closed trades: ${d.closed_trades}<br>Wins: ${d.wins} · Losses: ${d.losses}<br><span class="big">${d.win_rate_pct===null?"N/A":d.win_rate_pct+"%"}</span> historical win rate</p><small class="muted">${d.warning}</small>`;
 }catch(e){$("bt").textContent="Backtest error: "+e.message}
};
$("upload").onclick=async()=>{
 const f=$("pdf").files[0];if(!f){$("pdfout").textContent="Choose a PDF first.";return}
 const fd=new FormData();fd.append("file",f);$("pdfout").textContent="Extracting PDF text…";
 try{const r=await fetch("/api/upload-pdf",{method:"POST",body:fd});const d=await r.json();if(!r.ok)throw Error(d.detail||"Upload failed");
 $("pdfout").innerHTML=`<b>${d.document.name}</b><p>${d.document.pages} pages · ${d.document.characters} extracted characters</p><p>${d.important}</p><pre style="white-space:pre-wrap;color:#9eacc2">${d.preview}</pre>`;
 }catch(e){$("pdfout").textContent="Upload error: "+e.message}
};
init();


// Basic V1: scan the fixed 20-pair watchlist sequentially while the app is open.
$("scan20").onclick=async()=>{
 const btn=$("scan20"),out=$("scanresults"),tf=$("tf").value;
 btn.disabled=true;out.textContent="Scanning 20 USDT pairs… Keep this app open and connected to the internet.";
 const s=strategy(),results=[];
 for(let i=0;i<pairs.length;i++){
  out.textContent=`Scanning ${i+1}/ ${pairs.length}: ${pairs[i]} (${tf})…`;
  try{
   const q=new URLSearchParams({symbol:pairs[i],interval:tf});
   const r=await fetch("/api/analyze?"+q,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(s)});
   const d=await r.json();if(!r.ok)throw Error(d.detail||"Request failed");
   const x=d.result;results.push({symbol:pairs[i],signal:x.signal,score:Number(x.score??0),note:x.note||""});
  }catch(e){results.push({symbol:pairs[i],signal:"ERROR",score:0,note:e.message});}
 }
 results.sort((a,b)=>b.score-a.score);
 out.innerHTML=`<b>20-pair scan complete · ${tf}</b><p class="muted tiny">Ranked by the demo rule score; not a probability of profit.</p>`+results.map((x,i)=>`<div class="pair" style="display:flex;justify-content:space-between;gap:8px"><span>${String(i+1).padStart(2,"0")} · ${x.symbol.replace("USDT","/USDT")}</span><b>${x.signal}</b><span>${x.score?x.score.toFixed(0):"—"}</span></div>`).join("");
 btn.disabled=false;
};
