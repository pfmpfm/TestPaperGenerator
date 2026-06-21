# ==================== 前端静态资源 ====================
location / {
    root /usr/share/nginx/html/frontend;
    try_files $uri $uri/ /index.html;
    expires 7d;
    add_header Cache-Control "public, immutable";
}

# ==================== API 接口代理 ====================
location /api/ {
    proxy_pass http://backend_servers;

    # 代理头
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # 超时配置
    proxy_connect_timeout 60s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    # 缓冲配置
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
    proxy_busy_buffers_size 8k;

    # 错误处理
    proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
    proxy_next_upstream_tries 2;
}

# ==================== WebSocket 代理 ====================
location /ws/ {
    proxy_pass http://backend_servers;

    # WebSocket 升级
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    # 代理头
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # 超时配置 (WebSocket 长连接)
    proxy_connect_timeout 7d;
    proxy_send_timeout 7d;
    proxy_read_timeout 7d;
}

# ==================== 静态资源 (图片、文件等) ====================
location /static/ {
    alias /usr/share/nginx/html/static/;
    expires 30d;
    add_header Cache-Control "public, immutable";

    # 跨域配置
    add_header Access-Control-Allow-Origin *;
    add_header Access-Control-Allow-Methods "GET, OPTIONS";
    add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range";

    # 图片格式
    location ~* \.(jpg|jpeg|png|gif|svg|webp)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 文档格式
    location ~* \.(pdf|doc|docx|xls|xlsx)$ {
        expires 7d;
        add_header Content-Disposition "inline";
    }
}

# ==================== 健康检查 ====================
location /health {
    access_log off;
    proxy_pass http://backend_servers/health;
    proxy_set_header Host $host;
}

# ==================== Prometheus Metrics ====================
location /metrics {
    proxy_pass http://backend_servers/metrics;
    proxy_set_header Host $host;

    # 仅允许内网访问
    allow 172.28.0.0/16;
    deny all;
}

# ==================== 安全配置 ====================
# 禁止访问隐藏文件
location ~ /\. {
    deny all;
    access_log off;
    log_not_found off;
}

# 禁止访问备份文件
location ~ ~$ {
    deny all;
    access_log off;
    log_not_found off;
}
