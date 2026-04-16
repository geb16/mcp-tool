CUSTOMER_HTML = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Enterprise Support Chat</title>
  <style>
    body{margin:0;background:#f5f8fb;font-family:Segoe UI,Arial,sans-serif;color:#12212d}
    .wrap{max-width:820px;margin:0 auto;padding:20px}
    .card{background:#fff;border:1px solid #d8e2ea;border-radius:14px;box-shadow:0 10px 24px rgba(20,33,42,.08)}
    .head{padding:16px 18px;border-bottom:1px solid #e6edf2}
    .title{margin:0;font-size:1.15rem}
    .policy{margin:8px 0 0;color:#526474;font-size:.9rem}
    .chat{height:460px;overflow:auto;padding:14px;background:#f9fcff}
    .b{max-width:84%;margin:8px 0;padding:10px 12px;border-radius:10px;white-space:pre-wrap;line-height:1.35}
    .u{margin-left:auto;background:#dff1ff;border:1px solid #bee5ff}
    .a{background:#eef8f4;border:1px solid #cde8df}
    .e{background:#fff1eb;border:1px solid #ffd8cb;color:#a73416}
    .row{display:grid;grid-template-columns:1fr auto;gap:8px;padding:12px;border-top:1px solid #e6edf2}
    textarea,button{font:inherit;border-radius:10px;border:1px solid #d8e2ea}
    textarea{padding:10px;resize:vertical;min-height:64px}
    button{padding:0 18px;background:#0f766e;color:#fff;border:0;font-weight:600;cursor:pointer}
    button:disabled{opacity:.65;cursor:not-allowed}
  </style>
</head>
<body>
  <main class=\"wrap\">
    <section class=\"card\">
      <div class=\"head\">
        <h1 class=\"title\">Enterprise Support</h1>
        <p class=\"policy\">GDPR notice: chats may be recorded for quality/security monitoring. Please avoid abusive language; staff safety and respectful conduct are enforced.</p>
      </div>
      <div id=\"chat\" class=\"chat\"></div>
      <div class=\"row\">
        <textarea id=\"msg\" placeholder=\"Type your request...\"></textarea>
        <button id=\"send\">Send</button>
      </div>
    </section>
  </main>

  <script>
    const chatEl = document.getElementById('chat');
    const msgEl = document.getElementById('msg');
    const sendEl = document.getElementById('send');
    const SESSION_KEY = 'customer_session_id';
    const LAST_MSG_KEY = 'customer_last_message_id';
    const POLL_INTERVAL_MS = 2500;
    let pollTimer = null;

    function bubble(text, cls){const d=document.createElement('div');d.className=`b ${cls}`;d.textContent=text;chatEl.appendChild(d);chatEl.scrollTop=chatEl.scrollHeight;}
    function sessionId(){return sessionStorage.getItem(SESSION_KEY)||''}
    function setSession(id){if(id)sessionStorage.setItem(SESSION_KEY,id)}
    function lastMessageId(){return Number(sessionStorage.getItem(LAST_MSG_KEY)||'0')||0}
    function setLastMessageId(v){sessionStorage.setItem(LAST_MSG_KEY,String(Math.max(0,Number(v)||0)))}

    async function syncHistory(){
      const sid=sessionId();
      if(!sid)return;
      try{
        const params=new URLSearchParams({session_id:sid,after_id:String(lastMessageId())});
        const res=await fetch(`/portal/api/customer/history?${params.toString()}`);
        const data=await res.json();
        if(!res.ok)return;
        const messages=Array.isArray(data.messages)?data.messages:[];
        for(const m of messages){
          if(m.role==='user')bubble(m.content,'u');
          else if(m.role==='assistant')bubble(m.content,'a');
          else bubble(m.content,'a');
        }
        if(typeof data.last_message_id==='number')setLastMessageId(data.last_message_id);
      }catch(_err){
        // Keep polling silently; transient failures should not interrupt the chat UX.
      }
    }

    async function send(){
      const message=msgEl.value.trim();
      if(!message||sendEl.disabled)return;
      bubble(message,'u');
      msgEl.value='';
      sendEl.disabled=true;
      try{
        const res=await fetch('/portal/api/customer/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,session_id:sessionId()})});
        const data=await res.json();
        if(!res.ok){bubble(`Error: ${data.error||'request failed'}`,'e');}
        else{
          const previousSession=sessionId();
          if(!previousSession||previousSession!==data.session_id){setLastMessageId(0);}
          setSession(data.session_id);
          bubble(data.answer||'(empty response)','a');
          if(typeof data.assistant_message_id==='number'){
            setLastMessageId(Math.max(lastMessageId(),data.assistant_message_id));
          }
        }
      }catch(err){bubble(`Error: ${err}`,'e');}
      finally{
        sendEl.disabled=false;
        msgEl.focus();
        await syncHistory();
      }
    }

    sendEl.addEventListener('click',send);
    msgEl.addEventListener('keydown',(e)=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey))send();});
    if(sessionId()){syncHistory();}
    else{setLastMessageId(0);bubble('Hello. I can help with order status and support requests.','a');}
    pollTimer=setInterval(()=>{void syncHistory();},POLL_INTERVAL_MS);
  </script>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Enterprise Admin Console</title>
  <style>
    body{margin:0;background:#0f172a;color:#e2e8f0;font-family:Segoe UI,Arial,sans-serif}
    .wrap{max-width:1300px;margin:0 auto;padding:16px}
    .head{display:grid;grid-template-columns:2fr 1fr 1fr 1fr auto auto;gap:8px;margin-bottom:12px}
    input,select,button{font:inherit;border-radius:8px;border:1px solid #334155;padding:9px;background:#111b31;color:#e2e8f0}
    button{background:#0f766e;border:0;font-weight:600;cursor:pointer}
    .grid{display:grid;grid-template-columns:1.2fr 1fr;gap:12px}
    .card{background:#111b31;border:1px solid #243244;border-radius:12px;padding:12px}
    h2,h3{margin:0 0 8px}
    pre{background:#0b1222;border:1px solid #243244;border-radius:8px;padding:8px;max-height:190px;overflow:auto;color:#c7d2fe;font-size:.78rem}
    table{width:100%;border-collapse:collapse;font-size:.82rem}
    th,td{padding:6px;border-bottom:1px solid #223044;vertical-align:top}
    th{text-align:left;color:#93c5fd}
    .table{max-height:220px;overflow:auto;border:1px solid #243244;border-radius:8px}
    .row-btn{display:flex;gap:6px}
    .ghost{background:#1e293b}
    .ok{color:#86efac}.warn{color:#fbbf24}.bad{color:#fca5a5}
  </style>
</head>
<body>
  <main class=\"wrap\">
    <div class=\"head\">
      <input id=\"admin-key\" type=\"password\" placeholder=\"Admin API Key\" />
      <input id=\"tenant\" value=\"tenant-a\" placeholder=\"tenant\" />
      <select id=\"role\"><option>support_agent</option><option selected>support_manager</option><option>admin</option></select>
      <button id=\"save-role\">Save Agent Role</button>
      <button id=\"refresh\" class=\"ghost\">Refresh</button>
      <span id=\"status\" class=\"warn\">Disconnected</span>
    </div>

    <div class=\"grid\">
      <section class=\"card\">
        <h2>Pending Approvals</h2>
        <div class=\"table\"><table id=\"approvals\"></table></div>
        <h3 style=\"margin-top:10px\">Tool Audit Events</h3>
        <pre id=\"audit\">loading...</pre>
      </section>

      <section class=\"card\">
        <h2>System Summary</h2>
        <h3>Metrics</h3><pre id=\"metrics\">loading...</pre>
        <h3>Orders</h3><div class=\"table\"><table id=\"orders\"></table></div>
        <h3>Refunds</h3><div class=\"table\"><table id=\"refunds\"></table></div>
        <h3>Redis Cache Keys</h3><pre id=\"cache\">loading...</pre>
      </section>
    </div>
  </main>

  <script>
    const el=(id)=>document.getElementById(id);
    const adminKey=el('admin-key'); const tenant=el('tenant'); const role=el('role');
    const approvals=el('approvals'); const metrics=el('metrics'); const orders=el('orders'); const refunds=el('refunds'); const cache=el('cache'); const audit=el('audit'); const status=el('status');

    function headers(){const key=adminKey.value.trim(); return {'Content-Type':'application/json','x-admin-api-key':key,'x-api-key':key,'x-role':'admin','x-tenant-id':tenant.value.trim()||'tenant-a'};}

    async function jfetch(url,opts={}){
      const res=await fetch(url,{...opts,headers:{...headers(),...(opts.headers||{})}});
      const data=await res.json();
      if(!res.ok) throw new Error(data.error||`HTTP ${res.status}`);
      return data;
    }

    function table(node, rows){
      if(!rows||!rows.length){node.innerHTML='<tr><td>No rows</td></tr>';return;}
      const cols=Object.keys(rows[0]);
      let h='<thead><tr>'+cols.map(c=>`<th>${c}</th>`).join('')+'</tr></thead><tbody>';
      for(const r of rows){h+='<tr>'+cols.map(c=>`<td>${typeof r[c]==='object'?JSON.stringify(r[c]):(r[c]??'')}</td>`).join('')+'</tr>';} h+='</tbody>'; node.innerHTML=h;
    }

    function approvalsTable(rows){
      if(!rows||!rows.length){approvals.innerHTML='<tr><td>No approvals</td></tr>';return;}
      let h='<thead><tr><th>approval_id</th><th>tool</th><th>status</th><th>execution</th><th>args</th><th>action</th></tr></thead><tbody>';
      for(const r of rows){
        const args=JSON.stringify(r.arguments||{});
        const exec=(r.execution_result&&typeof r.execution_result==='object')?JSON.stringify(r.execution_result):'-';
        const actions=r.status==='pending'?`<div class=\"row-btn\"><button onclick=\"decide('${r.approval_id}',true)\">Approve</button><button class=\"ghost\" onclick=\"decide('${r.approval_id}',false)\">Reject</button></div>`:'-';
        h+=`<tr><td>${r.approval_id}</td><td>${r.tool_name}</td><td>${r.status}</td><td>${exec}</td><td>${args}</td><td>${actions}</td></tr>`;
      }
      h+='</tbody>'; approvals.innerHTML=h;
    }

    async function load(){
      try{
        const data=await jfetch('/portal/api/admin/state');
        status.textContent='Connected'; status.className='ok';
        role.value=data.assigned_agent_role||role.value;
        approvalsTable(data.approvals||[]);
        metrics.textContent=(data.metrics||[]).join('\\n')||'No metrics.';
        table(orders,data.orders||[]); table(refunds,data.refunds||[]);
        cache.textContent=(data.redis_cache_keys||[]).join('\\n')||'No keys';
        audit.textContent=(data.tool_audit_events||[]).map(e=>`${e.timestamp} ${e.tool_name} ${e.status} ${e.role}`).join('\\n')||'No events';
      }catch(err){status.textContent=`Error: ${err.message||err}`; status.className='bad';}
    }

    async function saveRole(){
      try{await jfetch('/portal/api/admin/agent-role',{method:'POST',body:JSON.stringify({assigned_role:role.value})}); await load();}
      catch(err){alert(err.message||err);}
    }

    window.decide=async function(approvalId, approve){
      try{await jfetch(`/portal/api/admin/approvals/${approvalId}/decision`,{method:'POST',body:JSON.stringify({approve,decision_note: approve?'Approved by staff':'Rejected by staff'})}); await load();}
      catch(err){alert(err.message||err);}
    }

    el('refresh').addEventListener('click',load); el('save-role').addEventListener('click',saveRole);
    setInterval(load,5000); load();
  </script>
</body>
</html>
"""
