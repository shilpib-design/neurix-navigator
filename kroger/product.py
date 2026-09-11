"""
Kroger Product Request & Extraction Module.

Responsible for building product API requests with delivery location context
and extracting structured product attributes from the response payload.
"""

from typing import Dict, Any, Optional
import urllib.parse
from kroger.resolver import resolve_delivery_context, extract_delivery_context

KROGER_PRODUCT_API_URL = "https://www.kroger.com/atlas/v1/product/v2/products"

def build_product_request(
    upc: str, 
    delivery_context: Optional[Dict[str, Any]] = None,
    zip_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Constructs the HTTP request specification for Kroger's /atlas/v1/product/v2/products API.
    
    Args:
        upc: Product UPC/GTIN string (e.g. "0004000042431").
        delivery_context: Extracted delivery context dict from resolver.
        zip_code: Target ZIP code (used if delivery context needs resolution).
        
    Returns:
        Dict containing url, method, params, headers.
    """
    gtin13 = upc.zfill(13) if len(upc) < 13 else upc
    
    params = {
        "filter.gtin13s": gtin13,
        "filter.verified": "true",
        "projections": "items.full,offers.compact,nutrition.label,inventory.projected,variantGroupings.compact"
    }
    
    query_string = urllib.parse.urlencode(params)
    full_url = f"{KROGER_PRODUCT_API_URL}?{query_string}"
    
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "referer": f"https://www.kroger.com/p/product/{gtin13}?fulfillment=DELIVERY",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
        "x-call-origin": '{"page":"pdp","component":"productDetails"}',
        "x-kroger-channel": "WEB",
        "x-modality-type": "DELIVERY"
    }
    
    if delivery_context and "headers" in delivery_context:
        headers.update(delivery_context["headers"])
    elif zip_code:
        headers["x-modality"] = f'{{"type":"DELIVERY","postalCode":"{zip_code}"}}'

    return {
        "url": full_url,
        "base_url": KROGER_PRODUCT_API_URL,
        "method": "GET",
        "params": params,
        "headers": headers
    }

def extract_product_data(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts standardized product schema and location metadata from Kroger product response JSON.
    
    Args:
        response_data: Parsed JSON response from /atlas/v1/product/v2/products.
        
    Returns:
        Dict containing normalized product data.
    """
    products = response_data.get("data", {}).get("products", [])
    if not products:
        return {"error": "No products found in response"}

    product = products[0]
    item = product.get("item", {})
    
    product_name = item.get("description", "")
    brand = item.get("brand", {}).get("name", "")
    upc = item.get("upc") or item.get("gtin14", "")
    
    prices = product.get("postalCodes", [{}])[0].get("prices", [{}])[0] if product.get("postalCodes") else {}
    regular_price = prices.get("regular", {}).get("price")
    sale_price = prices.get("sale", {}).get("price")
    
    fulfillment_summaries = product.get("fulfillmentSummaries", [])
    delivery_summary = next((f for f in fulfillment_summaries if f.get("type") == "DELIVERY"), {})
    availability = delivery_summary.get("availability", {}).get("inventoryLevel") or ("Available" if delivery_summary.get("availability", {}).get("sellable") else "Unavailable")
    
    inventory_summaries = product.get("inventorySummaries", [])
    delivery_inventory = next((inv for inv in inventory_summaries if inv.get("modalityType") == "DELIVERY"), {})
    stock_count = delivery_inventory.get("availableToSell")
    
    laf_list = product.get("laf", [])
    sources = laf_list[0].get("sources", []) if laf_list else []
    location_ids = [s.get("storeId") for s in sources if "storeId" in s]
    
    return {
        "product_name": product_name,
        "brand": brand,
        "upc": upc,
        "price": sale_price or regular_price,
        "regular_price": regular_price,
        "sale_price": sale_price,
        "currency": "USD",
        "availability": availability,
        "inventory_count": stock_count,
        "fulfillment_modality": "DELIVERY",
        "location_ids": location_ids,
        "raw_item": item
    }

def get_product(
    zip_code: str, 
    upc: str, 
    modality_response: Optional[Dict[str, Any]] = None,
    product_response: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Prepares the Kroger product request for a given ZIP code and UPC using
    delivery context from the resolver.
    
    Separates ZIP resolution from product acquisition.
    
    Args:
        zip_code: Target US postal code.
        upc: Product UPC/GTIN.
        modality_response: Optional response payload from /atlas/v1/modality/options to build full location headers.
        product_response: Optional response payload from product API for extraction.
        
    Returns:
        Dict containing resolution status, product request spec, and extracted data (if provided).
    """
    resolution = resolve_delivery_context(zip_code, modality_response)
    delivery_context = resolution.get("delivery_context")
    
    product_request = build_product_request(upc, delivery_context=delivery_context, zip_code=zip_code)
    
    result = {
        "zip_code": str(zip_code),
        "upc": str(upc),
        "resolution_spec": resolution["request"],
        "delivery_context": delivery_context,
        "product_request": product_request,
        "extracted_product": None
    }
    
    if product_response:
        result["extracted_product"] = extract_product_data(product_response)
        
    return result

