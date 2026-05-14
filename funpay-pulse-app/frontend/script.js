document.addEventListener('DOMContentLoaded', () => {

    // Login Logic
    const btnLogin = document.getElementById('btn-login');
    const btnTelegram = document.getElementById('btn-telegram-login');
    const pwdInput = document.getElementById('login-password');
    const emailInput = document.getElementById('login-email');
    const errorMsg = document.getElementById('login-error');
    const overlay = document.getElementById('login-overlay');
    const appContent = document.getElementById('app-content');
    const loginBoxStandard = document.getElementById('login-box-standard');
    const loginBoxTelegram = document.getElementById('login-box-telegram');
    const tgAuthCode = document.getElementById('tg-auth-code');
    const timerVal = document.getElementById('timer-val');

    let isRegistering = false;

    // Telegram Auth Only Logic
    const handleLogin = () => {
        // Disabled email login
        errorMsg.textContent = 'Используйте вход через Telegram';
        errorMsg.style.display = 'block';
    };

    const handleTelegramLogin = async () => {
        // Force clear any old state
        const oldTimer = loginBoxTelegram.dataset.intervalId;
        const oldPoll = loginBoxTelegram.dataset.pollId;
        if (oldTimer) clearInterval(oldTimer);
        if (oldPoll) clearInterval(oldPoll);

        // Generate random 6-digit code
        const code = Math.floor(100000 + Math.random() * 900000).toString();
        tgAuthCode.textContent = code;
        console.log("Generated TG code:", code);

        // Initialize auth on server
        try {
            await fetch(`http://127.0.0.1:8000/api/auth/init/${code}`);
        } catch (e) {
            console.error("Failed to init TG auth", e);
        }

        // Switch boxes
        loginBoxStandard.style.display = 'none';
        loginBoxTelegram.style.display = 'block';

        // Start mock timer
        let timeLeft = 180; // 3 minutes
        const timerInterval = setInterval(() => {
            timeLeft--;
            const mins = Math.floor(timeLeft / 60);
            const secs = timeLeft % 60;
            timerVal.textContent = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
            
            if (timeLeft <= 0) {
                clearInterval(timerInterval);
                timerVal.textContent = "0:00";
            }
        }, 1000);

        // Start Polling for confirmation
        console.log(`Starting polling for code: ${code}`);
        const pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`http://127.0.0.1:8000/api/auth/check/${code}`);
                const data = await res.json();
                
                if (data.success) {
                    console.log("Auth success confirmed by server!");
                    clearInterval(timerInterval);
                    clearInterval(pollInterval);
                    
                    // Success! Redirect
                    overlay.style.display = 'none';
                    appContent.style.display = 'block';
                    initDashboard();
                }
            } catch (e) {
                console.error("Polling error", e);
            }
        }, 2000);

        // Store intervals to clear if canceled
        loginBoxTelegram.dataset.intervalId = timerInterval;
        loginBoxTelegram.dataset.pollId = pollInterval;
    };

    const handleTelegramCancel = () => {
        const intervalId = loginBoxTelegram.dataset.intervalId;
        const pollId = loginBoxTelegram.dataset.pollId;
        if (intervalId) clearInterval(intervalId);
        if (pollId) clearInterval(pollId);
        
        loginBoxTelegram.style.display = 'none';
        loginBoxStandard.style.display = 'block';
    };

    btnLogin.addEventListener('click', handleLogin);
    btnTelegram.addEventListener('click', handleTelegramLogin);
    document.getElementById('btn-tg-cancel').addEventListener('click', handleTelegramCancel);
    pwdInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleLogin();
    });

    // Обработка табов
    document.getElementById('tab-login').addEventListener('click', (e) => {
        isRegistering = false;
        e.target.classList.add('active');
        document.getElementById('tab-register').classList.remove('active');
        document.getElementById('btn-login').textContent = 'Войти';
    });
    document.getElementById('tab-register').addEventListener('click', (e) => {
        isRegistering = true;
        e.target.classList.add('active');
        document.getElementById('tab-login').classList.remove('active');
        document.getElementById('btn-login').textContent = 'Зарегистрироваться';
    });

    // Initialize Dashboard after login
    function initDashboard() {
        const plugins = [
            { 
                id: 1, 
                title: 'Аккаунты FunPay', 
                desc: 'Это удобная панель для управления аккаунтами FunPay, лотами и основными действиями.', 
                icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>',
                tags: ['Подключение аккаунтов', 'Контроль лотов']
            },
            { 
                id: 2, 
                title: 'Чаты и заказы', 
                desc: 'Сообщения, заказы и уведомления собраны в одном месте.', 
                icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2h-4l-4 4-4-4H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path></svg>',
                tags: ['Сообщения', 'Заказы', 'Уведомления']
            },
            { 
                id: 3, 
                title: 'Плагины для автоматизации', 
                desc: 'Стараемся автоматизировать как можно больше задач для вашего удобства.', 
                icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><path d="M12 11h4"></path><path d="M12 16h4"></path><path d="M8 11h.01"></path><path d="M8 16h.01"></path></svg>',
                tags: ['AutoResponder', 'AutoTicket', 'AutoGift']
            },
            { 
                id: 4, 
                title: 'Управление VPS', 
                desc: 'Вы всегда можете управлять воркером на VPS прямо из приложения.', 
                icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>',
                tags: ['Подключение VPS', 'Статус воркера', 'Токен подключения']
            }
        ];

        const pluginsContainer = document.getElementById('plugins-container');
        // Обновляем CSS сетку для больших карточек (2 колонки)
        pluginsContainer.style.gridTemplateColumns = 'repeat(auto-fit, minmax(450px, 1fr))';
        
        plugins.forEach(plugin => {
            const card = document.createElement('div');
            card.className = 'plugin-card';
            
            const tagsHTML = plugin.tags.map(tag => `<button class="plugin-tag">${tag}</button>`).join('');
            
            card.innerHTML = `
                <div class="plugin-icon">${plugin.icon}</div>
                <h3 class="plugin-title">${plugin.title}</h3>
                <p class="plugin-desc">${plugin.desc}</p>
                <div class="plugin-tags">
                    ${tagsHTML}
                </div>
            `;
            pluginsContainer.appendChild(card);
        });

        // Fetch and render Sniper tasks
        const fetchSniperTasks = async () => {
            const sniperContainer = document.getElementById('sniper-container');
            sniperContainer.innerHTML = '';
            try {
                const sniperResponse = await fetch('http://127.0.0.1:8000/api/sniper/tasks');
                if (sniperResponse.ok) {
                    const sniperTasks = await sniperResponse.json();
                    
                    if (sniperTasks.length === 0) {
                        sniperContainer.innerHTML = '<p style="color: var(--text-muted); text-align: center; grid-column: 1 / -1;">Нет активных задач парсинга. Добавьте их выше.</p>';
                    } else {
                        sniperTasks.forEach(task => {
                            const card = document.createElement('div');
                            card.className = 'plugin-card';
                            card.innerHTML = `
                                <div class="plugin-icon" style="color: var(--accent);">🎯</div>
                                <h3 class="plugin-title">${task.query}</h3>
                                <p class="plugin-desc">Парсинг на <b>${task.platform}</b> для товаров до <b>${task.max_price} руб.</b></p>
                                <div class="plugin-meta">
                                    <div class="plugin-price">ID Пользователя: <span>${task.user_id}</span></div>
                                    <button class="btn-secondary btn-stop-task" data-id="${task.id}" data-userid="${task.user_id}" style="color: var(--accent); border-color: rgba(244, 63, 94, 0.3);">Остановить</button>
                                </div>
                            `;
                            sniperContainer.appendChild(card);
                        });

                        document.querySelectorAll('.btn-stop-task').forEach(btn => {
                            btn.addEventListener('click', async (e) => {
                                const taskId = e.target.getAttribute('data-id');
                                const userId = e.target.getAttribute('data-userid');
                                try {
                                    await fetch(`http://127.0.0.1:8000/api/sniper/tasks/${taskId}/${userId}`, { method: 'DELETE' });
                                    fetchSniperTasks(); 
                                } catch (err) {
                                    console.error('Failed to delete task', err);
                                }
                            });
                        });
                    }
                }
            } catch (e) {
                sniperContainer.innerHTML = '<p style="color: var(--accent); text-align: center; grid-column: 1 / -1;">Бэкенд не запущен. Сервер отключен.</p>';
            }
            
            applyGlassHover();
        };

        fetchSniperTasks();

        // Add new task logic
        const btnAddTask = document.getElementById('btn-add-task');
        if (btnAddTask) {
            btnAddTask.addEventListener('click', async () => {
                const query = document.getElementById('task-query').value;
                const price = document.getElementById('task-price').value;
                const platform = document.getElementById('task-platform').value;
                const userId = document.getElementById('task-userid').value;

                if (!query || !price || !userId) {
                    alert("Пожалуйста, заполните все поля!");
                    return;
                }

                try {
                    const res = await fetch('http://127.0.0.1:8000/api/sniper/tasks', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            user_id: parseInt(userId),
                            query: query,
                            max_price: parseInt(price),
                            platform: platform
                        })
                    });
                    if (res.ok) {
                        document.getElementById('task-query').value = '';
                        fetchSniperTasks();
                    }
                } catch (err) {
                    console.error('Failed to add task', err);
                }
            });
        }

        // Fetch Analytics Data
        const fetchAnalytics = async () => {
            try {
                const res = await fetch('http://127.0.0.1:8000/api/analytics');
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('stat-revenue').textContent = data.revenue;
                    document.getElementById('stat-auto').textContent = data.auto_delivered;
                    document.getElementById('stat-sniper').textContent = data.active_sniper_tasks;
                    document.getElementById('stat-alerts').textContent = data.competitor_alerts;
                    
                    initChart();
                }
            } catch (err) {
                console.error('Failed to load analytics', err);
            }
        };
        
        fetchAnalytics();
        
        // Chart.js Setup
        function initChart() {
            const ctx = document.getElementById('revenueChart').getContext('2d');
            
            // Градиент для графика
            const gradient = ctx.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, 'rgba(16, 185, 129, 0.5)'); // Зеленый
            gradient.addColorStop(1, 'rgba(16, 185, 129, 0.0)');

            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
                    datasets: [{
                        label: 'Доход (руб)',
                        data: [1200, 1900, 3000, 2500, 3200, 4100, 14500],
                        borderColor: '#10b981',
                        backgroundColor: gradient,
                        borderWidth: 3,
                        pointBackgroundColor: '#10b981',
                        pointBorderColor: '#fff',
                        pointRadius: 5,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            labels: { color: '#e5e7eb', font: { family: 'Inter', size: 14 } }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#9ca3af' },
                            grid: { color: 'rgba(255, 255, 255, 0.05)' }
                        },
                        y: {
                            ticks: { color: '#9ca3af' },
                            grid: { color: 'rgba(255, 255, 255, 0.05)' }
                        }
                    }
                }
            });
        }
        
        applyGlassHover();
    }

    // Glassmorphism hover effect function
    function applyGlassHover() {
        document.querySelectorAll('.plugin-card').forEach(card => {
            card.addEventListener('mousemove', e => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                card.style.setProperty('--mouse-x', `${x}px`);
                card.style.setProperty('--mouse-y', `${y}px`);
            });
        });
    }

});
