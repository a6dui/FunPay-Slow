const API_BASE = "http://127.0.0.1:8080";

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
                localStorage.setItem('funpay_user', JSON.stringify(this.user));
                this.updateUI();
            }
        } catch (e) {
            console.error("Sync Error:", e);
        }
    },

    updateUI() {
        const authBtn = document.getElementById('login-trigger-btn');
        const profileNav = document.getElementById('user-profile-nav');
        const userAvatar = document.getElementById('user-avatar');
        const adminLink = document.getElementById('admin-link');
        
        if (this.user) {
            if (authBtn) authBtn.style.display = 'none';
            if (profileNav) profileNav.style.display = 'flex';
            if (userAvatar) userAvatar.textContent = this.user.name ? this.user.name[0].toUpperCase() : 'U';
            
            const currentUserId = String(this.user.user_id);
            const adminIds = ["6360699049", "5304677735", "755843448"];
            const isAdmin = this.user.is_admin || adminIds.includes(currentUserId); 
            
            console.log("Checking admin rights for:", currentUserId, "Is admin:", isAdmin);
            if (isAdmin) {
                // Also add to main nav for better visibility
                const navLinks = document.querySelector('.nav-links');
                if (navLinks && !document.getElementById('nav-admin-link')) {
                    const li = document.createElement('li');
                    li.id = 'nav-admin-link';
                    li.innerHTML = '<a href="admin.html" style="color: #f43f5e; font-weight: bold;"><i class="fas fa-shield-alt"></i> Админка</a>';
                    navLinks.appendChild(li);
                }
                if (adminLink) adminLink.style.display = 'flex';
            }
        } else {
            if (authBtn) authBtn.style.display = 'flex';
            if (profileNav) profileNav.style.display = 'none';
            if (adminLink) adminLink.style.display = 'none';
        }
    }
};

// --- Payment Acquiring Integration ---
window.initiatePayment = async (planId, amount, method = "cryptobot") => {
    const user = window.App.user;
    if (!user) {
        alert("Пожалуйста, войдите в аккаунт для оплаты.");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/payment/initiate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: user.user_id.toString(),
                plan_id: planId,
                amount: amount,
                method: method
            })
        });
        const data = await res.json();
        if (data.payment_url) {
            window.open(data.payment_url, '_blank');
        } else {
            alert("Ошибка инициализации платежа. Попробуйте позже.");
        }
    } catch (e) {
        console.error("Payment error:", e);
        alert("Ошибка соединения с сервером");
    }
};

// --- Support Logic ---
window.sendSupport = async (title, message, contact, type = "bug") => {
    const user = window.App.user;
    const payload = {
        user_id: user ? user.user_id.toString() : "guest",
        username: user ? user.name : "Guest",
        message: `[${type.toUpperCase()}] ${title}\n\n${message}\n\nКонтакт: ${contact}`,
        type: type
    };
    
    try {
        console.log("Sending support payload:", payload);
        const res = await fetch(`${API_BASE}/api/support`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        console.log("Support response:", data);
        return data;
    } catch (e) {
        console.error("Support submission error:", e);
        return { success: false, message: "Ошибка сети" };
    }
};

// --- Changelog Logic ---
window.loadChangelog = async () => {
    const container = document.querySelector('.timeline');
    if (!container) return;
    
    try {
        const res = await fetch(`${API_BASE}/api/changelog`);
        const data = await res.json();
        
        container.innerHTML = data.map(item => `
            <div class="version-block">
                <div class="version-dot"></div>
                <div class="version-card">
                    <div class="version-tag">${item.version}</div>
                    <div class="version-date"><i class="far fa-calendar"></i> ${item.date}</div>
                    <div class="change-section">
                        <div class="change-title new"><i class="fas fa-plus-circle"></i> Новое</div>
                        <ul class="change-list">
                            ${item.changes.map(c => `<li>${c}</li>`).join('')}
                        </ul>
                    </div>
                    <div class="change-section">
                        <div class="change-title"><i class="fas fa-wrench"></i> Улучшения</div>
                        <ul class="change-list">
                            ${item.improvements.map(i => `<li>${i}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            </div>
        `).join('');
        
        // Update summary card
        const lastVer = document.querySelector('.summary-value');
        if (lastVer && data.length > 0) lastVer.textContent = data[0].version;
    } catch (e) {
        console.error("Changelog load error:", e);
    }
};

window.loadAdminStats = async () => {
    try {
        const res = await fetch(`${API_BASE}/api/admin/stats`);
        if (res.ok) return await res.json();
        return { error: "Access denied" };
    } catch (e) {
        console.error("Admin stats error:", e);
        return { error: e.message };
    }
};

document.addEventListener('DOMContentLoaded', () => {
    console.log("--- FunPay Slow Desktop v.2.2.0 Loaded ---");
    window.App.init();

    // Load dynamic version numbers on all pages
    const versionBadges = document.querySelectorAll('.hero-badge, .mockup-version, .logo span');
    versionBadges.forEach(b => {
        if (b.textContent.includes('v.')) b.innerHTML = b.innerHTML.replace(/v\.[0-9.]+/, 'v.2.2.0');
        if (b.textContent.includes('v2.')) b.innerHTML = b.innerHTML.replace(/v2\.[0-9.]+/, 'v2.2.0');
    });

    if (window.location.pathname.includes('changelog.html')) {
        window.loadChangelog();
    }

    const tgAuthCode = document.getElementById('tg-auth-code');
    const timerVal = document.getElementById('timer-val');
    const loginTrigger = document.getElementById('login-trigger-btn');
    const profileNav = document.getElementById('user-profile-nav');
    const userAvatar = document.getElementById('user-avatar');
    const errorMsg = document.getElementById('login-error');
    const overlay = document.getElementById('login-overlay');
    const loginBoxStandard = document.getElementById('login-box-standard');
    const loginBoxTelegram = document.getElementById('login-box-telegram');
    const btnTelegram = document.getElementById('btn-telegram-login');

    // Telegram Auth Logic
    const handleTelegramLogin = async () => {
        if (loginBoxTelegram.dataset.intervalId) clearInterval(parseInt(loginBoxTelegram.dataset.intervalId));
        if (loginBoxTelegram.dataset.pollId) clearInterval(parseInt(loginBoxTelegram.dataset.pollId));

        const code = Math.floor(100000 + Math.random() * 900000).toString();
        if (tgAuthCode) tgAuthCode.textContent = code;
        
        const linkToBot = document.getElementById('link-to-bot');
        if (linkToBot) {
            linkToBot.href = `https://t.me/FunPaySlov_Bot?start=${code}`;
        }
        
        try {
            await fetch(`${API_BASE}/api/auth/init/${code}`);
        } catch (e) {
            console.error("Failed to init TG auth", e);
            if (errorMsg) {
                errorMsg.textContent = 'Сервер недоступен!';
                errorMsg.style.display = 'block';
            }
            return;
        }

        if (loginBoxStandard) loginBoxStandard.style.display = 'none';
        if (loginBoxTelegram) loginBoxTelegram.style.display = 'block';

        let timeLeft = 180;
        const timerInterval = setInterval(() => {
            timeLeft--;
            const mins = Math.floor(timeLeft / 60);
            const secs = timeLeft % 60;
            if (timerVal) timerVal.textContent = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
            if (timeLeft <= 0) clearInterval(timerInterval);
        }, 1000);
        if (loginBoxTelegram) loginBoxTelegram.dataset.intervalId = timerInterval;

        const pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`${API_BASE}/api/auth/check/${code}`);
                const data = await res.json();
                
                if (data.success) {
                    clearInterval(timerInterval);
                    clearInterval(pollInterval);
                    if (overlay) overlay.style.display = 'none';
                    
                    if (loginTrigger) loginTrigger.style.display = 'none';
                    if (profileNav) profileNav.style.display = 'flex';
                    if (userAvatar && data.name) userAvatar.textContent = data.name.charAt(0);

                    localStorage.setItem('funpay_user', JSON.stringify({
                        name: data.name,
                        user_id: data.user_id,
                        isLoggedIn: true
                    }));

                    window.location.reload();
                }
            } catch (e) { console.error("Polling error", e); }
        }, 2000);
        if (loginBoxTelegram) loginBoxTelegram.dataset.pollId = pollInterval;
    };

    if (btnTelegram) btnTelegram.addEventListener('click', handleTelegramLogin);

    if (loginTrigger) {
        loginTrigger.addEventListener('click', (e) => {
            e.preventDefault();
            if (overlay) overlay.style.display = 'flex';
        });
    }

    const btnCancel = document.getElementById('btn-tg-cancel');
    if (btnCancel) {
        btnCancel.addEventListener('click', () => {
            if (loginBoxTelegram.dataset.intervalId) clearInterval(parseInt(loginBoxTelegram.dataset.intervalId));
            if (loginBoxTelegram.dataset.pollId) clearInterval(parseInt(loginBoxTelegram.dataset.pollId));
            if (loginBoxTelegram) loginBoxTelegram.style.display = 'none';
            if (loginBoxStandard) loginBoxStandard.style.display = 'block';
        });
    }

    // --- System Status ---
    async function fetchSystemStatus() {
        try {
            const response = await fetch(`${API_BASE}/api/system/status`);
            const data = await response.json();
            const container = document.getElementById('system-status');
            if (container) {
                container.classList.remove('status-green', 'status-orange', 'status-red');
                const statusText = container.querySelector('.status-text');
                if (data.status === 'online') container.classList.add('status-green');
                else if (data.status === 'unstable') container.classList.add('status-orange');
                else container.classList.add('status-red');
                if (statusText) statusText.innerText = data.text || data.status.toUpperCase();
            }
        } catch (e) {
            console.error("System Status Fetch Error:", e);
        }
    }
    
    fetchSystemStatus();
    setInterval(fetchSystemStatus, 30000);

    // --- Profile Tabs & Logout ---
    window.logout = () => {
        localStorage.removeItem('funpay_user');
        window.location.href = 'index.html';
    };

    const profileTabs = document.querySelectorAll('.sidebar-nav-item');
    const sections = document.querySelectorAll('.content-section');
    
    if (profileTabs.length > 0) {
        window.switchTab = (targetTab) => {
            profileTabs.forEach(t => t.classList.remove('active'));
            const activeTab = document.querySelector(`.sidebar-nav-item[data-tab="${targetTab}"]`);
            if (activeTab) activeTab.classList.add('active');
            
            sections.forEach(s => s.classList.remove('active'));
            const targetSection = document.getElementById(`section-${targetTab}`);
            if (targetSection) targetSection.classList.add('active');
            
            // Save hash without jump
            if (history.replaceState) {
                history.replaceState(null, null, targetTab === 'profile' ? 'profile.html' : `#${targetTab}`);
            }
        };

        profileTabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                if (tab.getAttribute('href') !== '#') return; // Let links like admin.html work
                e.preventDefault();
                window.switchTab(tab.dataset.tab);
            });
        });
    }

    // --- Feedback & Payments ---
    window.sendFeedback = async (data) => {
        try {
            const res = await fetch(`${API_BASE}/api/feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            return await res.json();
        } catch (e) {
            console.error("Feedback error:", e);
            return { success: false };
        }
    };

    // Payment logic moved to global scope

    const hash = window.location.hash.replace('#', '');
    if (hash && typeof window.switchTab === 'function' && document.getElementById(`section-${hash}`)) {
        window.switchTab(hash);
    }
});
