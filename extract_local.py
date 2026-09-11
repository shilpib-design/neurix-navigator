import os
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def parse_price(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    match = re.search(r'[\d,]+(?:\.\d+)?', str(val).replace(',', ''))
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            pass
    return None

def parse_int(val):
    if val is None:
        return None
    if isinstance(val, int):
        return val
    match = re.search(r'\d+', str(val).replace(',', ''))
    if match:
        try:
            return int(match.group(0))
        except ValueError:
            pass
    return None

def extract_schema_from_html(html_content, filename):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    extracted = {
        "product_name": "",
        "brand": "",
        "price": None,
        "currency": "",
        "availability": "",
        "rating": None,
        "review_count": None,
        "product_id": ""
    }

    # --- 1. PREFER JSON-LD FIRST ---
    ld_scripts = soup.find_all('script', type='application/ld+json')
    for script in ld_scripts:
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_type = item.get('@type', '')
                if item_type == 'Product' or (isinstance(item_type, list) and 'Product' in item_type):
                    extracted["product_name"] = extracted["product_name"] or item.get('name', '')
                    
                    # Brand
                    brand = item.get('brand')
                    if isinstance(brand, dict):
                        extracted["brand"] = extracted["brand"] or brand.get('name', '')
                    elif isinstance(brand, str):
                        extracted["brand"] = extracted["brand"] or brand
                        
                    # Product ID / SKU / GTIN / ASIN
                    extracted["product_id"] = extracted["product_id"] or item.get('sku', '') or item.get('productID', '') or item.get('gtin13', '') or item.get('gtin', '')

                    # Offers
                    offers = item.get('offers')
                    if isinstance(offers, list) and len(offers) > 0:
                        offers = offers[0]
                    if isinstance(offers, dict):
                        extracted["price"] = extracted["price"] or parse_price(offers.get('price'))
                        extracted["currency"] = extracted["currency"] or offers.get('priceCurrency', '')
                        extracted["availability"] = extracted["availability"] or offers.get('availability', '')

                    # Aggregate Rating
                    rating_obj = item.get('aggregateRating')
                    if isinstance(rating_obj, dict):
                        extracted["rating"] = extracted["rating"] or parse_price(rating_obj.get('ratingValue'))
                        extracted["review_count"] = extracted["review_count"] or parse_int(rating_obj.get('reviewCount') or rating_obj.get('ratingCount'))
        except Exception:
            pass

    # --- 2. FALLBACK TO OPEN GRAPH / META TAGS ---
    if not extracted["product_name"]:
        og_title = soup.find('meta', property='og:title') or soup.find('meta', attrs={'name': 'title'})
        if og_title and og_title.get('content'):
            extracted["product_name"] = clean_text(og_title['content'])

    if not extracted["price"]:
        meta_price = soup.find('meta', property='product:price:amount') or soup.find('meta', property='og:price:amount')
        if meta_price and meta_price.get('content'):
            extracted["price"] = parse_price(meta_price['content'])

    if not extracted["currency"]:
        meta_curr = soup.find('meta', property='product:price:currency') or soup.find('meta', property='og:price:currency')
        if meta_curr and meta_curr.get('content'):
            extracted["currency"] = meta_curr['content']

    if not extracted["availability"]:
        meta_avail = soup.find('meta', property='product:availability') or soup.find('meta', property='og:availability')
        if meta_avail and meta_avail.get('content'):
            extracted["availability"] = meta_avail['content']

    # --- 3. TARGET-SPECIFIC DOM FALLBACKS ---
    
    # Kroger Fallbacks
    if "kroger" in filename:
        if not extracted["product_name"]:
            name_el = soup.find(attrs={"data-testid": "product-details-name"}) or soup.find('title')
            if name_el:
                extracted["product_name"] = clean_text(name_el.text).replace("- Kroger", "").strip()

        if not extracted["product_id"]:
            upc_el = soup.find(attrs={"data-testid": "product-details-upc"})
            if upc_el:
                match = re.search(r'\d+', upc_el.text)
                if match:
                    extracted["product_id"] = match.group(0)

        if not extracted["price"]:
            price_el = soup.find('span', class_=re.compile(r'citrus-Price--current-price'))
            if price_el:
                extracted["price"] = parse_price(price_el.text)
                if "$" in price_el.text:
                    extracted["currency"] = "USD"

        if not extracted["rating"]:
            rating_el = soup.find('span', attrs={"aria-label": re.compile(r'average rating', re.I)}) or soup.find('div', attrs={"data-testid": "product-star-rating"})
            if rating_el:
                match = re.search(r'[\d\.]+', rating_el.text or rating_el.get('aria-label', ''))
                if match:
                    extracted["rating"] = parse_price(match.group(0))

        if not extracted["review_count"]:
            reviews_el = soup.find('span', attrs={"aria-label": re.compile(r'total reviews', re.I)})
            if reviews_el:
                extracted["review_count"] = parse_int(reviews_el.text or reviews_el.get('aria-label'))

        if not extracted["availability"]:
            avail_el = soup.find(attrs={"data-testid": re.compile(r'purchase-options', re.I)})
            if avail_el and "Available" in avail_el.text:
                extracted["availability"] = "InStock"

    # Flipkart Fallbacks
    elif "flipkart" in filename:
        if not extracted["product_name"]:
            title_el = soup.find('span', class_=re.compile(r'VU-BzE|B_NuT2')) or soup.find('h1') or soup.find('title')
            if title_el:
                extracted["product_name"] = clean_text(title_el.text).replace("Online at Best Price in India", "").strip()

        if not extracted["product_id"]:
            canonical = soup.find('link', rel='canonical')
            if canonical and canonical.get('href'):
                match = re.search(r'/p/([^/?#]+)', canonical['href'])
                if match:
                    extracted["product_id"] = match.group(1)

        if not extracted["price"]:
            price_el = soup.find('div', class_=re.compile(r'_30jeq3|_16Jk6d|Nx9bqj'))
            if price_el:
                extracted["price"] = parse_price(price_el.text)
                if "₹" in price_el.text:
                    extracted["currency"] = "INR"

        if not extracted["rating"]:
            rating_el = soup.find('div', class_=re.compile(r'_3LWZlK|X1v2V5'))
            if rating_el:
                extracted["rating"] = parse_price(rating_el.text)

        if not extracted["review_count"]:
            reviews_el = soup.find('span', class_=re.compile(r'_2_R_ns|WAVB2n'))
            if reviews_el:
                extracted["review_count"] = parse_int(reviews_el.text)

        if not extracted["brand"]:
            brand_el = soup.find('span', class_=re.compile(r'm3227n|G6A2B3'))
            if brand_el:
                extracted["brand"] = clean_text(brand_el.text)

        if not extracted["availability"]:
            if soup.find(string=re.compile(r'Sold Out|Currently Unavailable', re.I)):
                extracted["availability"] = "OutOfStock"
            else:
                extracted["availability"] = "InStock"

    # Amazon India Fallbacks
    elif "amazon" in filename:
        if not extracted["product_name"]:
            title_el = soup.find(id='productTitle') or soup.find('span', id='productTitle')
            if title_el:
                extracted["product_name"] = clean_text(title_el.text)

        if not extracted["product_id"]:
            asin_input = soup.find('input', id='ASIN')
            if asin_input and asin_input.get('value'):
                extracted["product_id"] = asin_input['value']

        if not extracted["price"]:
            price_whole = soup.find('span', class_='a-price-whole')
            price_frac = soup.find('span', class_='a-price-fraction')
            if price_whole:
                whole_str = price_whole.text.replace('.', '').replace(',', '')
                frac_str = price_frac.text if price_frac else "00"
                extracted["price"] = parse_price(f"{whole_str}.{frac_str}")
                extracted["currency"] = "INR"

        if not extracted["rating"]:
            rating_el = soup.find('i', class_=re.compile(r'a-icon-star')) or soup.find('span', id='acrPopover')
            if rating_el:
                extracted["rating"] = parse_price(rating_el.text)

        if not extracted["review_count"]:
            rev_el = soup.find('span', id='acrCustomerReviewText')
            if rev_el:
                extracted["review_count"] = parse_int(rev_el.text)

        if not extracted["brand"]:
            brand_el = soup.find('a', id='bylineInfo') or soup.find('tr', class_=re.compile(r'po-brand'))
            if brand_el:
                extracted["brand"] = clean_text(brand_el.text).replace("Brand:", "").replace("Visit the", "").strip()

        if not extracted["availability"]:
            avail_div = soup.find('div', id='availability')
            if avail_div:
                extracted["availability"] = "InStock" if "In Stock" in avail_div.text or "in stock" in avail_div.text.lower() else "OutOfStock"
            else:
                extracted["availability"] = "InStock"

    return extracted

def main():
    results_dir = Path("results")
    output_dir = results_dir / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    files_to_process = [
        "string_flipkart_20260910_084120.html",
        "string_amazon_india_20260910_084120.html",
        "string_kroger_20260910_084120.html"
    ]

    extracted_results = {}

    for fname in files_to_process:
        fpath = results_dir / fname
        if not fpath.exists():
            print(f"File {fname} not found!")
            continue

        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()

        data = extract_schema_from_html(html_content, fname)

        # Output individual file JSON
        out_name = fname.replace(".html", ".json")
        out_path = output_dir / out_name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        target_key = fname.split("_")[1]
        extracted_results[target_key] = {
            "source_file": fname,
            "extracted_data": data,
            "fields_present": [k for k, v in data.items() if v not in (None, "", [])]
        }
        print(f"\nExtracted [{target_key}] from {fname}:")
        print(json.dumps(data, indent=2))

    summary_file = output_dir / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(extracted_results, f, indent=2)

    print(f"\nSaved extracted JSON results to: {output_dir}/")

if __name__ == "__main__":
    main()
