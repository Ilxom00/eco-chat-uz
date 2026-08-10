document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        // We are on login page
        if (localStorage.getItem('token')) {
            window.location.href = 'index.html';
        }

        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('loginBtn');
            const errorMsg = document.getElementById('errorMessage');
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            btn.disabled = true;
            btn.textContent = 'Кутилмоқда...';
            errorMsg.style.display = 'none';

            try {
                const res = await API.login(username, password);
                
                if (res.token) {
                    localStorage.setItem('token', res.token);
                    window.location.href = 'index.html';
                }
            } catch (err) {
                errorMsg.style.display = 'block';
                errorMsg.textContent = err.message || 'Хатолик юз берди';
            } finally {
                btn.disabled = false;
                btn.textContent = 'Кириш';
            }
        });
    } else {
        // We are on admin page
        if (!localStorage.getItem('token')) {
            window.location.href = 'login.html';
        }

        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                localStorage.removeItem('token');
                window.location.href = 'login.html';
            });
        }
    }
});
