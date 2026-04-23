/**
 * API Helper
 * Centralized HTTP client with JWT token management.
 */

const API = (() => {
    const BASE_URL = '/api';

    /**
     * Get stored JWT token.
     */
    function getToken() {
        return localStorage.getItem('access_token');
    }

    /**
     * Set JWT token.
     */
    function setToken(token) {
        localStorage.setItem('access_token', token);
    }

    /**
     * Remove JWT token.
     */
    function clearToken() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
    }

    /**
     * Get stored user data.
     */
    function getUser() {
        const data = localStorage.getItem('user');
        return data ? JSON.parse(data) : null;
    }

    /**
     * Store user data.
     */
    function setUser(user) {
        localStorage.setItem('user', JSON.stringify(user));
    }

    /**
     * Check if user is authenticated.
     */
    function isAuthenticated() {
        return !!getToken();
    }

    /**
     * Check if current user is admin.
     */
    function isAdmin() {
        const user = getUser();
        return user && user.role === 'admin';
    }

    /**
     * Build headers with optional auth.
     */
    function buildHeaders(includeAuth = true, isJson = true) {
        const headers = {};
        if (isJson) {
            headers['Content-Type'] = 'application/json';
        }
        if (includeAuth) {
            const token = getToken();
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }
        return headers;
    }

    /**
     * Make a JSON API request.
     */
    async function request(endpoint, options = {}) {
        const url = `${BASE_URL}${endpoint}`;
        const {
            method = 'GET',
            body = null,
            auth = true,
            json = true,
        } = options;

        const config = {
            method,
            headers: buildHeaders(auth, json && !(body instanceof FormData)),
        };

        if (body) {
            if (body instanceof FormData) {
                config.body = body;
                // Let browser set Content-Type for FormData
                delete config.headers['Content-Type'];
            } else {
                config.body = JSON.stringify(body);
            }
        }

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                // Handle auth errors
                if (response.status === 401) {
                    clearToken();
                    if (window.location.pathname !== '/login.html') {
                        window.location.href = '/login.html';
                    }
                }
                throw new Error(data.error || `HTTP ${response.status}`);
            }

            return data;
        } catch (error) {
            if (error.message === 'Failed to fetch') {
                throw new Error('Network error. Please check your connection.');
            }
            throw error;
        }
    }

    /**
     * Upload a file to a prediction endpoint.
     */
    async function uploadFile(endpoint, file) {
        const formData = new FormData();
        formData.append('file', file);
        return request(endpoint, { method: 'POST', body: formData });
    }

    return {
        getToken,
        setToken,
        clearToken,
        getUser,
        setUser,
        isAuthenticated,
        isAdmin,
        request,
        uploadFile,
    };
})();
