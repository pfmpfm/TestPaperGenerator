#!/bin/bash

# MySQL 数据库备份脚本
# 由 Docker Compose 定时调用

BACKUP_DIR="/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/exam_generator_${TIMESTAMP}.sql"

# 执行备份
mysqldump -h mysql -u root -proot_password_change_me exam_generator > "$BACKUP_FILE"

# 压缩备份
gzip "$BACKUP_FILE"

# 删除7天前的备份
find "$BACKUP_DIR" -name "exam_generator_*.sql.gz" -mtime +7 -delete

echo "备份完成: ${BACKUP_FILE}.gz"
