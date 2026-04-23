/**
 * Admin Dashboard Logic
 * User management, statistics display, and search functionality.
 */

document.addEventListener('DOMContentLoaded', () => {
    if (!requireAdmin()) return;

    loadStats();
    loadUsers();
    initSearch();
});

// ── Stats ──────────────────────────────────────────────────
async function loadStats() {
    try {
        const data = await API.request('/admin/stats');

        document.getElementById('stat-total-users').textContent = data.total_users;
        document.getElementById('stat-active-users').textContent = data.active_users;
        document.getElementById('stat-total-predictions').textContent = data.total_predictions;
        document.getElementById('stat-recent-signups').textContent = data.recent_signups;

    } catch (error) {
        showToast('Failed to load stats: ' + error.message, 'error');
    }
}

// ── Users Table ────────────────────────────────────────────
let allUsers = [];

async function loadUsers() {
    try {
        const data = await API.request('/admin/users');
        allUsers = data.users;
        renderUsers(allUsers);
    } catch (error) {
        showToast('Failed to load users: ' + error.message, 'error');
    }
}

function renderUsers(users) {
    const tbody = document.getElementById('users-tbody');
    if (!tbody) return;

    if (users.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                    No users found.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = users.map(user => {
        const statusClass = user.is_active ? 'active' : 'disabled';
        const statusText = user.is_active ? 'Active' : 'Disabled';
        const roleClass = user.role;
        const date = user.created_at ? new Date(user.created_at).toLocaleDateString() : '—';
        const lastLogin = user.last_login ? new Date(user.last_login).toLocaleDateString() : '—';

        return `
            <tr>
                <td>
                    <div style="font-weight: 600;">${escapeHtml(user.name)}</div>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(user.email)}</div>
                </td>
                <td><span class="role-badge ${roleClass}">${user.role}</span></td>
                <td><span class="status-badge ${statusClass}">● ${statusText}</span></td>
                <td>${user.login_count || 0}</td>
                <td>${user.total_usage || 0}</td>
                <td>${date}</td>
                <td>
                    ${user.role !== 'admin' ? `
                        <button class="btn btn-sm ${user.is_active ? 'btn-danger' : 'btn-primary'}"
                                onclick="toggleUserStatus(${user.id})"
                                id="toggle-btn-${user.id}">
                            ${user.is_active ? 'Disable' : 'Enable'}
                        </button>
                    ` : '<span style="color:var(--text-muted);font-size:0.8rem;">—</span>'}
                </td>
            </tr>
        `;
    }).join('');
}

// ── Toggle User Status ─────────────────────────────────────
async function toggleUserStatus(userId) {
    const btn = document.getElementById(`toggle-btn-${userId}`);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span>';
    }

    try {
        const data = await API.request('/admin/disable_user', {
            method: 'POST',
            body: { user_id: userId },
        });

        showToast(data.message, 'success');

        // Refresh data
        await loadUsers();
        await loadStats();
    } catch (error) {
        showToast(error.message, 'error');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = 'Toggle';
        }
    }
}

// ── Search ─────────────────────────────────────────────────
function initSearch() {
    const input = document.getElementById('user-search');
    if (!input) return;

    input.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();

        if (!query) {
            renderUsers(allUsers);
            return;
        }

        const filtered = allUsers.filter(user =>
            user.name.toLowerCase().includes(query) ||
            user.email.toLowerCase().includes(query) ||
            user.role.toLowerCase().includes(query)
        );

        renderUsers(filtered);
    });
}

// ── Utilities ──────────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
