// tg2emall 前端 JavaScript

// 暗黑模式管理
class ThemeManager {
    constructor() {
        this.theme = localStorage.getItem('theme') || this.getSystemTheme();
        this.init();
    }

    getSystemTheme() {
        const hour = new Date().getHours();
        return (hour >= 18 || hour <= 6) ? 'dark' : 'light';
    }

    init() {
        this.applyTheme(this.theme);
        this.createThemeToggle();
        this.bindEvents();
    }

    createThemeToggle() {
        const toggle = document.createElement('button');
        toggle.className = 'theme-toggle';
        toggle.innerHTML = this.theme === 'dark' ? '☀️' : '🌙';
        toggle.title = this.theme === 'dark' ? '切换到浅色模式' : '切换到深色模式';
        toggle.onclick = () => this.toggleTheme();
        document.body.appendChild(toggle);
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-bs-theme', theme);
        localStorage.setItem('theme', theme);
        
        // 更新主题切换按钮
        const toggle = document.querySelector('.theme-toggle');
        if (toggle) {
            toggle.innerHTML = theme === 'dark' ? '☀️' : '🌙';
            toggle.title = theme === 'dark' ? '切换到浅色模式' : '切换到深色模式';
        }
    }

    toggleTheme() {
        this.theme = this.theme === 'dark' ? 'light' : 'dark';
        this.applyTheme(this.theme);
    }

    bindEvents() {
        // 监听系统主题变化
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                if (!localStorage.getItem('theme')) {
                    this.theme = e.matches ? 'dark' : 'light';
                    this.applyTheme(this.theme);
                }
            });
        }
    }
}

// 搜索功能
class SearchManager {
    constructor() {
        this.bindEvents();
    }

    bindEvents() {
        // 搜索框自动完成
        const searchInputs = document.querySelectorAll('.search-input');
        searchInputs.forEach(input => {
            input.addEventListener('input', this.handleSearchInput.bind(this));
            input.addEventListener('keydown', this.handleSearchKeydown.bind(this));
        });

        // 搜索建议点击
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('search-suggestion')) {
                const query = e.target.textContent;
                this.performSearch(query);
            }
        });
    }

    handleSearchInput(e) {
        const query = e.target.value.trim();
        if (query.length > 2) {
            this.showSearchSuggestions(query);
        } else {
            this.hideSearchSuggestions();
        }
    }

    handleSearchKeydown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const query = e.target.value.trim();
            if (query) {
                this.performSearch(query);
            }
        }
    }

    showSearchSuggestions(query) {
        // 这里可以添加搜索建议逻辑
        // 暂时使用静态建议
        const suggestions = [
            '百度网盘', '阿里云盘', '夸克网盘', '移动云盘',
            '电影', '电视剧', '软件', '游戏', '音乐', '电子书'
        ].filter(item => item.includes(query));

        if (suggestions.length > 0) {
            this.renderSuggestions(suggestions);
        }
    }

    renderSuggestions(suggestions) {
        let container = document.querySelector('.search-suggestions-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'search-suggestions-container position-absolute w-100 bg-white border rounded shadow-lg';
            container.style.zIndex = '1000';
            document.querySelector('.search-form').appendChild(container);
        }

        container.innerHTML = suggestions.map(suggestion => 
            `<div class="search-suggestion p-2 cursor-pointer hover-bg-light">${suggestion}</div>`
        ).join('');

        container.style.display = 'block';
    }

    hideSearchSuggestions() {
        const container = document.querySelector('.search-suggestions-container');
        if (container) {
            container.style.display = 'none';
        }
    }

    performSearch(query) {
        window.location.href = `/search?q=${encodeURIComponent(query)}`;
    }
}

// 图片懒加载
class LazyLoader {
    constructor() {
        this.observer = null;
        this.init();
    }

    init() {
        if ('IntersectionObserver' in window) {
            this.observer = new IntersectionObserver(this.handleIntersection.bind(this), {
                rootMargin: '50px 0px',
                threshold: 0.01
            });

            this.observeImages();
        } else {
            // 降级处理
            this.loadAllImages();
        }
    }

    observeImages() {
        const images = document.querySelectorAll('img[data-src]');
        images.forEach(img => this.observer.observe(img));
    }

    handleIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                this.loadImage(img);
                this.observer.unobserve(img);
            }
        });
    }

    loadImage(img) {
        const src = img.dataset.src;
        if (src) {
            img.src = src;
            img.removeAttribute('data-src');
            img.classList.add('loaded');
        }
    }

    loadAllImages() {
        const images = document.querySelectorAll('img[data-src]');
        images.forEach(img => this.loadImage(img));
    }
}

// 工具函数
class Utils {
    static formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return '刚刚';
        if (minutes < 60) return `${minutes}分钟前`;
        if (hours < 24) return `${hours}小时前`;
        if (days < 7) return `${days}天前`;
        return date.toLocaleDateString();
    }

    static copyToClipboard(text) {
        if (navigator.clipboard) {
            return navigator.clipboard.writeText(text);
        } else {
            // 降级处理
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            return Promise.resolve();
        }
    }

    static showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => {
            document.body.removeChild(toast);
        });
    }

    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化主题管理器
    new ThemeManager();

    // 初始化搜索管理器
    new SearchManager();

    // 初始化图片懒加载
    new LazyLoader();

    // 添加页面加载动画
    document.body.classList.add('loaded');

    // 绑定全局事件
    bindGlobalEvents();
});

// 绑定全局事件
function bindGlobalEvents() {
    // 返回顶部按钮
    const backToTop = document.createElement('button');
    backToTop.className = 'btn btn-primary position-fixed';
    backToTop.style.cssText = 'bottom: 20px; right: 20px; z-index: 1000; display: none; border-radius: 50%; width: 50px; height: 50px;';
    backToTop.innerHTML = '<i class="fas fa-arrow-up"></i>';
    backToTop.onclick = () => window.scrollTo({ top: 0, behavior: 'smooth' });
    document.body.appendChild(backToTop);

    // 监听滚动事件
    window.addEventListener('scroll', Utils.debounce(() => {
        if (window.pageYOffset > 300) {
            backToTop.style.display = 'block';
        } else {
            backToTop.style.display = 'none';
        }
    }, 100));

    // 键盘快捷键
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K 聚焦搜索框
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('.search-input');
            if (searchInput) {
                searchInput.focus();
            }
        }

        // ESC 键清除搜索建议
        if (e.key === 'Escape') {
            const container = document.querySelector('.search-suggestions-container');
            if (container) {
                container.style.display = 'none';
            }
        }
    });

    // 点击外部关闭搜索建议
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-form')) {
            const container = document.querySelector('.search-suggestions-container');
            if (container) {
                container.style.display = 'none';
            }
        }
    });
}

// 导出工具函数供其他脚本使用
window.Utils = Utils;
