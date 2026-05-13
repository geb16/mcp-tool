
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

    const SESSION_API_KEY = 'trainer_openai_api_key';
    let timer = null;
    let isSending = false;
    let isRefreshing = false;

    //we escape HTML in messages and table cells to prevent XSS, since these can contain arbitrary content from the model or user input
    // replacing &, <, >, ", ' with their HTML entities to ensure they are displayed as text rather than interpreted as HTML tags or attributes
    //e.g. if the model outputs a message like: `<script>alert('XSS')</script>` it will be displayed safely(as e.g. &lt;script&gt;alert('XSS')&lt;/script&gt;) in the chat window instead of executing as a script
    // this is a simple implementation and may not cover all edge cases, but it should be sufficient for basic usage in this trainer interface
    function escapeHtml(s) {
      return s
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    function addBubble(text, cls) {
      const el = document.createElement('div');
      el.className = `bubble ${cls}`;
      el.innerHTML = escapeHtml(text);
      chatWindow.appendChild(el);
      chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    function renderTable(table, rows) {
      if (!rows || !rows.length) {
        table.innerHTML = '<tr><td>No rows</td></tr>';
        return;
      }

      const columns = Object.keys(rows[0]);
      let html = '<thead><tr>';
      for (const col of columns) html += `<th>${escapeHtml(col)}</th>`;
      html += '</tr></thead><tbody>';

      for (const row of rows) {
        html += '<tr>';
        for (const col of columns) {
          const val = row[col] == null ? '' : String(row[col]);
          html += `<td>${escapeHtml(val)}</td>`;
        }
        html += '</tr>';
      }
      html += '</tbody>';
      table.innerHTML = html;
    }

    function setConnection(status, label) {
      connectionBadge.classList.remove('ok', 'warn');
      connectionBadge.classList.add(status === 'ok' ? 'ok' : 'warn');
      connectionBadge.textContent = label;
    }

    function updateSendState() {
      const hasMessage = !!messageInput.value.trim();
      sendBtn.disabled = isSending || !hasMessage;
    }

    function updateKeyMeta(hasServerKey = false) {
      const runtime = openaiKeyInput.value.trim();
      if (runtime) {
        keyMeta.textContent = 'Runtime key set in this browser session.';
        return;
      }
      if (hasServerKey) {
        keyMeta.textContent = 'Using server env OPENAI_API_KEY.';
        return;
      }
      keyMeta.textContent = 'No key detected. Add runtime key above or set OPENAI_API_KEY in server env.';
    }

    async function fetchJson(url, options = {}, timeoutMs = 9000, retries = 0) {
      let attempt = 0;
      while (true) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), timeoutMs);
        try {
          const merged = { ...options, signal: controller.signal };
          const res = await fetch(url, merged);
          const data = await res.json();
          if (!res.ok) {
            throw new Error(data.error || `HTTP ${res.status}`);
          }
          return data;
        } catch (err) {
          if (attempt >= retries) throw err;
          await new Promise((resolve) => setTimeout(resolve, 350 * (attempt + 1)));
          attempt += 1;
        } finally {
          clearTimeout(timeout);
        }
      }
    }

    async function refreshState() {
      if (isRefreshing) return;
      isRefreshing = true;
      try {
        const data = await fetchJson('/trainer/api/state', {}, 9000, 1);

        metricsPre.textContent = (data.metrics || []).join('\n') || 'No metric lines yet.';
        cachePre.textContent = (data.redis_cache_keys || []).join('\n') || 'No cache keys.';
        renderTable(ordersTable, data.orders || []);
        renderTable(refundsTable, data.refunds || []);
        updateKeyMeta(!!data.has_openai_api_key);

        const now = new Date().toLocaleTimeString();
        lastRefresh.textContent = `Last refresh: ${now}`;
        setConnection('ok', 'Connected');
      } catch (err) {
        setConnection('warn', 'Disconnected');
        stateMeta.textContent = `State refresh failed: ${err.message || err}`;
      } finally {
        isRefreshing = false;
      }
    }

    async function sendMessage() {
      const message = messageInput.value.trim();
      if (!message || isSending) return;

      addBubble(message, 'user');
      messageInput.value = '';
      isSending = true;
      updateSendState();
      sendBtn.textContent = 'Sending...';
      chatMeta.textContent = 'Model running...';

      try {
        const data = await fetchJson(
          '/trainer/api/chat',
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message,
              tenant_id: tenantInput.value.trim() || 'tenant-a',
              role: roleSelect.value,
              openai_api_key: openaiKeyInput.value.trim(),
            }),
          },
          32000,
          0,
        );

        addBubble(data.answer || '(empty response)', 'assistant');
        chatMeta.textContent = `Model: ${data.model}`;
      } catch (err) {
        addBubble(`Error: ${err.message || err}`, 'error');
      } finally {
        isSending = false;
        sendBtn.textContent = 'Send';
        updateSendState();
        await refreshState();
      }
    }

    function restartTimer() {
      if (timer) clearInterval(timer);
      const sec = Math.max(2, Number(refreshSecondsInput.value || 4));
      timer = setInterval(refreshState, sec * 1000);
      stateMeta.textContent = `Auto refresh: every ${sec}s`;
    }

    function loadRuntimeKey() {
      const saved = sessionStorage.getItem(SESSION_API_KEY) || '';
      openaiKeyInput.value = saved;
      updateKeyMeta(false);
    }

    function saveRuntimeKey() {
      const value = openaiKeyInput.value.trim();
      if (value) {
        sessionStorage.setItem(SESSION_API_KEY, value);
      } else {
        sessionStorage.removeItem(SESSION_API_KEY);
      }
      updateKeyMeta(false);
    }

    document.querySelectorAll('.prompt-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        messageInput.value = btn.dataset.prompt;
        messageInput.focus();
        updateSendState();
      });
    });

    sendBtn.addEventListener('click', sendMessage);
    refreshBtn.addEventListener('click', refreshState);
    refreshSecondsInput.addEventListener('change', restartTimer);

    messageInput.addEventListener('input', updateSendState);
    messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) sendMessage();
    });

    openaiKeyInput.addEventListener('input', saveRuntimeKey);
    clearKeyBtn.addEventListener('click', () => {
      openaiKeyInput.value = '';
      saveRuntimeKey();
    });

    addBubble('Lab ready. Start with "Read demo" and inspect metrics/cache.', 'assistant');
    loadRuntimeKey();
    updateSendState();
    refreshState();
    restartTimer();
  
