import re
from app.config import settings
from app.scrapers.base import PlaywrightScraper, parse_price, parse_area, parse_bedrooms


class MidlandScraper(PlaywrightScraper):
    SOURCE_NAME = "美聯"
    AREA_URLS = [
        "https://www.midland.com.hk/zh-hk/list/buy/屯門-市中心-D-130ND30013",
        "https://www.midland.com.hk/zh-hk/list/buy/屯門-碼頭-D-130ND30012",
        "https://www.midland.com.hk/zh-hk/list/buy/掃管笏-D-130ND30014",
        "https://www.midland.com.hk/zh-hk/list/buy/掃管笏-D-130ND30015",
        "https://www.midland.com.hk/zh-hk/list/buy/小欖-D-130ND30016",
        "https://www.midland.com.hk/zh-hk/list/buy/黃金海岸-D-130ND30021",
    ]
    ESTATE_SEARCH_NAMES = ["黃金海灣", "上源", "飛揚"]
    MAX_PAGES = settings.playwright_max_pages

    @staticmethod
    def _extract_estate_name(text: str) -> str:
        estate_suffixes = "苑園閣灣山居庭峰海軒豪臺台廈橋堤岸畔匯城堡廊"
        estate_keywords = {"屋苑", "花園", "廣場", "大廈", "山莊", "豪庭", "新邨", "村"}
        generic_terms = {"屋苑", "住宅", "工商廈", "車位", "寫字樓", "商舖", "工廠", "村屋", "成交紀錄", "月供", "出售中", "寵物樂園", "露台", "有匙", "豪宅", "即時聯絡", "現樓", "全新樓", "九成按揭", "八成按揭", "供平過租", "連露台", "低水", "開揚", "園景", "會所", "泳池", "寵物天地", "屯門公園", "公園", "排行榜", "高層", "中層", "低層", "有海", "池海", "內園", "池園", "花園湖", "大花園", "特大花園", "連花園", "花園", "休憩花園"}
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
        if not url or "/zh-hk/property/" not in url:
            return ""
        from urllib.parse import unquote
        path = unquote(url.split("/zh-hk/property/", 1)[-1])
        # Path: 新界-{district}-{estate}-...
        parts = path.split("-")
        # Skip first part (新界) and known districts
        districts = {"屯門", "屯門市中心", "屯門碼頭", "掃管笏", "小欖", "黃金海岸", "元朗", "元朗市中心", "天水圍", "錦田", "加州", "錦綉", "上水", "南昌站", "新界", "九龍"}
        estate_suffixes = "苑園閣灣山居庭峰海軒豪臺台廈橋堤岸畔匯城堡廊"
        estate_keywords = {"屋苑", "花園", "廣場", "大廈", "山莊", "豪庭", "新邨", "村"}
        for part in parts:
            if part in districts:
                continue
            words = re.findall(r'[\u4e00-\u9fff]{2,}', part)
            for w in words:
                if w[-1] in estate_suffixes:
                    return w
                if w in estate_keywords:
                    return w
        return ""

    async def _extract_page(self, page) -> list[dict]:
        results = []
        cards = await page.query_selector_all(
            "[class*=property-card], [class*=listing-card], [class*=item-card], "
            "[class*=prop-card], [class*=result-item]"
        )
        if not cards:
            try:
                raw = await page.inner_text("body")
                if "萬" not in raw:
                    return results

                # Extract real property links from the page
                link_elements = await page.query_selector_all(
                    "a[href*='/zh-hk/property/']:not([href*='process']):not([href*='bookmark'])"
                )
                links = []
                for el in link_elements:
                    try:
                        href = await el.get_attribute("href")
                        if href and ("process" not in href and "bookmark" not in href):
                            links.append(href)
                    except Exception:
                        continue

                blocks = re.split(r'(?=\$[\d,]+[\s]*萬)', raw)
                link_idx = 0
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
                        floor = ""
                        m = re.search(r"(高層|中層|低層)", block)
                        if m:
                            floor = m.group(1)

                        source_url = ""
                        if link_idx < len(links):
                            href = links[link_idx]
                            source_url = href if href.startswith("http") else f"https://www.midland.com.hk{href}"
                            link_idx += 1

                        if not source_url and estate_name and price:
                            from hashlib import md5
                            uid = md5(f"{estate_name}:{price}:{area}:{bedrooms}".encode()).hexdigest()[:12]
                            source_url = f"https://www.midland.com.hk/property/{uid}"

                        if source_url:
                            estate_name = self._extract_estate_name_from_url(source_url) or estate_name

                        is_transaction = "成交紀錄" in estate_name
                        results.append(self.build_property(
                            title=estate_name, price=price, area_sqft=area,
                            bedrooms=bedrooms, floor=floor or None,
                            estate_name=estate_name,
                            source_url=source_url,
                            description=block[:500],
                            is_transaction=is_transaction,
                        ))
                    except Exception:
                        continue
            except Exception:
                pass
            return results

        for card in cards:
            try:
                raw = await card.inner_text()
                if "萬" not in raw:
                    continue
                price = parse_price(raw)
                if price == 0:
                    continue
                area = parse_area(raw)
                bedrooms = parse_bedrooms(raw)
                estate_name = self._extract_estate_name(raw)

                floor = ""
                m = re.search(r"(高層|中層|低層)", raw)
                if m:
                    floor = m.group(1)

                from hashlib import md5
                link_el = await card.query_selector("a[href]")
                source_url = ""
                if link_el:
                    href = await link_el.get_attribute("href")
                    if href:
                        source_url = href if href.startswith("http") else f"https://www.midland.com.hk{href}"

                if not source_url and estate_name and price:
                    uid = md5(f"{estate_name}:{price}:{area}:{bedrooms}".encode()).hexdigest()[:12]
                    source_url = f"https://www.midland.com.hk/property/{uid}"

                img_el = await card.query_selector("img")
                image_url = None
                if img_el:
                    src = await img_el.get_attribute("src")
                    if src and not src.startswith("data:") and "res-fh" in src:
                        image_url = src

                is_transaction = "成交紀錄" in estate_name
                results.append(self.build_property(
                    title=estate_name, price=price, area_sqft=area,
                    bedrooms=bedrooms, floor=floor or None,
                    estate_name=estate_name, source_url=source_url,
                    image_url=image_url, description=raw[:500],
                    is_transaction=is_transaction,
                ))
            except Exception:
                continue
        return results

    async def _scrape_keyword(self, keyword: str, page, seen_urls: set, results: list) -> None:
        from urllib.parse import quote
        url = f"https://www.midland.com.hk/zh-hk/list/buy?keyword={quote(keyword)}"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(5000)
            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(3000)
            await self.session.delay()
            page_results = await self._extract_page(page)
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
                p["is_transaction"] = False
                results.append(p)
        except Exception:
            pass

    async def scrape(self, keyword: str = "") -> list[dict]:
        kw = keyword or self.keyword
        page = await self.session.new_page()
        all_results = []
        seen_urls = set()
        try:
            if kw:
                await self._scrape_keyword(kw, page, seen_urls, all_results)
                return all_results

            for base_url in self.AREA_URLS:
                for page_num in range(1, self.MAX_PAGES + 1):
                    url = f"{base_url}?page={page_num}" if page_num > 1 else base_url
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        await page.wait_for_timeout(8000)
                        await self.session.delay()
                    except Exception:
                        break

                    page_results = await self._extract_page(page)
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

            for estate_name in self.ESTATE_SEARCH_NAMES:
                await self._scrape_keyword(estate_name, page, seen_urls, all_results)
        finally:
            await page.close()
        return all_results