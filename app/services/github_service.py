import os
import requests
import base64
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GithubService:
    def __init__(self, token=None):
        # GitHub API基础URL
        self.api_base_url = os.environ.get('GITHUB_API_URL', 'https://api.github.com')
        # 仓库信息（默认使用你的仓库）
        # 格式: owner/repo，例如: waiyanhein96/ComposeWeb
        self.repo = os.environ.get('GITHUB_REPO', 'waiyanhein96/ComposeWeb')
        # 解析 owner 与 repo
        if '/' in self.repo:
            self.owner, self.repo_name = self.repo.split('/', 1)
        else:
            self.owner = self.repo
            self.repo_name = self.repo

        # 数据目录（保持与原实现一致）
        self.base_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
        # GitHub Token
        self.token = token

    def _get_headers(self):
        """构建请求头，包含 Authorization（如果有 token）和 Accept"""
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'ComposeWeb-App'
        }
        if self.token:
            headers['Authorization'] = f'token {self.token}'
        return headers

    def _get_request_params(self):
        """构建请求参数占位（保留与 gitee 类似签名）"""
        return {}

    def get_files_list(self, system_type, path_branch='main'):
        """
        列出仓库中指定目录下的文件（与原来 gitee_service.get_files_list 行为类似）
        system_type 对应仓库中的目录名，例如 fnOS、QNAP 等
        返回： (True, {'files': [...]}) 或 (False, {'error': '...'})
        """
        try:
            if not system_type or not isinstance(system_type, str):
                logger.error(f"无效的系统类型参数: {system_type}")
                return False, {"error": "无效的系统类型参数"}

            # 调用 GitHub contents API
            # e.g. GET /repos/{owner}/{repo}/contents/{path}
            path = system_type.strip('/')
            url = f"{self.api_base_url}/repos/{self.owner}/{self.repo_name}/contents/{path}"
            params = {}
            # 如果需要指定分支可以传 ?ref=branch
            if path_branch:
                params['ref'] = path_branch

            response = requests.get(url, headers=self._get_headers(), params=params, timeout=10)

            if response.status_code == 404:
                logger.warning(f"系统类型 {system_type} 目录不存在")
                return True, {"files": []}

            if response.status_code != 200:
                err_msg = f"API请求失败，状态码: {response.status_code}"
                try:
                    j = response.json()
                    if isinstance(j, dict) and 'message' in j:
                        err_msg = j.get('message')
                except:
                    pass
                return False, {"error": err_msg}

            items = response.json()
            if not isinstance(items, list):
                return False, {"error": "API返回数据格式错误"}

            yaml_files = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                # 只要文件且扩展名为 yml/yaml
                if item.get('type') == 'file' and item.get('name', '').lower().endswith(('.yml', '.yaml')):
                    local_path = os.path.join(self.base_data_path, system_type, item.get('name',''))
                    exists_locally = os.path.exists(local_path)

                    yaml_files.append({
                        'name': item.get('name', ''),
                        'size': item.get('size', 0),
                        'updated_at': item.get('git_url', ''),  # GitHub没有直接updated_at在此接口，保留git_url占位
                        'download_url': item.get('download_url', ''),  # 这个字段通常存在并指向 raw 文件
                        'html_url': item.get('html_url', ''),
                        'path': item.get('path', ''),
                        'exists_locally': exists_locally
                    })

            return True, {"files": yaml_files}

        except requests.exceptions.RequestException as e:
            logger.error(f"获取GitHub文件列表失败: {str(e)}")
            return False, {"error": f"获取文件列表失败: {str(e)}"}
        except Exception as e:
            logger.error(f"获取文件列表时发生错误: {str(e)}")
            return False, {"error": f"内部错误: {str(e)}"}

    def download_file(self, download_url, system_type, filename):
        """
        下载 raw 文件到本地 data/{system_type}/{filename}
        download_url: 优先使用从 contents API 返回的 download_url（raw URL），若为 GitHub API 内容 URL，会自动处理
        """
        try:
            headers = self._get_headers()

            # 如果 download_url 是空，尝试用 contents API 通过 path 获取内容
            if not download_url:
                # 构造 contents API URL： /repos/{owner}/{repo}/contents/{path}
                # 假设 filename 与 system_type 拼接成路径
                api_path = f"{system_type}/{filename}".lstrip('/')
                url = f"{self.api_base_url}/repos/{self.owner}/{self.repo_name}/contents/{api_path}"
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                if 'content' in data and data.get('encoding') == 'base64':
                    content = base64.b64decode(data['content'])
                else:
                    # fallback: use download_url if provided
                    dl = data.get('download_url')
                    if not dl:
                        return False, {"error": "无法获取文件下载地址"}
                    r = requests.get(dl, headers=headers, timeout=10)
                    r.raise_for_status()
                    content = r.content
            else:
                # 直接请求 download_url（通常是 raw.githubusercontent.com 或 api.github.com/.../contents）
                response = requests.get(download_url, headers=headers, timeout=10)
                response.raise_for_status()
                content = response.content

            # 保存到本地 data 目录
            system_dir = os.path.join(self.base_data_path, system_type)
            os.makedirs(system_dir, exist_ok=True)
            file_path = os.path.join(system_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(content)

            return True, {"file_path": file_path}

        except requests.exceptions.RequestException as e:
            logger.error(f"下载GitHub文件失败: {str(e)}")
            return False, {"error": f"文件下载失败: {str(e)}"}
        except Exception as e:
            logger.error(f"下载文件时发生错误: {str(e)}")
            return False, {"error": f"内部错误: {str(e)}"}

    def get_file_content(self, file_path, path_branch='main'):
        """
        获取文件内容：优先读取本地文件；若不存在则从 GitHub 仓库读取并返回文本内容（解 base64）
        返回 (True, content, {'source': 'local'|'github'}) 或 (False, None, {'error':...})
        """
        try:
            # 本地优先
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return True, content, {"source": "local"}

            # 推断相对路径（相对于 base_data_path）
            relative_path = os.path.relpath(file_path, self.base_data_path).replace('\\','/')

            # 调用 contents API
            url = f"{self.api_base_url}/repos/{self.owner}/{self.repo_name}/contents/{relative_path}"
            params = {}
            if path_branch:
                params['ref'] = path_branch

            response = requests.get(url, headers=self._get_headers(), params=params, timeout=10)
            if response.status_code == 404:
                return False, None, {"error": "文件不存在"}
            response.raise_for_status()

            data = response.json()
            # 如果返回包含 content 且为 base64 编码，解码
            if isinstance(data, dict) and data.get('encoding') == 'base64' and 'content' in data:
                content = base64.b64decode(data['content']).decode('utf-8')
                return True, content, {"source": "github"}
            # 否则尝试通过 download_url 获取
            dl = data.get('download_url')
            if dl:
                r = requests.get(dl, headers=self._get_headers(), timeout=10)
                r.raise_for_status()
                return True, r.text, {"source": "github"}
            return False, None, {"error": "无法获取文件内容"}

        except Exception as e:
            logger.error(f"获取文件内容失败: {str(e)}")
            return False, None, {"error": str(e)}

    def update_file(self, file_path, content):
        """
        仅更新本地文件（与原 gitee_service.update_file 保持一致）
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, {"file_path": file_path}
        except Exception as e:
            logger.error(f"更新文件失败: {str(e)}")
            return False, {"error": str(e)}
