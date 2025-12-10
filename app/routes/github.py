from flask import Blueprint, request, jsonify
from app.services.github_service import GithubService
import os

github_bp = Blueprint('github', __name__, url_prefix='/api/github')

def get_service():
    token = os.environ.get("GITHUB_TOKEN", None)
    return GithubService(token=token)

# 获取指定系统类型的文件列表
@github_bp.route('/files/<system_type>', methods=['GET'])
def list_files(system_type):
    service = get_service()
    success, result = service.get_files_list(system_type)
    if success:
        return jsonify(result), 200
    return jsonify(result), 400

# 下载 GitHub 上的文件到本地
@github_bp.route('/download', methods=['POST'])
def download_file():
    service = get_service()
    data = request.get_json()

    download_url = data.get("download_url")
    system_type = data.get("system_type")
    filename = data.get("filename")

    if not download_url or not system_type or not filename:
        return jsonify({"error": "缺少必要参数"}), 400

    success, result = service.download_file(download_url, system_type, filename)
    if success:
        return jsonify(result), 200
    return jsonify(result), 400

# 获取文件内容（本地优先）
@github_bp.route('/content', methods=['POST'])
def get_content():
    data = request.get_json()
    file_path = data.get("file_path")

    if not file_path:
        return jsonify({"error": "缺少 file_path 参数"}), 400

    service = get_service()
    success, content, info = service.get_file_content(file_path)

    if success:
        return jsonify({"content": content, "info": info}), 200
    return jsonify({"error": info.get("error")}), 400

# 更新文件内容（只更新本地）
@github_bp.route('/update', methods=['POST'])
def update_file():
    data = request.get_json()
    file_path = data.get("file_path")
    content = data.get("content")

    if not file_path or content is None:
        return jsonify({"error": "缺少参数"}), 400

    service = get_service()
    success, result = service.update_file(file_path, content)

    if success:
        return jsonify(result), 200
    return jsonify(result), 400
