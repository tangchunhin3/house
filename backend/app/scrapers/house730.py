import re
from app.scrapers.base import PlaywrightScraper, parse_price, parse_area, parse_bedrooms
from app.config import settings


class House730Scraper(PlaywrightScraper):
    SOURCE_NAME = "House730"
    AREA_URLS = [
        "https://www.house730.com/en-us/buy/hkp063/",
        "https://www.house730.com/zh-hk/buy/hkp063/",
        "https://www.house730.com/en-us/buy/hk/",
        "https://www.house730.com/zh-hk/buy/hk/",
    ]
    ESTATE_SEARCH_NAMES = ["黃金海灣", "上源", "飛揚"]
    MAX_PAGES = settings.playwright_max_pages

    @staticmethod
    def _extract_estate_name(text: str) -> str:
        estate_suffixes = "苑園閣灣山居庭峰海軒豪臺台廈橋堤岸畔匯城堡廊"
        estate_keywords = {"屋苑", "花園", "廣場", "大廈", "山莊", "豪庭", "新邨", "村"}
        generic_terms = {"屋苑", "住宅", "工商廈", "車位", "寫字樓", "商舖", "工廠", "村屋", "成交紀錄", "月供", "出售中", "寵物樂園", "露台", "有匙", "豪宅", "即時聯絡", "現樓", "全新樓", "九成按揭", "八成按揭", "供平過租", "連露台", "低水", "開揚", "園景", "會所", "泳池", "寵物天地", "屯門公園", "公園", "排行榜", "高層", "中層", "低層", "有海", "池海", "內園", "池園", "花園湖", "大花園", "特大花園", "連花園", "花園"}
        words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        for w in words:
            if w in generic_terms:
                continue
            if len(w) >= 2 and w[-1] in estate_suffixes:
                return w
            if w in estate_keywords:
                return w
        return ""

    @staticmethod
    def _extract_estate_name_from_url(url: str) -> str:
        if not url:
            return ""
        from urllib.parse import unquote
        path = unquote(url.rstrip("/").rsplit("/", 1)[-1])
        districts = {"青山公路", "屯門", "錦田", "元朗", "深井", "掃管笏", "小欖", "青龍頭", "洪水橋", "天水圍", "東涌", "北角", "青衣", "兆康"}
        estate_suffixes = "苑園閣灣山居庭峰海軒豪臺台廈橋堤岸畔匯城堡廊"
        words = re.findall(r'[\u4e00-\u9fff]{2,}', path)
        for w in words:
            if w in districts:
                continue
            if w[-1] in estate_suffixes:
                return w
        # Fallback: return the first non-district Chinese word
        for w in words:
            if w not in districts:
                return w
        return ""

    async def _try_extract(self, page) -> list[dict]:
        results = []
        raw = await page.inner_text("body")
        if "萬" not in raw:
            return results

        cards = await page.query_selector_all("[class*=card], [class*=listing], [class*=property], article")
        if cards:
            for card in cards:
                try:
                    raw = await card.inner_text()
                    if "萬" not in raw:
                        continue

                    # Skip container elements that contain multiple prices
                    price_count = len(re.findall(r'[\$][\d,][\d]*[\s]*萬', raw))
                    if price_count != 1:
                        continue

                    price = parse_price(raw)
                    if price == 0:
                        continue
                    area = parse_area(raw)
                    bedrooms = parse_bedrooms(raw)

                    link_el = await card.query_selector("a[href]")
                    source_url = ""
                    if link_el:
                        href = await link_el.get_attribute("href")
                        if href:
                            if href.startswith("//"):
                                source_url = f"https:{href}"
                            elif href.startswith("http"):
                                source_url = href
                            else:
                                source_url = f"https://www.house730.com{href}"

                    estate_name = self._extract_estate_name_from_url(source_url) or self._extract_estate_name(raw)

                    floor = ""
                    m = re.search(r"(高層|中層|低層)", raw)
                    if m:
                        floor = m.group(1)

                    img_el = await card.query_selector("img")
                    image_url = None
                    if img_el:
                        src = await img_el.get_attribute("src")
                        if src and not src.startswith("data:"):
                            image_url = src

                    results.append(self.build_property(
                        title=estate_name,
                        price=price,
                        area_sqft=area,
                        bedrooms=bedrooms,
                        floor=floor or None,
                        estate_name=estate_name,
                        source_url=source_url,
                        image_url=image_url,
                        description=raw[:500],
                    ))
                except Exception:
                    continue

        # Fallback: block-based regex parsing
        if not results:
            blocks = re.split(r'(?=\$[\d,]+[\s]*萬)', raw)
            for block in blocks:
                if "萬" not in block:
                    continue
                try:
                    price = parse_price(block)
                    if price == 0:
                        continue
                    area = parse_area(block)
                    bedrooms = parse_bedrooms(block)
                    estate_name = self._extract_estate_name(block)

                    results.append(self.build_property(
                        title=estate_name, price=price, area_sqft=area,
                        bedrooms=bedrooms, estate_name=estate_name,
                        source_url="", description=block[:500],
                    ))
                except Exception:
                    continue

        return results

    async def _scrape_with_stealth(self, page, url: str) -> list[dict]:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)
            await self.session.delay()

            try:
                await page.wait_for_selector("[class*=listing], [class*=card], [class*=property], article, main", timeout=8000)
            except Exception:
                pass

            results = await self._try_extract(page)
            if results:
                return results

            # Try scrolling to trigger lazy loading
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, 800)")
                await page.wait_for_timeout(2000)
                results = await self._try_extract(page)
                if results:
                    break

            return results
        except Exception:
            return []

    async def _scrape_keyword(self, keyword: str, page, seen_urls: set, results: list) -> None:
        from urllib.parse import quote
        url = f"https://www.house730.com/zh-hk/buy/?key={quote(keyword)}"
        try:
            page_results = await self._scrape_with_stealth(page, url)
            for p in page_results:
                u = p.get("source_url", "")
                if u and u in seen_urls:
                    continue
                if u:
                    seen_urls.add(u)
                url_estate = self._extract_estate_name_from_url(u)
                if url_estate:
                    p["estate_name"] = url_estate
                    p["title"] = url_estate
                elif not p.get("estate_name"):
                    p["estate_name"] = keyword
                    p["title"] = keyword
                results.append(p)
        except Exception:
            pass

    async def scrape(self, keyword: str = "") -> list[dict]:
        kw = keyword or self.keyword
        all_results = []
        seen_urls = set()

        if kw:
            page = await self.session.new_page()
            try:
                await self._scrape_keyword(kw, page, seen_urls, all_results)
            finally:
                await page.close()
            return all_results

        for base_url in self.AREA_URLS:
            page = await self.session.new_page()
            try:
                for page_num in range(1, self.MAX_PAGES + 1):
                    url = f"{base_url}?page={page_num}" if page_num > 1 else base_url
                    page_results = await self._scrape_with_stealth(page, url)
                    if not page_results:
                        break

                    new_count = 0
                    for p in page_results:
                        u = p.get("source_url", "")
                        if u and u in seen_urls:
                            continue
                        if u:
                            seen_urls.add(u)
                        all_results.append(p)
                        new_count += 1

                    if new_count < 2:
                        break
            finally:
                await page.close()

            if all_results:
                break

        page = await self.session.new_page()
        try:
            for estate_name in self.ESTATE_SEARCH_NAMES:
                await self._scrape_keyword(estate_name, page, seen_urls, all_results)
        finally:
            await page.close()

        if not all_results:
            try:
                from playwright.async_api import async_playwright
                async with async_playwright() as pw:
                    browser = await pw.firefox.launch(headless=settings.playwright_headless)
                    ctx = await browser.new_context(
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:131.0) Gecko/20100101 Firefox/131.0",
                        viewport={"width": 1920, "height": 1080},
                        locale="zh-HK",
                    )
                    page = await ctx.new_page()
                    try:
                        url = self.AREA_URLS[0]
                        page_results = await self._scrape_with_stealth(page, url)
                        for p in page_results:
                            u = p.get("source_url", "")
                            if u and u in seen_urls:
                                continue
                            if u:
                                seen_urls.add(u)
                            all_results.append(p)
                    finally:
                        await page.close()
                        await browser.close()
            except Exception:
                pass

        return all_results
