import re
from app.config import settings
from app.scrapers.base import PlaywrightScraper, parse_price, parse_area, parse_bedrooms


class CentalineScraper(PlaywrightScraper):
    SOURCE_NAME = "中原"
    BASE_URL = "https://hk.centanet.com/findproperty/list/buy/%E5%B1%AF%E9%96%80_23-WS046"
    ESTATE_SEARCH_NAMES = ["黃金海灣", "上源", "飛揚"]
    MAX_PAGES = settings.playwright_max_pages

    @staticmethod
    def _extract_estate_name(text: str) -> str:
        estate_suffixes = "苑園閣灣山居庭峰海軒豪臺台廈橋堤岸畔匯城堡廊"
        estate_keywords = {"屋苑", "花園", "廣場", "大廈", "山莊", "豪庭", "新邨", "村"}
        generic_terms = {"屋苑", "住宅", "工商廈", "車位", "寫字樓", "商舖", "工廠", "村屋", "成交紀錄", "月供", "出售中", "寵物樂園", "露台", "有匙", "豪宅", "即時聯絡", "現樓", "全新樓", "九成按借", "八成按揭", "供平過租", "連露台", "低水", "開揚", "園景", "會所", "泳池", "寵物天地", "屯門公園", "公園", "排行榜", "高層", "中層", "低層", "有海", "池海", "內園", "池園", "花園湖", "大花園", "特大花園", "連花園", "花園", "休憩花園"}
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
        estate_suffixes = "苑園閣灣山居庭峰海軒豪臺台廈橋堤岸畔匯城堡廊"
        words = re.findall(r'[\u4e00-\u9fff]{2,}', path)
        for w in words:
            if w[-1] in estate_suffixes:
                return w
        if words:
            return words[0]
        return ""

    async def _extract_page(self, page) -> list[dict]:
        results = []
        try:
            cards = await page.query_selector_all("div.list")
        except Exception:
            return results

        for card in cards:
            try:
                raw = await card.inner_text()

                link_el = await card.query_selector("a.property-text")
                if not link_el:
                    continue
                href = await link_el.get_attribute("href")
                source_url = href if href.startswith("http") else f"https://hk.centanet.com{href}"

                title_el = await card.query_selector("span.title-lg")
                title = await title_el.inner_text() if title_el else ""
                estate_name = self._extract_estate_name_from_url(source_url) or self._extract_estate_name(title) or self._extract_estate_name(raw) or title.strip()[:30]

                price = parse_price(raw)
                area = parse_area(raw)
                bedrooms = parse_bedrooms(raw)

                img_el = await card.query_selector("img")
                image_url = None
                if img_el:
                    src = await img_el.get_attribute("src")
                    if src and not src.startswith("data:"):
                        image_url = src

                floor = ""
                m = re.search(r"(高層|中層|低層)", raw)
                if m:
                    floor = m.group(1)

                results.append(self.build_property(
                    title=title.strip(),
                    price=price,
                    area_sqft=area,
                    bedrooms=bedrooms,
                    floor=floor or None,
                    estate_name=estate_name,
                    source_url=source_url,
                    image_url=image_url,
                    description=raw.strip()[:500],
                ))
            except Exception:
                continue
        return results

    async def _click_next_page(self, page) -> bool:
        try:
            has_next = await page.eval_on_selector_all(
                "button[aria-label*='next' i], button[aria-label*='下一頁'], "
                ".mat-paginator-navigation-next:not([disabled]), "
                "a[rel='next']",
                "els => els.length > 0 && !els[0].disabled"
            )
            if not has_next:
                return False

            await page.eval_on_selector(
                "button[aria-label*='next' i], button[aria-label*='下一頁'], "
                ".mat-paginator-navigation-next",
                "el => el.click()"
            )
            await page.wait_for_timeout(5000)
            return True
        except Exception:
            return False

    async def _scrape_keyword(self, keyword: str, page, seen_urls: set, results: list) -> None:
        from urllib.parse import quote
        url = f"https://hk.centanet.com/findproperty/list/buy/?keyword={quote(keyword)}"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector("div.list", timeout=10000)
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

            for page_num in range(1, self.MAX_PAGES + 1):
                url = f"{self.BASE_URL}?page={page_num}"
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_selector("div.list", timeout=10000)
                    await self.session.delay()
                except Exception:
                    break

                page_results = await self._extract_page(page)
                new_count = 0
                for p in page_results:
                    u = p.get("source_url", "")
                    if u and u in seen_urls:
                        continue
                    if u:
                        seen_urls.add(u)
                    all_results.append(p)
                    new_count += 1

                if len(page_results) < 20 and page_num > 1:
                    break

            for _ in range(5):
                has_more = await self._click_next_page(page)
                if not has_more:
                    break

                page_results = await self._extract_page(page)
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