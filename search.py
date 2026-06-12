#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猪猪侠搜索工具 v2 - 使用 Playwright + Google Chrome
支持 Google 和 Bing 搜索
用法: python3 search.py "搜索关键词" [google|bing]
"""

import sys
import json
import time
from playwright.sync_api import sync_playwright

def search_google(page, query, num_results=10):
    """使用 Google 搜索并返回结果"""
    # 先访问 Google 首页，模拟人类行为
    page.goto("https://www.google.com", wait_until="domcontentloaded")
    time.sleep(1)
    
    # 尝试找到搜索框并输入
    try:
        search_box = page.wait_for_selector("input[name='q']", timeout=5000)
        search_box.fill(query)
        search_box.press("Enter")
        page.wait_for_load_state("networkidle")
    except:
        # 如果找不到搜索框，直接访问搜索结果页
        search_url = f"https://www.google.com/search?q={query}&hl=zh-CN&num={num_results}"
        page.goto(search_url, wait_until="domcontentloaded")
    
    time.sleep(2)
    
    # 尝试多种选择器
    results = []
    
    # 方法1: 标准搜索结果
    try:
        search_results = page.query_selector_all("div.g")
        for result in search_results[:num_results]:
            try:
                title_elem = result.query_selector("h3")
                title = title_elem.inner_text() if title_elem else ""
                
                link_elem = result.query_selector("a[href^='http']")
                link = link_elem.get_attribute("href") if link_elem else ""
                
                snippet_elem = (
                    result.query_selector("div.VwiC3b") or 
                    result.query_selector("span.aCOpRe") or
                    result.query_selector("div[style*='-webkit-line-clamp']")
                )
                snippet = snippet_elem.inner_text() if snippet_elem else ""
                
                if title and link and not link.startswith("/search"):
                    results.append({
                        "title": title,
                        "link": link,
                        "snippet": snippet
                    })
            except:
                continue
    except:
        pass
    
    # 方法2: 如果方法1失败，尝试其他选择器
    if not results:
        try:
            all_links = page.query_selector_all("a[href^='http']")
            for link_elem in all_links[:num_results * 2]:
                try:
                    href = link_elem.get_attribute("href")
                    if href and not any(x in href for x in ["google.com", "youtube.com", "gstatic.com"]):
                        title = link_elem.inner_text().strip()
                        if title and len(title) > 5:
                            results.append({
                                "title": title,
                                "link": href,
                                "snippet": ""
                            })
                            if len(results) >= num_results:
                                break
                except:
                    continue
        except:
            pass
    
    return results

def search_bing(page, query, num_results=10):
    """使用 Bing 搜索并返回结果"""
    search_url = f"https://www.bing.com/search?q={query}&count={num_results}"
    page.goto(search_url, wait_until="domcontentloaded")
    time.sleep(2)
    
    results = []
    try:
        search_results = page.query_selector_all("li.b_algo")
        for result in search_results[:num_results]:
            try:
                title_elem = result.query_selector("h2 a")
                title = title_elem.inner_text() if title_elem else ""
                link = title_elem.get_attribute("href") if title_elem else ""
                
                snippet_elem = result.query_selector("p") or result.query_selector("div.b_caption p")
                snippet = snippet_elem.inner_text() if snippet_elem else ""
                
                if title and link:
                    results.append({
                        "title": title,
                        "link": link,
                        "snippet": snippet
                    })
            except:
                continue
    except:
        pass
    
    return results

def main():
    if len(sys.argv) < 2:
        print("用法: python3 search.py '搜索关键词' [google|bing]")
        sys.exit(1)
    
    query = sys.argv[1]
    engine = sys.argv[2] if len(sys.argv) > 2 else "bing"  # 默认用 Bing，更宽松
    
    print(f"🔍 使用 {engine.upper()} 搜索: {query}\n")
    
    with sync_playwright() as p:
        # 使用系统已安装的 Google Chrome
        browser = p.chromium.launch(
            channel="chrome",
            headless=True
        )
        
        # 设置更真实的浏览器配置
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        try:
            if engine == "google":
                results = search_google(page, query)
            else:
                results = search_bing(page, query)
            
            if not results:
                print("❌ 没有找到结果")
                # 保存页面截图用于调试
                page.screenshot(path="/tmp/search_debug.png")
                print("📸 已保存调试截图到 /tmp/search_debug.png")
                sys.exit(1)
            
            print(f"✅ 找到 {len(results)} 条结果:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']}")
                print(f"   链接: {result['link']}")
                if result['snippet']:
                    print(f"   摘要: {result['snippet'][:200]}")
                print()
            
            # 输出 JSON 格式（方便后续处理）
            print("\n=== JSON 格式 ===")
            print(json.dumps(results, ensure_ascii=False, indent=2))
            
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
            page.screenshot(path="/tmp/search_debug.png")
            print("📸 已保存调试截图到 /tmp/search_debug.png")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    main()
