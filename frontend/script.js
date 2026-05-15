const API_BASE = "https://funpay-slow.onrender.com"; 

// --- Global App State ---
window.App = {
    user: JSON.parse(localStorage.getItem('funpay_user')) || null,
    
    init() {
        this.updateUI();
        if (this.user) {
            this.syncUser();
        }
    },
    
    async syncUser() {
        if (!this.user || !this.user.user_id) return;
        try {
            const res = await fetch(`${API_BASE}/api/user/subscription/${this.user.user_id}`);
            if (res.ok) {
                const sub = await res.json();
                this.user.subscription = sub;
                this.user.plan = sub.plan; // fast, slow, none
                localStorage.setItem('funpay_user', JSON.stringify(this.user));
                this.updateUI();
                this.updateProfilePage(sub);
            }
        } catch (e) {
            console.error("Sync Error:", e);
        }
    },

    updateUI() {
        const loginBtn = document.getElementById('login-trigger-btn');
        const profileNav = document.getElementById('user-profile-nav');
        const avatar = document.getElementById('user-avatar');
        const adminLink = document.getElementById('admin-link');
        
        if (this.user) {
            if (loginBtn) loginBtn.style.display = 'none';
            if (profileNav) {
                profileNav.style.display = 'flex';
                if (avatar) avatar.textContent = (this.user.first_name || 'U').charAt(0).toUpperCase();
            }

            // --- Admin Visibility ---
            const admins = ["6360699049", "5304677735", "755843448"];
            if (admins.includes(String(this.user.user_id))) {
                if (adminLink) {
                    adminLink.style.display = 'flex';
                    // Show in navbar dropdown too if exists
                    const adminDrop = document.querySelectorAll('#admin-link');
                    adminDrop.forEach(el => el.style.display = 'flex');
                }
            }

            // Update Profile Info on Page
            const profileName = document.getElementById('profile-name');
            const profileID = document.getElementById('profile-tg-id');
            const heroAvatar = document.getElementById('hero-avatar-letter');
            if (profileName) profileName.textContent = this.user.first_name || "Пользователь";
            if (profileID) profileID.textContent = "@id" + this.user.user_id;
            if (heroAvatar) heroAvatar.textContent = (this.user.first_name || 'U').charAt(0).toUpperCase();
        }
    },

    updateProfilePage(sub) {
        const planVal = document.getElementById('sub-plan-val');
        const expiresVal = document.getElementById('sub-expires-val');
        if (planVal) planVal.textContent = (sub.plan || 'none').toUpperCase();
        if (expiresVal) {
            if (sub.expires && sub.expires > 0) {
                const date = new Date(sub.expires * 1000);
                expiresVal.textContent = date.toLocaleDateString();
            } else {
                expiresVal.textContent = "Нет активной подписки";
            }
        }
    }
};

window.logout = function() {
    localStorage.removeItem('funpay_user');
    window.location.href = 'index.html';
};

// --- Admin Stats ---
async function loadAdminStats() {
    const user = JSON.parse(localStorage.getItem('funpay_user'));
    if (!user) return;
    try {
        const res = await fetch(`${API_BASE}/api/admin/stats?admin_id=${user.user_id}`);
        if (res.ok) {
            const stats = await res.json();
            document.getElementById('stat-users').textContent = stats.total_users;
            document.getElementById('stat-online').textContent = Math.floor(stats.total_users * 0.4); // Mock online
            document.getElementById('stat-sales').textContent = stats.revenue_estimated;
            document.getElementById('stat-subs').textContent = stats.active_fast;
        }
    } catch (e) { console.error("Admin Stats Error", e); }
}

// --- Telegram Auth ---
async function handleTelegramLogin() {
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
        document.getElementById('link-to-bot').href = `https://t.me/FunpaySlov_Bot?start=${code}`;

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
}

document.addEventListener('DOMContentLoaded', () => {
    window.App.init();
    if (window.location.pathname.includes('admin.html')) loadAdminStats();
    
    const trigger = document.getElementById('login-trigger-btn');
    if (trigger) trigger.onclick = () => document.getElementById('login-overlay').style.display = 'flex';
    
    const tgBtn = document.getElementById('btn-telegram-login');
    if (tgBtn) tgBtn.onclick = handleTelegramLogin;
});
