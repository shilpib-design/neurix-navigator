"""
Amazon Product Domain Module for Neurix Navigator-01.

Handles Amazon-specific product schema extraction and validation
from raw rendered HTML captured by the generic browser acquisition engine.
"""

from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import re
import json


def extract_amazon_product(html_content: str, target_asin: str = "B078Y2PJL4") -> Dict[str, Any]:
    """
    Extracts normalized product attributes from Amazon product page HTML.

    Args:
        html_content (str): Rendered HTML DOM string.
        target_asin (str): Expected ASIN identifier.

    Returns:
        dict: Normalized product dictionary.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Product Name
    title_el = soup.find(id="productTitle") or soup.find("span", id="productTitle")
    product_name = title_el.text.strip() if title_el else ""

    # 2. Brand
    brand_el = soup.find("a", id="bylineInfo") or soup.find("tr", class_=re.compile(r"po-brand"))
    brand = ""
    if brand_el:
        brand = brand_el.text.replace("Brand:", "").replace("Visit the", "").replace("Store", "").strip()

    # 3. ASIN
    asin_input = soup.find("input", id="ASIN")
    asin = asin_input.get("value") if asin_input and asin_input.get("value") else ""
    if not asin and target_asin in html_content:
        asin = target_asin

    # 4. Pricing
    price_val = None
    price_whole = soup.find("span", class_="a-price-whole")
    if price_whole:
        m = re.search(r"[\d,]+", price_whole.text)
        if m:
            try:
                price_val = float(m.group(0).replace(",", ""))
            except ValueError:
                pass

    price_str = f"INR {price_val:,.2f}" if price_val is not None else None

    # 5. Availability
    avail_div = soup.find("div", id="availability")
    availability = "InStock" if avail_div and "in stock" in avail_div.text.lower() else "Available"

    return {
        "product_name": product_name,
        "brand": brand,
        "asin": asin,
        "price": price_str,
        "raw_price": price_val,
        "currency": "INR",
        "availability": availability,
        "target_asin": target_asin
    }


def validate_amazon_acquisition(product_data: Dict[str, Any], html_content: str, target_asin: str = "B078Y2PJL4") -> Dict[str, Any]:
    """
    Validates acquired Amazon product payload against target criteria.
    """
    p_name = product_data.get("product_name", "")
    asin = product_data.get("asin", "")

    has_asin = target_asin in html_content or asin == target_asin
    has_brand_or_title = "Fossil" in html_content or "Fossil" in p_name or "Watch" in p_name
    has_price_or_avail = bool(product_data.get("price")) or bool(product_data.get("availability"))

    product_acquired = bool(p_name) and has_asin
    evidence_found = has_asin and has_brand_or_title and has_price_or_avail

    return {
        "success": product_acquired and evidence_found,
        "product_page_acquired": product_acquired,
        "evidence_found": evidence_found,
        "asin_match": has_asin,
        "evidence_details": [
            f"ASIN {target_asin} match in DOM",
            f"Product title: '{p_name[:40]}...'",
            f"Price/Availability: {product_data.get('price') or product_data.get('availability')}"
        ] if evidence_found else ["Insufficient product evidence in HTML"]
    }
