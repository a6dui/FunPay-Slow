const API_BASE = "https://funpay-slow.onrender.com";

// --- Global App State ---
window.App = {
    user: JSON.parse(localStorage.getItem('funpay_user')) || null,
    
    init() {
        console.log("🐌 FunPay Slow v2.4.2 Initializing...");
        this.updateUI();
        if (this.user) {
            this.syncUser();
        }
        this.initTabs();
    },

    async syncUser() {
        if (!this.user || !this.user.user_id) return;
        try {
            const res = await fetch(`${API_BASE}/api/user/info?user_id=${this.user.user_id}`);
            if (res.ok) {
                const data = await res.json();
                this.user = data;
                localStorage.setItem('funpay_user', JSON.stringify(data));
                this.updateUI();
            }
        } catch (e) { console.warn("Sync failed"); }
    },

    updateUI() {
        const authBtn = document.getElementById('login-trigger-btn');
        const profileNav = document.getElementById('user-profile-nav');
        const userAvatar = document.getElementById('user-avatar');
        const adminLink = document.getElementById('admin-link');
        
        if (this.user) {
            if (authBtn) authBtn.style.display = 'none';
            if (profileNav) profileNav.style.display = 'flex';
            if (userAvatar) userAvatar.textContent = this.user.first_name ? this.user.first_name[0].toUpperCase() : 'U';
            
            // Admin check
            const adminIds = ["6360699049", "5304677735", "755843448"];
            if (this.user.is_admin || adminIds.includes(String(this.user.user_id))) {
                if (adminLink) adminLink.style.display = 'flex';
            }

            // Profile Page Specific
            const nameEl = document.getElementById('user-name-large');
            if (nameEl) nameEl.textContent = this.user.first_name || 'User';
            
            const idEl = document.getElementById('user-id-display');
            if (idEl) idEl.textContent = this.user.user_id;

            const balanceEls = document.querySelectorAll('#profile-balance, #sub-balance-value, #btn-current-balance');
            balanceEls.forEach(el => el.textContent = Math.floor(this.user.balance || 0));

            const planEls = document.querySelectorAll('#sub-plan-name, #sidebar-user-status');
            planEls.forEach(el => el.textContent = (this.user.plan || 'NONE').toUpperCase());

            // Trial Banner
            const trialBanner = document.getElementById('trial-banner');
            if (trialBanner) {
                const noPlan = !this.user.plan || this.user.plan.toUpperCase() === 'NONE';
                trialBanner.style.display = (noPlan && !this.user.trial_used) ? 'flex' : 'none';
            }

            // Referral
            const refLinkInput = document.getElementById('ref-link-input');
            const refCodeDisplay = document.getElementById('display-ref-code');
            if (refCodeDisplay) refCodeDisplay.textContent = this.user.ref_code || '---';
            if (refLinkInput && this.user.ref_code) {
                refLinkInput.value = `https://t.me/FunPaySlov_Bot?start=ref_${this.user.ref_code}`;
            }
        } else {
            if (authBtn) authBtn.style.display = 'flex';
            if (profileNav) profileNav.style.display = 'none';
        }
    },

    initTabs() {
        const tabs = document.querySelectorAll('.sidebar-nav-item');
        const sections = document.querySelectorAll('.content-section');
        tabs.forEach(tab => {
            tab.onclick = (e) => {
                e.preventDefault();
                const target = tab.getAttribute('data-tab');
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                sections.forEach(s => {
                    s.style.display = (s.id === `section-${target}` || s.id === target) ? 'block' : 'none';
                });
                if (target === 'devices') this.loadAccountsList();
            };
        });
    },

    showAddAccountModal() {
        const m = document.getElementById('add-account-modal');
        if (m) m.style.display = 'flex';
    },

    async loadAccountsList() {
        const body = document.getElementById('accounts-list-body');
        if (!body || !this.user) return;
        body.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;">Загрузка...</td></tr>';
        try {
            const res = await fetch(`${API_BASE}/api/accounts/list?user_id=${this.user.user_id}`);
            const accounts = await res.json();
            if (accounts.length === 0) {
                body.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:40px;">Аккаунтов нет</td></tr>';
                return;
            }
            body.innerHTML = accounts.map(acc => `
                <tr>
                    <td style="padding:15px;">${acc.name}</td>
                    <td style="padding:15px;">${acc.proxy || '—'}</td>
                    <td style="padding:15px;"><span class="badge-status">АКТИВЕН</span></td>
                    <td style="padding:15px;text-align:right;">
                        <button onclick="window.App.deleteAccount(${acc.id})" style="color:#f43f5e;background:none;border:none;cursor:pointer;"><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');
        } catch(e) { body.innerHTML = '<tr><td colspan="4">Ошибка</td></tr>'; }
    },

    async deleteAccount(id) {
        if (!confirm('Удалить?')) return;
        await fetch(`${API_BASE}/api/accounts/${id}?user_id=${this.user.user_id}`, { method: 'DELETE' });
        this.loadAccountsList();
    }
};

// --- Auth Logic ---
window.handleTelegramLogin = async function() {
    const overlay = document.getElementById('login-overlay');
    const box1 = document.getElementById('login-box-standard');
    const box2 = document.getElementById('login-box-telegram');
    const codeEl = document.getElementById('tg-auth-code');
    const botLink = document.getElementById('link-to-bot');

    if (!overlay || !box1 || !box2) return;

    box1.style.display = 'none';
    box2.style.display = 'block';
    codeEl.textContent = '...';

    try {
        const res = await fetch(`${API_BASE}/api/auth/request`, { method: 'POST' });
        const data = await res.json();
        if (!data.code) throw new Error("No code");

        codeEl.textContent = data.code;
        botLink.href = `https://t.me/FunPaySlov_Bot?start=${data.code}`;

        if (window._authPoll) clearInterval(window._authPoll);
        window._authPoll = setInterval(async () => {
            try {
                const check = await fetch(`${API_BASE}/api/auth/confirm?code=${data.code}`);
                if (check.ok) {
                    const user = await check.json();
                    clearInterval(window._authPoll);
                    localStorage.setItem('funpay_user', JSON.stringify(user));
                    overlay.style.display = 'none';
                    alert(`✅ Привет, ${user.first_name || 'Друг'}!`);
                    window.location.reload();
                }
            } catch (e) {}
        }, 2500);
    } catch (e) {
        codeEl.textContent = 'ERR';
        setTimeout(() => { box1.style.display='block'; box2.style.display='none'; }, 2000);
    }
};

window.logout = function() {
    localStorage.removeItem('funpay_user');
    window.location.href = 'index.html';
};

window.activateTrial = async function() {
    if (!window.App.user) return;
    try {
        const res = await fetch(`${API_BASE}/api/user/activate-trial`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ user_id: String(window.App.user.user_id) })
        });
        if (res.ok) {
            alert("Триал активирован!");
            window.App.syncUser();
        }
    } catch(e) {}
};

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
    window.App.init();

    // Bind triggers
    const trigger = document.getElementById('login-trigger-btn');
    if (trigger) {
        trigger.onclick = (e) => {
            e.preventDefault();
            const overlay = document.getElementById('login-overlay');
            if (overlay) overlay.style.display = 'flex';
        };
    }

    const tgBtn = document.getElementById('btn-telegram-login');
    if (tgBtn) {
        tgBtn.onclick = () => window.handleTelegramLogin();
    }
});
