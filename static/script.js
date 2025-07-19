document.addEventListener('DOMContentLoaded', () => {
    // ÇOK ÖNEMLİ: BU BİLGİLERİ KENDİ FIREBASE PROJENİZDEN ALIP DOLDURUN
    const firebaseConfig = {
        apiKey: "AIzaSyDkJch-8B46dpZSB-pMSR4q1uvzadCVekE", // Sizin verdiğiniz anahtar
        authDomain: "aviator-90c8b.firebaseapp.com",    // Sizin verdiğiniz
        databaseURL: "https://aviator-90c8b-default-rtdb.firebaseio.com", // Sizin verdiğiniz
        projectId: "aviator-90c8b",                  // Sizin verdiğiniz
        storageBucket: "aviator-90c8b.appspot.com",  // Sizin verdiğiniz
        messagingSenderId: "823763988442",           // Sizin verdiğiniz
        appId: "1:823763988442:web:16a797275675a219c3dae3" // Sizin verdiğiniz
    };
    // -----------------------------------------------------------------

    // Firebase servislerini başlat
    firebase.initializeApp(firebaseConfig);
    const auth = firebase.auth();
    const database = firebase.database();

    // HTML elementlerini seç
    const loginContainer = document.getElementById('login-container');
    const appContainer = document.getElementById('app-container');
    const loginButton = document.getElementById('login-button');
    const logoutButton = document.getElementById('logout-button');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const loginError = document.getElementById('login-error');
    const symbolInput = document.getElementById('symbol-input');
    const startButton = document.getElementById('start-button');
    const stopButton = document.getElementById('stop-button');
    const statusMessageSpan = document.getElementById('status-message');
    const currentSymbolSpan = document.getElementById('current-symbol');
    const positionStatusSpan = document.getElementById('position-status');
    const lastSignalSpan = document.getElementById('last-signal');
    const statsTotal = document.getElementById('stats-total-trades');
    const statsWinning = document.getElementById('stats-winning-trades');
    const statsNetPnl = document.getElementById('stats-net-pnl');
    const statsDailyPnl = document.getElementById('stats-daily-pnl');
    const statsWeeklyPnl = document.getElementById('stats-weekly-pnl');
    const statsMonthlyPnl = document.getElementById('stats-monthly-pnl');
    let statusInterval;

    // --- KİMLİK DOĞRULAMA ---
    loginButton.addEventListener('click', () => {
        loginError.textContent = "";
        auth.signInWithEmailAndPassword(emailInput.value, passwordInput.value)
            .catch(error => { loginError.textContent = "Hatalı e-posta veya şifre."; });
    });

    logoutButton.addEventListener('click', () => { auth.signOut(); });

    auth.onAuthStateChanged(user => {
        if (user) {
            loginContainer.style.display = 'none';
            appContainer.style.display = 'flex';
            getStatus();
            statusInterval = setInterval(getStatus, 5000);
            listenForTradeUpdates();
        } else {
            loginContainer.style.display = 'flex';
            appContainer.style.display = 'none';
            if (statusInterval) clearInterval(statusInterval);
        }
    });

    // --- API İSTEKLERİ ---
    async function fetchApi(endpoint, options = {}) {
        const user = auth.currentUser;
        if (!user) { alert("Lütfen tekrar giriş yapın."); return null; }
        const idToken = await user.getIdToken(true);
        const headers = { ...options.headers, 'Authorization': `Bearer ${idToken}` };
        if (options.body) headers['Content-Type'] = 'application/json';
        try {
            const response = await fetch(endpoint, { ...options, headers });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                alert(`Hata: ${errorData.detail}`);
                return null;
            }
            return response.json();
        } catch (error) {
            console.error("API isteği hatası:", error);
            return null;
        }
    }
    
    // --- ARAYÜZ GÜNCELLEME ---
    const updateUI = (data) => {
        if (!data) return;
        statusMessageSpan.textContent = data.status_message;
        currentSymbolSpan.textContent = data.symbol || 'N/A';
        lastSignalSpan.textContent = data.last_signal || 'N/A';
        if (data.is_running) {
            startButton.disabled = true; stopButton.disabled = false; symbolInput.disabled = true;
            symbolInput.value = data.symbol; statusMessageSpan.className = 'status-running';
        } else {
            startButton.disabled = false; stopButton.disabled = true; symbolInput.disabled = false;
            statusMessageSpan.className = 'status-stopped';
        }
        positionStatusSpan.textContent = data.in_position ? 'Evet' : 'Hayır';
        positionStatusSpan.className = data.in_position ? 'status-in-position' : '';
    };

    const getStatus = async () => updateUI(await fetchApi('/api/status'));
    startButton.addEventListener('click', async () => {
        const symbol = symbolInput.value.trim().toUpperCase();
        if (!symbol) return alert('Lütfen bir coin sembolü girin.');
        updateUI(await fetchApi('/api/start', { method: 'POST', body: JSON.stringify({ symbol }) }));
    });
    stopButton.addEventListener('click', async () => updateUI(await fetchApi('/api/stop', { method: 'POST' })));

    // --- İSTATİSTİK HESAPLAMA ---
    function listenForTradeUpdates() {
        const tradesRef = database.ref('trades');
        tradesRef.on('value', (snapshot) => {
            const tradesData = snapshot.val();
            const trades = tradesData ? Object.values(tradesData) : [];
            calculateAndDisplayStats(trades);
        });
    }

    function calculateAndDisplayStats(trades) {
        const now = new Date();
        const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
        const weekStart = new Date(now.setDate(now.getDate() - now.getDay() + (now.getDay() === 0 ? -6 : 1))).getTime();
        const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).getTime();

        let totalTrades = trades.length;
        let winningTrades = trades.filter(t => (t.pnl || 0) > 0).length;
        let netPnl = 0, dailyPnl = 0, weeklyPnl = 0, monthlyPnl = 0;

        trades.forEach(trade => {
            const pnl = parseFloat(trade.pnl) || 0;
            const timestamp = new Date(trade.timestamp).getTime();
            netPnl += pnl;
            if (timestamp >= todayStart) dailyPnl += pnl;
            if (timestamp >= weekStart) weeklyPnl += pnl;
            if (timestamp >= monthStart) monthlyPnl += pnl;
        });
        
        statsTotal.textContent = totalTrades;
        const winRate = totalTrades > 0 ? ((winningTrades / totalTrades) * 100).toFixed(1) : 0;
        statsWinning.textContent = `${winningTrades} (%${winRate})`;

        formatPnl(statsNetPnl, netPnl);
        formatPnl(statsDailyPnl, dailyPnl);
        formatPnl(statsWeeklyPnl, weeklyPnl);
        formatPnl(statsMonthlyPnl, monthlyPnl);
    }

    function formatPnl(element, value) {
        element.textContent = `${value.toFixed(2)} USDT`;
        element.className = value > 0 ? 'stats-value pnl-positive' : (value < 0 ? 'stats-value pnl-negative' : 'stats-value');
    }
});
