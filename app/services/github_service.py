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
        # Github API基础URL
        self.api_base_url = "https://api.github.com"
        # 仓库信息
        self.owner = "waiyanhein96"
        self.repo = "Docker-Compose-File"
        # 数据目录
        self.base_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
        # Github Token
        self.token = token
        
    def _get_headers(self):
        """构建请求头"""
        return {}
    
    def _get_request_params(self):
        """构建请求参数，包含可选的token"""
        params = {}
        if self.token:
            params['access_token'] = self.token
        return params
    
    def get_files_list(self, system_type):
        """获取Github仓库中指定系统类型的文件列表"""
        try:
            # 验证输入参数
            if not system_type or not isinstance(system_type, str):
                logger.error(f"无效的系统类型参数: {system_type}")
                return False, {"error": "无效的系统类型参数"}
            
            # 构建API URL
            url = f"{self.api_base_url}/repos/{self.owner}/{self.repo}/contents/{system_type}"
            
            # 发送请求
            response = requests.get(url, headers=self._get_headers(), params=self._get_request_params())
            
            # 检查响应状态码
            if response.status_code == 404:
                logger.warning(f"系统类型 {system_type} 目录不存在")
                return True, {"files": []}  # 返回空列表而不是错误
            
            # 对于其他错误状态码
            if response.status_code != 200:
                error_msg = f"API请求失败，状态码: {response.status_code}"
                
                # 尝试解析错误信息
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict) and 'message' in error_data:
                        error_msg = error_data['message']
                except:
                    pass
                
                return False, {"error": error_msg}
            
            # 解析响应
            try:
                files = response.json()
                
                # 验证响应格式
                if not isinstance(files, list):
                    logger.error(f"Github API 返回非列表格式: {type(files)}")
                    return False, {"error": "API返回数据格式错误"}
                
                # 过滤出.yml和.yaml文件
                yaml_files = []
                for file in files:
                    # 安全检查每个文件项
                    if not isinstance(file, dict):
                        logger.warning(f"忽略非字典格式的文件项: {file}")
                        continue
                    
                    # 必需字段检查
                    if 'type' not in file or 'name' not in file:
                        logger.warning(f"忽略缺少必需字段的文件项: {file}")
                        continue
                    
                    # 检查是否为文件且是YAML文件
                    if file['type'] == 'file' and (file['name'].endswith('.yml') or file['name'].endswith('.yaml')):
                        # 检查本地是否已存在
                        local_path = os.path.join(self.base_data_path, system_type, file['name'])
                        exists_locally = os.path.exists(local_path)
                        
                        yaml_files.append({
                            'name': file.get('name', ''),
                            'size': file.get('size', 0),
                            'updated_at': file.get('updated_at', ''),
                            'download_url': file.get('download_url', ''),
                            'exists_locally': exists_locally
                        })
            except ValueError as e:
                logger.error(f"解析JSON响应失败: {str(e)}")
                return False, {"error": "解析API响应失败"}
            except Exception as e:
                return False, {"error": f"获取文件列表失败: {str(e)}"}
            
            return True, {"files": yaml_files}
        except requests.exceptions.RequestException as e:
            logger.error(f"获取Github文件列表失败: {str(e)}")
            return False, {"error": f"获取文件列表失败: {str(e)}"}
        except Exception as e:
            logger.error(f"获取Github文件列表时发生错误: {str(e)}")
            return False, {"error": f"内部错误: {str(e)}"}
    
    def download_file(self, download_url, system_type, filename):
        """从Github下载文件"""
        try:
            # 对于下载URL，我们需要手动添加token参数
            import urllib.parse
            parsed_url = urllib.parse.urlparse(download_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            # 如果有token，添加到查询参数
            if self.token:
                query_params['access_token'] = [self.token]
            
            # 重新构建URL
            new_query = urllib.parse.urlencode(query_params, doseq=True)
            new_url = urllib.parse.urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                new_query,
                parsed_url.fragment
            ))
            
            # 发送请求下载文件
            response = requests.get(new_url, headers=self._get_headers())
            response.raise_for_status()
            
            # 确保系统类型目录存在
            system_dir = os.path.join(self.base_data_path, system_type)
            if not os.path.exists(system_dir):
                os.makedirs(system_dir)
            
            # 保存文件
            file_path = os.path.join(system_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            return True, {"file_path": file_path}
        except requests.exceptions.RequestException as e:
            logger.error(f"下载Github文件失败: {str(e)}")
            return False, {"error": f"文件下载失败: {str(e)}"}
        except Exception as e:
            logger.error(f"下载文件时发生错误: {str(e)}")
            return False, {"error": f"内部错误: {str(e)}"}
    
    def get_file_content(self, file_path):
        """获取文件内容（支持本地和Github文件）"""
        try:
            # 如果是本地文件路径，直接读取
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return True, content, {"source": "local"}
            
            # 否则尝试从Github获取
            # 注意：这里需要解析路径，从本地路径推断Github路径
            # 例如：/app/data/fnOS/example.yml -> fnOS/example.yml
            relative_path = os.path.relpath(file_path, self.base_data_path)
            
            # 获取文件内容
            url = f"{self.api_base_url}/repos/{self.owner}/{self.repo}/contents/{relative_path}"
            response = requests.get(url, headers=self._get_headers(), params=self._get_request_params())
            
            if response.status_code == 404:
                return False, None, {"error": "文件不存在"}
            
            response.raise_for_status()
            
            # 解析响应
            file_data = response.json()
            
            # 解码base64内容
            content = base64.b64decode(file_data['content']).decode('utf-8')
            
            return True, content, {"source": "github"}
        except Exception as e:
            logger.error(f"获取文件内容失败: {str(e)}")
            return False, None, {"error": str(e)}
    
    def update_file(self, file_path, content):
        """更新本地文件内容"""
        try:
            # 只更新本地文件
            if not os.path.exists(file_path):
                # 确保目录存在
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 写入内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True, {"file_path": file_path}
        except Exception as e:
            logger.error(f"更新文件失败: {str(e)}")
            return False, {"error": str(e)}
    
    def get_system_types(self):
        """获取支持的系统类型列表"""
        # 这里应该从API获取，暂时硬编码
        return [
            {"key": "fnOS", "name": "飞牛系统 (fnOS)"},
            {"key": "QNAP", "name": "威联通系统 (QNAP)"},
            {"key": "Synology", "name": "群晖系统 (Synology)"},
            {"key": "TrueNAS", "name": "True系统 (TrueNAS)"},
            {"key": "UgreenNew", "name": "绿联系统 (UgreenNew)"},
            {"key": "Ugreen", "name": "绿联旧系统 (Ugreen - 废弃)"},
            {"key": "ZSpace", "name": "极空间系统 (ZSpace)"},
            {"key": "ZimaOS", "name": "Zima系统 (ZimaOS)"}
        ]
    
    def check_file_exists_remote(self, system_type, filename):
        """检查远程文件是否存在"""
        try:
            url = f"{self.api_base_url}/repos/{self.owner}/{self.repo}/contents/{system_type}/{filename}"
            response = requests.get(url, params=self._get_request_params())
            
            if response.status_code == 200:
                return True, {"exists": True, "file_info": response.json()}
            elif response.status_code == 404:
                return True, {"exists": False}
            else:
                response.raise_for_status()
        except Exception as e:
            logger.error(f"检查远程文件失败: {str(e)}")
            return False, {"error": str(e)}
    
    def get_repo_info(self):
        """获取仓库信息"""
        try:
            url = f"{self.api_base_url}/repos/{self.owner}/{self.repo}"
            response = requests.get(url, params=self._get_request_params())
            response.raise_for_status()
            
            return True, response.json()
        except Exception as e:
            logger.error(f"获取仓库信息失败: {str(e)}")
            return False, {"error": str(e)}
    
    def search_files(self, keyword, system_type=None):
        """搜索文件"""
        try:
            results = []
            
            # 如果指定了系统类型，只搜索该类型
            if system_type:
                success, data = self.get_files_list(system_type)
                if not success:
                    logger.error(f"搜索文件失败: {data.get('error', '未知错误')}")
                    return False, {"error": f"搜索失败: {data.get('error', '未知错误')}"}
                
                for file in data.get('files', []):
                    if keyword.lower() in file['name'].lower():
                        file['system_type'] = system_type
                        results.append(file)
            else:
                # 否则搜索所有系统类型
                system_types = self.get_system_types()
                for system in system_types:
                    success, data = self.get_files_list(system['key'])
                    if not success:
                        logger.error(f"搜索系统 {system['key']} 文件失败: {data.get('error', '未知错误')}")
                        continue  # 继续搜索其他系统类型，不中断整个搜索
                    
                    for file in data.get('files', []):
                        if keyword.lower() in file['name'].lower():
                            file['system_type'] = system['key']
                            results.append(file)
            
            return True, {"files": results}
        except Exception as e:
            logger.error(f"搜索文件失败: {str(e)}")
            return False, {"error": str(e)}
    
    def validate_download_url(self, url):
        """验证下载URL是否有效"""
        try:
            # 检查URL是否属于github
            if not url.startswith('https://github.com/'):
                return False, "URL不是有效的Github链接"
            
            # 发送HEAD请求检查URL
            response = requests.head(url, allow_redirects=True)
            if response.status_code == 200:
                # 检查Content-Type
                content_type = response.headers.get('Content-Type', '')
                if 'text/plain' in content_type or 'application/x-yaml' in content_type or url.endswith(('.yml', '.yaml')):
                    return True, {"valid": True}
                else:
                    return False, "URL不是有效的YAML文件"
            else:
                return False, f"URL访问失败，状态码: {response.status_code}"
        except Exception as e:
            logger.error(f"验证URL失败: {str(e)}")
            return False, {"error": str(e)}
    
    def get_file_history(self, system_type, filename):
        """获取文件的修改历史"""
        try:
            url = f"{self.api_base_url}/repos/{self.owner}/{self.repo}/commits?path={system_type}/{filename}"
            response = requests.get(url, params=self._get_request_params())
            response.raise_for_status()
            
            commits = response.json()
            
            # 提取重要信息
            history = []
            for commit in commits:
                history.append({
                    'sha': commit['sha'],
                    'message': commit['commit']['message'],
                    'author': commit['commit']['author']['name'],
                    'date': commit['commit']['author']['date'],
                    'url': commit['html_url']
                })
            
            return True, {"history": history}
        except Exception as e:
            logger.error(f"获取文件历史失败: {str(e)}")
            return False, {"error": str(e)}
    
    def get_latest_updates(self, limit=5):
        """获取最近更新的文件"""
        try:
            all_files = []
            system_types = self.get_system_types()
            
            # 获取所有系统类型的文件
            for system in system_types:
                success, data = self.get_files_list(system['key'])
                if success:
                    for file in data.get('files', []):
                        file['system_type'] = system['key']
                        file['system_name'] = system['name']
                        all_files.append(file)
            
            # 按更新时间排序
            all_files.sort(key=lambda x: x['updated_at'], reverse=True)
            
            # 返回限制数量的结果
            return True, {"files": all_files[:limit]}
        except Exception as e:
            logger.error(f"获取最近更新失败: {str(e)}")
            return False, {"error": str(e)}