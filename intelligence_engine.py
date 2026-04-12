import wikipediaapi
import re
import requests
import random
import time
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from typing import Optional, Dict

class IntelligenceEngine:
    def __init__(self, user_agent: str = "ReconSphere-OSINT/1.0 (https://reconsphere.io; contact@reconsphere.io)"):
        self.wiki = wikipediaapi.Wikipedia(
            user_agent=user_agent,
            language='en',
            extract_format=wikipediaapi.ExtractFormat.WIKI
        )
        self.ua = UserAgent()

    def fetch_wikipedia_summary(self, name: str) -> Optional[Dict[str, str]]:
        """Priority 1: Wikipedia Intelligence"""
        try:
            page = self.wiki.page(name)
            if page.exists():
                summary = page.summary
                paragraphs = summary.split('\n')
                display_summary = "\n\n".join(paragraphs[:2])
                if len(display_summary) > 600:
                    display_summary = display_summary[:600] + "..."
                
                return {
                    "title": page.title,
                    "summary": display_summary,
                    "fullurl": page.fullurl,
                    "source": "Wikipedia"
                }
        except Exception as e:
            print(f"[INTEL] Wikipedia error for {name}: {e}")
        return None

    def _scrape_google(self, query: str) -> Optional[Dict[str, str]]:
        """Priority 2: Google Intelligence (Mobile/Lite Interface)"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.181 Mobile Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            # gbv=1 (google basic version) often bypasses complex JS checks
            url = f"https://www.google.com/search?q={requests.utils.quote(query)}&gbv=1"
            response = requests.get(url, headers=headers, timeout=8)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")
                # In basic mode, snippets are often in specific div structures
                snippets = []
                # Selector for results
                for div in soup.select("div.BNeawe.s3v9rd.AP7Wnd"):
                    text = div.get_text().strip()
                    if len(text) > 60 and not text.startswith("http"):
                        snippets.append(text)
                
                if snippets:
                    return {
                        "title": query,
                        "summary": snippets[0],
                        "fullurl": url,
                        "source": "Google Intelligence"
                    }
        except Exception as e:
            print(f"[INTEL] Google scrape fallback triggered: {e}")
        return None

    def _scrape_ddg(self, query: str) -> Optional[Dict[str, str]]:
        """Priority 3: DuckDuckGo Lite (High-Reliability Scrape)"""
        try:
            headers = {"User-Agent": self.ua.random}
            url = f"https://lite.duckduckgo.com/lite/?q={requests.utils.quote(query)}"
            response = requests.get(url, headers=headers, timeout=8)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")
                snippets = []
                for td in soup.select("td.result-snippet"):
                    text = td.get_text().strip()
                    if len(text) > 40:
                        snippets.append(text)
                
                if snippets:
                    return {
                        "title": query,
                        "summary": snippets[0],
                        "fullurl": url,
                        "source": "Global Web Intelligence"
                    }
        except Exception as e:
            print(f"[INTEL] DDG scrape error: {e}")
        return None

    def _check_github(self, name: str) -> Optional[str]:
        """Check for developer presence on GitHub"""
        try:
            query = f'"{name}"'
            url = f"https://github.com/search?q={requests.utils.quote(query)}&type=users"
            headers = {"User-Agent": self.ua.random}
            response = requests.get(url, headers=headers, timeout=5)
            # Simple check if "User" results exist in the page
            if response.status_code == 200 and "User results" in response.text:
                return url
        except:
            pass
        return None

    def normalize_name(self, name: str) -> str:
        name = re.sub(r'\.(jpg|jpeg|png|bmp|gif)$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[_\-]+', ' ', name)
        return name.strip().title()

    def get_identity_report(self, candidate_name: str) -> Dict:
        normalized = self.normalize_name(candidate_name)
        
        # 0. Social Footprint Detection
        github_url = self._check_github(normalized)
        
        # 1. Wikipedia (Highest Confidence - Notable Figure)
        wiki = self.fetch_wikipedia_summary(normalized)
        if wiki:
            return {
                "name": wiki["title"],
                "type": "Notable Figure / Celebrity",
                "description": wiki["summary"],
                "source": "Wikipedia Intelligence",
                "url": wiki["fullurl"],
                "github": github_url
            }
        
        # 2. Google (Web Context)
        google = self._scrape_google(normalized)
        if google:
            is_notable = any(word in google["summary"].lower() for word in ["celebrity", "actor", "ceo", "founder", "famous", "renowned"])
            return {
                "name": google["title"],
                "type": "Notable Figure / Celebrity" if is_notable else "Public Profile",
                "description": google["summary"],
                "source": "Google Intelligence",
                "url": google["fullurl"],
                "github": github_url
            }
        
        # 3. DuckDuckGo (Reliability Fallback)
        ddg = self._scrape_ddg(normalized)
        if ddg:
            return {
                "name": ddg["title"],
                "type": "Web Identity Profile",
                "description": ddg["summary"],
                "source": "Global Intelligence Scan",
                "url": ddg["fullurl"],
                "github": github_url
            }
        
        # 4. Neural Local Fallback
        return {
            "name": normalized,
            "type": "Unverified Identity",
            "description": "No intelligence profile discovered in public web clusters.",
            "source": "Local Analysis",
            "url": None,
            "github": github_url
        }

engine = IntelligenceEngine()
