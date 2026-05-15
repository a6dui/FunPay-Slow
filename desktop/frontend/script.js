const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? "http://127.0.0.1:8080" 
    : "https://funpay-slow.onrender.com"; 

// --- Global App State ---
window.App = {
    user: JSON.parse(localStorage.getItem('funpay_user')) || null,
    
    init() {
        this.updateUI();
        if (this.user) {
            this.syncUser();
        }
    },
    
    async checkVersion() {
        // Disabled permanently by user request
        return;
    },

    showUpdateNotification(newVersion) {
        // Disabled permanently by user request
        return;
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

            // --- Referral Link ---
            const refInput = document.getElementById('ref-link-input');
            if (refInput) {
                refInput.value = `https://funpayslow.com/?ref=${this.user.user_id}`;
            }

            // --- Admin Visibility ---
            const admins = ["6360699049", "5304677735", "755843448"];
            if (admins.includes(String(this.user.user_id))) {
                if (adminLink) adminLink.style.display = 'flex';
            }
        } else {
            if (loginBtn) loginBtn.style.display = 'flex';
            if (profileNav) profileNav.style.display = 'none';
        }
    }
};

window.logout = function() {
    localStorage.removeItem('funpay_user');
    window.location.href = 'index.html';
};

// --- Telegram Auth Logic ---
let authPollInterval = null;

async function handleTelegramLogin() {
    const overlay = document.getElementById('login-overlay');
    const boxStandard = document.getElementById('login-box-standard');
    const boxTelegram = document.getElementById('login-box-telegram');
    const codeDisplay = document.getElementById('tg-auth-code');
    const timerDisplay = document.getElementById('timer-val');
    
    overlay.style.display = 'flex';
    boxStandard.style.display = 'none';
    boxTelegram.style.display = 'block';

    try {
        const res = await fetch(`${API_BASE}/api/auth/generate`);
        const { code, token } = await res.json();
        
        codeDisplay.textContent = code;
        document.getElementById('link-to-bot').href = `https://t.me/FunpaySlov_Bot?start=${code}`;

        let timeLeft = 180;
        const timer = setInterval(() => {
            timeLeft--;
            const mins = Math.floor(timeLeft / 60);
            const secs = timeLeft % 60;
            timerDisplay.textContent = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
            if (timeLeft <= 0) clearInterval(timer);
        }, 1000);

        // Polling
        if (authPollInterval) clearInterval(authPollInterval);
        authPollInterval = setInterval(async () => {
            const checkRes = await fetch(`${API_BASE}/api/auth/check/${token}`);
            if (checkRes.ok) {
                const userData = await checkRes.json();
                clearInterval(authPollInterval);
                clearInterval(timer);
                window.App.user = userData;
                localStorage.setItem('funpay_user', JSON.stringify(userData));
                window.location.reload();
            }
        }, 3000);

    } catch (e) {
        console.error("Auth error", e);
        alert("Ошибка сервера авторизации.");
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.App.init();
    
    const trigger = document.getElementById('login-trigger-btn');
    if (trigger) trigger.onclick = (e) => {
        e.preventDefault();
        document.getElementById('login-overlay').style.display = 'flex';
        document.getElementById('login-box-standard').style.display = 'block';
        document.getElementById('login-box-telegram').style.display = 'none';
    };

    const tgBtn = document.getElementById('btn-telegram-login');
    if (tgBtn) tgBtn.onclick = handleTelegramLogin;

    // Close dropdown on click outside
    document.addEventListener('click', (e) => {
        const dropdown = document.getElementById('profile-dropdown');
        if (dropdown && dropdown.style.display === 'flex' && !e.target.closest('.profile-nav-item')) {
            dropdown.style.display = 'none';
        }
    });
});
