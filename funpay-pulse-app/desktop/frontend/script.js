const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? "http://127.0.0.1:8080" 
    : "https://funpay-slow.onrender.com"; // Замените на ваш URL на Render после деплоя

// --- Global App State ---
window.App = {
    user: JSON.parse(localStorage.getItem('funpay_user')) || null,
    
    init() {
        this.updateUI();
        if (this.user) {
            this.syncUser();
        }
        this.checkVersion();
    },
    
    async checkVersion() {
        try {
            const res = await fetch(`${API_BASE}/`);
            if (res.ok) {
                const data = await res.json();
                const localVersion = "2.2.2"; // Текущая версия десктопа
                if (data.version && data.version !== localVersion) {
                    console.log(`Update available: ${data.version} (Local: ${localVersion})`);
                    this.showUpdateNotification(data.version);
                }
            }
        } catch (e) {
            console.error("Version Check Error:", e);
        }
    },

    showUpdateNotification(newVersion) {
        if (document.querySelector('.update-notification')) return;
        
        const notify = document.createElement('div');
        notify.className = 'update-notification';
        notify.innerHTML = `
            <div class="update-content">
                <i class="fas fa-sync-alt fa-spin"></i>
                <span>Доступна новая версия <b>v.${newVersion}</b></span>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <button onclick="window.location.reload()">Обновить</button>
                    <div onclick="this.parentElement.parentElement.parentElement.remove()" style="cursor: pointer; opacity: 0.6; padding: 5px;">&times;</div>
                </div>
            </div>
        `;
        document.body.appendChild(notify);
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

            // --- Update Profile Fields ---
            const planName = document.getElementById('profile-plan-name');
            const statusBadge = document.getElementById('profile-status-badge');
            const expireDate = document.getElementById('profile-expire-date');
            const expireDays = document.getElementById('profile-expire-days');
            const sidebarStatus = document.getElementById('sidebar-user-status');
            const sidebarAvatar = document.getElementById('sidebar-avatar-char');
            const sidebarName = document.getElementById('sidebar-user-name');
            const heroName = document.getElementById('hero-user-name');
            const heroAvatar = document.getElementById('hero-avatar-char');

            if (sidebarAvatar) sidebarAvatar.textContent = userAvatar.textContent;
            if (heroAvatar) heroAvatar.textContent = userAvatar.textContent;
            if (sidebarName) sidebarName.textContent = this.user.name || "Пользователь";
            if (heroName) heroName.textContent = this.user.name || "Пользователь";

            const sub = this.user.subscription;
            const hasSub = sub && (sub.status === 'active' || sub.plan === 'Fast' || sub.plan === 'Slow');
            
            if (hasSub) {
                const isFast = sub.plan === 'Fast';
                
                if (planName) {
                    planName.textContent = sub.plan || "Fast";
                    planName.className = `value ${isFast ? 'plan-fast-text' : 'plan-slow-text'}`;
                }
                
                if (statusBadge) {
                    statusBadge.textContent = sub.status === 'active' ? "Активна" : "Обработка";
                    statusBadge.style.color = sub.status === 'active' ? "#10b981" : "#fbbf24";
                    statusBadge.style.background = sub.status === 'active' ? "rgba(16, 185, 129, 0.1)" : "rgba(251, 191, 36, 0.1)";
                    statusBadge.style.borderColor = sub.status === 'active' ? "rgba(16, 185, 129, 0.3)" : "rgba(251, 191, 36, 0.3)";
                }
                
                if (expireDate) expireDate.textContent = sub.expires_at || "Бессрочно";
                
                if (sidebarStatus) {
                    sidebarStatus.textContent = sub.plan || "Fast";
                    sidebarStatus.style.color = isFast ? "#fbbf24" : "#3b82f6";
                    sidebarStatus.style.textShadow = isFast ? "0 0 10px rgba(251, 191, 36, 0.3)" : "none";
                }
                
                // Calculate days left
                if (expireDays && sub.expires_at && sub.expires_at !== '-') {
                    const now = new Date();
                    const expStr = sub.expires_at.includes('T') ? sub.expires_at : sub.expires_at.replace(' ', 'T');
                    const exp = new Date(expStr);
                    const diff = Math.ceil((exp - now) / (1000 * 60 * 60 * 24));
                    expireDays.textContent = diff > 0 ? `${diff} дн.` : "Истекла";
                } else if (expireDays) {
                    expireDays.textContent = "∞";
                }
            } else {
                if (planName) {
                    planName.textContent = "Бесплатно";
                    planName.className = "value";
                }
                if (statusBadge) {
                    statusBadge.textContent = "Не активна";
                    statusBadge.style.color = "var(--text-muted)";
                    statusBadge.style.background = "rgba(255,255,255,0.05)";
                }
                if (expireDate) expireDate.textContent = "Нет активной подписки";
                if (sidebarStatus) {
                    sidebarStatus.textContent = "Бесплатно";
                    sidebarStatus.style.color = "var(--text-muted)";
                    sidebarStatus.style.textShadow = "none";
                }
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

// --- Support & Developer Verification ---
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

window.submitDevVerification = async () => {
    const user = window.App.user;
    if (!user) {
        alert("Пожалуйста, войдите в аккаунт.");
        return;
    }
    
    const section = document.getElementById('section-dev');
    const inputs = section.querySelectorAll('.dev-input');
    
    if (!inputs[3].value) {
        alert("Пожалуйста, укажите ваш CryptoBot ID или адрес кошелька!");
        return;
    }
    
    const payload = {
        user_id: user.user_id.toString(),
        username: user.name || "Unknown",
        payout_method: inputs[0].value,
        payout_name: inputs[1].value,
        contact: inputs[2].value,
        wallet_label: inputs[3].value,
        comment: inputs[4].value
    };
    
    try {
        const res = await fetch(`${API_BASE}/api/developer/verify`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            alert("✅ Ваша заявка на выплаты через CryptoBot отправлена! Мы свяжемся с вами после проверки.");
        } else {
            alert("❌ Ошибка при отправке заявки: " + (data.detail || "Неизвестная ошибка"));
        }
    } catch (e) {
        console.error("Dev verification error:", e);
        alert("❌ Ошибка соединения с сервером.");
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
    console.log("--- FunPay Slow Desktop v.2.2.2 Loaded ---");
    window.App.init();

    // Load dynamic version numbers on all pages
    const versionBadges = document.querySelectorAll('.hero-badge, .mockup-version, .logo span');
    versionBadges.forEach(b => {
        if (b.textContent.includes('v.')) b.innerHTML = b.innerHTML.replace(/v\.[0-9.]+/, 'v.2.2.2');
        if (b.textContent.includes('v2.')) b.innerHTML = b.innerHTML.replace(/v2\.[0-9.]+/, 'v2.2.2');
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
            
            // Referral system hook
            if (targetTab === 'referral') {
                window.loadReferralData();
            }

            // My Plugins hook
            if (targetTab === 'plugins') {
                window.loadUserPlugins();
            }

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

    // --- Referral System Logic ---
    window.loadReferralData = async () => {
        const user = window.App.user;
        if (!user || !user.user_id) return;
        
        try {
            const res = await fetch(`${API_BASE}/api/user/referral/${user.user_id}`);
            if (!res.ok) return;
            
            const data = await res.json();
            
            // Update UI elements
            const displayCode = document.getElementById('display-ref-code');
            const linkInput = document.getElementById('ref-link-input');
            const balanceText = document.getElementById('ref-balance');
            const countText = document.getElementById('ref-count-text');
            const levelBadge = document.getElementById('ref-level-badge');
            const progressBar = document.getElementById('ref-progress-bar');
            const applyBox = document.getElementById('referral-apply-box');
            
            if (displayCode) displayCode.textContent = data.referral_code;
            if (linkInput) linkInput.value = `${window.location.origin}/?ref=${data.referral_code}`;
            if (balanceText) balanceText.textContent = data.balance.toFixed(2);
            if (countText) countText.textContent = `${data.invited_count} приглашённых`;
            
            // Levels logic (example)
            let levelName = "Ур. 1 -- Новичок";
            let percent = 5;
            let progress = (data.invited_count % 5) * 20;
            
            if (data.level === 2) { levelName = "Ур. 2 -- Партнер"; percent = 7; }
            if (data.level === 3) { levelName = "Ур. 3 -- Амбассадор"; percent = 10; }
            
            if (levelBadge) levelBadge.textContent = levelName;
            if (progressBar) progressBar.style.width = `${progress}%`;
            const refPercent = document.getElementById('ref-percent');
            if (refPercent) refPercent.textContent = percent;

            // Show apply box only if user doesn't have a referrer yet
            if (applyBox) {
                applyBox.style.display = data.has_referrer ? 'none' : 'block';
            }

            // Update List
            const listEmpty = document.getElementById('referrals-list-empty');
            const listContainer = document.getElementById('referrals-list-container');
            const tableBody = document.getElementById('referrals-table-body');
            const totalCount = document.getElementById('total-ref-count');

            if (data.referrals && data.referrals.length > 0) {
                if (listEmpty) listEmpty.style.display = 'none';
                if (listContainer) listContainer.style.display = 'block';
                if (totalCount) totalCount.textContent = `Всего: ${data.referrals.length}`;
                
                if (tableBody) {
                    tableBody.innerHTML = data.referrals.map(ref => `
                        <div class="referral-friend-row">
                            <div class="friend-avatar">${ref.referred_id.toString().slice(-2)}</div>
                            <div class="friend-info">
                                <span class="friend-id">Пользователь #${ref.referred_id}</span>
                                <span class="friend-date">Присоединился: ${new Date(ref.created_at).toLocaleDateString()}</span>
                            </div>
                            <div class="friend-reward">+5% с оплат</div>
                        </div>
                    `).join('');
                }
            } else {
                if (listEmpty) listEmpty.style.display = 'flex';
                if (listContainer) listContainer.style.display = 'none';
            }

        } catch (e) {
            console.error("Referral load error:", e);
        }
    };

    window.applyReferralCode = async () => {
        const input = document.getElementById('input-referral-code');
        const code = input.value.trim().toUpperCase();
        const user = window.App.user;

        if (!code) {
            alert("Введите код!");
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/api/user/referral/apply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: user.user_id.toString(),
                    code: code
                })
            });
            const data = await res.json();
            if (data.success) {
                alert("✅ Код успешно применен! Вы получили бонус.");
                window.loadReferralData();
            } else {
                alert("❌ " + (data.detail || "Ошибка применения кода"));
            }
        } catch (e) {
            alert("Ошибка соединения");
        }
    };

    window.copyReferralLink = () => {
        const input = document.getElementById('ref-link-input');
        input.select();
        document.execCommand('copy');
        alert("🔗 Ссылка скопирована!");
    };

    window.shareToTelegram = () => {
        const input = document.getElementById('ref-link-input');
        const url = encodeURIComponent(input.value);
        const text = encodeURIComponent("Пользуйся лучшим софтом для FunPay вместе со мной в FunPay Slow! 🐌🚀");
        window.open(`https://t.me/share/url?url=${url}&text=${text}`, '_blank');
    };

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

    // --- My Plugins System ---
    window.loadUserPlugins = async () => {
        const user = window.App.user;
        if (!user || !user.user_id) return;
        
        try {
            const res = await fetch(`${API_BASE}/api/user/plugins/${user.user_id}`);
            if (!res.ok) return;
            
            const data = await res.json();
            
            // Update Stats
            const stats = document.querySelectorAll('#section-plugins .stat-value');
            if (stats.length >= 3) {
                stats[0].textContent = data.owned_count;
                stats[1].textContent = data.installations_count;
                stats[2].textContent = data.pending_payment_count;
            }
            
            // Update Available Plugins List
            const availableContainer = document.querySelector('#section-plugins .plugins-lists .list-card:first-child .card-content');
            if (availableContainer) {
                if (data.plugins && data.plugins.length > 0) {
                    availableContainer.classList.remove('empty-state');
                    availableContainer.style.padding = '0.5rem 0';
                    availableContainer.innerHTML = data.plugins.map(p => `
                        <div class="last-op-row">
                            <div class="op-main">
                                <div class="op-icon" style="background: rgba(255,255,255,0.05);">${p.icon}</div>
                                <div class="op-info">
                                    <span class="op-title">${p.title}</span>
                                    <span class="op-date">Активирован: ${p.activated_at || 'Недавно'}</span>
                                </div>
                            </div>
                        </div>
                    `).join('');
                } else {
                    availableContainer.classList.add('empty-state');
                    availableContainer.innerHTML = `
                        <div class="empty-icon" style="width: 60px; height: 60px; font-size: 1.5rem; margin-bottom: 1rem;">
                            <i class="fas fa-box-open"></i>
                        </div>
                        <p style="font-size: 0.9rem;">У вас пока нет доступных плагинов.</p>
                    `;
                }
            }
            
            // Update Installations List
            const installContainer = document.querySelector('#section-plugins .plugins-lists .list-card:nth-child(2) .card-content');
            if (installContainer) {
                if (data.installations && data.installations.length > 0) {
                    installContainer.classList.remove('empty-state');
                    installContainer.style.padding = '0.5rem 0';
                    installContainer.innerHTML = data.installations.map(i => `
                        <div class="last-op-row">
                            <div class="op-main">
                                <div class="op-icon" style="background: rgba(167, 139, 250, 0.1); color: #a78bfa;"><i class="fas fa-server"></i></div>
                                <div class="op-info">
                                    <span class="op-title">${i.plugin_title} @ ${i.ip}</span>
                                    <span class="op-date">${i.date} — <span style="color: #34d399;">${i.status}</span></span>
                                </div>
                            </div>
                        </div>
                    `).join('');
                } else {
                    installContainer.classList.add('empty-state');
                    installContainer.innerHTML = `
                        <div class="empty-icon" style="width: 60px; height: 60px; font-size: 1.5rem; margin-bottom: 1rem;">
                            <i class="fas fa-server"></i>
                        </div>
                        <p style="font-size: 0.9rem;">Активных установок не найдено.</p>
                    `;
                }
            }
            
            // Update Dropdown
            const select = document.querySelector('#section-plugins select.dev-input');
            if (select) {
                if (data.plugins && data.plugins.length > 0) {
                    select.innerHTML = data.plugins.map(p => `<option value="${p.id}">${p.title}</option>`).join('');
                } else {
                    select.innerHTML = '<option value="">Нет доступных плагинов</option>';
                }
            }
            
            // Update Sub Status
            const subBadge = document.querySelector('.info-card .status-badge');
            const subText = document.querySelector('.info-card .info-text .value');
            const subNote = document.querySelector('.info-card div[style*="width: 100%"]');
            
            if (data.subscription && subBadge) {
                if (data.subscription.status === 'active') {
                    subBadge.textContent = 'Активна';
                    subBadge.style.background = 'rgba(16, 185, 129, 0.1)';
                    subBadge.style.color = '#10b981';
                    subText.textContent = data.subscription.plan;
                    subNote.textContent = `Ваша подписка действует до ${data.subscription.expires_at}`;
                    
                    // Hide trial card
                    const trialCard = document.querySelector('.trial-card');
                    if (trialCard) trialCard.style.display = 'none';
                } else if (data.subscription.trial_used) {
                    // Hide trial card if used
                    const trialCard = document.querySelector('.trial-card');
                    if (trialCard) trialCard.style.display = 'none';
                }
            }
            
        } catch (e) {
            console.error("Plugins load error:", e);
        }
    };

    window.selectedPlan = null;
    window.selectedPrice = 0;

    window.selectPlan = (planId, price, element, type) => {
        window.selectedPlan = planId;
        window.selectedPrice = price;
        
        // Remove active from all options in the current type
        document.querySelectorAll(`.tier-card#tier-${type} .plan-option`).forEach(opt => opt.classList.remove('active'));
        // Remove active from other types to be safe
        document.querySelectorAll(`.tier-card:not(#tier-${type}) .plan-option`).forEach(opt => opt.classList.remove('active'));
        
        // Remove selected from all cards
        document.querySelectorAll('.tier-card').forEach(card => card.classList.remove('selected'));
        // Hide/Disable all buy buttons
        document.querySelectorAll('.btn-buy-now').forEach(btn => btn.classList.remove('ready'));

        // Add active to clicked option
        element.classList.add('active');
        
        // Add selected to parent card
        const card = document.getElementById(`tier-${type}`);
        if (card) card.classList.add('selected');
        
        // Enable corresponding button
        const btn = document.getElementById(`btn-buy-${type}`);
        if (btn) {
            btn.classList.add('ready');
            btn.innerHTML = `<i class="fas fa-shopping-cart"></i> Оплатить ${price} ₽`;
        }
        
        console.log(`Plan selected: ${planId} (${price} RUB)`);
    };

    window.buySelectedPlan = async () => {
        if (!window.selectedPlan) {
            alert("Выберите период подписки!");
            return;
        }
        
        const user = window.App.user;
        if (!user) {
            alert("Сначала авторизуйтесь!");
            return;
        }
        
        try {
            const res = await fetch(`${API_BASE}/api/payment/create?user_id=${user.user_id}&plan=${window.selectedPlan}&amount=${window.selectedPrice}`, {
                method: 'POST'
            });
            const data = await res.json();
            if (data.success) {
                // Open CryptoBot link
                window.open(data.pay_url, '_blank');
                
                // Start checking status
                alert("Платеж создан! Оплатите его в CryptoBot и нажмите OK для проверки статуса.");
                
                const verifyRes = await fetch(`${API_BASE}/api/payment/verify/${data.invoice_id}`);
                const verifyData = await verifyRes.json();
                if (verifyData.success) {
                    alert("✅ " + verifyData.message);
                    window.location.reload();
                } else {
                    alert("❌ " + verifyData.message);
                }
            }
        } catch (e) {
            alert("Ошибка при создании платежа");
        }
    };

    window.activateTrial = async () => {
        const user = window.App.user;
        if (!user) {
            alert("Сначала авторизуйтесь!");
            return;
        }
        
        try {
            const res = await fetch(`${API_BASE}/api/subscription/trial`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: user.user_id.toString() })
            });
            const data = await res.json();
            if (data.success) {
                alert("✅ Пробный период активирован на 4 дня!");
                window.location.reload();
            } else {
                alert("❌ " + (data.message || data.detail));
            }
        } catch (e) {
            alert("Ошибка активации");
        }
    };

    window.installPluginOnVps = async () => {
        const user = window.App.user;
        const section = document.getElementById('section-plugins');
        const select = section.querySelector('select.dev-input');
        const ipInput = section.querySelector('input[placeholder="1.1.1.1"]');
        const passInput = section.querySelector('input[type="password"]');
        
        if (!select || !select.value) {
            alert("Выберите плагин!");
            return;
        }
        if (!ipInput.value || !passInput.value) {
            alert("Заполните IP и пароль сервера!");
            return;
        }
        
        try {
            const res = await fetch(`${API_BASE}/api/user/plugins/install`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: user.user_id,
                    plugin_id: parseInt(select.value),
                    ip_address: ipInput.value,
                    password: passInput.value
                })
            });
            const data = await res.json();
            if (data.success) {
                alert("✅ " + data.message);
                window.loadUserPlugins();
            } else {
                alert("❌ Ошибка: " + (data.detail || "Неизвестная ошибка"));
            }
        } catch (e) {
            alert("Ошибка соединения");
        }
    };

    // Payment logic moved to global scope

    const hash = window.location.hash.replace('#', '');
    if (hash && typeof window.switchTab === 'function' && document.getElementById(`section-${hash}`)) {
        window.switchTab(hash);
    }
    
    // Initial data load if on referral tab
    if (hash === 'referral') window.loadReferralData();
});
