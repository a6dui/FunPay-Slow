const API_BASE = "https://funpay-slow.onrender.com";

// --- Global App State ---
window.App = {
    user: JSON.parse(localStorage.getItem('funpay_user')) || null,
    
    init() {
        console.log("🐌 FunPay Slow Initializing...");
        this.updateUI();
        if (this.user) {
            this.syncUser();
        }
        this.initTabs();
        
        // Start automation worker
        if (window.FunPayWorker) {
            window.FunPayWorker.start();
        }
    },
    
    async syncUser() {
        if (!this.user || !this.user.user_id) return;
        try {
            const res = await fetch(`${API_BASE}/api/user/subscription/${this.user.user_id}`);
            if (res.ok) {
                const sub = await res.json();
                this.user.subscription = sub;
                // Important: Update subscription_type based on server data
                this.user.subscription_type = sub.plan ? sub.plan.toLowerCase() : 'free';
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

            // --- Update Profile Fields ---
            const planName = document.getElementById('profile-plan-name');
            const statusBadge = document.getElementById('profile-status-badge');
            const trialBanner = document.getElementById('trial-activation-banner');
            const sidebarStatus = document.getElementById('sidebar-user-status');
            
            const sub = this.user.subscription || {};
            const hasSub = (sub.status === 'active' || this.user.subscription_type === 'fast' || this.user.subscription_type === 'slow');

            if (hasSub) {
                const isFast = this.user.subscription_type === 'fast' || sub.plan === 'Fast';
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
                    sidebarStatus.textContent = isFast ? "FAST" : "SLOW";
                    sidebarStatus.style.color = isFast ? "#fbbf24" : "#3b82f6";
                }
                if (trialBanner) trialBanner.style.display = 'none';
            } else {
                if (planName) planName.textContent = "FREE PLAN";
                if (statusBadge) statusBadge.textContent = "Бесплатно";
                if (trialBanner && !this.user.is_trial_used) trialBanner.style.display = 'flex';
            }

            // --- Referral Link (Fixed Branding) ---
            const refInput = document.getElementById('ref-link-input');
            if (refInput) {
                refInput.value = `https://t.me/FunpaySlowBot?start=ref_${this.user.user_id}`;
            }
            const refCodeDisplay = document.getElementById('display-ref-code');
            if (refCodeDisplay) refCodeDisplay.textContent = this.user.user_id || "OFFLINE";
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
            });
        });
    },

    // --- Account Management (Golden Key) ---
    showAddAccountModal() {
        document.getElementById('add-account-modal').style.display = 'flex';
    },

    addNewAccount() {
        const name = document.getElementById('acc-name').value || "Без имени";
        const cookie = document.getElementById('acc-cookie').value;
        const proxy = document.getElementById('acc-proxy').value;

        if (!cookie) return alert("Введите куки (Golden Key)!");

        const accounts = JSON.parse(localStorage.getItem('funpay_accounts') || '[]');
        accounts.push({ id: Date.now(), name, cookie, proxy, status: 'active' });
        localStorage.setItem('funpay_accounts', JSON.stringify(accounts));

        document.getElementById('add-account-modal').style.display = 'none';
        this.loadAccountsList();
        
        document.getElementById('acc-name').value = '';
        document.getElementById('acc-cookie').value = '';
        document.getElementById('acc-proxy').value = '';
    },

    deleteAccount(id) {
        if (!confirm("Удалить аккаунт?")) return;
        let accounts = JSON.parse(localStorage.getItem('funpay_accounts') || '[]');
        accounts = accounts.filter(a => a.id !== id);
        localStorage.setItem('funpay_accounts', JSON.stringify(accounts));
        this.loadAccountsList();
    },

    loadAccountsList() {
        const body = document.getElementById('accounts-list-body');
        if (!body) return;
        const accounts = JSON.parse(localStorage.getItem('funpay_accounts') || '[]');
        
        if (accounts.length === 0) {
            body.innerHTML = '<tr><td colspan="4" style="padding: 20px; text-align: center; color: var(--text-muted);">Аккаунты не добавлены. Нажмите кнопку выше.</td></tr>';
            return;
        }

        body.innerHTML = accounts.map(acc => `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                <td style="padding: 15px;">
                    <div style="font-weight: 600;">${acc.name}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Cookie: ****${acc.cookie.slice(-4)}</div>
                </td>
                <td style="padding: 15px; font-family: monospace; font-size: 0.8rem;">
                    ${acc.proxy || '<span style="color: #666;">Без прокси</span>'}
                </td>
                <td style="padding: 15px;">
                    <span class="status-badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; font-size: 0.7rem;">РАБОТАЕТ</span>
                </td>
                <td style="padding: 15px; text-align: right;">
                    <button class="btn-outline" style="padding: 6px 12px; font-size: 0.8rem;" onclick="window.App.deleteAccount(${acc.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }
};

// --- Automation Worker (Core v2.4.1) ---
window.FunPayWorker = {
    isRunning: false,
    lastLog: "Ожидание запуска...",
    
    start() {
        if (this.isRunning) return;
        this.isRunning = true;
        this.log("🚀 Воркер запущен");
        this.loop();
    },
    
    log(msg) {
        console.log(`[Worker] ${msg}`);
        this.lastLog = msg;
        const logEl = document.getElementById('worker-status-log');
        if (logEl) logEl.textContent = msg;
        this.notifyTelegram(msg);
    },

    async notifyTelegram(msg) {
        const chatId = localStorage.getItem('tg_chat_id');
        if (!chatId) return;
        // Simple throttling
        const now = Date.now();
        if (this.lastNotifyTime && now - this.lastNotifyTime < 30000) return; 
        this.lastNotifyTime = now;
        // fetch(...) would go here
    },

    async loop() {
        while (this.isRunning) {
            try {
                const accounts = JSON.parse(localStorage.getItem('funpay_accounts') || '[]');
                if (accounts.length === 0) {
                    this.log("⏳ Аккаунты не добавлены. Добавьте в профиле.");
                } else {
                    for (const acc of accounts) {
                        this.log(`👤 Обработка: ${acc.name}`);
                        await this.processAutoBump(acc);
                        await this.processAutoDelivery(acc);
                    }
                }
            } catch (e) { console.error("Worker Error:", e); }
            await new Promise(r => setTimeout(r, 60000));
        }
    },

    async processAutoBump(acc) {
        const config = JSON.parse(localStorage.getItem('plugin_bump_config') || '{"enabled":false}');
        if (!config.enabled || !acc.cookie) return;
        this.log(`⏰ [${acc.name}] Поднимаю лоты...`);
        // Logic for request...
    },

    async processAutoDelivery(acc) {
        const config = JSON.parse(localStorage.getItem('plugin_delivery_config') || '{"enabled":false}');
        if (!config.enabled || !acc.cookie) return;
        this.log(`📦 [${acc.name}] Проверка заказов...`);
    }
};

// --- Trial Activation ---
window.activateTrial = async function() {
    const user = window.App.user;
    if (!user) return alert("Войдите в аккаунт!");
    if (user.is_trial_used) return alert("Вы уже использовали пробный период.");

    try {
        const res = await fetch(`${API_BASE}/api/user/activate-trial`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ user_id: String(user.user_id) })
        });
        if (res.ok) {
            alert("Fast подписка на 4 дня активирована! 🚀");
            window.App.syncUser();
        } else {
            alert("Ошибка активации. Попробуйте через 5 минут.");
        }
    } catch (e) { alert("Сервер недоступен."); }
};

// --- Global UI Functions ---
window.savePluginConfig = function(type) {
    const config = {};
    if (type === 'bump') {
        config.enabled = document.getElementById('plugin-bump-enabled').checked;
        config.interval = document.getElementById('plugin-bump-interval').value;
        localStorage.setItem('plugin_bump_config', JSON.stringify(config));
    }
    alert('Настройки сохранены!');
};

window.saveTgSettings = function() {
    const cid = document.getElementById('tg-chat-id').value;
    localStorage.setItem('tg_chat_id', cid);
    alert('TG ID сохранен!');
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    window.App.init();
    if (window.location.pathname.includes('profile.html')) {
        window.App.loadAccountsList();
    }
    
    // Auth logic
    const trigger = document.getElementById('login-trigger-btn');
    if (trigger) trigger.onclick = () => document.getElementById('login-overlay').style.display = 'flex';
    
    const tgBtn = document.getElementById('btn-telegram-login');
    if (tgBtn) tgBtn.onclick = async () => {
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
            document.getElementById('link-to-bot').href = `https://t.me/FunpaySlowBot?start=${code}`;
            const poll = setInterval(async () => {
                const check = await fetch(`${API_BASE}/api/auth/check/${token}`);
                if (check.ok) {
                    const userData = await check.json();
                    clearInterval(poll);
                    localStorage.setItem('funpay_user', JSON.stringify(userData));
                    window.location.reload();
                }
            }, 3000);
        } catch (e) { alert("Ошибка авторизации."); }
    };
});
