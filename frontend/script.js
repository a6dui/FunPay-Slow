const API_BASE = "https://funpay-slow.onrender.com";

// --- Global App State ---
window.App = {
    user: JSON.parse(localStorage.getItem('funpay_user')) || null,
    
    init() {
        console.log("🐌 FunPay Slow v2.4.1 Initializing...");
        this.ensureLoginOverlay();
        this.updateUI();
        if (this.user) {
            this.syncUser();
        }
        this.initTabs();
    },

    // --- Admin Functions ---
    async fetchAdminStats() {
        if (!this.user) return null;
        try {
            const res = await fetch(`${API_BASE}/api/admin/stats?admin_id=${this.user.user_id}`);
            return await res.json();
        } catch (e) { return null; }
    },

    async fetchAdminUsers() {
        if (!this.user) return [];
        try {
            const res = await fetch(`${API_BASE}/api/admin/users?admin_id=${this.user.user_id}`);
            return await res.json();
        } catch (e) { return []; }
    },

    async fetchAdminPayments() {
        // Mock or actual API call for payments
        return [];
    },

    async adminUserAction(targetUserId, action, plan = "none", days = 0) {
        if (!this.user) return null;
        try {
            const res = await fetch(`${API_BASE}/api/admin/user/action`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    admin_id: String(this.user.user_id),
                    target_user_id: String(targetUserId),
                    action: action,
                    plan: plan,
                    duration_days: days
                })
            });
            return await res.json();
        } catch (e) { return null; }
    },

    async updateUserBalance(targetUserId, amount) {
        // Reuse adminUserAction or a specific balance endpoint if added
        // For now, let's assume we use a specific balance update for legacy compat
        try {
            const res = await fetch(`${API_BASE}/api/admin/user/action`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    admin_id: String(this.user.user_id),
                    target_user_id: String(targetUserId),
                    action: "update_balance", // Fixed comment
                    balance_delta: amount
                })
            });
            return await res.json();
        } catch (e) { return null; }
    },

    showAddAccountModal() {
        const modal = document.getElementById('add-account-modal');
        if (modal) modal.style.display = 'flex';
    },

    async addNewAccount() {
        const name = document.getElementById('acc-name').value;
        const cookie = document.getElementById('acc-cookie').value;
        const proxy = document.getElementById('acc-proxy').value;

        if (!name || !cookie) return alert("Введите имя и куки!");

        try {
            const res = await fetch(`${API_BASE}/api/accounts/add`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: String(this.user.user_id),
                    name: name,
                    cookie: cookie,
                    proxy: proxy
                })
            });

            if (res.ok) {
                alert("✅ Аккаунт добавлен!");
                document.getElementById('add-account-modal').style.display = 'none';
                this.loadAccountsList();
            } else {
                alert("Ошибка при добавлении");
            }
        } catch (e) { alert("Ошибка связи с сервером"); }
    },

    async loadAccountsList() {
        if (!this.user) return;
        const body = document.getElementById('accounts-list-body');
        if (!body) return;

        try {
            const res = await fetch(`${API_BASE}/api/accounts/list?user_id=${this.user.user_id}`);
            const accounts = await res.json();
            
            if (accounts.length === 0) {
                body.innerHTML = '<tr><td colspan="4" style="padding: 40px; text-align: center; color: #444; font-size: 0.9rem;">Аккаунты не добавлены.</td></tr>';
                return;
            }

            body.innerHTML = accounts.map(acc => `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.02); transition: 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.01)'" onmouseout="this.style.background='transparent'">
                    <td style="padding: 20px;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="width: 40px; height: 40px; background: rgba(255,255,255,0.03); border-radius: 12px; display: flex; align-items: center; justify-content: center; color: var(--accent);">
                                <i class="fas fa-user-circle"></i>
                            </div>
                            <div>
                                <div style="font-weight: 700; color: #fff;">${acc.name}</div>
                                <div style="font-size: 0.75rem; color: #444;">ID: ${acc.id}</div>
                            </div>
                        </div>
                    </td>
                    <td style="padding: 20px; color: #888; font-family: monospace; font-size: 0.85rem;">${acc.proxy || '<span style="color: #333;">—</span>'}</td>
                    <td style="padding: 20px;">
                        <span style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; background: rgba(16, 185, 129, 0.1); color: #10b981; border-radius: 100px; font-size: 0.75rem; font-weight: 800; border: 1px solid rgba(16, 185, 129, 0.1);">
                            <div style="width: 6px; height: 6px; background: #10b981; border-radius: 50%;"></div>
                            АКТИВЕН
                        </span>
                    </td>
                    <td style="padding: 20px; text-align: right;">
                        <button class="btn-outline" onclick="window.App.deleteAccount(${acc.id})" style="width: 36px; height: 36px; border-radius: 10px; display: inline-flex; align-items: center; justify-content: center; color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.1); background: rgba(244, 63, 94, 0.05);">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } catch (e) { console.error(e); }
    },

    syncUserUI() {
        if (!this.user) return;
        
        // Update basic info
        const nameEls = [document.getElementById('user-name-large')];
        const initialEls = [document.getElementById('user-initial-large')];
        const idEls = [document.getElementById('user-id-display')];
        
        const firstName = this.user.first_name || 'User';
        nameEls.forEach(el => { if (el) el.textContent = firstName; });
        initialEls.forEach(el => { if (el) el.textContent = firstName[0].toUpperCase(); });
        idEls.forEach(el => { if (el) el.textContent = this.user.user_id; });

        // Registration Date
        const regDateEl = document.getElementById('registration-date');
        if (regDateEl && this.user.created_at) {
            const d = new Date(this.user.created_at * 1000);
            regDateEl.textContent = d.toLocaleDateString('ru-RU');
        }

        // Balance & Stats
        const balanceEls = [document.getElementById('profile-balance'), document.getElementById('btn-current-balance')];
        balanceEls.forEach(el => { if (el) el.textContent = Math.floor(this.user.balance || 0); });

        // Subscription Logic
        this.updateSubscriptionUI();
    },

    updateSubscriptionUI() {
        if (!this.user) return;
        
        const plan = (this.user.plan || 'NONE').toUpperCase();
        const badge = document.getElementById('user-plan-badge');
        if (badge) {
            badge.textContent = plan;
            badge.style.color = plan === 'FAST' ? '#10b981' : (plan === 'SLOW' ? '#3b82f6' : '#888');
        }

        const trialCard = document.getElementById('trial-card');
        const statusCard = document.getElementById('sub-status-card');
        
        if (plan === 'NONE') {
            if (trialCard) trialCard.style.display = 'flex';
            if (statusCard) statusCard.style.display = 'none';
        } else {
            if (trialCard) trialCard.style.display = 'none';
            if (statusCard) statusCard.style.display = 'block';
            
            // Calculate remaining time
            const now = Math.floor(Date.now() / 1000);
            const expiry = this.user.sub_end || (now + 86400 * 3); // Fallback for display
            const remaining = Math.max(0, expiry - now);
            const days = Math.ceil(remaining / 86400);
            
            const expiryDateEl = document.getElementById('sub-expiry-date');
            const daysRemainingEl = document.getElementById('sub-days-remaining');
            const progressBar = document.getElementById('sub-progress-bar');
            
            if (expiryDateEl) {
                const d = new Date(expiry * 1000);
                expiryDateEl.textContent = d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
            }
            
            if (daysRemainingEl) {
                daysRemainingEl.textContent = `${days} ${this.getPlural(days, ['день', 'дня', 'дней'])}`;
                daysRemainingEl.style.color = days < 3 ? '#f43f5e' : '#fbbf24';
            }
            
            if (progressBar) {
                const percent = Math.min(100, (days / 30) * 100);
                progressBar.style.width = `${percent}%`;
                progressBar.style.background = days < 3 ? 'linear-gradient(to right, #f43f5e, #991b1b)' : 'linear-gradient(to right, #fbbf24, #f43f5e)';
            }
        }
    },

    getPlural(n, forms) {
        return n % 10 == 1 && n % 100 != 11 ? forms[0] : (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20) ? forms[1] : forms[2]);
    },

    ensureLoginOverlay() {
        if (document.getElementById('login-overlay')) return;
        
        // Add CSS for the modal
        const style = document.createElement('style');
        style.textContent = `
            .login-overlay {
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0,0,0,0.85); backdrop-filter: blur(10px);
                display: flex; align-items: center; justify-content: center; z-index: 10000;
            }
            .login-box {
                background: #111; border: 1px solid rgba(255,255,255,0.1);
                padding: 40px; border-radius: 24px; width: 100%; max-width: 400px;
                position: relative; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
                animation: modalAppear 0.3s ease-out;
            }
            @keyframes modalAppear {
                from { opacity: 0; transform: scale(0.9); }
                to { opacity: 1; transform: scale(1); }
            }
            .btn-close-modal-new {
                position: absolute; top: -15px; right: -15px;
                width: 35px; height: 35px; border-radius: 50%;
                background: #f43f5e; color: white; border: none;
                display: flex; align-items: center; justify-content: center;
                cursor: pointer; font-size: 1.2rem; font-weight: bold;
                box-shadow: 0 4px 15px rgba(244, 63, 94, 0.4);
                transition: 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                z-index: 11000;
            }
            .btn-close-modal-new:hover {
                transform: scale(1.15) rotate(90deg);
                background: #fb7185;
            }
            .login-logo-circle {
                width: 60px; height: 60px; background: rgba(255,255,255,0.05);
                border-radius: 50%; display: flex; align-items: center; justify-content: center;
                margin: 0 auto 20px; font-size: 2rem;
            }
        `;
        document.head.appendChild(style);

        const overlay = document.createElement('div');
        overlay.id = 'login-overlay';
        overlay.className = 'login-overlay';
        overlay.style.display = 'none';
        overlay.innerHTML = `
            <div class="login-box" id="login-box-standard">
                <button class="btn-close-modal-new" onclick="document.getElementById('login-overlay').style.display='none'">&times;</button>
                <div class="login-logo-circle">🐌</div>
                <div class="login-header" style="text-align: center; margin-bottom: 30px;">
                    <h2 style="font-size: 1.5rem; color: white; margin-bottom: 10px;">Авторизация</h2>
                    <p style="color: #666; font-size: 0.9rem;">Выберите способ входа в систему</p>
                </div>
                <button class="btn-login-method telegram" id="btn-telegram-login-injected" style="width: 100%; padding: 18px; border-radius: 16px; border: none; background: linear-gradient(135deg, #0088cc, #00aaff); color: white; font-weight: 800; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 12px; box-shadow: 0 10px 20px -5px rgba(0, 136, 204, 0.4); transition: 0.3s;">
                    <i class="fab fa-telegram-plane"></i> Войти через Telegram
                </button>
                <div style="margin-top: 25px; font-size: 0.75rem; color: #444; text-align: center;">Безопасный вход через официальный API</div>
            </div>
            
            <div class="login-box" id="login-box-telegram" style="display: none;">
                <button class="btn-close-modal-new" onclick="document.getElementById('login-overlay').style.display='none'">&times;</button>
                <div class="login-logo-circle">🐌</div>
                <div class="login-header" style="text-align: center; margin-bottom: 20px;">
                    <h2 style="font-size: 1.5rem; color: white; margin-bottom: 10px;">Код доступа</h2>
                    <p style="color: #666; font-size: 0.9rem;">Отправьте этот код нашему боту</p>
                </div>
                <div class="tg-auth-container" style="text-align: center;">
                    <div class="tg-auth-code" id="tg-auth-code" style="font-size: 2.8rem; font-weight: 900; letter-spacing: 8px; color: #10b981; margin: 20px 0; font-family: 'Courier New', monospace; background: rgba(16, 185, 129, 0.05); padding: 15px; border-radius: 12px; border: 1px dashed rgba(16, 185, 129, 0.3);">------</div>
                    <a href="#" target="_blank" class="btn-primary" id="link-to-bot" style="width: 100%; justify-content: center; margin-top: 1.5rem; height: 55px; border-radius: 16px; font-weight: 800; background: #10b981; box-shadow: 0 10px 20px -5px rgba(16, 185, 129, 0.4);">
                        <i class="fab fa-telegram-plane"></i> Открыть бота
                    </a>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        
        const btn = document.getElementById('btn-telegram-login-injected');
        if (btn) btn.onclick = () => window.handleTelegramLogin();
    },
    
    async syncUser() {
        if (!this.user || !this.user.user_id) return;
        try {
            const res = await fetch(`${API_BASE}/api/user/subscription/${this.user.user_id}`);
            if (res.ok) {
                const fresh = await res.json();
                // Merge ALL fresh fields into user object
                this.user.plan      = fresh.plan      || 'NONE';
                this.user.balance   = fresh.balance   || 0;
                this.user.sub_end   = fresh.sub_end   || 0;
                this.user.has_trial = fresh.has_trial || false;
                this.user.ref_code  = fresh.ref_code  || this.user.ref_code;
                // legacy compatibility fields
                this.user.subscription = fresh;
                this.user.subscription_type = (fresh.plan || 'none').toLowerCase();
                localStorage.setItem('funpay_user', JSON.stringify(this.user));
                this.updateUI();
            }
        } catch (e) { console.error("Sync Error:", e); }
    },

    updateUI() {
        const authBtn = document.getElementById('login-trigger-btn');
        const profileNav = document.getElementById('user-profile-nav');
        const userAvatar = document.getElementById('user-avatar');
        const adminLink = document.getElementById('admin-link');
        const adminSidebar = document.getElementById('admin-sidebar-item');
        
        if (this.user) {
            if (authBtn) authBtn.style.display = 'none';
            if (profileNav) profileNav.style.display = 'flex';
            if (userAvatar) userAvatar.textContent = this.user.first_name ? this.user.first_name[0].toUpperCase() : 'U';
            
            const currentUserId = String(this.user.user_id || this.user.telegram_id);
            const adminIds = ["6360699049", "5304677735", "755843448"];
            const isAdmin = this.user.is_admin || adminIds.includes(currentUserId); 
            
            if (isAdmin) {
                const navLinks = document.querySelector('.nav-links');
                if (navLinks && !document.getElementById('nav-admin-link')) {
                    const li = document.createElement('li');
                    li.id = 'nav-admin-link';
                    li.innerHTML = '<a href="admin.html" style="color: #f43f5e; font-weight: bold;"><i class="fas fa-shield-alt"></i> Админка</a>';
                    navLinks.appendChild(li);
                }
                if (adminLink) adminLink.style.display = 'flex';
                if (adminSidebar) adminSidebar.style.display = 'block';
            }

            this.syncUserUI();

            // --- Plan detection using top-level this.user.plan ---
            const plan = (this.user.plan || 'NONE').toUpperCase();
            const hasSub = plan === 'FAST' || plan === 'SLOW';
            const isFast = plan === 'FAST';

            const planName    = document.getElementById('profile-plan-name');
            const statusBadge = document.getElementById('profile-status-badge');
            const sidebarStatus = document.getElementById('sidebar-user-status');

            if (hasSub) {
                if (planName) {
                    planName.textContent = isFast ? "FAST" : "SLOW";
                    planName.className = `value ${isFast ? 'plan-fast-text' : 'plan-slow-text'}`;
                }
                if (statusBadge) {
                    statusBadge.textContent = "АКТИВНА";
                    statusBadge.style.color = "#10b981";
                    statusBadge.style.background = "rgba(16, 185, 129, 0.1)";
                }
                if (sidebarStatus) {
                    sidebarStatus.textContent = plan;
                    sidebarStatus.style.color = isFast ? "#fbbf24" : "#3b82f6";
                }
            } else {
                if (planName) planName.textContent = "FREE PLAN";
                if (statusBadge) {
                    statusBadge.textContent = "Не активна";
                    statusBadge.style.color = "var(--text-muted)";
                }
            }

            // --- Referral & Balance UI ---
            const refInput = document.getElementById('ref-link-input');
            const refCodeDisplay = document.getElementById('display-ref-code');
            const refBalanceDisplay = document.getElementById('ref-balance');
            const btnBalanceDisplay = document.getElementById('btn-current-balance');
            
            const userBalance = Math.floor(this.user.balance || 0);
            const userRefCode = this.user.ref_code || "UNKNOWN";

            if (refInput) refInput.value = `https://t.me/FunPaySlov_Bot?start=ref_${userRefCode}`;
            if (refCodeDisplay) refCodeDisplay.textContent = userRefCode;
            if (refBalanceDisplay) refBalanceDisplay.textContent = userBalance;
            if (btnBalanceDisplay) btnBalanceDisplay.textContent = userBalance;

            const progressBar = document.getElementById('ref-progress-bar');
            if (progressBar) {
                const progress = Math.min((userBalance / 500) * 100, 100);
                progressBar.style.width = `${progress}%`;
            }
        }
    },

    initTabs() {
        const tabs = document.querySelectorAll('.sidebar-nav-item');
        const sections = document.querySelectorAll('.content-section');

        
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabId = tab.getAttribute('data-tab');
                if (!tabId) return;
                
                e.preventDefault();
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                sections.forEach(s => {
                    s.classList.remove('active');
                    s.style.display = 'none';
                    if (s.id === `section-${tabId}` || s.id === tabId) {
                        s.classList.add('active');
                        s.style.display = 'block';
                    }
                });

                // Load data for specific tabs
                if (tabId === 'devices') {
                    window.App.loadAccountsList();
                }
                if (tabId === 'subscription') {
                    window.App.syncUser(); // Refresh balance and plan
                }
            });
        });
    },

    // --- Account Management ---
    showAddAccountModal() {
        const modal = document.getElementById('add-account-modal');
        if (modal) modal.style.display = 'flex';
        else alert("Ошибка: Модальное окно не найдено.");
    },

    async addNewAccount() {
        const name   = document.getElementById('acc-name')?.value?.trim();
        const cookie = document.getElementById('acc-cookie')?.value?.trim();
        const proxy  = document.getElementById('acc-proxy')?.value?.trim() || '';

        if (!name)   return alert('Введите название аккаунта!');
        if (!cookie) return alert('Введите Golden Key (cookie)!');
        if (!this.user) return alert('Войдите в аккаунт!');

        const btn = document.querySelector('#add-account-modal .btn-primary');
        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Сохраняем...'; }

        try {
            const res = await fetch(`${API_BASE}/api/accounts/add`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: String(this.user.user_id), name, cookie, proxy })
            });
            if (res.ok) {
                document.getElementById('add-account-modal').style.display = 'none';
                document.getElementById('acc-name').value   = '';
                document.getElementById('acc-cookie').value = '';
                document.getElementById('acc-proxy').value  = '';
                await this.loadAccountsList();
            } else {
                const d = await res.json();
                alert(d.detail || 'Ошибка при добавлении аккаунта.');
            }
        } catch (e) {
            alert('Ошибка связи с сервером.');
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = 'Сохранить аккаунт'; }
        }
    },

    async deleteAccount(id) {
        if (!confirm('Удалить аккаунт?')) return;
        try {
            await fetch(`${API_BASE}/api/accounts/${id}?user_id=${this.user.user_id}`, { method: 'DELETE' });
            await this.loadAccountsList();
        } catch (e) { alert('Ошибка при удалении.'); }
    },

    async loadAccountsList() {
        const body = document.getElementById('accounts-list-body');
        if (!body || !this.user) return;

        body.innerHTML = '<tr><td colspan="4" style="padding:30px;text-align:center;color:#555"><i class="fas fa-spinner fa-spin"></i> Загрузка...</td></tr>';

        try {
            const res = await fetch(`${API_BASE}/api/accounts/list?user_id=${this.user.user_id}`);
            const accounts = await res.json();

            if (accounts.length === 0) {
                body.innerHTML = '<tr><td colspan="4" style="padding:50px;text-align:center;color:#333;font-size:0.95rem"><i class="fas fa-plus-circle" style="font-size:2rem;display:block;margin-bottom:12px;color:#222"></i>Аккаунты не добавлены.<br><small style="color:#2a2a2a">Нажмите «+ Добавить аккаунт»</small></td></tr>';
                return;
            }

            body.innerHTML = accounts.map(acc => `
                <tr style="border-bottom:1px solid rgba(255,255,255,0.02);transition:0.2s" onmouseover="this.style.background='rgba(255,255,255,0.01)'" onmouseout="this.style.background='transparent'">
                    <td style="padding:20px">
                        <div style="display:flex;align-items:center;gap:12px">
                            <div style="width:40px;height:40px;background:rgba(16,185,129,0.08);border-radius:12px;display:flex;align-items:center;justify-content:center;color:var(--accent);font-size:1.1rem">
                                <i class="fas fa-user-circle"></i>
                            </div>
                            <div>
                                <div style="font-weight:700;color:#fff">${acc.name}</div>
                                <div style="font-size:0.75rem;color:#333;font-family:monospace">key: ****</div>
                            </div>
                        </div>
                    </td>
                    <td style="padding:20px;color:#555;font-family:monospace;font-size:0.85rem">${acc.proxy || '<span style="color:#222">—</span>'}</td>
                    <td style="padding:20px">
                        <span style="display:inline-flex;align-items:center;gap:6px;padding:5px 12px;background:rgba(16,185,129,0.07);color:#10b981;border-radius:100px;font-size:0.73rem;font-weight:800;border:1px solid rgba(16,185,129,0.1)">
                            <div style="width:5px;height:5px;background:#10b981;border-radius:50%"></div> АКТИВЕН
                        </span>
                    </td>
                    <td style="padding:20px;text-align:right">
                        <button onclick="window.App.deleteAccount(${acc.id})" style="width:36px;height:36px;border-radius:10px;display:inline-flex;align-items:center;justify-content:center;color:#f43f5e;border:1px solid rgba(244,63,94,0.1);background:rgba(244,63,94,0.04);cursor:pointer">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } catch(e) {
            body.innerHTML = '<tr><td colspan="4" style="padding:30px;text-align:center;color:#f43f5e">Ошибка загрузки</td></tr>';
        }
    }
};

// --- Automation Worker ---
window.FunPayWorker = {
    isRunning: false,
    
    start() {
        if (this.isRunning) return;
        this.isRunning = true;
        console.log("🚀 Воркер активен");
        this.loop();
    },
    
    async loop() {
        while (this.isRunning) {
            const accounts = JSON.parse(localStorage.getItem('funpay_accounts') || '[]');
            for (const acc of accounts) {
                console.log(`[Worker] Обработка ${acc.name}`);
                // Automation logic placeholder
            }
            await new Promise(r => setTimeout(r, 60000));
        }
    }
};

// --- Auth Logic ---
window.handleTelegramLogin = async function() {
    const overlay = document.getElementById('login-overlay');
    const boxTelegram = document.getElementById('login-box-telegram');
    const codeDisplay = document.getElementById('tg-auth-code');
    overlay.style.display = 'flex';
    document.getElementById('login-box-standard').style.display = 'none';
    boxTelegram.style.display = 'block';
    try {
        const res = await fetch(`${API_BASE}/api/auth/generate`);
        const { code, token } = await res.json();
        codeDisplay.textContent = code;
        document.getElementById('link-to-bot').href = `https://t.me/FunPaySlov_Bot?start=${code}`;
        const poll = setInterval(async () => {
            const check = await fetch(`${API_BASE}/api/auth/check/${token}`);
            if (check.ok) {
                const userData = await check.json();
                clearInterval(poll);
                localStorage.setItem('funpay_user', JSON.stringify(userData));
                window.location.reload();
            }
        }, 3000);
    } catch (e) { alert("Ошибка связи с сервером."); }
};

window.logout = function() {
    localStorage.removeItem('funpay_user');
    window.location.href = 'index.html';
};

window.activateTrial = async function() {
    if (!window.App.user) return alert("Войдите в аккаунт!");
    try {
        const res = await fetch(`${API_BASE}/api/user/activate-trial`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ user_id: String(window.App.user.user_id) })
        });
        if (res.ok) {
            alert("Подписка на 4 дня активирована!");
            window.App.syncUser();
        } else {
            alert("Ошибка или триал уже использован.");
        }
    } catch (e) { alert("Сервер недоступен."); }
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    window.App.init();
    if (window.location.pathname.includes('profile.html')) {
        window.App.loadAccountsList();
    }
    
    const trigger = document.getElementById('login-trigger-btn');
    if (trigger) trigger.onclick = () => document.getElementById('login-overlay').style.display = 'flex';
    
        const tgBtn = document.getElementById('btn-telegram-login');
    if (tgBtn) tgBtn.onclick = () => window.handleTelegramLogin();
});

// --- Subscription Logic ---
window.selectedPlan = null;

window.selectPlan = function(planId, price) {
    window.selectedPlan = { id: planId, price: price };
    
    // UI Feedback: Remove active class from all buttons
    document.querySelectorAll('.btn-tier-select').forEach(btn => {
        btn.style.borderColor = 'rgba(255,255,255,0.05)';
        btn.style.background = 'rgba(255,255,255,0.02)';
        btn.style.color = '#ccc';
        btn.style.boxShadow = 'none';
    });

    // Add active class to selected button
    const selectedBtn = document.getElementById(`btn-${planId}`);
    if (selectedBtn) {
        const isFast = planId.startsWith('fast');
        const activeColor = isFast ? '#10b981' : '#3b82f6';
        selectedBtn.style.borderColor = activeColor;
        selectedBtn.style.background = isFast ? 'rgba(16, 185, 129, 0.05)' : 'rgba(59, 130, 246, 0.05)';
        selectedBtn.style.color = 'white';
        selectedBtn.style.boxShadow = `0 0 20px ${isFast ? 'rgba(16, 185, 129, 0.1)' : 'rgba(59, 130, 246, 0.1)'}`;
    }

    // Enable Crypto Buy Button
    const buyBtn = document.getElementById('buy-subscription-btn');
    if (buyBtn) {
        buyBtn.style.opacity = '1';
        buyBtn.style.cursor = 'pointer';
        buyBtn.style.background = 'var(--accent)';
        buyBtn.style.color = 'black';
        buyBtn.style.boxShadow = '0 10px 25px var(--accent-glow)';
        buyBtn.innerHTML = `<i class="fas fa-shopping-cart"></i> Оплатить ${price} ₽`;
    }

    // Handle Balance Button
    const balanceBtn = document.getElementById('pay-balance-btn');
    if (balanceBtn && window.App.user) {
        const userBalance = window.App.user.balance || 0;
        const btnBalanceEl = document.getElementById('btn-current-balance');
        if (btnBalanceEl) btnBalanceEl.textContent = Math.floor(userBalance);

        if (userBalance >= price) {
            balanceBtn.style.opacity = '1';
            balanceBtn.style.cursor = 'pointer';
            balanceBtn.style.borderColor = '#10b981';
            balanceBtn.style.color = '#10b981';
            balanceBtn.style.background = 'rgba(16, 185, 129, 0.05)';
        } else {
            balanceBtn.style.opacity = '0.3';
            balanceBtn.style.cursor = 'not-allowed';
            balanceBtn.style.borderColor = 'rgba(255,255,255,0.05)';
            balanceBtn.style.color = '#444';
            balanceBtn.style.background = 'none';
        }
    }
};

window.payWithBalance = async function() {
    if (!window.selectedPlan) return alert("Выберите тариф!");
    if (!window.App.user) return;
    
    const { id, price } = window.selectedPlan;
    const userBalance = window.App.user.balance || 0;
    
    if (userBalance < price) {
        return alert(`Недостаточно средств. У вас ${Math.floor(userBalance)} ₽, а нужно ${price} ₽. Приглашайте друзей!`);
    }
    
    if (!confirm(`Вы уверены, что хотите оплатить подписку ${id.toUpperCase()} с баланса (${price} ₽)?`)) return;

    try {
        const res = await fetch(`${API_BASE}/api/payment/pay-with-balance`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: String(window.App.user.user_id),
                plan_type: id,
                price: price
            })
        });
        
        const data = await res.json();
        if (res.ok) {
            alert("✅ Подписка успешно оплачена с баланса и активирована!");
            window.App.syncUser();
        } else {
            alert(data.detail || "Ошибка при оплате.");
        }
    } catch (e) {
        alert("Ошибка связи с сервером.");
    }
};

window.processPayment = async function() {
    if (!window.selectedPlan) return alert("Пожалуйста, выберите тариф!");
    if (!window.App.user) {
        document.getElementById('login-overlay').style.display = 'flex';
        return;
    }

    const { id, price } = window.selectedPlan;
    const userId = window.App.user.user_id || window.App.user.telegram_id;
    
    // UI Feedback: Disable button while loading
    const buyBtn = document.getElementById('buy-subscription-btn');
    const originalContent = buyBtn.innerHTML;
    buyBtn.disabled = true;
    buyBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Создаем счет...';
    buyBtn.style.opacity = '0.7';

    try {
        const res = await fetch(`${API_BASE}/api/payment/create`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: String(userId),
                plan_type: id,
                price: price
            })
        });
        
        const data = await res.json();
        
        if (res.ok && data.payment_url) {
            // Redirect to the actual Crypto Bot invoice
            window.open(data.payment_url, '_blank');
            alert(`Счет на ${price} ₽ создан! Оплатите его в открывшемся окне Telegram.`);
        } else {
            alert(data.detail || "Ошибка при создании счета. Попробуйте позже.");
        }
    } catch (e) {
        console.error(e);
        alert("Ошибка связи с сервером платежей.");
    } finally {
        buyBtn.disabled = false;
        buyBtn.innerHTML = originalContent;
        buyBtn.style.opacity = '1';
    }
};

window.activateTrial = async function() {
    if (!window.App.user) {
        document.getElementById('login-overlay').style.display = 'flex';
        return;
    }
    
    const trialBtn = document.querySelector('.btn-marketplace[onclick="window.activateTrial()"]');
    if (!trialBtn) return;
    
    const originalText = trialBtn.innerHTML;
    trialBtn.disabled = true;
    trialBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Активация...';
    trialBtn.style.opacity = '0.7';

    try {
        const res = await fetch(`${API_BASE}/api/user/activate-trial`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                user_id: String(window.App.user.user_id),
                plan: "FAST" 
            })
        });
        
        if (res.ok) {
            alert("🔥 FAST-подписка на 4 дня активирована! Все плагины доступны.");
            window.App.syncUser();
            const trialCard = document.getElementById('trial-card');
            if (trialCard) trialCard.style.display = 'none';
        } else {
            const data = await res.json();
            alert(data.detail || "Вы уже использовали пробный период.");
        }
    } catch (e) { 
        console.error(e);
        alert("Ошибка связи с сервером. Проверьте, запущен ли Render!"); 
    } finally {
        trialBtn.disabled = false;
        trialBtn.innerHTML = originalText;
        trialBtn.style.opacity = '1';
    }
};
