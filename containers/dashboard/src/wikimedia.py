import httpx
import logging
import asyncio

logger = logging.getLogger("Wikimedia")

class WikimediaService:
    BASE_URL = "https://en.wikipedia.org/w/api.php"
    USER_AGENT = "Silvasonic/1.0 (https://github.com/kyellsen/silvasonic; contact@example.com)"

    @staticmethod
    async def fetch_species_data(scientific_name: str):
        """
        Fetches metadata for a species from Wikimedia API.
        Returns a dict with keys matching SpeciesInfo model or None if failed.
        """
        try:
            async with httpx.AsyncClient(headers={"User-Agent": WikimediaService.USER_AGENT}) as client:
                # 1. Search for the page by scientific name to get the title
                params = {
                    "action": "query",
                    "format": "json",
                    "prop": "pageimages|extracts|langlinks|pageprops",
                    "titles": scientific_name,
                    "pithumbsize": 600,
                    "exintro": True,
                    "explaintext": True,
                    "lllang": "de", # Get German link
                    "redirects": True
                }
                
                response = await client.get(WikimediaService.BASE_URL, params=params, timeout=10.0)
                data = response.json()
                
                pages = data.get("query", {}).get("pages", {})
                if not pages or "-1" in pages:
                    logger.warning(f"No Wikipedia page found for {scientific_name}")
                    return None
                
                # Get the first page result
                page = next(iter(pages.values()))
                
                # Extract Data
                image_url = page.get("thumbnail", {}).get("source")
                description = page.get("extract")
                
                # German Name from Langlinks
                german_name = None
                if "langlinks" in page:
                    for link in page["langlinks"]:
                        if link.get("lang") == "de":
                            german_name = link.get("*")
                            break
                            
                # Construct result
                return {
                    "scientific_name": scientific_name, # PK
                    "german_name": german_name or scientific_name, # Fallback
                    "image_url": image_url,
                    "description": description,
                    "wikipedia_url": f"https://en.wikipedia.org/?curid={page.get('pageid')}",
                    "family": None # Todo: Fetch from Wikidata if needed, or parse text
                }

        except Exception as e:
            logger.error(f"Wikimedia fetch error for {scientific_name}: {e}")
            return None
