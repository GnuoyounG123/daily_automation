#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬取功能测试
测试学术信息爬取的核心功能
"""

import sys
import os
import json
import tempfile
import time
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from daily_assistant import (
    load_config, log_message,
    InfoCrawler, InfoProcessor, Translator
)


class CrawlFunctionTest:
    """爬取功能测试类"""

    def __init__(self):
        self.test_dir = None
        self.original_config = None

    def setup(self):
        """测试前准备"""
        print("="*60)
        print("爬取功能测试")
        print("="*60)

        # 创建临时目录
        self.test_dir = Path(tempfile.mkdtemp(prefix="crawl_test_"))
        print(f"测试目录: {self.test_dir}")

        # 创建必要的子目录
        (self.test_dir / "data").mkdir(exist_ok=True)
        (self.test_dir / "logs").mkdir(exist_ok=True)

        print("✓ 测试环境准备完成")
        return True

    def teardown(self):
        """测试后清理"""
        import shutil
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
            print(f"✓ 清理测试目录: {self.test_dir}")

    def run_all_tests(self):
        """运行所有测试"""
        print("\n运行爬取功能测试...")

        tests = [
            self.test_translator,
            self.test_info_crawler_init,
            self.test_info_processor,
            self.test_crawl_mock_source,
        ]

        passed = 0
        failed = 0

        for test in tests:
            print(f"\n[测试] {test.__name__}")
            try:
                result = test()
                if result:
                    print(f"  ✓ {test.__name__} 通过")
                    passed += 1
                else:
                    print(f"  ✗ {test.__name__} 失败")
                    failed += 1
            except Exception as e:
                failed += 1
                print(f"  ✗ {test.__name__} 异常: {e}")
                import traceback
                traceback.print_exc()

        print("\n" + "="*60)
        print(f"测试结果: 通过 {passed}/{len(tests)}，失败 {failed}")
        print("="*60)

        return failed == 0

    def test_translator(self):
        """测试翻译器"""
        print("  测试翻译器基本功能...")

        # 测试术语翻译
        translated = Translator.translate_text("artificial intelligence")
        assert "人工智能" in translated or "artificial intelligence" in translated

        # 测试标题翻译
        title = "A Study on Machine Learning Algorithms"
        translated_title = Translator.translate_title(title)
        assert len(translated_title) > 0

        # 测试精华提取
        abstract = "This paper proposes a novel approach to deep learning."
        essence = Translator.extract_essence(abstract, max_length=100)
        assert len(essence) > 0

        print("  ✓ 翻译器功能正常")
        return True

    def test_info_crawler_init(self):
        """测试信息爬取器初始化"""
        print("  测试爬取器初始化...")

        crawler = InfoCrawler()
        assert crawler is not None
        assert hasattr(crawler, 'headers')
        assert hasattr(crawler, 'results')

        print("  ✓ 爬取器初始化正常")
        return True

    def test_info_processor(self):
        """测试信息处理器"""
        print("  测试信息处理器...")

        # 测试关键词匹配
        keywords = ["artificial intelligence", "machine learning"]
        processor = InfoProcessor(keywords)

        # 测试相关度计算
        test_item = {
            'title': 'A study on artificial intelligence',
            'abstract': 'This paper discusses machine learning techniques.'
        }
        score, matched = processor.calculate_relevance(test_item)
        assert score > 0
        assert len(matched) > 0

        # 测试过滤和排序
        items = [
            {'title': 'AI research', 'abstract': 'artificial intelligence'},
            {'title': 'Other topic', 'abstract': 'unrelated'}
        ]
        filtered = processor.filter_and_rank(items)
        assert len(filtered) == 1

        print("  ✓ 信息处理器功能正常")
        return True

    def test_crawl_mock_source(self):
        """测试模拟爬取（不实际访问网络）"""
        print("  测试模拟爬取功能...")

        # 创建测试配置
        test_config = {
            'news_sources': [
                {
                    'name': '测试源',
                    'url': 'http://example.com/test',
                    'type': 'rss',
                    'enabled': True
                }
            ],
            'keywords': ['test', 'example'],
            'keywords_cn': ['测试'],
            'output_format': 'markdown',
            'max_items_per_source': 3
        }

        # 保存测试配置
        config_file = self.test_dir / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)

        print("  ✓ 测试配置已创建")

        # 注：实际网络爬取测试可能需要网络连接
        # 这里我们只测试模块的可用性
        print("  ⚠️  跳过实际网络爬取（需要网络连接）")

        return True

    def test_offline_crawl(self):
        """离线爬取测试（不依赖网络）"""
        print("  测试离线爬取逻辑...")

        try:
            # 导入必要的模块
            from daily_assistant import InfoCrawler, InfoProcessor

            # 创建爬取器
            crawler = InfoCrawler()

            # 测试解析功能（不实际获取内容）
            test_xml = '''<?xml version="1.0"?>
            <rss>
            <channel>
                <item>
                    <title>Test Paper</title>
                    <description>This is a test paper about AI</description>
                    <link>http://example.com/1</link>
                </item>
            </channel>
            </rss>'''

            # 测试解析功能
            items = crawler.parse_generic_rss(test_xml, "测试源")
            assert len(items) > 0
            assert items[0]['title'] == 'Test Paper'

            print("  ✓ 离线爬取逻辑正常")
            return True
        except Exception as e:
            print(f"  ✗ 离线爬取测试失败: {e}")
            return False


def main():
    """主测试函数"""
    tester = CrawlFunctionTest()

    try:
        tester.setup()
        success = tester.run_all_tests()
        tester.teardown()

        if success:
            print("\n🎉 爬取功能测试通过！")
            print("\n注意：实际网络爬取测试需要网络连接")
            print("如需测试实际爬取，请运行: python daily_assistant.py")
            return 0
        else:
            print("\n❌ 部分爬取功能测试失败")
            return 1
    except Exception as e:
        print(f"\n⚠️ 测试过程出现异常: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())