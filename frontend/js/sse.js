const SSE = {
    connection: null,
    reconnectDelay: 3000,
    maxReconnectDelay: 30000,
    
    connect() {
        if (this.connection) return;
        
        try {
            // MOCK SSE connect
            // this.connection = new EventSource('/api/sse/dashboard');
            console.log('SSE Connected (mock)');
            
            // Mock interval to simulate SSE messages
            setInterval(() => {
                const val = document.getElementById('kpi-active');
                if (val) {
                    let current = parseInt(val.textContent) || 0;
                    current += Math.floor(Math.random() * 3) - 1; // -1, 0, 1
                    if (current < 0) current = 0;
                    val.textContent = current;
                }
            }, 5000);
            
        } catch (e) {
            console.error('SSE connect failed', e);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('dashboard')) {
        SSE.connect();
    }
});
