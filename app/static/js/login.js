document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('login-form');
    const errorMessage = document.getElementById('error-message');
    const successMessage = document.getElementById('success-message');
    const loginBtn = document.getElementById('login-btn');
    const btnText = document.getElementById('btn-text');
    const btnLoading = document.getElementById('btn-loading');
    const togglePasswordBtn = document.getElementById('toggle-password');
    const passwordInput = document.getElementById('password');
    
    // 密码显示切换
    togglePasswordBtn.addEventListener('click', function() {
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);
        
        // 切换图标
        const icon = togglePasswordBtn.querySelector('i');
        icon.classList.toggle('fa-eye-slash');
        icon.classList.toggle('fa-eye');
    });
    
    // 表单提交
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // 清除之前的消息
        errorMessage.classList.add('hidden');
        successMessage.classList.add('hidden');
        
        // 获取表单数据
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        
        // 简单验证
        if (!username || !password) {
            showError('请输入用户名和密码');
            return;
        }
        
        // 显示加载状态
        btnText.textContent = '登录中';
        btnLoading.classList.remove('hidden');
        loginBtn.disabled = true;
        
        try {
            // 发送登录请求
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                // 登录成功
                showSuccess('登录成功，正在跳转...');
                // 延迟跳转，让用户看到成功消息
                setTimeout(() => {
                    window.location.href = '/';
                }, 1500);
            } else {
                // 登录失败
                showError(data.error || '登录失败，请检查用户名和密码');
            }
        } catch (error) {
            console.error('Login error:', error);
            showError('登录失败，请稍后重试');
        } finally {
            // 恢复按钮状态
            btnText.textContent = '登录';
            btnLoading.classList.add('hidden');
            loginBtn.disabled = false;
        }
    });
    
    // 函数：显示错误消息
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
        // 5秒后自动隐藏
        setTimeout(() => {
            errorMessage.classList.add('hidden');
        }, 5000);
    }
    
    // 函数：显示成功消息
    function showSuccess(message) {
        successMessage.textContent = message;
        successMessage.classList.remove('hidden');
    }
    
    // 自动聚焦用户名输入框
    document.getElementById('username').focus();
    
    // 支持回车键快速登录
    passwordInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            loginForm.dispatchEvent(new Event('submit'));
        }
    });
    
    // 添加表单字段的交互效果
    const inputs = loginForm.querySelectorAll('input');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('ring-2', 'ring-blue-200');
        });
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('ring-2', 'ring-blue-200');
        });
    });
});