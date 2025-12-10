import os
import subprocess
import json
import time
import uuid
import threading
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DockerService:
    def __init__(self):
        # 部署状态存储
        self.deployments = {}
        # 确保路径存在
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def check_docker_installed(self):
        """检查Docker是否已安装"""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False, "Docker未安装或不可用"
    
    def check_compose_version(self):
        """检查Docker Compose版本"""
        version_info = {
            "version": None,
            "details": None
        }
        
        # 先尝试检查 v2 版本
        try:
            result = subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                text=True,
                check=True
            )
            version_info["version"] = "v2"
            version_info["details"] = result.stdout.strip()
            return True, version_info
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # 再尝试检查 v1 版本
        try:
            result = subprocess.run(
                ['docker-compose', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            version_info["version"] = "v1"
            version_info["details"] = result.stdout.strip()
            return True, version_info
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False, version_info
    
    def upgrade_compose(self):
        """升级Docker Compose到v2版本"""
        try:
            # 下载并安装Docker Compose v2
            install_script = """
            curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
            chmod +x /usr/local/bin/docker-compose
            ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
            """
            
            # 在容器中安装Docker Compose v2
            result = subprocess.run(
                ['sh', '-c', install_script],
                capture_output=True,
                text=True,
                check=True
            )
            
            # 验证安装
            success, version_info = self.check_compose_version()
            if success and version_info["version"] == "v2":
                return True, "Docker Compose已成功升级到v2"
            else:
                return False, "安装成功但无法验证版本，请手动检查"
        except Exception as e:
            return False, f"升级失败: {str(e)}"
    
    def get_docker_stats(self):
        """获取Docker统计信息"""
        try:
            # 获取容器数量
            containers_result = subprocess.run(
                ['docker', 'ps', '-a', '-q'],
                capture_output=True,
                text=True,
                check=True
            )
            containers_count = len(containers_result.stdout.strip().split('\n')) if containers_result.stdout.strip() else 0
            
            # 获取运行中的容器数量
            running_containers_result = subprocess.run(
                ['docker', 'ps', '-q'],
                capture_output=True,
                text=True,
                check=True
            )
            running_containers_count = len(running_containers_result.stdout.strip().split('\n')) if running_containers_result.stdout.strip() else 0
            
            # 获取镜像数量
            images_result = subprocess.run(
                ['docker', 'images', '-q'],
                capture_output=True,
                text=True,
                check=True
            )
            images_count = len(images_result.stdout.strip().split('\n')) if images_result.stdout.strip() else 0
            
            return True, {
                "containers_count": containers_count,
                "running_containers_count": running_containers_count,
                "images_count": images_count
            }
        except Exception as e:
            logger.error(f"获取Docker统计信息失败: {str(e)}")
            return False, {"error": str(e)}
    
    def deploy_with_compose(self, file_path):
        """使用Docker Compose部署容器"""
        # 生成部署ID
        deployment_id = str(uuid.uuid4())
        
        # 初始化部署状态
        self.deployments[deployment_id] = {
            "status": "pending",
            "progress": 0,
            "output": "",
            "completed": False,
            "error": None,
            "start_time": time.time()
        }
        
        # 获取日志文件路径
        log_file = os.path.join(self.log_dir, f"deployment_{deployment_id}.log")
        
        # 在后台线程中执行部署
        thread = threading.Thread(
            target=self._execute_deployment,
            args=(deployment_id, file_path, log_file)
        )
        thread.daemon = True
        thread.start()
        
        return True, deployment_id
    
    def _execute_deployment(self, deployment_id, file_path, log_file):
        """执行部署的实际函数"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                self._update_deployment_status(deployment_id, "failed", 0, "文件不存在")
                return
            
            # 更新状态为部署中
            self._update_deployment_status(deployment_id, "deploying", 10, "开始部署...")
            
            # 检查Docker Compose版本
            success, version_info = self.check_compose_version()
            if not success:
                self._update_deployment_status(deployment_id, "failed", 0, "Docker Compose不可用")
                return
            
            # 根据版本选择命令
            if version_info["version"] == "v2":
                compose_cmd = ["docker", "compose"]
            else:
                compose_cmd = ["docker-compose"]
            
            # 执行部署命令
            full_cmd = compose_cmd + ["-f", file_path, "up", "-d"]
            
            # 更新状态
            self._update_deployment_status(deployment_id, "deploying", 30, f"执行命令: {' '.join(full_cmd)}")
            
            # 记录日志
            with open(log_file, 'w') as f:
                f.write(f"部署开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"执行命令: {' '.join(full_cmd)}\n")
                
                try:
                    # 执行命令
                    process = subprocess.Popen(
                        full_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                    
                    output_lines = []
                    for line in process.stdout:
                        line = line.strip()
                        output_lines.append(line)
                        f.write(f"{line}\n")
                        
                        # 更新进度和输出
                        output = "\n".join(output_lines)
                        self._update_deployment_status(deployment_id, "deploying", 60, output)
                    
                    process.wait()
                    
                    if process.returncode == 0:
                        # 部署成功
                        self._update_deployment_status(deployment_id, "success", 100, "部署成功完成")
                        f.write(f"部署成功完成: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    else:
                        # 部署失败
                        error_msg = f"部署失败，返回代码: {process.returncode}"
                        self._update_deployment_status(deployment_id, "failed", 0, error_msg)
                        f.write(f"{error_msg}\n")
                except Exception as e:
                    error_msg = f"部署过程中发生错误: {str(e)}"
                    self._update_deployment_status(deployment_id, "failed", 0, error_msg)
                    f.write(f"{error_msg}\n")
        except Exception as e:
            logger.error(f"部署执行失败: {str(e)}")
            self._update_deployment_status(deployment_id, "failed", 0, str(e))
    
    def _update_deployment_status(self, deployment_id, status, progress, output):
        """更新部署状态"""
        if deployment_id in self.deployments:
            self.deployments[deployment_id].update({
                "status": status,
                "progress": progress,
                "output": output,
                "completed": status in ["success", "failed"]
            })
    
    def get_deployment_status(self, deployment_id):
        """获取部署状态"""
        if deployment_id not in self.deployments:
            return False, {"error": "部署ID不存在"}
        
        return True, self.deployments[deployment_id]
    
    def stop_containers(self, file_path):
        """停止容器"""
        try:
            # 检查Docker Compose版本
            success, version_info = self.check_compose_version()
            if not success:
                return False, "Docker Compose不可用"
            
            # 根据版本选择命令
            if version_info["version"] == "v2":
                compose_cmd = ["docker", "compose"]
            else:
                compose_cmd = ["docker-compose"]
            
            # 执行停止命令
            cmd = compose_cmd + ["-f", file_path, "down"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            return True, "容器已成功停止"
        except subprocess.CalledProcessError as e:
            return False, f"停止容器失败: {e.stderr.strip()}"
        except Exception as e:
            return False, f"操作失败: {str(e)}"
    
    def start_containers(self, file_path):
        """启动容器"""
        return self.deploy_with_compose(file_path)
    
    def check_mirror_status(self):
        """检查镜像源状态"""
        mirrors = {
            "docker.1ms.run": "https://docker.1ms.run",
            "docker.1panel.live": "https://docker.1panel.live"
        }
        
        status = {}
        
        for mirror_name, mirror_url in mirrors.items():
            mirror_status = {
                "available": False,
                "response_time": None,
                "error": None
            }
            
            try:
                # 使用curl检查URL是否可访问
                start_time = time.time()
                result = subprocess.run(
                    ["curl", "-s", "-I", "--max-time", "3", mirror_url],
                    capture_output=True,
                    text=True
                )
                end_time = time.time()
                
                # 检查返回码
                if result.returncode == 0:
                    mirror_status["available"] = True
                    mirror_status["response_time"] = round((end_time - start_time) * 1000, 2)
                else:
                    mirror_status["error"] = "请求失败"
            except Exception as e:
                mirror_status["error"] = str(e)
            
            status[mirror_name] = mirror_status
        
        return status
    
    def clean_old_deployments(self, max_age=86400):
        """清理旧的部署记录"""
        current_time = time.time()
        old_ids = []
        
        for deployment_id, info in self.deployments.items():
            if info.get("completed", False) and current_time - info.get("start_time", 0) > max_age:
                old_ids.append(deployment_id)
        
        for deployment_id in old_ids:
            del self.deployments[deployment_id]
    
    def get_container_logs(self, container_name):
        """获取容器日志"""
        try:
            result = subprocess.run(
                ["docker", "logs", container_name, "--tail", "100"],
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, f"获取日志失败: {e.stderr.strip()}"
        except Exception as e:
            return False, f"操作失败: {str(e)}"