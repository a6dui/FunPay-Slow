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
        
        // Start automation worker
        if (window.FunPayWorker) {
            window.FunPayWorker.start();
        }
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
                const sub = await res.json();
                this.user.subscription = sub;
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

            // --- Update Profile UI ---
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
                if (statusBadge) {
                    statusBadge.textContent = "Не активна";
                    statusBadge.style.color = "var(--text-muted)";
                }
                if (trialBanner && !this.user.is_trial_used) trialBanner.style.display = 'flex';
            }

            // --- Referral Link ---
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

    // --- Account Management ---
    showAddAccountModal() {
        const modal = document.getElementById('add-account-modal');
        if (modal) modal.style.display = 'flex';
        else alert("Ошибка: Модальное окно не найдено.");
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
            body.innerHTML = '<tr><td colspan="4" style="padding: 20px; text-align: center; color: var(--text-muted);">Аккаунты не добавлены.</td></tr>';
            return;
        }

        body.innerHTML = accounts.map(acc => `
            <tr>
                <td style="padding: 15px;"><b>${acc.name}</b><br><small>****${acc.cookie.slice(-4)}</small></td>
                <td style="padding: 15px;">${acc.proxy || 'Без прокси'}</td>
                <td style="padding: 15px;"><span class="status-badge" style="color:#10b981">АКТИВЕН</span></td>
                <td style="padding: 15px; text-align:right;"><button class="btn-outline" onclick="window.App.deleteAccount(${acc.id})"><i class="fas fa-trash"></i></button></td>
            </tr>
        `).join('');
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
