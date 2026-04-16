
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
      let h='<thead><tr><th>approval_id</th><th>tool</th><th>status</th><th>args</th><th>action</th></tr></thead><tbody>';
      for(const r of rows){
        const args=JSON.stringify(r.arguments||{});
        const actions=r.status==='pending'?`<div class="row-btn"><button onclick="decide('${r.approval_id}',true)">Approve</button><button class="ghost" onclick="decide('${r.approval_id}',false)">Reject</button></div>`:'-';
        h+=`<tr><td>${r.approval_id}</td><td>${r.tool_name}</td><td>${r.status}</td><td>${args}</td><td>${actions}</td></tr>`;
      }
      h+='</tbody>'; approvals.innerHTML=h;
    }

    async function load(){
      try{
        const data=await jfetch('/portal/api/admin/state');
        status.textContent='Connected'; status.className='ok';
        role.value=data.assigned_agent_role||role.value;
        approvalsTable(data.approvals||[]);
        metrics.textContent=(data.metrics||[]).join('\n')||'No metrics.';
        table(orders,data.orders||[]); table(refunds,data.refunds||[]);
        cache.textContent=(data.redis_cache_keys||[]).join('\n')||'No keys';
        audit.textContent=(data.tool_audit_events||[]).map(e=>`${e.timestamp} ${e.tool_name} ${e.status} ${e.role}`).join('\n')||'No events';
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
  
