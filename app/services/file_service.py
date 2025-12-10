import os
import json
import yaml
from datetime import datetime
from pathlib import Path

class FileService:
    def __init__(self):
        # 基础文件存储路径
        self.base_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
        self.local_files_path = os.path.join(self.base_data_path, 'local')
        
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录结构存在"""
        # 确保数据目录存在
        if not os.path.exists(self.base_data_path):
            os.makedirs(self.base_data_path)
        
        # 确保本地文件目录存在
        if not os.path.exists(self.local_files_path):
            os.makedirs(self.local_files_path)
        
        # 确保系统类型目录存在
        system_types = ['fnOS', 'QNAP', 'Synology', 'TrueNAS', 'UgreenNew', 'Ugreen', 'ZSpace', 'ZimaOS']
        for system_type in system_types:
            system_path = os.path.join(self.base_data_path, system_type)
            if not os.path.exists(system_path):
                os.makedirs(system_path)
    
    def get_local_files(self):
        """获取所有本地文件信息"""
        files = []
        
        # 遍历所有系统目录
        for root, _, filenames in os.walk(self.base_data_path):
            # 跳过__pycache__目录
            if '__pycache__' in root:
                continue
                
            for filename in filenames:
                # 只处理.yml文件
                if not filename.endswith('.yml') and not filename.endswith('.yaml'):
                    continue
                
                file_path = os.path.join(root, filename)
                try:
                    # 获取文件信息
                    stat_info = os.stat(file_path)
                    mtime = stat_info.st_mtime
                    size = stat_info.st_size
                    
                    # 确定系统名称
                    relative_path = os.path.relpath(file_path, self.base_data_path)
                    system_name = 'local' if relative_path.startswith('local') else os.path.basename(os.path.dirname(relative_path))
                    
                    files.append({
                        'filename': filename,
                        'file_path': file_path,
                        'system_name': system_name,
                        'size': size,
                        'mtime': mtime
                    })
                except Exception as e:
                    print(f"Error reading file info {file_path}: {e}")
        
        # 按修改时间倒序排序
        files.sort(key=lambda x: x['mtime'], reverse=True)
        
        return {
            'total': len(files),
            'files': files
        }
    
    def save_file(self, file_path, content):
        """保存文件内容"""
        try:
            # 确保目录存在
            directory = os.path.dirname(file_path)
            if not os.path.exists(directory):
                os.makedirs(directory)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True, None
        except Exception as e:
            return False, str(e)
    
    def read_file(self, file_path):
        """读取文件内容"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return False, None, "文件不存在"
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试解析YAML格式
            parsed = True
            error = None
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                parsed = False
                error = str(e)
            
            return True, content, {"parsed": parsed, "error": error}
        except Exception as e:
            return False, None, str(e)
    
    def delete_file(self, file_path):
        """删除文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True, None
            return False, "文件不存在"
        except Exception as e:
            return False, str(e)
    
    def check_file_exists(self, file_path):
        """检查文件是否存在"""
        return os.path.exists(file_path)
    
    def get_system_types(self):
        """获取支持的系统类型列表"""
        # 这里应该从配置中读取，暂时硬编码
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
    
    def get_system_directory(self, system_type):
        """获取指定系统类型的文件目录"""
        if system_type == 'local':
            return self.local_files_path
        return os.path.join(self.base_data_path, system_type)
    
    def normalize_file_path(self, file_path):
        """标准化文件路径，确保在数据目录内"""
        # 安全检查：确保路径在数据目录内
        base_realpath = os.path.realpath(self.base_data_path)
        file_realpath = os.path.realpath(file_path)
        
        if not file_realpath.startswith(base_realpath):
            return None
        
        return file_realpath
    
    def validate_yaml_content(self, content):
        """验证YAML内容格式是否正确"""
        try:
            parsed = yaml.safe_load(content)
            return True, parsed
        except yaml.YAMLError as e:
            return False, str(e)
    
    def update_yaml_field(self, content, field_path, value):
        """更新YAML中的特定字段"""
        try:
            # 解析YAML
            data = yaml.safe_load(content)
            
            # 处理字段路径 (如 'services.web.container_name')
            parts = field_path.split('.')
            current = data
            
            # 遍历除最后一部分外的所有路径
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # 更新最后一部分的值
            current[parts[-1]] = value
            
            # 转换回YAML
            updated_content = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            return True, updated_content
        except Exception as e:
            return False, str(e)