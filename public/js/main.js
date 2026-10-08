/**
 * Steam 蒸汽猎手 - 客户端交互脚本
 * 主题切换 / 即时筛选 / 链接复制 / 移动端菜单
 */

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initMobileMenu();
  initLiveSearch();
  initCopyLink();
  initBackToTop();
});

// 1. 明暗主题切换与本地记忆
function initThemeToggle() {
  const toggleBtn = document.getElementById('themeToggleBtn');
  const html = document.documentElement;

  // 读取已保存主题或跟随系统
  const savedTheme = localStorage.getItem('sh_theme');
  if (savedTheme) {
    html.setAttribute('data-theme', savedTheme);
  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
    html.setAttribute('data-theme', 'light');
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const currentTheme = html.getAttribute('data-theme') || 'dark';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', newTheme);
      localStorage.setItem('sh_theme', newTheme);
    });
  }
}

// 2. 移动端抽屉菜单
function initMobileMenu() {
  const menuBtn = document.getElementById('mobileMenuBtn');
  const mainNav = document.getElementById('mainNav');

  if (menuBtn && mainNav) {
    menuBtn.addEventListener('click', () => {
      mainNav.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
      if (!mainNav.contains(e.target) && !menuBtn.contains(e.target) && mainNav.classList.contains('open')) {
        mainNav.classList.remove('open');
      }
    });
  }
}

// 3. 首页与列表页即时卡片筛选
function initLiveSearch() {
  const searchInput = document.getElementById('siteSearchInput');
  const postsGrid = document.getElementById('postsGrid');

  if (searchInput && postsGrid) {
    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.trim().toLowerCase();
      const cards = postsGrid.querySelectorAll('.post-card');

      cards.forEach(card => {
        const title = card.getAttribute('data-title') || '';
        const tags = card.getAttribute('data-tags') || '';
        if (!query || title.includes(query) || tags.includes(query)) {
          card.style.display = '';
        } else {
          card.style.display = 'none';
        }
      });
    });
  }
}

// 4. 一键复制文章链接
function initCopyLink() {
  const copyBtn = document.getElementById('copyArticleLinkBtn');
  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      const url = copyBtn.getAttribute('data-url') || window.location.href;
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(url);
        } else {
          const textarea = document.createElement('textarea');
          textarea.value = url;
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand('copy');
          document.body.removeChild(textarea);
        }
        const originalText = copyBtn.innerHTML;
        copyBtn.innerHTML = '✅ 链接已复制！';
        copyBtn.style.borderColor = 'var(--accent-green)';
        copyBtn.style.color = 'var(--accent-green)';
        setTimeout(() => {
          copyBtn.innerHTML = originalText;
          copyBtn.style.borderColor = '';
          copyBtn.style.color = '';
        }, 2200);
      } catch (err) {
        console.error('复制失败:', err);
      }
    });
  }
}

// 5. 平滑回到顶部
function initBackToTop() {
  const backToTopBtn = document.getElementById('backToTopBtn');
  if (backToTopBtn) {
    backToTopBtn.addEventListener('click', () => {
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });
  }
}
