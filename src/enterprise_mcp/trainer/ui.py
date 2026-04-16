TRAINER_HTML = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>MCP Day-1 Lab</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
    :root { --bg:#f3f6f8; --card:#fff; --ink:#14212a; --muted:#5a6a77; --accent:#0f766e; --danger:#c2410c; --line:#d9e2e8; --ok:#166534; --warn:#92400e; --shadow:0 14px 32px rgba(20,33,42,.1); }
    *{box-sizing:border-box} body{margin:0;min-height:100vh;background:radial-gradient(circle at 15% 20%, rgba(14,165,233,.15), transparent 32%),radial-gradient(circle at 85% 0%, rgba(15,118,110,.16), transparent 28%),var(--bg);color:var(--ink);font-family:"IBM Plex Sans","Segoe UI",sans-serif;padding:24px}
    .shell{max-width:1280px;margin:0 auto;display:grid;gap:18px}.hero{background:linear-gradient(120deg,#133a4a,#1a5f6d);color:#f3fbff;border-radius:18px;box-shadow:var(--shadow);padding:20px}
    .hero h1{margin:0;font-size:1.45rem}.hero p{margin:8px 0 0;color:#d6eef7}.grid{display:grid;grid-template-columns:1.25fr 1fr;gap:18px}
    .card{background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);overflow:hidden}.card-head{padding:14px 16px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:10px}
    .card-body{padding:14px 16px}.meta{color:var(--muted);font-size:.87rem}.badge{display:inline-flex;align-items:center;gap:6px;padding:4px 8px;border-radius:999px;font-size:.78rem;font-weight:600;border:1px solid var(--line);background:#f8fbfc;color:#334b5c}
    .badge.ok{background:#ebf9ef;border-color:#c8f0d4;color:var(--ok)}.badge.warn{background:#fff4e6;border-color:#ffd9b5;color:var(--warn)}
    .toolbar{display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:10px;margin-bottom:10px}.toolbar-secondary{display:grid;grid-template-columns:1fr auto;gap:10px;margin-bottom:12px}
    .toolbar-note{font-size:.78rem;color:var(--muted);margin-bottom:12px}.prompt-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
    input,select,button,textarea{font:inherit;border-radius:10px;border:1px solid var(--line);padding:10px 12px;background:#fff;color:var(--ink)}
    button{border:0;background:linear-gradient(120deg,var(--accent),#145f8d);color:#fff;cursor:pointer;font-weight:600}button:disabled{opacity:.72;cursor:not-allowed}
    button.ghost{background:#f8fbfc;color:#0f3646;border:1px solid var(--line)}.prompt-btn{background:#f2fbff;color:#0b4f74;border:1px solid #cce8f9;font-size:.86rem;padding:8px 10px}
    .chat-window{height:360px;overflow:auto;border:1px solid var(--line);border-radius:12px;padding:10px;background:#f9fcfe}.bubble{max-width:88%;margin:9px 0;padding:10px 12px;border-radius:12px;line-height:1.4;white-space:pre-wrap}
    .user{margin-left:auto;background:#e3f4ff;border:1px solid #c7e6ff}.assistant{background:#eef8f6;border:1px solid #c8e9e3}.error{background:#fff1eb;border:1px solid #ffd9cb;color:var(--danger)}
    .input-row{display:grid;grid-template-columns:1fr auto;gap:10px;margin-top:10px}.pane{margin-bottom:12px}.pane h3{margin:0 0 8px;font-size:.88rem;text-transform:uppercase;letter-spacing:.05em;color:#304758}
    pre{margin:0;max-height:170px;overflow:auto;border:1px solid var(--line);border-radius:10px;padding:10px;background:#0f172a;color:#cbe6ff;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.78rem}
    .table-wrap{border:1px solid var(--line);border-radius:10px;overflow:auto;max-height:180px;background:#fff}table{width:100%;border-collapse:collapse;font-size:.83rem}
    th,td{padding:8px;border-bottom:1px solid #edf2f5;text-align:left;vertical-align:top}th{position:sticky;top:0;background:#f8fbfc;z-index:1;color:#3d5565}
    .foot{font-size:.8rem;color:var(--muted);display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}
    @media (max-width:980px){.grid{grid-template-columns:1fr}.toolbar{grid-template-columns:1fr 1fr}.toolbar-secondary{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <main class=\"shell\">
    <section class=\"hero\"><h1>MCP Day-1 Lab: Chat + Observability + Data Activity</h1><p>Run prompts, trigger tools, and watch Prometheus metrics, PostgreSQL rows, and Redis cache keys update in real time.</p></section>
    <section class=\"grid\">
      <article class=\"card\">
        <div class=\"card-head\"><h2>Model Chat</h2><span class=\"meta\" id=\"chat-meta\">Ready</span></div>
        <div class=\"card-body\">
          <div class=\"toolbar\">
            <input id=\"tenant-id\" value=\"tenant-a\" placeholder=\"tenant id\" />
            <select id=\"role\"><option value=\"viewer\">viewer</option><option value=\"support_agent\">support_agent</option><option value=\"support_manager\" selected>support_manager</option><option value=\"admin\">admin</option></select>
            <input id=\"refresh-seconds\" type=\"number\" min=\"2\" value=\"4\" />
            <button class=\"ghost\" id=\"refresh-btn\">Refresh Now</button>
          </div>
          <div class=\"toolbar-secondary\"><input id=\"openai-api-key\" type=\"password\" placeholder=\"Optional runtime OpenAI API key (session only)\" /><button class=\"ghost\" id=\"clear-key-btn\">Clear Key</button></div>
          <div class=\"toolbar-note\" id=\"key-meta\">Using server env API key if configured.</div>
          <div class=\"prompt-row\">
            <button class=\"prompt-btn\" data-prompt=\"Check order status for ORD-1002 and explain if refundable.\">Read prompt</button>
            <button class=\"prompt-btn\" data-prompt=\"Create refund request for ORD-1002 with reason: wrong item delivered.\">Write prompt</button>
            <button class=\"prompt-btn\" id=\"direct-read-btn\">Direct Read Tool</button>
            <button class=\"prompt-btn\" id=\"direct-write-btn\">Direct Write Tool</button>
          </div>
          <div id=\"chat-window\" class=\"chat-window\"></div>
          <div class=\"input-row\"><textarea id=\"message\" rows=\"3\" placeholder=\"Ask the model. Example: Check order ORD-1001 and then create refund for ORD-1002.\"></textarea><button id=\"send-btn\">Send</button></div>
        </div>
      </article>
      <article class=\"card\">
        <div class=\"card-head\"><h2>Live Observability + Data</h2><div style=\"display:flex;gap:8px;align-items:center;\"><span class=\"badge warn\" id=\"connection-badge\">Connecting</span><span class=\"meta\" id=\"state-meta\">Auto refresh on</span></div></div>
        <div class=\"card-body\">
          <section class=\"pane\"><h3>Prometheus Signals</h3><pre id=\"metrics-pre\">loading...</pre></section>
          <section class=\"pane\"><h3>Orders (PostgreSQL)</h3><div class=\"table-wrap\"><table id=\"orders-table\"></table></div></section>
          <section class=\"pane\"><h3>Refund Requests (PostgreSQL)</h3><div class=\"table-wrap\"><table id=\"refunds-table\"></table></div></section>
          <section class=\"pane\"><h3>Redis Cache Keys</h3><pre id=\"cache-pre\">loading...</pre></section>
        </div>
      </article>
    </section>
    <footer class=\"foot\"><span>Tip: use <code>Direct Write Tool</code> with role <code>viewer</code> to prove RBAC denial.</span><span id=\"last-refresh\">Last refresh: pending</span></footer>
  </main>
  <script>
    const chatWindow = document.getElementById('chat-window');
    const chatMeta = document.getElementById('chat-meta');
    const stateMeta = document.getElementById('state-meta');
    const connectionBadge = document.getElementById('connection-badge');
    const sendBtn = document.getElementById('send-btn');
    const refreshBtn = document.getElementById('refresh-btn');
    const messageInput = document.getElementById('message');
    const tenantInput = document.getElementById('tenant-id');
    const roleSelect = document.getElementById('role');
    const metricsPre = document.getElementById('metrics-pre');
    const cachePre = document.getElementById('cache-pre');
    const ordersTable = document.getElementById('orders-table');
    const refundsTable = document.getElementById('refunds-table');
    const refreshSecondsInput = document.getElementById('refresh-seconds');
    const lastRefresh = document.getElementById('last-refresh');
    const openaiKeyInput = document.getElementById('openai-api-key');
    const clearKeyBtn = document.getElementById('clear-key-btn');
    const keyMeta = document.getElementById('key-meta');
    const directReadBtn = document.getElementById('direct-read-btn');
    const directWriteBtn = document.getElementById('direct-write-btn');

    const SESSION_API_KEY = 'trainer_openai_api_key';
    let timer = null;
    let isSending = false;
    let isRefreshing = false;

    function esc(s){return s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');}
    function addBubble(text, cls){const el=document.createElement('div');el.className=`bubble ${cls}`;el.innerHTML=esc(text);chatWindow.appendChild(el);chatWindow.scrollTop=chatWindow.scrollHeight;}
    function renderTable(table, rows){if(!rows||!rows.length){table.innerHTML='<tr><td>No rows</td></tr>';return;}const cols=Object.keys(rows[0]);let html='<thead><tr>';for(const c of cols)html+=`<th>${esc(c)}</th>`;html+='</tr></thead><tbody>';for(const row of rows){html+='<tr>';for(const c of cols){const v=row[c]==null?'':String(row[c]);html+=`<td>${esc(v)}</td>`;}html+='</tr>';}html+='</tbody>';table.innerHTML=html;}
    function setConn(ok,label){connectionBadge.classList.remove('ok','warn');connectionBadge.classList.add(ok?'ok':'warn');connectionBadge.textContent=label;}
    function updateSendState(){sendBtn.disabled=isSending||!messageInput.value.trim();}
    function updateKeyMeta(hasServer=false){const runtime=openaiKeyInput.value.trim();if(runtime){keyMeta.textContent='Runtime key set in this browser session.';return;}if(hasServer){keyMeta.textContent='Using server env OPENAI_API_KEY.';return;}keyMeta.textContent='No key detected. Add runtime key above or set OPENAI_API_KEY in server env.';}

    async function fetchJson(url, options={}, timeoutMs=9000, retries=0){let attempt=0;while(true){const ctrl=new AbortController();const t=setTimeout(()=>ctrl.abort(),timeoutMs);try{const res=await fetch(url,{...options,signal:ctrl.signal});const data=await res.json();if(!res.ok)throw new Error(data.error||`HTTP ${res.status}`);return data;}catch(err){if(attempt>=retries)throw err;await new Promise(r=>setTimeout(r,350*(attempt+1)));attempt+=1;}finally{clearTimeout(t);}}}

    async function refreshState(){if(isRefreshing)return;isRefreshing=true;try{const data=await fetchJson('/trainer/api/state',{},9000,1);metricsPre.textContent=(data.metrics||[]).join('\\n')||'No metric lines yet.';cachePre.textContent=(data.redis_cache_keys||[]).join('\\n')||'No cache keys.';renderTable(ordersTable,data.orders||[]);renderTable(refundsTable,data.refunds||[]);updateKeyMeta(!!data.has_openai_api_key);lastRefresh.textContent=`Last refresh: ${new Date().toLocaleTimeString()}`;setConn(true,'Connected');}catch(err){setConn(false,'Disconnected');stateMeta.textContent=`State refresh failed: ${err.message||err}`;}finally{isRefreshing=false;}}

    function toolTraceText(trace){if(!trace||!trace.length)return 'No tool calls executed in this response.';return trace.map((t,i)=>`${i+1}. ${t.tool}(${JSON.stringify(t.arguments)}) => ${JSON.stringify(t.result)}`).join('\\n');}

    async function sendMessage(){const message=messageInput.value.trim();if(!message||isSending)return;addBubble(message,'user');messageInput.value='';isSending=true;updateSendState();sendBtn.textContent='Sending...';chatMeta.textContent='Model running...';try{const data=await fetchJson('/trainer/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,tenant_id:tenantInput.value.trim()||'tenant-a',role:roleSelect.value,openai_api_key:openaiKeyInput.value.trim()})},32000,0);addBubble(data.answer||'(empty response)','assistant');addBubble(`Tool trace:\n${toolTraceText(data.tool_trace)}`,'assistant');chatMeta.textContent=`Model: ${data.model}`;}catch(err){addBubble(`Error: ${err.message||err}`,'error');}finally{isSending=false;sendBtn.textContent='Send';updateSendState();await refreshState();}}

    async function runDirectTool(toolName, args){try{const data=await fetchJson('/trainer/api/direct-tool',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tool_name:toolName,arguments:args,tenant_id:tenantInput.value.trim()||'tenant-a',role:roleSelect.value})},12000,0);addBubble(`Direct ${toolName} result:\n${JSON.stringify(data.result,null,2)}`,'assistant');}catch(err){addBubble(`Direct tool error: ${err.message||err}`,'error');}finally{await refreshState();}}

    function restartTimer(){if(timer)clearInterval(timer);const sec=Math.max(2,Number(refreshSecondsInput.value||4));timer=setInterval(refreshState,sec*1000);stateMeta.textContent=`Auto refresh: every ${sec}s`;}
    function loadRuntimeKey(){const s=sessionStorage.getItem(SESSION_API_KEY)||'';openaiKeyInput.value=s;updateKeyMeta(false);} 
    function saveRuntimeKey(){const v=openaiKeyInput.value.trim();if(v)sessionStorage.setItem(SESSION_API_KEY,v);else sessionStorage.removeItem(SESSION_API_KEY);updateKeyMeta(false);}

    document.querySelectorAll('.prompt-btn[data-prompt]').forEach((btn)=>{btn.addEventListener('click',()=>{messageInput.value=btn.dataset.prompt;messageInput.focus();updateSendState();});});
    sendBtn.addEventListener('click',sendMessage);refreshBtn.addEventListener('click',refreshState);refreshSecondsInput.addEventListener('change',restartTimer);messageInput.addEventListener('input',updateSendState);
    messageInput.addEventListener('keydown',(e)=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey))sendMessage();});
    openaiKeyInput.addEventListener('input',saveRuntimeKey);clearKeyBtn.addEventListener('click',()=>{openaiKeyInput.value='';saveRuntimeKey();});
    directReadBtn.addEventListener('click',()=>runDirectTool('get_order_status_tool',{order_id:'ORD-1002'}));
    directWriteBtn.addEventListener('click',()=>runDirectTool('create_refund_request',{order_id:'ORD-1002',reason:'wrong item delivered',approved_by_human:true}));

    addBubble('Lab ready. Use Direct Write Tool with viewer role to validate RBAC block.','assistant');
    loadRuntimeKey();updateSendState();refreshState();restartTimer();
  </script>
</body>
</html>
"""
