document.addEventListener('DOMContentLoaded', () => {
    // SİZİN TARAFINIZDAN SAĞLANAN FIREBASE YAPILANDIRMASI
    const firebaseConfig = {
        apiKey: "AIzaSyDkJch-8B46dpZSB-pMSR4q1uvzadCVekE",
        authDomain: "aviator-90c8b.firebaseapp.com",
        databaseURL: "https://aviator-90c8b-default-rtdb.firebaseio.com",
        projectId: "aviator-90c8b",
        storageBucket: "aviator-90c8b.appspot.com",
        messagingSenderId: "823763988442",
        appId: "1:823763988442:web:16a797275675a219c3dae3",
        measurementId: "G-EXN4S71F2Z"
    };
    // -------------------------------------------------------------

    // Firebase'i başlat
    firebase.initializeApp(firebaseConfig);
    const auth = firebase.auth();

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

    let statusInterval;

    // --- AUTHENTICATION (KİMLİK DOĞRULAMA) ---
    loginButton.addEventListener('click', () => {
        const email = emailInput.value;
        const password = passwordInput.value;
        loginError.textContent = "";
        auth.signInWithEmailAndPassword(email, password)
            .catch(error => {
                loginError.textContent = "Hatalı e-posta veya şifre.";
                console.error("Giriş hatası:", error);
            });
    });

    logoutButton.addEventListener('click', () => {
        auth.signOut();
    });

    auth.onAuthStateChanged(user => {
        if (user) {
            loginContainer.style.display = 'none';
            appContainer.style.display = 'flex';
            getStatus();
            statusInterval = setInterval(getStatus, 5000);
        } else {
            loginContainer.style.display = 'flex';
            appContainer.style.display = 'none';
            if (statusInterval) clearInterval(statusInterval);
        }
    });

    // --- API İSTEKLERİ ---
    async function fetchApi(endpoint, options = {}) {
        const user = auth.currentUser;
        if (!user) {
            console.error("Kullanıcı giriş yapmamış.");
            alert("Lütfen tekrar giriş yapın.");
            return null;
        }
        const idToken = await user.getIdToken(true); // Token'ı yenile
        
        const headers = {
            ...options.headers,
            'Authorization': `Bearer ${idToken}`
        };

        if (options.body) {
            headers['Content-Type'] = 'application/json';
        }

        const response = await fetch(endpoint, { ...options, headers });
        
        if (!response.ok) {
            const errorData = await response.json();
            alert(`Hata: ${errorData.detail || response.statusText}`);
            return null;
        }
        return response.json();
    }
    
    const updateUI = (data) => {
        if (!data) return;
        statusMessageSpan.textContent = data.status_message;
        currentSymbolSpan.textContent = data.symbol || 'N/A';
        lastSignalSpan.textContent = data.last_signal || 'N/A';
        
        if (data.is_running) {
            startButton.disabled = true;
            stopButton.disabled = false;
            symbolInput.disabled = true;
            symbolInput.value = data.symbol;
            statusMessageSpan.className = 'status-running';
        } else {
            startButton.disabled = false;
            stopButton.disabled = true;
            symbolInput.disabled = false;
            statusMessageSpan.className = 'status-stopped';
        }

        if (data.in_position) {
            positionStatusSpan.textContent = 'Evet';
            positionStatusSpan.className = 'status-in-position';
        } else {
            positionStatusSpan.textContent = 'Hayır';
            positionStatusSpan.className = '';
        }
    };

    const getStatus = async () => {
        const data = await fetchApi('/api/status');
        updateUI(data);
    };

    startButton.addEventListener('click', async () => {
        const symbol = symbolInput.value.trim().toUpperCase();
        if (!symbol) {
            alert('Lütfen bir coin sembolü girin.');
            return;
        }
        const data = await fetchApi('/api/start', {
            method: 'POST',
            body: JSON.stringify({ symbol: symbol })
        });
        updateUI(data);
    });

    stopButton.addEventListener('click', async () => {
        const data = await fetchApi('/api/stop', { method: 'POST' });
        updateUI(data);
    });
});
