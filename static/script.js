document.addEventListener('DOMContentLoaded', () => {
    // HTML elementlerini seç
    const symbolInput = document.getElementById('symbol-input');
    const startButton = document.getElementById('start-button');
    const stopButton = document.getElementById('stop-button');
    
    const statusMessageSpan = document.getElementById('status-message');
    const currentSymbolSpan = document.getElementById('current-symbol');
    const positionStatusSpan = document.getElementById('position-status');
    const lastSignalSpan = document.getElementById('last-signal');

    let statusInterval;

    // API'den botun durumunu çeken ve arayüzü güncelleyen fonksiyon
    const getStatus = async () => {
        try {
            const response = await fetch('/api/status');
            if (!response.ok) {
                throw new Error('Sunucuyla iletişim kurulamadı.');
            }
            const data = await response.json();
            updateUI(data);
        } catch (error) {
            console.error('Durum güncellenirken hata:', error);
            statusMessageSpan.textContent = 'Sunucuya bağlanılamıyor!';
            statusMessageSpan.className = 'status-stopped';
            // Durum alınamazsa periyodik sorguyu durdur
            if (statusInterval) clearInterval(statusInterval);
        }
    };

    // Gelen verilere göre arayüzü güncelleyen fonksiyon
    const updateUI = (data) => {
        statusMessageSpan.textContent = data.status_message;
        currentSymbolSpan.textContent = data.symbol || 'N/A';
        lastSignalSpan.textContent = data.last_signal || 'N/A';
        
        // is_running durumuna göre butonları ve renkleri ayarla
        if (data.is_running) {
            startButton.disabled = true;
            stopButton.disabled = false;
            statusMessageSpan.className = 'status-running';
            symbolInput.disabled = true;
            symbolInput.value = data.symbol;
        } else {
            startButton.disabled = false;
            stopButton.disabled = true;
            statusMessageSpan.className = 'status-stopped';
            symbolInput.disabled = false;
        }

        // in_position durumunu ayarla
        if (data.in_position) {
            positionStatusSpan.textContent = 'Evet';
            positionStatusSpan.className = 'status-in-position';
        } else {
            positionStatusSpan.textContent = 'Hayır';
            positionStatusSpan.className = '';
        }
    };

    // Başlat butonuna tıklanınca
    startButton.addEventListener('click', async () => {
        const symbol = symbolInput.value.trim();
        if (!symbol) {
            alert('Lütfen bir coin sembolü girin (örn: BTCUSDT).');
            return;
        }

        try {
            const response = await fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol: symbol }),
            });
            const data = await response.json();
            updateUI(data);

            if (response.ok && !statusInterval) {
                 // Bot başarıyla başlarsa, durumu periyodik olarak kontrol etmeye başla
                statusInterval = setInterval(getStatus, 3000); // 3 saniyede bir
            }
        } catch (error) {
            console.error('Bot başlatılırken hata:', error);
        }
    });

    // Durdur butonuna tıklanınca
    stopButton.addEventListener('click', async () => {
        try {
            const response = await fetch('/api/stop', { method: 'POST' });
            const data = await response.json();
            updateUI(data);

            // Bot durunca periyodik sorguyu temizle
            if (statusInterval) {
                clearInterval(statusInterval);
                statusInterval = null;
            }
        } catch (error) {
            console.error('Bot durdurulurken hata:', error);
        }
    });

    // Sayfa yüklendiğinde mevcut durumu hemen al
    getStatus();
    // Bot zaten çalışıyorsa durumu periyodik olarak kontrol etmeye başla
    if (stopButton.disabled === false) {
        statusInterval = setInterval(getStatus, 3000);
    }
});