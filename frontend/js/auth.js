/**
 * Auth Logic
 * Handles login, signup, logout, and route guards.
 */

// ── Toast Notifications ────────────────────────────────────
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    toast.innerHTML = `<span>${icons[type] || ''}</span> ${message}`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
        if (container.children.length === 0) container.remove();
    }, 4000);
}

// ── Login Handler ──────────────────────────────────────────
async function handleLogin(e) {
    e.preventDefault();

    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const btn = document.getElementById('login-btn');

    if (!email || !password) {
        showToast('Please fill in all fields.', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Signing in...';

    try {
        const data = await API.request('/auth/login', {
            method: 'POST',
            body: { email, password },
            auth: false,
        });

        API.setToken(data.access_token);
        API.setUser(data.user);

        showToast('Login successful!', 'success');

        // Redirect based on role
        setTimeout(() => {
            if (data.user.role === 'admin') {
                window.location.href = '/admin.html';
            } else {
                window.location.href = '/dashboard.html';
            }
        }, 500);
    } catch (error) {
        showToast(error.message, 'error');
        btn.disabled = false;
        btn.innerHTML = 'Sign In';
    }
}

// ── Signup Handler ─────────────────────────────────────────
async function handleSignup(e) {
    e.preventDefault();

    const name = document.getElementById('signup-name').value.trim();
    const email = document.getElementById('signup-email').value.trim();
    const password = document.getElementById('signup-password').value;
    const confirmPassword = document.getElementById('signup-confirm').value;
    const btn = document.getElementById('signup-btn');

    if (!name || !email || !password) {
        showToast('Please fill in all fields.', 'error');
        return;
    }

    if (password !== confirmPassword) {
        showToast('Passwords do not match.', 'error');
        return;
    }

    if (password.length < 6) {
        showToast('Password must be at least 6 characters.', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Creating account...';

    try {
        await API.request('/auth/signup', {
            method: 'POST',
            body: { name, email, password },
            auth: false,
        });

        showToast('Account created! Redirecting to login...', 'success');

        setTimeout(() => {
            window.location.href = '/login.html';
        }, 1000);
    } catch (error) {
        showToast(error.message, 'error');
        btn.disabled = false;
        btn.innerHTML = 'Create Account';
    }
}

// ── Logout Handler ─────────────────────────────────────────
async function handleLogout() {
    try {
        await API.request('/auth/logout', { method: 'POST' });
    } catch (e) {
        // Token may already be invalid
    }
    API.clearToken();
    showToast('Logged out.', 'info');
    setTimeout(() => {
        window.location.href = '/login.html';
    }, 500);
}

// ── Route Guards ───────────────────────────────────────────
function requireAuth() {
    if (!API.isAuthenticated()) {
        window.location.href = '/login.html';
        return false;
    }
    return true;
}

function requireAdmin() {
    if (!requireAuth()) return false;
    if (!API.isAdmin()) {
        window.location.href = '/dashboard.html';
        return false;
    }
    return true;
}

function redirectIfAuthed() {
    if (API.isAuthenticated()) {
        const user = API.getUser();
        if (user && user.role === 'admin') {
            window.location.href = '/admin.html';
        } else {
            window.location.href = '/dashboard.html';
        }
    }
}

// ── Update Navbar ──────────────────────────────────────────
function updateNavbar() {
    const authLinks = document.getElementById('auth-links');
    if (!authLinks) return;

    if (API.isAuthenticated()) {
        const user = API.getUser();
        const dashLink = API.isAdmin() ? '/admin.html' : '/dashboard.html';
        authLinks.innerHTML = `
            <a href="${dashLink}">Dashboard</a>
            <a href="#" onclick="handleLogout(); return false;">Logout</a>
        `;
    } else {
        authLinks.innerHTML = `
            <a href="/login.html">Login</a>
            <a href="/signup.html">Sign Up</a>
        `;
    }
}

// Auto-update navbar on page load
document.addEventListener('DOMContentLoaded', updateNavbar);
