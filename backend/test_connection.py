#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试后端连接"""
import socket
import sys

def test_port(host, port):
    """测试端口是否开放"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex((host, port))
        s.close()
        if result == 0:
            print(f"✓ 端口 {port} 开放，后端服务正在运行")
            return True
        else:
            print(f"✗ 端口 {port} 关闭或不可达 (错误码: {result})")
            return False
    except Exception as e:
        print(f"✗ 测试端口时出错: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("后端连接诊断")
    print("=" * 60)
    test_port("localhost", 1998)
    print("=" * 60)


