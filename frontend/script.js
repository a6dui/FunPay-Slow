const API_BASE = "https://funpay-slow.onrender.com"; 

// --- Global App State ---
window.App = {
    user: JSON.parse(localStorage.getItem('funpay_user')) || null,
    
    init() {
        this.updateUI();
        if (this.user) {
            this.syncUser();
        }
        this.initTabs();
    },
    
    async syncUser() {
        if (!this.user || !this.user.user_id) return;
        try {
            const res = await fetch(`${API_BASE}/api/user/subscription/${this.user.user_id}`);
            if (res.ok) {
                const sub = await res.json();
                this.user.subscription = sub;
                this.user.plan = sub.plan; 
                localStorage.setItem('funpay_user', JSON.stringify(this.user));
                this.updateUI();
                this.updateProfilePage(sub);
            }
        } catch (e) { console.error("Sync Error:", e); }
    },

    updateUI() {
        const loginBtn = document.getElementById('login-trigger-btn');
        const profileNav = document.getElementById('user-profile-nav');
        const avatar = document.getElementById('user-avatar');
        
        if (this.user) {
            if (loginBtn) loginBtn.style.display = 'none';
            if (profileNav) {
                profileNav.style.display = 'flex';
                if (avatar) avatar.textContent = (this.user.first_name || 'U').charAt(0).toUpperCase();
            }

            const admins = ["6360699049", "5304677735", "755843448"];
            if (admins.includes(String(this.user.user_id))) {
                const adminLinks = document.querySelectorAll('#admin-link');
                adminLinks.forEach(el => el.style.display = 'flex');
            }

            const pName = document.getElementById('profile-name');
            const pID = document.getElementById('profile-tg-id');
            const hAvatar = document.getElementById('hero-avatar-letter');
            if (pName) pName.textContent = this.user.first_name || "Пользователь";
            if (pID) pID.textContent = "@id" + this.user.user_id;
            if (hAvatar) hAvatar.textContent = (this.user.first_name || 'U').charAt(0).toUpperCase();
            
            const refInput = document.getElementById('ref-link-input');
            if (refInput) refInput.value = `https://funpayslow.com/?ref=${this.user.user_id}`;
        }
    },

    updateProfilePage(sub) {
        const planVal = document.getElementById('sub-plan-val');
        const expiresVal = document.getElementById('sub-expires-val');
        if (planVal) planVal.textContent = (sub.plan || 'none').toUpperCase();
        if (expiresVal) {
            if (sub.expires && sub.expires > 0) {
                expiresVal.textContent = new Date(sub.expires * 1000).toLocaleDateString();
            } else { expiresVal.textContent = "Нет активной подписки"; }
        }
    },

    initTabs() {
        // Кнопки в сайдбаре могут иметь класс .sidebar-nav-item
        const tabs = document.querySelectorAll('.sidebar-nav-item');
        const sections = document.querySelectorAll('.content-section');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabId = tab.getAttribute('data-tab');
                if (!tabId) return;
                
                e.preventDefault();

                // 1. Убираем активный класс у всех кнопок
                tabs.forEach(t => t.classList.remove('active'));
                // 2. Добавляем активный класс текущей кнопке
                tab.classList.add('active');
                
                // 3. Прячем все секции и показываем нужную
                sections.forEach(s => {
                    s.classList.remove('active');
                    s.style.display = 'none'; // Гарантированное скрытие
                    
                    // Сопоставляем data-tab="profile" с id="section-profile"
                    if (s.id === `section-${tabId}` || s.id === tabId) {
                        s.classList.add('active');
                        s.style.display = 'block'; // Показываем
                    }
                });
            });
        });
    }
};

window.sendSupport = async function(title, desc, contact, type) {
    const user = JSON.parse(localStorage.getItem('funpay_user'));
    const message = `[${type.toUpperCase()}] ${title}\n\n${desc}\n\nКонтакт: ${contact || 'не указан'}`;
    
    try {
        const res = await fetch(`${API_BASE}/api/report/send`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: String(user ? user.user_id : "0"),
                username: user ? user.username : 'Anonymous',
                message: message
            })
        });
        const data = await res.json();
        return { success: res.ok };
    } catch (e) { 
        console.error("Support Send Error:", e);
        return { success: false }; 
    }
};

window.logout = function() {
    localStorage.removeItem('funpay_user');
    window.location.href = 'index.html';
};

async function loadAdminStats() {
    const user = JSON.parse(localStorage.getItem('funpay_user'));
    if (!user) return;
    try {
        const res = await fetch(`${API_BASE}/api/admin/stats?admin_id=${user.user_id}`);
        if (res.ok) {
            const stats = await res.json();
            if (document.getElementById('stat-users')) document.getElementById('stat-users').textContent = stats.total_users;
            if (document.getElementById('stat-online')) document.getElementById('stat-online').textContent = Math.floor(stats.total_users * 0.4);
            if (document.getElementById('stat-sales')) document.getElementById('stat-sales').textContent = stats.revenue_estimated;
            if (document.getElementById('stat-subs')) document.getElementById('stat-subs').textContent = stats.active_fast;
        }
    } catch (e) { console.error("Admin Stats Error", e); }
}

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
