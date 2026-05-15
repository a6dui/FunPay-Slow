const API_BASE = "https://funpay-slow.onrender.com"; 

// --- Global App State ---
window.App = {
    user: JSON.parse(localStorage.getItem('funpay_user')) || null,
    selectedPlan: null,
    
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

        // --- Trial Visibility Logic ---
        const trialCard = document.getElementById('trial-card');
        if (trialCard) {
            const daysSinceReg = sub.created_at ? (Date.now() / 1000 - sub.created_at) / (24 * 3600) : 0;
            if (sub.has_trial || sub.plan !== 'none' || daysSinceReg > 4) {
                trialCard.style.display = 'none';
            } else {
                trialCard.style.display = 'flex';
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
            });
        });
    }
};

// --- Trial & Payment Functions ---
window.activateTrial = async function() {
    if (!window.App.user) return;
    try {
        const res = await fetch(`${API_BASE}/api/subscription/trial?user_id=${window.App.user.user_id}`, { method: 'POST' });
        if (res.ok) {
            alert("Пробный период 4 дня активирован!");
            window.App.syncUser();
        } else {
            const err = await res.json();
            alert(err.detail || "Ошибка активации.");
        }
    } catch (e) { alert("Сервер недоступен."); }
};

window.selectPlan = function(planType, price) {
    window.App.selectedPlan = { type: planType, price: price };
    
    // UI Feedback
    const cards = document.querySelectorAll('.tier-card');
    cards.forEach(c => c.classList.remove('selected'));
    
    const selectedCard = document.getElementById(`plan-card-${planType}`);
    if (selectedCard) selectedCard.classList.add('selected');
    
    const buyBtn = document.getElementById('buy-subscription-btn');
    if (buyBtn) {
        buyBtn.classList.add('ready');
        buyBtn.innerHTML = `<i class="fas fa-shopping-cart"></i> Оплатить $${price}`;
    }
};

window.processPayment = async function() {
    if (!window.App.user || !window.App.selectedPlan) return;
    
    try {
        const res = await fetch(`${API_BASE}/api/payment/create`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: window.App.user.user_id,
                plan_type: window.App.selectedPlan.type,
                price: window.App.selectedPlan.price
            })
        });
        if (res.ok) {
            const data = await res.json();
            window.open(data.payment_url, '_blank');
            alert("Вы переходите в Crypto Bot для оплаты чеком. После оплаты подписка активируется автоматически.");
        }
    } catch (e) { alert("Ошибка платежной системы."); }
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
        return { success: res.ok };
    } catch (e) { return { success: false }; }
};

window.logout = function() {
    localStorage.removeItem('funpay_user');
    window.location.href = 'index.html';
};

document.addEventListener('DOMContentLoaded', () => {
    window.App.init();
});
