import re
from app.config import settings
from app.scrapers.base import PlaywrightScraper, parse_price, parse_area, parse_bedrooms


class RicacorpScraper(PlaywrightScraper):
    SOURCE_NAME = "利嘉閣"
    PLAYWRIGHT_CHANNEL = "chrome"
    AREA_URLS = [
        "https://www.ricacorp.com/zh-hk/property/list/buy/%E5%B1%AF%E9%96%80-district-%E6%96%B0%E7%95%8C%E8%A5%BF-scope-hk",
        "https://www.ricacorp.com/zh-hk/property/list/buy/%E6%8E%83%E7%AE%A1%E7%AC%8F-district-%E6%96%B0%E7%95%8C%E8%A5%BF-scope-hk",
        "https://www.ricacorp.com/zh-hk/property/list/buy/%E5%B0%8F%E6%AC%96-district-%E6%96%B0%E7%95%8C%E8%A5%BF-scope-hk",
        "https://www.ricacorp.com/zh-hk/property/list/buy/%E9%9D%92%E9%BE%8D%E9%A0%AD-district-%E6%96%B0%E7%95%8C%E8%A5%BF-scope-hk",
        "https://www.ricacorp.com/zh-hk/property/list/buy/%E6%B7%B1%E4%BA%95-district-%E6%96%B0%E7%95%8C%E8%A5%BF-scope-hk",
        "https://www.ricacorp.com/zh-hk/property/list/buy/%E9%BB%83%E9%87%91%E6%B5%B7%E5%B2%B8-district-%E6%96%B0%E7%95%8C%E8%A5%BF-scope-hk",
        "https://www.ricacorp.com/zh-hk/property/list/buy/%E9%9D%92%E5%B1%B1%E5%85%AC%E8%B7%AF-district-%E6%96%B0%E7%95%8C%E8%A5%BF-scope-hk",
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
        if not url or "/detail/" not in url:
            return ""
        from urllib.parse import unquote
        path = unquote(url.split("/detail/", 1)[-1])
        districts = {"屯門", "屯門市中心", "屯門新墟", "屯門北", "屯門碼頭", "掃管笏", "小欖", "黃金海岸", "元朗", "元朗東南", "朗屏", "天水圍", "錦田", "加州", "錦綉", "上水", "南昌站", "藍田", "調景嶺", "將軍澳", "青衣", "東涌", "東涌市中心", "北角", "西半山", "九龍站", "下葵涌", "兆康", "葵涌", "荃灣"}
        estate_suffixes = "苑園閣灣山居庭峰海軒豪臺台廈橋堤岸畔匯城堡廊"
        if "-hma-" in path:
            after_hma = path.split("-hma-", 1)[-1]
            words = re.findall(r'[\u4e00-\u9fff]{2,}', after_hma)
            for w in words:
                if w not in districts and w[-1] in estate_suffixes:
                    return w
            for w in words:
                if w not in districts:
                    return w
        words = re.findall(r'[\u4e00-\u9fff]{2,}', path)
        for w in words:
            if w not in districts and w[-1] in estate_suffixes:
                return w
        for w in words:
            if w not in districts:
                return w
        return ""

    async def _extract_page(self, page) -> list[dict]:
        results = []
        raw = await page.inner_text("body")
        if "萬" not in raw:
            return results

        link_elements = await page.query_selector_all("a[href*='/property/detail/']")
        links = []
        for el in link_elements:
            try:
                href = await el.get_attribute("href")
                text = await el.inner_text()
                parent = await el.query_selector("xpath=..")
                img_url = None
                if parent:
                    imgs = await parent.query_selector_all("img")
                    for img in imgs:
                        src = await img.get_attribute("src")
                        if src and "resourcecdn" in src and not src.startswith("data:") and "slogans" not in src and "tag" not in src:
                            img_url = src
                            break
                links.append({"href": href or "", "text": text or "", "image_url": img_url})
            except Exception:
                continue

        cards = await page.query_selector_all(
            "RC-PROPERTY-LISTING-ITEM-DESKTOP, RC-PROPERTY-LISTING-ITEM-MOBILE"
        )
        if cards:
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
                    link_el = await card.query_selector("a[href*='/property/detail/']")
                    source_url = ""
                    if link_el:
                        href = await link_el.get_attribute("href")
                        if href:
                            source_url = href if href.startswith("http") else f"https://www.ricacorp.com{href}"

                    estate_name = self._extract_estate_name_from_url(source_url) or self._extract_estate_name(raw)

                    floor = ""
                    m = re.search(r"(高層|中層|低層)", raw)
                    if m:
                        floor = m.group(1)

                    img_el = await card.query_selector("img[src*='resourcecdn']")
                    image_url = None
                    if img_el:
                        src = await img_el.get_attribute("src")
                        if src and not src.startswith("data:") and "slogans" not in src and "tag" not in src:
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

            if results:
                return results

        # Fallback: body text regex parsing — match links by property ID, not sequential index
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

                pid_match = re.search(r'物業編號\s*(\S+)', block)
                source_url = ""
                image_url = None
                if pid_match:
                    pid = pid_match.group(1)
                    raw_pid = pid.lower()
                    # Find matching link by property ID
                    for link in links:
                        href = link.get("href", "")
                        if raw_pid in href.lower():
                            source_url = href if href.startswith("http") else f"https://www.ricacorp.com{href}"
                            image_url = link.get("image_url")
                            break
                    if not source_url:
                        source_url = f"https://www.ricacorp.com/zh-hk/property/detail/{pid}"

                estate_name = self._extract_estate_name_from_url(source_url) or self._extract_estate_name(block)

                floor = ""
                m = re.search(r"(高層|中層|低層)", block)
                if m:
                    floor = m.group(1)

                is_transaction = "成交紀錄" in estate_name

                results.append(self.build_property(
                    title=estate_name, price=price, area_sqft=area,
                    bedrooms=bedrooms, floor=floor or None,
                    estate_name=estate_name, source_url=source_url,
                    image_url=image_url,
                    description=block[:500],
                    is_transaction=is_transaction,
                ))
            except Exception:
                continue

        return results

    async def _scrape_area(self, base_url: str, page, seen_urls: set) -> list[dict]:
        area_results = []
        for page_num in range(1, self.MAX_PAGES + 1):
            url = f"{base_url}?page={page_num}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(5000)
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
                area_results.append(p)
                new_count += 1

            if new_count < 2:
                break

        # Try Angular paginator click-based pagination
        for _ in range(5):
            try:
                has_next = await page.eval_on_selector_all(
                    "button[aria-label*='next' i], button[aria-label*='下一頁'], "
                    ".mat-paginator-navigation-next:not([disabled]), "
                    "a[rel='next']:not([disabled])",
                    "els => els.length > 0"
                )
                if not has_next:
                    break

                await page.eval_on_selector(
                    "button[aria-label*='next' i], button[aria-label*='下一頁'], "
                    ".mat-paginator-navigation-next",
                    "el => el.click()"
                )
                await page.wait_for_timeout(5000)
                await self.session.delay()

                page_results = await self._extract_page(page)
                for p in page_results:
                    u = p.get("source_url", "")
                    if u and u in seen_urls:
                        continue
                    if u:
                        seen_urls.add(u)
                    area_results.append(p)
            except Exception:
                break

        return area_results

    async def _scrape_keyword(self, keyword: str, page, seen_urls: set, results: list) -> None:
        from urllib.parse import quote
        url = f"https://www.ricacorp.com/zh-hk/property/list/search?keyword={quote(keyword)}"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(5000)
            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(2000)
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
                area_results = await self._scrape_area(base_url, page, seen_urls)
                all_results.extend(area_results)

            for estate_name in self.ESTATE_SEARCH_NAMES:
                await self._scrape_keyword(estate_name, page, seen_urls, all_results)
        finally:
            await page.close()
        return all_results
