import re
from urllib.parse import quote

from app.config import settings
from app.scrapers.base import RequestScraper, get_soup, parse_price, parse_area, parse_bedrooms


class House28SeScraper(RequestScraper):
    SOURCE_NAME = "28Hse"
    AREA_URLS = [
        "https://www.28hse.com/buy/a3/dg48",
        "https://www.28hse.com/buy/a3/dg52",
    ]
    SEARCH_URL = "https://www.28hse.com/buy"
    MAX_PAGES = settings.max_pages

    def __init__(self, keyword: str = ""):
        self.keyword = keyword

    @staticmethod
    def _extract_estate_name(text: str) -> str:
        m = re.search(r'屯門(?:\(青山公路\))?\s+([^|]+?)\s*\|', text)
        if m:
            return m.group(1).strip()
        for area_label in ("屯門", "青山公路"):
            if area_label in text:
                m = re.search(rf'{area_label}[)）]?\s*([\u4e00-\u9fff]+)', text)
                if m:
                    return m.group(1)
        all_words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        skip = {
            "實用面積", "建築面積", "小時前", "不限",
            "按揭計算機", "萬元", "校網", "低層", "中層", "高層", "新界",
            "浴室", "開放式間隔", "向西北", "向東南", "向西南", "向東北",
            "已補地價", "優質校網", "豪華裝修", "雅緻裝修", "有會所",
            "近地鐵站", "近大型商場", "望山景", "望園景", "望開揚景", "望市景",
            "望河景", "望海景", "有景觀", "靚裝即住", "價錢可議", "業主急走",
            "移民急讓", "投資收租", "歡迎查詢", "歡迎諮詢", "歡迎大學生",
            "鐵路沿線", "普通盤", "獨家盤", "全層單位",
            "黃金", "連套房", "向南", "有工人房", "有露台", "連花園",
            "私人屋苑", "大型屋苑", "室內車位", "望泳池景", "全幢",
            "屯門", "青山公路", "邊", "居屋",
            "新鴻基", "恒基", "恒隆", "大昌", "華懋", "信和", "莊士中國",
            "世紀", "香港置業",
        }
        for w in reversed(all_words):
            if w not in skip and len(w) >= 2 and re.match(r'[\u4e00-\u9fff]', w[-1]):
                if not any(kw in w for kw in ["代理", "地產"]):
                    return w
        return ""

    def _parse_cards(self, cards, seen_urls: set = None) -> list[dict]:
        if seen_urls is None:
            seen_urls = set()
        results = []
        for card in cards:
            try:
                link_el = card.select_one("a[href*='/buy/']")
                if not link_el:
                    continue
                href = link_el.get("href", "")
                source_url = href if href.startswith("http") else f"https://www.28hse.com{href}"
                if source_url and source_url in seen_urls:
                    continue
                if source_url:
                    seen_urls.add(source_url)

                price_el = card.select_one("div.large.label")
                if not price_el:
                    continue
                price_text = price_el.get_text(strip=True)
                if "萬" not in price_text:
                    continue
                price = parse_price(price_text)
                if price == 0:
                    continue

                raw = card.get_text(" ", strip=True)
                area = parse_area(raw)
                bedrooms = parse_bedrooms(raw)
                estate = self._extract_estate_name(raw)
                if not estate:
                    continue

                img = card.select_one("img")
                image_url = None
                if img:
                    src = img.get("src") or img.get("data-src") or ""
                    if src and not src.startswith("data:"):
                        image_url = src if src.startswith("http") else f"https:{src}" if src.startswith("//") else src

                results.append(self.build_property(
                    title=estate,
                    price=price,
                    area_sqft=area,
                    bedrooms=bedrooms,
                    estate_name=estate,
                    source_url=source_url,
                    image_url=image_url,
                    description="",
                ))
            except Exception:
                continue
        return results

    def _scrape_area(self, base_url: str) -> list[dict]:
        results = []
        page_num = 1
        seen_urls = set()

        while True:
            url = f"{base_url}?page={page_num}"
            try:
                soup = get_soup(url)
            except Exception:
                break

            cards = soup.select("div.item.property_item")
            if not cards:
                break

            page_results = self._parse_cards(cards, seen_urls)
            if not page_results:
                break

            results.extend(page_results)
            page_num += 1
            if page_num > self.MAX_PAGES:
                break

        return results

    def _scrape_keyword(self, keyword: str) -> list[dict]:
        url = f"{self.SEARCH_URL}?keyword={quote(keyword)}"
        try:
            soup = get_soup(url)
        except Exception:
            return []

        cards = soup.select("div.item.property_item")
        if not cards:
            return []

        seen = set()
        results = self._parse_cards(cards, seen)

        page_num = 2
        while results:
            try:
                soup = get_soup(f"{url}&page={page_num}")
            except Exception:
                break
            cards = soup.select("div.item.property_item")
            if not cards:
                break
            page_results = self._parse_cards(cards, seen)
            if not page_results:
                break
            results.extend(page_results)
            page_num += 1
            if page_num > self.MAX_PAGES:
                break

        return results

    def scrape(self, keyword: str = "") -> list[dict]:
        kw = keyword or self.keyword
        if kw:
            return self._scrape_keyword(kw)

        all_results = []
        seen_urls = set()
        for area_url in self.AREA_URLS:
            props = self._scrape_area(area_url)
            for p in props:
                u = p.get("source_url", "")
                if u and u in seen_urls:
                    continue
                if u:
                    seen_urls.add(u)
                all_results.append(p)
        return all_results
