// auth.js - Sistema de Autenticação Compartilhado
// Salve este arquivo como: auth.js

class AuthSystem {
    constructor() {
        this.API_URL = 'http://localhost:5000/api';
        this.currentUser = null;
        this.inactivityTimeout = null;
        this.inactivityLimit = 2 * 60 * 60 * 1000; // 2 horas em milissegundos
        this.init();
    }

    init() {
        // Carregar usuário do armazenamento
        this.loadUser();
        
        // Verificar se está em página protegida
        if (this.isProtectedPage() && !this.isAuthenticated()) {
            this.redirectToLogin();
        }
        
        // Se estiver autenticado, atualizar UI
        if (this.isAuthenticated()) {
            this.updateUserUI();
            this.setupInactivityMonitor();
        }
    }

    // Configurar monitoramento de inatividade
    setupInactivityMonitor() {
        // Eventos que resetam o timer de inatividade
        const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
        
        // Resetar timer quando houver atividade
        events.forEach(event => {
            document.addEventListener(event, () => this.resetInactivityTimer(), true);
        });

        // Iniciar o timer
        this.resetInactivityTimer();
    }

    // Resetar timer de inatividade
    resetInactivityTimer() {
        // Limpar timeout anterior
        if (this.inactivityTimeout) {
            clearTimeout(this.inactivityTimeout);
        }

        // Criar novo timeout
        this.inactivityTimeout = setTimeout(() => {
            this.logoutByInactivity();
        }, this.inactivityLimit);

        // Salvar última atividade
        sessionStorage.setItem('lastActivity', new Date().getTime().toString());
    }

    // Logout por inatividade
    logoutByInactivity() {
        alert('Sua sessão expirou por inatividade. Você será redirecionado para a tela de login.');
        this.logout();
    }

    // Verificar se a página atual precisa de autenticação
    isProtectedPage() {
        const currentPage = window.location.pathname;
        const protectedPages = ['dashboard.html', 'registros.html', 'cartoes.html'];
        return protectedPages.some(page => currentPage.includes(page));
    }

    // Verificar se usuário está autenticado
    isAuthenticated() {
        return this.currentUser !== null;
    }

    // Salvar usuário no sessionStorage
    saveUser(userData) {
        this.currentUser = userData;
        sessionStorage.setItem('currentUser', JSON.stringify(userData));
    }

    // Carregar usuário do sessionStorage
    loadUser() {
        const userData = sessionStorage.getItem('currentUser');
        if (userData) {
            try {
                this.currentUser = JSON.parse(userData);
            } catch (e) {
                console.error('Erro ao carregar dados do usuário:', e);
                this.currentUser = null;
            }
        }
    }

    // Obter usuário atual
    getCurrentUser() {
        return this.currentUser;
    }

    // Fazer login
    async login(usuario, pin) {
        try {
            const response = await fetch(`${this.API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ usuario, pin })
            });

            const result = await response.json();

            if (result.success) {
                this.saveUser(result.data.usuario);
                return { success: true, user: result.data.usuario };
            } else {
                return { success: false, message: result.message };
            }
        } catch (error) {
            console.error('Erro no login:', error);
            return { success: false, message: 'Erro ao conectar com o servidor' };
        }
    }

    // Fazer logout
    logout() {
        this.currentUser = null;
        sessionStorage.removeItem('currentUser');
        this.redirectToLogin();
    }

    // Redirecionar para login
    redirectToLogin() {
        window.location.href = 'login.html';
    }

    // Redirecionar para dashboard
    redirectToDashboard() {
        window.location.href = 'dashboard.html';
    }

    // Atualizar UI com informações do usuário
    updateUserUI() {
        if (!this.currentUser) return;

        // Atualizar nome do usuário
        const userNameElements = document.querySelectorAll('.user-name');
        userNameElements.forEach(element => {
            element.textContent = this.currentUser.nome || 'Usuário';
        });

        // Atualizar role/função
        const userRoleElements = document.querySelectorAll('.user-role');
        userRoleElements.forEach(element => {
            const roleText = this.currentUser.role === 'admin' ? 'Administrador' : 'Inspetor de Qualidade';
            element.textContent = roleText;
        });

        // Atualizar avatar com inicial do nome
        const userAvatarElements = document.querySelectorAll('.user-avatar');
        userAvatarElements.forEach(element => {
            const inicial = (this.currentUser.nome || 'U').charAt(0).toUpperCase();
            element.textContent = inicial;
        });

        // Configurar botão de logout
        const logoutButtons = document.querySelectorAll('.logout-btn, #logout-btn');
        logoutButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                if (confirm('Deseja realmente sair do sistema?')) {
                    this.logout();
                }
            });
        });
    }

    // Obter nome do usuário
    getUserName() {
        return this.currentUser ? this.currentUser.nome : 'Usuário';
    }

    // Obter role do usuário
    getUserRole() {
        return this.currentUser ? this.currentUser.role : 'inspetor';
    }

    // Verificar se é admin
    isAdmin() {
        return this.currentUser && this.currentUser.role === 'admin';
    }
}

// Criar instância global
const auth = new AuthSystem();

// Exportar para uso global
window.auth = auth;