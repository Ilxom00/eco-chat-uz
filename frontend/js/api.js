const API = {
    baseURL: '/api',

    async fetch(endpoint, options = {}) {
        const token = localStorage.getItem('token');
        const headers = {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` }),
            ...options.headers
        };

        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, { ...options, headers });
            
            if (response.status === 401) {
                localStorage.removeItem('token');
                window.location.href = 'login.html';
                return null;
            }
            
            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.message || `HTTP error ${response.status}`);
            }
            
            // Handle blob (for files)
            const contentType = response.headers.get('content-type');
            if (contentType && (contentType.includes('application/pdf') || contentType.includes('application/vnd.ms-excel') || contentType.includes('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))) {
                return response.blob();
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    // Auth
    async login(username, password) {
        return this.fetch('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    },

    // Dashboard
    async getDashboardStats() {
        return this.fetch('/dashboard/stats');
    },
    async getDashboardEmployees(params) {
        const q = new URLSearchParams(params).toString();
        return this.fetch(`/dashboard/employees?${q}`);
    },
    async getEmployeeDetail(id) {
        return this.fetch(`/employees/${id}`);
    },

    // Topics
    async getTopics() {
        return this.fetch('/topics');
    },
    async createTopic(data) {
        return this.fetch('/topics', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // Questions
    async getQuestions(topicId, params) {
        const q = new URLSearchParams(params).toString();
        return this.fetch(`/topics/${topicId}/questions?${q}`);
    },

    // Branches
    async getBranches() {
        return this.fetch('/branches');
    },

    // Reports
    async downloadReport(type, params) {
        const q = new URLSearchParams(params).toString();
        return this.fetch(`/reports/download/${type}?${q}`);
    },

    // Audit
    async getAuditLogs(params) {
        const q = new URLSearchParams(params).toString();
        return this.fetch(`/audit-logs?${q}`);
    }
};

window.API = API;
