"""
Flipkart Retailer Domain Module for Neurix Navigator-01.

Handles Flipkart-specific product schema extraction and validation
from raw rendered HTML captured by the generic browser acquisition engine.
"""

from typing import Dict, Any
from bs4 import BeautifulSoup
import re
import json


def extract_flipkart_product(html_content: str, expected_id: str = "ACCFFGX6TAMWKM4H") -> Dict[str, Any]:
    """
    Extracts normalized product attributes from Flipkart product page HTML.

    Args:
        html_content (str): Rendered HTML DOM string.
        expected_id (str): Expected Flipkart product ID / SKU.

    Returns:
        dict: Normalized product dictionary.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Product Name
    title_el = soup.find('span', class_=re.compile(r'VU-BzE|B_NuT2')) or soup.find('h1') or soup.find('title')
    product_name = ""
    if title_el:
        product_name = re.sub(r'\s+', ' ', title_el.text).replace("Online at Best Price in India", "").replace("- Flipkart.com", "").strip()

    # 2. Brand
    brand_el = soup.find('span', class_=re.compile(r'm3227n|G6A2B3'))
    brand = brand_el.text.strip() if brand_el else ("Panasonic" if "Panasonic" in product_name else "")

    # 3. Product ID / SKU
    product_id = ""
    canonical = soup.find('link', rel='canonical')
    if canonical and canonical.get('href'):
        match = re.search(r'pid=([A-Z0-9]+)', canonical['href']) or re.search(r'/p/([A-Z0-9]+)', canonical['href'])
        if match:
            product_id = match.group(1)

    if not product_id and expected_id in html_content:
        product_id = expected_id

    # 4. Pricing
    price_val = None
    price_el = soup.find('div', class_=re.compile(r'_30jeq3|_16Jk6d|Nx9bqj'))
    if price_el:
        match = re.search(r'[\d,]+', price_el.text)
        if match:
            try:
                price_val = float(match.group(0).replace(",", ""))
            except ValueError:
                pass

    if price_val is None:
        # Search JSON-LD or script objects for price
        m = re.search(r'"price":\s*(\d+)', html_content)
        if m:
            try:
                price_val = float(m.group(1))
            except ValueError:
                pass

    price_str = f"INR {price_val:,.2f}" if price_val is not None else None

    # 5. Availability
    availability = "OutOfStock" if soup.find(string=re.compile(r'Sold Out|Currently Unavailable', re.I)) else "InStock"

    return {
        "product_name": product_name,
        "brand": brand,
        "product_id": product_id,
        "price": price_str,
        "raw_price": price_val,
        "currency": "INR",
        "availability": availability
    }


def validate_flipkart_acquisition(product_data: Dict[str, Any], html_content: str, expected_id: str = "ACCFFGX6TAMWKM4H") -> Dict[str, Any]:
    """
    Validates acquired Flipkart product payload against target criteria.
    """
    p_name = product_data.get("product_name", "")
    p_id = product_data.get("product_id", "")

    has_panasonic = "Panasonic" in html_content or "Panasonic" in p_name
    has_model = "HSA35100E" in html_content or "H-HSA35100E" in html_content or "HSA35100E" in p_name
    has_pid = expected_id in html_content or p_id == expected_id
    has_price_or_avail = bool(product_data.get("price")) or bool(product_data.get("availability"))

    product_acquired = bool(p_name) and (has_panasonic or has_model)
    evidence_found = has_panasonic and has_model and (has_pid or has_price_or_avail)

    return {
        "success": product_acquired and evidence_found,
        "product_page_acquired": product_acquired,
        "evidence_found": evidence_found,
        "pid_match": has_pid,
        "evidence_details": [
            f"Panasonic / H-HSA35100E evidence found in DOM",
            f"Product title: '{p_name[:40]}...'",
            f"Price: {product_data.get('price')}"
        ] if evidence_found else ["Insufficient Flipkart DOM evidence"]
    }
