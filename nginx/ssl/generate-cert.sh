#!/bin/bash
# 生成自签名 SSL 证书 (仅用于开发/测试环境)
# 生产环境请使用 Let's Encrypt 或购买的证书

CERT_DIR="/home/pengfaming/python-practise/TestPaperGenerator/nginx/ssl"
CERT_FILE="$CERT_DIR/cert.pem"
KEY_FILE="$CERT_DIR/key.pem"

mkdir -p "$CERT_DIR"

if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo "SSL 证书已存在，跳过生成"
    exit 0
fi

echo "生成自签名 SSL 证书..."

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=ExamGenerator/OU=IT/CN=localhost"

chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

echo "SSL 证书生成完成:"
echo "  证书: $CERT_FILE"
echo "  密钥: $KEY_FILE"
echo ""
echo "注意: 这是自签名证书，仅用于开发/测试环境"
echo "生产环境请使用 Let's Encrypt 或购买的证书"
