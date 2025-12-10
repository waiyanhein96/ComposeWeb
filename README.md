# Docker Compose 管理工具

一个轻量级的Docker Compose管理工具，支持本地和Gitee仓库中的Compose文件管理与部署。

## 功能特点

- **本地文件管理**：上传、编辑、部署本地Docker Compose文件
- **Gitee仓库集成**：从Gitee拉取和部署Docker Compose文件
- **多系统适配**：支持多种NAS系统的Docker Compose配置
- **实时部署状态**：查看部署进度和日志
- **Docker Compose版本管理**：自动检测并支持升级到v2版本
- **镜像源可用性检测**：检查常用镜像源的可用性
- **安全认证**：内置管理员登录系统

## 部署方式

### 使用 docker pull 拉取镜像

```bash
docker pull lastthree/docker-compose-manager:latest
```

### 使用 docker run 快速部署

```bash
docker run -d \
  --name docker-compose-manager \
  -p 5000:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ./data:/app/data \
  --restart unless-stopped \
  lastthree/docker-compose-manager:latest
```

## 访问方式

部署完成后，可以通过以下地址访问管理界面：

```
http://your-server-ip:5000
```

默认登录凭据会在首次启动时生成，查看容器日志获取：

```bash
docker logs docker-compose-manager
```

## 目录结构

- `/app/data`：存储本地和Gitee下载的Docker Compose文件
  - `/app/data/local`：本地上传的文件
  - `/app/data/fnOS`、`/app/data/QNAP`等：各系统类型的文件
- `/app/logs`：部署日志目录

## 支持的系统类型

- 飞牛系统 (fnOS)
- 威联通系统 (QNAP)
- 群晖系统 (Synology)
- True系统 (TrueNAS)
- 绿联系统 (UgreenNew)
- 绿联旧系统 (Ugreen - 废弃)
- 极空间系统 (ZSpace)
- Zima系统 (ZimaOS)

## 注意事项

1. **Docker套接字权限**：确保容器能够正确访问宿主机的Docker套接字
2. **数据持久化**：使用卷挂载保存数据，避免重启容器后数据丢失
3. **首次启动**：系统会自动生成管理员账号和16位强密码，请妥善保存
4. **版本兼容性**：自动检测Docker Compose版本，支持v1和v2版本
5. **安全建议**：建议在生产环境中配置HTTPS和网络访问限制

## API 接口

系统提供以下主要API接口：

- `/api/auth/check` - 检查认证状态
- `/api/local/files` - 获取本地文件列表
- `/api/gitee/files/{system_type}` - 获取指定系统类型的Gitee文件
- `/api/docker/deploy` - 部署Docker Compose文件
- `/api/docker/deployment/status/{id}` - 获取部署状态
- `/api/docker/upgrade-compose` - 升级Docker Compose

## 常见问题

### 1. 无法访问宿主机Docker

确保Docker套接字权限正确，可能需要调整宿主机上的权限或使用docker组。

### 2. 文件上传失败

检查卷挂载是否正确，以及容器内是否有足够的写入权限。

### 3. Gitee文件无法下载

确保网络连接正常，容器可以访问Gitee API。

## 更新日志

### v1.0.0
- 初始版本发布
- 支持本地和Gitee文件管理
- 实现Docker Compose部署功能
- 添加版本检测和升级功能
- 实现多系统类型适配

## License

MIT License