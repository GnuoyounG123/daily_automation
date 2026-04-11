#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

# 重定向标准输出到文件
output_file = r"C:\Users\lenovo\AppData\Local\Temp\config_test_output.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    sys.stdout = f
    sys.stderr = f

    try:
        import test_config
        result = test_config.main()
        print(f"\n测试退出码: {result}")
    except Exception as e:
        print(f"运行测试时出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print(f"输出已保存到: {output_file}")
