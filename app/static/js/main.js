document.addEventListener('DOMContentLoaded', function() {
    // 页面元素
    const pageSections = document.querySelectorAll('.page-section');
    const pageTitle = document.getElementById('page-title');
    const logoutBtn = document.getElementById('logout-btn');
    const notification = document.getElementById('notification');
    const closeNotificationBtn = document.getElementById('close-notification');
    const notificationTitle = document.getElementById('notification-title');
    const notificationMessage = document.getElementById('notification-message');
    const notificationIcon = document.getElementById('notification-icon');
    const currentTime = document.getElementById('current-time');
    
    // 模态框元素
    const fileEditModal = document.getElementById('file-edit-modal');
    const closeEditModalBtn = document.getElementById('close-edit-modal');
    const fileContentText = document.getElementById('file-content-text');
    const saveFileBtn = document.getElementById('save-file-btn');
    const deployFileBtn = document.getElementById('deploy-file-btn');
    const editModalTitle = document.getElementById('edit-modal-title');
    
    const deploymentProgressModal = document.getElementById('deployment-progress-modal');
    const progressBar = document.getElementById('progress-bar');
    const progressPercentage = document.getElementById('progress-percentage');
    const progressStatus = document.getElementById('progress-status');
    const progressOutput = document.getElementById('progress-output');
    const closeProgressModalBtn = document.getElementById('close-progress-modal');
    const progressLoading = document.getElementById('progress-loading');
    const progressIcon = document.getElementById('progress-icon');
    
    // 文件管理相关元素
    const fileUploadInput = document.getElementById('file-upload');
    const refreshLocalFilesBtn = document.getElementById('refresh-local-files');
    const localFilesBody = document.getElementById('local-files-body');
    const localFileCount = document.getElementById('local-file-count');
    
    const systemTypeSelect = document.getElementById('system-type-select');
    const refreshGiteeFilesBtn = document.getElementById('refresh-gitee-files');
    const giteeFilesBody = document.getElementById('gitee-files-body');
    
    const refreshDeploymentsBtn = document.getElementById('refresh-deployments');
    const deploymentsBody = document.getElementById('deployments-body');
    
    // 设置相关元素
    const changePasswordForm = document.getElementById('change-password-form');
    const upgradeComposeBtn = document.getElementById('upgrade-compose-btn');
    const composeVersionWarning = document.getElementById('compose-version-warning');
    const giteeSettingsForm = document.getElementById('gitee-settings-form');
    const giteeTokenInput = document.getElementById('gitee-token');
    const clearGiteeTokenBtn = document.getElementById('clear-gitee-token');
    
    // 当前状态
    let currentEditingFile = null;
    let currentDeploymentId = null;
    let statusCheckInterval = null;
    
    // 初始化
    init();
    
    // 添加返回按钮到页面卡片
    function addBackButtons() {
        const pages = ['local-files', 'gitee-files', 'deployments', 'settings'];
        pages.forEach(pageId => {
            const section = document.getElementById(`${pageId}-section`);
            if (section) {
                // 查找卡片容器（第一个div元素）
                const cardContainer = section.querySelector('div.bg-white');
                if (cardContainer) {
                    // 查找h3标题元素作为头部
                    const headerElement = cardContainer.querySelector('h3');
                    if (headerElement) {
                        // 检查是否已经有返回按钮
                        if (!headerElement.querySelector('.back-button')) {
                            // 创建返回按钮
                            const backButton = document.createElement('button');
                            backButton.className = 'back-button text-blue-600 hover:text-blue-900 ml-auto';
                            backButton.innerHTML = '<i class="fa fa-arrow-left mr-1"></i> 返回';
                            backButton.addEventListener('click', function() {
                                navigateToPage('dashboard');
                            });
                            
                            // 修改h3样式为flex布局
                            headerElement.style.display = 'flex';
                            headerElement.style.justifyContent = 'flex-start';
                            headerElement.style.alignItems = 'center';
                            
                            // 添加按钮到h3元素
                            headerElement.appendChild(backButton);
                        }
                    }
                }
            }
        });
    }
    
    // 初始化函数
    function init() {
        // 检查认证状态
        checkAuth();
        
        // 加载Docker统计信息
        loadDockerStats();
        loadLocalFiles();
        loadSystemTypes();
        
        // 加载Gitee Token
        loadGiteeToken();
        
        // 添加返回按钮
        addBackButtons();
        
        // 事件监听器
        setupEventListeners();
    }
    
    // 加载Gitee Token
    async function loadGiteeToken() {
        if (!giteeTokenInput) return;
        
        try {
            const response = await fetch('/api/settings/gitee-token');
            if (response.ok) {
                const data = await response.json();
                if (data.token) {
                    giteeTokenInput.value = data.token;
                }
            }
        } catch (error) {
            console.error('加载Gitee Token失败:', error);
        }
    }
    
    // 获取Gitee Token
    function getGiteeToken() {
        return giteeTokenInput ? giteeTokenInput.value.trim() : '';
    }
    
    // 创建带Gitee Token的headers
    function createGiteeHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        const token = getGiteeToken();
        if (token) {
            headers['X-Gitee-Token'] = token;
        }
        return headers;
    }
    
    // 设置事件监听器
    function setupEventListeners() {
        // 快速操作按钮点击事件
        document.querySelectorAll('.action-card[data-target]').forEach(button => {
            button.addEventListener('click', function() {
                const target = this.getAttribute('data-target');
                navigateToPage(target);
            });
        });
        
        // 搜索框事件监听器
        const localFileSearch = document.getElementById('local-file-search');
        if (localFileSearch) {
            localFileSearch.addEventListener('input', function() {
                // 使用保存的原始文件列表进行过滤显示
                const searchKeyword = this.value.trim().toLowerCase();
                const filteredFiles = searchKeyword ? 
                    originalLocalFiles.filter(file => file.filename.toLowerCase().includes(searchKeyword)) : 
                    originalLocalFiles;
                
                // 更新文件计数
                localFileCount.textContent = filteredFiles.length;
                localFilesBody.innerHTML = '';
                
                if (filteredFiles.length > 0) {
                    filteredFiles.forEach(file => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td class="px-6 py-4 whitespace-nowrap">
                                <div class="flex items-center">
                                    <i class="fa fa-file-text-o text-blue-600 mr-3"></i>
                                    <div class="font-medium text-gray-900">${escapeHTML(file.filename)}</div>
                                </div>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span class="text-sm text-gray-900">${escapeHTML(file.system_name)}</span>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span class="text-sm text-gray-900">${formatFileSize(file.size)}</span>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span class="text-sm text-gray-500 timestamp">${formatDate(file.mtime)}</span>
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                <div class="flex space-x-2">
                                    <button class="text-blue-600 hover:text-blue-900 edit-file-btn" data-file-path="${escapeHTML(file.file_path)}" data-filename="${escapeHTML(file.filename)}">
                                        <i class="fa fa-edit"></i> 编辑
                                    </button>
                                    <button class="text-green-600 hover:text-green-900 deploy-file-btn" data-file-path="${escapeHTML(file.file_path)}">
                                        <i class="fa fa-rocket"></i> 部署
                                    </button>
                                </div>
                            <td>
                        `;
                        localFilesBody.appendChild(row);
                    });
                    
                    // 添加按钮事件
                    document.querySelectorAll('.edit-file-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            const filePath = this.getAttribute('data-file-path');
                            const filename = this.getAttribute('data-filename');
                            editFile(filePath, filename);
                        });
                    });
                    
                    document.querySelectorAll('.deploy-file-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            const filePath = this.getAttribute('data-file-path');
                            deployFile(filePath);
                        });
                    });
                } else {
                    localFilesBody.innerHTML = `
                        <tr>
                            <td colspan="5" class="px-6 py-10 text-center text-gray-500">
                                <i class="fa fa-file-text-o text-3xl mb-2 block"></i>
                                没有找到匹配的文件
                            <td>
                        <tr>
                    `;
                }
            });
        }
        
        const giteeFileSearch = document.getElementById('gitee-file-search');
        if (giteeFileSearch) {
            giteeFileSearch.addEventListener('input', function() {
                // 使用保存的原始文件列表进行过滤显示
                const searchKeyword = this.value.trim().toLowerCase();
                const filteredFiles = searchKeyword ? 
                    originalGiteeFiles.filter(file => file.name.toLowerCase().includes(searchKeyword)) : 
                    originalGiteeFiles;
                
                giteeFilesBody.innerHTML = '';
                
                if (filteredFiles.length > 0) {
                    filteredFiles.forEach(file => {
                        const existsIcon = file.exists_locally ? 
                            '<i class="fa fa-check-circle text-green-600"></i>' : 
                            '<i class="fa fa-times-circle text-gray-400"></i>';
                        const existsText = file.exists_locally ? '已下载' : '未下载';
                        const existsClass = file.exists_locally ? 'text-green-600' : 'text-gray-500';
                        const downloadBtn = file.exists_locally ? 
                            `<button class="text-blue-600 hover:text-blue-900 edit-file-btn ml-2" data-system="${escapeHTML(currentGiteeSystemType)}" data-filename="${escapeHTML(file.name)}">
                                <i class="fa fa-edit"></i> 编辑
                            </button>` : 
                            `<button class="text-green-600 hover:text-green-900 download-file-btn ml-2" data-url="${escapeHTML(file.download_url)}" data-system="${escapeHTML(currentGiteeSystemType)}" data-filename="${escapeHTML(file.name)}">
                                <i class="fa fa-download"></i> 下载
                            </button>`;
                        
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td class="px-6 py-4 whitespace-nowrap">
                                <div class="flex items-center">
                                    <i class="fa fa-file-text-o text-blue-600 mr-3"></i>
                                    <div class="font-medium text-gray-900">${escapeHTML(file.name)}</div>
                                </div>
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span class="text-sm ${existsClass} flex items-center">
                                    ${existsIcon} ${existsText}
                                </span>
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                <div class="flex space-x-2">
                                    ${file.exists_locally ? `
                                        <button class="text-green-600 hover:text-green-900 deploy-file-btn" data-file-path="/app/data/${escapeHTML(currentGiteeSystemType)}/${escapeHTML(file.name)}">
                                            <i class="fa fa-rocket"></i> 部署
                                        </button>
                                    ` : ''}
                                    ${downloadBtn}
                                </div>
                            </td>
                        `;
                        giteeFilesBody.appendChild(row);
                    });
                    
                    // 添加按钮事件
                    document.querySelectorAll('.download-file-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            const url = this.getAttribute('data-url');
                            const system = this.getAttribute('data-system');
                            const filename = this.getAttribute('data-filename');
                            downloadGiteeFile(url, system, filename);
                        });
                    });
                    
                    document.querySelectorAll('.edit-file-btn[data-system]').forEach(btn => {
                        btn.addEventListener('click', function() {
                            const system = this.getAttribute('data-system');
                            const filename = this.getAttribute('data-filename');
                            const filePath = `/app/data/${system}/${filename}`;
                            editFile(filePath, filename);
                        });
                    });
                    
                    document.querySelectorAll('.deploy-file-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            const filePath = this.getAttribute('data-file-path');
                            deployFile(filePath);
                        });
                    });
                } else {
                    giteeFilesBody.innerHTML = `
                        <tr>
                            <td colspan="3" class="px-6 py-10 text-center text-gray-500">
                                <i class="fa fa-file-text-o text-3xl mb-2 block"></i>
                                没有找到匹配的文件
                            </td>
                        </tr>
                    `;
                }
            });
        }
        
        // 导航链接点击已移除，因为侧边栏已取消
        
        // 登出按钮
        logoutBtn.addEventListener('click', logout);
        
        // 通知关闭
        closeNotificationBtn.addEventListener('click', hideNotification);
        
        // 文件上传
        fileUploadInput.addEventListener('change', handleFileUpload);
        
        // 刷新本地文件
        refreshLocalFilesBtn.addEventListener('click', loadLocalFiles);
        
        // 系统类型选择
        systemTypeSelect.addEventListener('change', handleSystemTypeChange);
        
        // 刷新Gitee文件
        refreshGiteeFilesBtn.addEventListener('click', loadGiteeFiles);
        
        // 刷新部署记录
        refreshDeploymentsBtn.addEventListener('click', loadDeployments);
        
        // Gitee Token设置
        if (giteeSettingsForm) {
            giteeSettingsForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                const token = giteeTokenInput.value.trim();
                
                try {
                    const response = await fetch('/api/settings/gitee-token', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ token: token })
                    });
                    
                    if (response.ok) {
                        showNotification('success', '设置成功', 'Gitee Token已保存');
                    } else {
                        const errorData = await response.json();
                        showNotification('error', '设置失败', errorData.message || '保存失败');
                    }
                } catch (error) {
                    console.error('Save Gitee token error:', error);
                    showNotification('error', '设置失败', '网络错误，请稍后重试');
                }
            });
        }
        
        // 清除Gitee Token
        if (clearGiteeTokenBtn) {
            clearGiteeTokenBtn.addEventListener('click', async function() {
                if (confirm('确定要清除Gitee Token吗？')) {
                    try {
                        const response = await fetch('/api/settings/gitee-token', {
                            method: 'DELETE'
                        });
                        
                        if (response.ok) {
                            giteeTokenInput.value = '';
                            showNotification('success', '操作成功', 'Gitee Token已清除');
                        } else {
                            showNotification('error', '操作失败', '清除失败');
                        }
                    } catch (error) {
                        console.error('Clear Gitee token error:', error);
                        showNotification('error', '操作失败', '网络错误，请稍后重试');
                    }
                }
            });
        }
        
        // 模态框事件
        closeEditModalBtn.addEventListener('click', closeEditModal);
        saveFileBtn.addEventListener('click', saveFile);
        deployFileBtn.addEventListener('click', saveAndDeployFile);
        closeProgressModalBtn.addEventListener('click', closeProgressModal);
        

        
        // 密码修改表单
        changePasswordForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleChangePassword();
        });
        
        // 点击模态框外部关闭
        fileEditModal.addEventListener('click', function(e) {
            if (e.target === fileEditModal) closeEditModal();
        });
        
        deploymentProgressModal.addEventListener('click', function(e) {
            if (e.target === deploymentProgressModal && !progressLoading.classList.contains('hidden')) {
                closeProgressModal();
            }
        });
    }
    
    // 检查认证状态
    async function checkAuth() {
        try {
            const response = await fetch('/api/check-auth');
            const data = await response.json();
            
            if (!response.ok || !data.authenticated) {
                window.location.href = '/login';
                return false;
            }
            
            return true;
        } catch (error) {
            console.error('Auth check failed:', error);
            window.location.href = '/login';
            return false;
        }
    }
    
    // 导航到页面
    function navigateToPage(pageId) {
        // 不再需要更新侧边栏导航链接，因为侧边栏已取消
        // 移除navLinks引用以修复错误
        
        // 更新页面标题
        const titleMap = {
            'dashboard': '首页',
            'local-files': '本地文件',
            'gitee-files': 'Gitee 文件',
            'deployments': '部署记录',
            'settings': '设置'
        };
        
        // 只有当pageTitle元素存在时才设置其textContent
        if (pageTitle) {
            pageTitle.textContent = titleMap[pageId] || '仪表盘';
        }
        
        // 显示对应页面
        pageSections.forEach(section => {
            section.classList.add('hidden');
        });
        
        const targetSection = document.getElementById(`${pageId}-section`);
        if (targetSection) {
            targetSection.classList.remove('hidden');
        }
        
        // 预加载数据
        if (pageId === 'local-files') {
            loadLocalFiles();
        } else if (pageId === 'deployments') {
            loadDeployments();
        }
    }
    
    // 显示通知
    function showNotification(type, title, message) {
        // 先确保通知可见
        notification.style.display = 'block';
        
        notificationTitle.textContent = title;
        notificationMessage.textContent = message;
        
        // 重置类
        notification.className = 'fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 transition-transform duration-300 max-w-sm';
        notification.classList.remove('translate-x-full');
        
        // 设置类型样式
        switch (type) {
            case 'success':
                notification.classList.add('success');
                notificationIcon.className = 'fa fa-check-circle text-xl mr-3 mt-0.5 text-green-500';
                break;
            case 'error':
                notification.classList.add('error');
                notificationIcon.className = 'fa fa-exclamation-circle text-xl mr-3 mt-0.5 text-red-500';
                break;
            case 'warning':
                notification.classList.add('warning');
                notificationIcon.className = 'fa fa-exclamation-triangle text-xl mr-3 mt-0.5 text-yellow-500';
                break;
            case 'info':
                notification.classList.add('info');
                notificationIcon.className = 'fa fa-info-circle text-xl mr-3 mt-0.5 text-blue-500';
                break;
        }
        
        // 自动隐藏
        setTimeout(hideNotification, 5000);
    }
    
    // 隐藏通知
    function hideNotification() {
        // 添加移出视野的过渡效果
        notification.classList.add('translate-x-full');
        
        // 等待过渡效果完成后完全隐藏
        setTimeout(() => {
            notification.style.display = 'none';
            // 重置通知内容
            notificationTitle.textContent = '';
            notificationMessage.textContent = '';
            // 移除所有类型类
            notification.classList.remove('success', 'error', 'warning', 'info');
        }, 300); // 匹配CSS过渡时间
    }
    
    // 更新当前时间
    function updateCurrentTime() {
        const now = new Date();
        currentTime.textContent = now.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
    
    // 登出
    async function logout() {
        try {
            const response = await fetch('/api/logout', { method: 'POST' });
            const data = await response.json();
            
            if (response.ok && data.success) {
                window.location.href = '/login';
            } else {
                showNotification('error', '登出失败', '请稍后重试');
            }
        } catch (error) {
            console.error('Logout error:', error);
            showNotification('error', '登出失败', '网络错误');
        }
    }
    
    // 加载系统信息
    async function loadSystemInfo() {
        try {
            const response = await fetch('/api/system-info');
            const data = await response.json();
            
            if (response.ok) {
                // 更新Docker Compose版本
                const composeVersionEl = document.getElementById('compose-version');
                if (data.docker_compose_version) {
                    composeVersionEl.textContent = data.docker_compose_version.details || '未知';
                    
                    // 显示升级警告
                    if (data.docker_compose_version.version === 'v1') {
                        composeVersionWarning.classList.remove('hidden');
                    } else {
                        composeVersionWarning.classList.add('hidden');
                    }
                }
                
                // 更新镜像源状态
                const mirrorStatusEl = document.getElementById('mirror-status');
                if (data.mirrors_status) {
                    let statusHTML = '';
                    for (const [mirror, status] of Object.entries(data.mirrors_status)) {
                        const shortName = mirror.split('.')[1];
                        const statusClass = status.available ? 'text-green-600' : 'text-red-600';
                        const statusIcon = status.available ? 'check-circle' : 'times-circle';
                        statusHTML += `${shortName}: <span class="${statusClass}"><i class="fa fa-${statusIcon}"></i></span> `;
                    }
                    mirrorStatusEl.innerHTML = statusHTML;
                }
                
                // 应用版本更新已移除
                if (document.getElementById('app-version-detail')) {
                    document.getElementById('app-version-detail').textContent = `v${data.app_version}`;
                }
            }
        } catch (error) {
            console.error('Load system info failed:', error);
        }
    }
    
    // 加载Docker统计信息
    async function loadDockerStats() {
        try {
            const response = await fetch('/api/docker-stats');
            const data = await response.json();
            
            if (response.ok) {
                document.getElementById('container-count').textContent = data.containers_count || 0;
                document.getElementById('running-count').textContent = data.running_containers_count || 0;
            }
        } catch (error) {
            console.error('Load Docker stats failed:', error);
        }
    }
    
    // 存储原始文件列表和搜索关键字
    let originalLocalFiles = [];
    let originalGiteeFiles = [];
    let currentGiteeSystemType = '';
    
    // 加载本地文件
    async function loadLocalFiles() {
        try {
            const response = await fetch('/api/local/files');
            const data = await response.json();
            
            if (response.ok) {
                // 保存原始文件列表
                originalLocalFiles = data.files || [];
                
                // 获取搜索关键字
                const searchKeyword = document.getElementById('local-file-search')?.value.trim().toLowerCase() || '';
                
                // 过滤文件
                const filteredFiles = searchKeyword ? 
                    originalLocalFiles.filter(file => file.filename.toLowerCase().includes(searchKeyword)) : 
                    originalLocalFiles;
                
                // 更新文件计数
                localFileCount.textContent = filteredFiles.length;
                localFilesBody.innerHTML = '';
                
                if (filteredFiles.length > 0) {
                    filteredFiles.forEach(file => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td class="px-6 py-4 whitespace-nowrap">
                                <div class="flex items-center">
                                    <i class="fa fa-file-text-o text-blue-600 mr-3"></i>
                                    <div class="font-medium text-gray-900">${escapeHTML(file.filename)}</div>
                                </div>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span class="text-sm text-gray-900">${escapeHTML(file.system_name)}</span>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span class="text-sm text-gray-900">${formatFileSize(file.size)}</span>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span class="text-sm text-gray-500 timestamp">${formatDate(file.mtime)}</span>
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                <div class="flex space-x-2">
                                    <button class="text-blue-600 hover:text-blue-900 edit-file-btn" data-file-path="${escapeHTML(file.file_path)}" data-filename="${escapeHTML(file.filename)}">
                                        <i class="fa fa-edit"></i> 编辑
                                    </button>
                                    <button class="text-green-600 hover:text-green-900 deploy-file-btn" data-file-path="${escapeHTML(file.file_path)}">
                                        <i class="fa fa-rocket"></i> 部署
                                    </button>
                                </div>
                            <td>
                        `;
                        localFilesBody.appendChild(row);
                    });
                    
                    // 添加按钮事件
                    document.querySelectorAll('.edit-file-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            const filePath = this.getAttribute('data-file-path');
                            const filename = this.getAttribute('data-filename');
                            editFile(filePath, filename);
                        });
                    });
                    
                    document.querySelectorAll('.deploy-file-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            const filePath = this.getAttribute('data-file-path');
                            deployFile(filePath);
                        });
                    });
                } else {
                    localFilesBody.innerHTML = `
                        <tr>
                            <td colspan="5" class="px-6 py-10 text-center text-gray-500">
                                <i class="fa fa-file-text-o text-3xl mb-2 block"></i>
                                暂无本地文件
                            <td>
                        <tr>
                    `;
                }
            }
        } catch (error) {
            console.error('Load local files failed:', error);
            showNotification('error', '加载失败', '无法加载本地文件');
        }
    }
    
    // 加载系统类型
    async function loadSystemTypes() {
        try {
            const response = await fetch('/api/gitee/system-types', {
            headers: createGiteeHeaders()
        });
            const data = await response.json();
            
            if (response.ok && data.system_types) {
                systemTypeSelect.innerHTML = '<option value="">请选择系统类型</option>';
                data.system_types.forEach(system => {
                    const option = document.createElement('option');
                    option.value = system.key;
                    option.textContent = system.name;
                    systemTypeSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Load system types failed:', error);
        }
    }
    
    // 处理系统类型选择变化
    function handleSystemTypeChange() {
        const systemType = systemTypeSelect.value;
        if (systemType) {
            loadGiteeFiles(systemType);
        } else {
            // 清除文件列表
            giteeFilesBody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-6 py-10 text-center text-gray-500">
                        <i class="fa fa-file-text-o text-3xl mb-2 block"></i>
                        请选择系统类型以查看文件
                    <td>
                <tr>
            `;
            // 重置文件计数
            const giteeFileCount = document.getElementById('gitee-file-count');
            if (giteeFileCount) {
                giteeFileCount.textContent = '0';
            }
        }
    }
    
    // 加载Gitee文件
    async function loadGiteeFiles(systemType = null) {
        const type = systemType || systemTypeSelect.value;
        if (!type) return;
        
        // 保存当前系统类型
        currentGiteeSystemType = type;
        
        try {
            const response = await fetch(`/api/gitee/files/${type}`, {
                headers: createGiteeHeaders()
            });
            const data = await response.json();
            
            if (response.ok) {
                // 保存原始文件列表
                originalGiteeFiles = data.files || [];
                
                // 获取搜索关键字
                const searchKeyword = document.getElementById('gitee-file-search')?.value.trim().toLowerCase() || '';
                
                // 过滤文件
                const filteredFiles = searchKeyword ? 
                    originalGiteeFiles.filter(file => file.name.toLowerCase().includes(searchKeyword)) : 
                    originalGiteeFiles;
                
                // 创建Gitee文件计数元素
                const giteeFileCount = document.getElementById('gitee-file-count');
                if (giteeFileCount) {
                    giteeFileCount.textContent = filteredFiles.length;
                }
                
                giteeFilesBody.innerHTML = '';
                
                if (filteredFiles.length > 0) {
                    filteredFiles.forEach(file => {
                        const existsIcon = file.exists_locally ? 
                            '<i class="fa fa-check-circle text-green-600"></i>' : 
                            '<i class="fa fa-times-circle text-gray-400"></i>';
                        const existsText = file.exists_locally ? '已下载' : '未下载';
                        const existsClass = file.exists_locally ? 'text-green-600' : 'text-gray-500';
                        const downloadBtn = file.exists_locally ? 
                            `<button class="text-blue-600 hover:text-blue-900 edit-file-btn ml-2" data-system="${escapeHTML(type)}" data-filename="${escapeHTML(file.name)}">
                                <i class="fa fa-edit"></i> 编辑
                            </button>` : 
                            `<button class="text-green-600 hover:text-green-900 download-file-btn ml-2" data-url="${escapeHTML(file.download_url)}" data-system="${escapeHTML(type)}" data-filename="${escapeHTML(file.name)}">
                                <i class="fa fa-download"></i> 下载
                            </button>`;
                        
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td class="px-6 py-4 whitespace-nowrap">
                                <div class="flex items-center">
                                    <i class="fa fa-file-text-o text-blue-600 mr-3"></i>
                                    <div class="font-medium text-gray-900">${escapeHTML(file.name)}</div>
                                </div>
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span class="text-sm ${existsClass} flex items-center">
                                    ${existsIcon} ${existsText}
                                </span>
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                <div class="flex space-x-2">
                                    ${file.exists_locally ? `
                                        <button class="text-green-600 hover:text-green-900 deploy-file-btn" data-file-path="/app/data/${escapeHTML(type)}/${escapeHTML(file.name)}">
                                            <i class="fa fa-rocket"></i> 部署
                                        </button>
                                    ` : ''}
                                    ${downloadBtn}
                                </div>
                            </td>
                        `;
                        giteeFilesBody.appendChild(row);
                    });
                    
                    // 添加按钮事件
                    document.querySelectorAll('.download-file-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            const url = this.getAttribute('data-url');
                            const system = this.getAttribute('data-system');
                            const filename = this.getAttribute('data-filename');
                            downloadGiteeFile(url, system, filename);
                        });
                    });
                    
                    document.querySelectorAll('.edit-file-btn[data-system]').forEach(btn => {
                        btn.addEventListener('click', function() {
                            const system = this.getAttribute('data-system');
                            const filename = this.getAttribute('data-filename');
                            const filePath = `/app/data/${system}/${filename}`;
                            editFile(filePath, filename);
                        });
                    });
                    
                    document.querySelectorAll('.deploy-file-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            const filePath = this.getAttribute('data-file-path');
                            deployFile(filePath);
                        });
                    });
                } else {
                    giteeFilesBody.innerHTML = `
                        <tr>
                            <td colspan="3" class="px-6 py-10 text-center text-gray-500">
                                <i class="fa fa-file-text-o text-3xl mb-2 block"></i>
                                该系统类型暂无文件
                            </td>
                        </tr>
                    `;
                }
            }
        } catch (error) {
            console.error('Load Gitee files failed:', error);
            showNotification('error', '加载失败', '无法加载Gitee文件');
        }
    }
    
    // 加载部署记录
    async function loadDeployments() {
        try {
            const response = await fetch('/api/docker/deployments');
            const data = await response.json();
            
            deploymentsBody.innerHTML = '';
            
            if (data && data.length > 0) {
                data.forEach(deployment => {
                    // 获取状态图标和颜色
                    let statusIcon, statusColor, statusText;
                    switch (deployment.status) {
                        case 'success':
                            statusIcon = 'fa-check-circle';
                            statusColor = 'text-green-600';
                            statusText = '部署成功';
                            break;
                        case 'failed':
                            statusIcon = 'fa-times-circle';
                            statusColor = 'text-red-600';
                            statusText = '部署失败';
                            break;
                        case 'deploying':
                            statusIcon = 'fa-spinner fa-spin';
                            statusColor = 'text-blue-600';
                            statusText = '部署中';
                            break;
                        default:
                            statusIcon = 'fa-clock-o';
                            statusColor = 'text-gray-500';
                            statusText = '等待部署';
                    }
                    
                    // 格式化时间
                    const createdAt = deployment.created_at ? 
                        new Date(deployment.created_at).toLocaleString() : '未知';
                    const completedAt = deployment.completed_at ? 
                        new Date(deployment.completed_at).toLocaleString() : '-';
                    
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="px-6 py-4 whitespace-nowrap">
                            <span class="text-sm font-medium text-gray-900">${escapeHTML(deployment.id)}</span>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            <span class="text-sm text-gray-900">${escapeHTML(deployment.file_name)}</span>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            <span class="text-sm ${statusColor} flex items-center">
                                <i class="fa ${statusIcon} mr-1"></i> ${statusText}
                            </span>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            <div>
                                <span class="text-sm text-gray-500">开始: ${createdAt}</span><br>
                                <span class="text-sm text-gray-500">完成: ${completedAt}</span>
                            </div>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <button class="text-blue-600 hover:text-blue-900 view-logs-btn" data-id="${deployment.id}">
                                <i class="fa fa-eye mr-1"></i> 查看日志
                            </button>
                        </td>
                    `;
                    deploymentsBody.appendChild(row);
                });
                
                // 添加查看日志按钮事件
                document.querySelectorAll('.view-logs-btn').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const deploymentId = this.getAttribute('data-id');
                        const deployment = data.find(d => d.id == deploymentId);
                        if (deployment) {
                            showDeploymentLogs(deployment);
                        }
                    });
                });
            } else {
                deploymentsBody.innerHTML = `
                    <tr>
                        <td colspan="5" class="px-6 py-10 text-center text-gray-500">
                            <i class="fa fa-history text-3xl mb-2 block"></i>
                            暂无部署记录
                        </td>
                    </tr>
                `;
            }
        } catch (error) {
            console.error('Load deployments failed:', error);
            deploymentsBody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-6 py-10 text-center text-red-500">
                        <i class="fa fa-exclamation-triangle text-3xl mb-2 block"></i>
                        加载部署记录失败
                    </td>
                </tr>
            `;
        }
    }
    
    // 显示部署日志
    function showDeploymentLogs(deployment) {
        // 创建日志模态框
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col">
                <div class="p-6 border-b">
                    <h3 class="text-lg font-semibold text-gray-800">部署日志 - ID: ${escapeHTML(deployment.id)}</h3>
                    <p class="text-sm text-gray-500">文件: ${escapeHTML(deployment.file_name)} | 状态: ${getDeploymentStatusText(deployment.status)}</p>
                </div>
                <div class="p-4 overflow-y-auto flex-grow bg-gray-50">
                    <div class="mb-4">
                        <h4 class="text-sm font-medium text-gray-700 mb-2">执行命令:</h4>
                        <pre class="bg-gray-100 p-3 rounded text-sm font-mono whitespace-pre-wrap">${escapeHTML(deployment.command)}</pre>
                    </div>
                    <div>
                        <h4 class="text-sm font-medium text-gray-700 mb-2">输出日志:</h4>
                        <pre class="bg-gray-100 p-3 rounded text-sm font-mono whitespace-pre-wrap h-64 overflow-y-auto">${escapeHTML(deployment.output || '无输出')}</pre>
                    </div>
                </div>
                <div class="p-4 border-t flex justify-end">
                    <button class="close-log-modal bg-gray-200 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-300 transition-colors">
                        关闭
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // 关闭模态框
        modal.querySelector('.close-log-modal').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        // 点击外部关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }
    
    // 获取部署状态文本
    function getDeploymentStatusText(status) {
        switch (status) {
            case 'success': return '部署成功';
            case 'failed': return '部署失败';
            case 'deploying': return '部署中';
            case 'pending': return '等待部署';
            default: return '未知状态';
        }
    }
    
    // 处理文件上传
    async function handleFileUpload(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch('/api/local/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                showNotification('success', '上传成功', `文件 ${file.name} 上传成功`);
                loadLocalFiles();
                fileUploadInput.value = '';
            } else {
                showNotification('error', '上传失败', data.error || '文件上传失败');
            }
        } catch (error) {
            console.error('File upload failed:', error);
            showNotification('error', '上传失败', '网络错误');
        }
    }
    
    // 下载Gitee文件
    async function downloadGiteeFile(url, systemType, filename) {
        try {
            const response = await fetch('/api/gitee/download', {
                method: 'POST',
                headers: createGiteeHeaders(),
                body: JSON.stringify({
                    download_url: url,
                    system_type: systemType,
                    filename: filename
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                showNotification('success', '下载成功', `文件 ${filename} 下载成功`);
                loadGiteeFiles(systemType);
            } else {
                showNotification('error', '下载失败', data.error || '文件下载失败');
            }
        } catch (error) {
            console.error('Gitee file download failed:', error);
            showNotification('error', '下载失败', '网络错误');
        }
    }
    
    // 编辑文件
    async function editFile(filePath, filename) {
        try {
            const response = await fetch('/api/gitee/file-content', {
                method: 'POST',
                headers: createGiteeHeaders(),
                body: JSON.stringify({ file_path: filePath })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                currentEditingFile = filePath;
                editModalTitle.textContent = `编辑文件: ${filename}`;
                fileContentText.value = data.content;
                
                // 显示文件格式警告
                if (!data.parsed && data.error) {
                    document.getElementById('file-preview-warning').classList.remove('hidden');
                } else {
                    document.getElementById('file-preview-warning').classList.add('hidden');
                }
                
                // 显示模态框
                fileEditModal.classList.remove('hidden');
                // 自动聚焦
                fileContentText.focus();
            } else {
                showNotification('error', '加载失败', '无法加载文件内容');
            }
        } catch (error) {
            console.error('Edit file failed:', error);
            showNotification('error', '加载失败', '网络错误');
        }
    }
    
    // 关闭编辑模态框
    function closeEditModal() {
        fileEditModal.classList.add('hidden');
        currentEditingFile = null;
        fileContentText.value = '';
        document.getElementById('file-preview-warning').classList.add('hidden');
    }
    
    // 保存文件
    async function saveFile() {
        if (!currentEditingFile) return;
        
        const content = fileContentText.value;
        
        try {
            const response = await fetch('/api/gitee/update-file', {
                method: 'POST',
                headers: createGiteeHeaders(),
                body: JSON.stringify({
                    file_path: currentEditingFile,
                    content: content
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                showNotification('success', '保存成功', '文件已成功保存');
                closeEditModal();
                // 刷新文件列表
                loadLocalFiles();
            } else {
                showNotification('error', '保存失败', data.error || '文件保存失败');
            }
        } catch (error) {
            console.error('Save file failed:', error);
            showNotification('error', '保存失败', '网络错误');
        }
    }
    
    // 保存并部署文件
    async function saveAndDeployFile() {
        if (!currentEditingFile) return;
        
        const content = fileContentText.value;
        
        try {
            // 先保存文件
            const saveResponse = await fetch('/api/gitee/update-file', {
                method: 'POST',
                headers: createGiteeHeaders(),
                body: JSON.stringify({
                    file_path: currentEditingFile,
                    content: content
                })
            });
            
            const saveData = await saveResponse.json();
            
            if (saveResponse.ok && saveData.success) {
                closeEditModal();
                // 然后部署
                deployFile(currentEditingFile);
            } else {
                showNotification('error', '保存失败', saveData.error || '文件保存失败');
            }
        } catch (error) {
            console.error('Save and deploy failed:', error);
            showNotification('error', '操作失败', '网络错误');
        }
    }
    
    // 部署文件
    async function deployFile(filePath) {
        try {
            const response = await fetch('/api/docker/deploy', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ file_path: filePath })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                // 显示部署进度模态框
                currentDeploymentId = data.deployment_id;
                showDeploymentProgress();
                // 开始轮询状态
                startDeploymentStatusCheck();
            } else {
                showNotification('error', '部署失败', data.error || '容器部署失败');
            }
        } catch (error) {
            console.error('Deploy file failed:', error);
            showNotification('error', '部署失败', '网络错误');
        }
    }
    
    // 显示部署进度模态框
    function showDeploymentProgress() {
        progressBar.style.width = '0%';
        progressPercentage.textContent = '0%';
        progressStatus.textContent = '准备中...';
        progressOutput.textContent = '';
        progressOutput.classList.add('hidden');
        closeProgressModalBtn.classList.add('hidden');
        progressLoading.classList.remove('hidden');
        progressIcon.className = 'fa fa-cogs text-blue-600 text-2xl';
        
        deploymentProgressModal.classList.remove('hidden');
    }
    
    // 关闭部署进度模态框
    function closeProgressModal() {
        deploymentProgressModal.classList.add('hidden');
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
            statusCheckInterval = null;
        }
        currentDeploymentId = null;
    }
    
    // 开始部署状态检查
    function startDeploymentStatusCheck() {
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
        }
        
        statusCheckInterval = setInterval(async () => {
            if (!currentDeploymentId) {
                clearInterval(statusCheckInterval);
                return;
            }
            
            try {
                const response = await fetch(`/api/docker/deployment/status/${currentDeploymentId}`);
                const data = await response.json();
                
                if (response.ok) {
                    // 更新进度
                    progressBar.style.width = `${data.progress}%`;
                    progressPercentage.textContent = `${data.progress}%`;
                    progressStatus.textContent = getStatusText(data.status);
                    
                    // 更新输出
                    if (data.output) {
                        progressOutput.textContent = data.output;
                        progressOutput.classList.remove('hidden');
                        progressOutput.scrollTop = progressOutput.scrollHeight;
                    }
                    
                    // 检查是否完成
                    if (data.completed) {
                        clearInterval(statusCheckInterval);
                        statusCheckInterval = null;
                        
                        // 更新UI
                        progressLoading.classList.add('hidden');
                        closeProgressModalBtn.classList.remove('hidden');
                        
                        if (data.status === 'success') {
                            progressIcon.className = 'fa fa-check-circle text-green-600 text-2xl';
                            showNotification('success', '部署成功', '容器已成功部署');
                            // 刷新Docker统计信息
                            loadDockerStats();
                        } else {
                            progressIcon.className = 'fa fa-times-circle text-red-600 text-2xl';
                            showNotification('error', '部署失败', '容器部署失败，请查看日志');
                        }
                    }
                }
            } catch (error) {
                console.error('Check deployment status failed:', error);
            }
        }, 2000); // 每2秒检查一次
    }
    
    // 获取状态文本
    function getStatusText(status) {
        const statusMap = {
            'pending': '等待中...',
            'deploying': '部署中...',
            'success': '部署成功',
            'failed': '部署失败'
        };
        return statusMap[status] || status;
    }
    
    // 处理Docker Compose升级
    async function handleUpgradeCompose() {
        if (!confirm('确定要升级Docker Compose到v2吗？这可能需要一些时间。')) {
            return;
        }
        
        try {
            const response = await fetch('/api/docker/upgrade-compose', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                showNotification('success', '升级成功', 'Docker Compose已成功升级到v2');
                // 重新加载系统信息
                loadSystemInfo();
            } else {
                showNotification('error', '升级失败', data.error || 'Docker Compose升级失败');
            }
        } catch (error) {
            console.error('Upgrade Docker Compose failed:', error);
            showNotification('error', '升级失败', '网络错误');
        }
    }
    
    // 处理密码修改
    async function handleChangePassword() {
        const currentPassword = document.getElementById('current-password').value;
        const newPassword = document.getElementById('new-password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        
        // 验证
        if (!currentPassword || !newPassword || !confirmPassword) {
            showNotification('warning', '请输入所有密码字段', '');
            return;
        }
        
        if (newPassword !== confirmPassword) {
            showNotification('warning', '新密码和确认密码不匹配', '');
            return;
        }
        
        if (newPassword.length < 8) {
            showNotification('warning', '新密码至少需要8个字符', '');
            return;
        }
        
        try {
            const response = await fetch('/api/change-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    old_password: currentPassword,
                    new_password: newPassword
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                showNotification('success', '密码修改成功', '请记住新密码');
                changePasswordForm.reset();
            } else {
                showNotification('error', '密码修改失败', data.error || '请检查当前密码是否正确');
            }
        } catch (error) {
            console.error('Change password failed:', error);
            showNotification('error', '密码修改失败', '网络错误');
        }
    }
    
    // 切换侧边栏
    // 工具函数：格式化文件大小
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // 工具函数：格式化日期
    function formatDate(timestamp) {
        const date = new Date(timestamp * 1000);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    // 工具函数：转义HTML
    function escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
    
    // 不再需要处理侧边栏，因为侧边栏已取消
    // 移除resize事件处理和sidebar引用以修复错误
});