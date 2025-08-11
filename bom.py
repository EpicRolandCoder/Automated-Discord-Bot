import requests
from bs4 import BeautifulSoup

def weather(city: str, stateAcronym: str, capital: bool = False, process: bool = False):
    """
    Returns a 2D list with one entry per day: [ [min, max, summary], ... ]
    If process=True, strings are returned where possible (not raw Tag objects).
    If capital=True, fetches the BOM front page and replaces today's min/max with the 'capital' values if available.
    """
    base_url = f"http://www.bom.gov.au/{stateAcronym.lower()}/forecasts/{city.lower()}.shtml"
    headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0"}
    #mozilla firefox used cos for some reason chrome throws a tantrum
    resp = requests.get(base_url, headers=headers, timeout=10)
    resp.raise_for_status()
    parsed = BeautifulSoup(resp.content, "html.parser")
    forecast_divs = parsed.find_all("div", class_="forecast")

    two_dim = []

    if not process:
        for div in forecast_divs:
            two_dim.append([div.find('em', attrs={'class':'min'}), div.find('em', attrs={'class':'max'}), div.find('p')])
    else:
        for i, div in enumerate(forecast_divs):
            if i == 0:
                min_tag = div.find('em', attrs={'class':'min'})
                max_tag = div.find('em', attrs={'class':'max'})
                summary_tag = div.find('p')
                min_text = min_tag.text if min_tag else None
                # sometimes the first day's max is missing in the local page
                max_text = max_tag.text if max_tag else None
                summary_text = summary_tag.text if summary_tag else None
                two_dim.append([min_text, max_text, summary_text])
            else:
                min_t = div.find('em', attrs={'class':'min'})
                max_t = div.find('em', attrs={'class':'max'})
                p_t = div.find('p')
                two_dim.append([
                    min_t.text if min_t else None,
                    max_t.text if max_t else None,
                    p_t.text if p_t else None
                ])

    if capital:
        front_resp = requests.get("http://www.bom.gov.au", headers=headers, timeout=10)
        front_resp.raise_for_status()
        front_parsed = BeautifulSoup(front_resp.content, "html.parser")
        try:
            anchor = front_parsed.find('a', attrs={'title': f'{city.capitalize()} forecast'})
            if anchor:
                if process:
                    # current temp, and last max span as used previously
                    val_span = anchor.find('span', attrs={'class':'val'})
                    if val_span:
                        two_dim[0][0] = val_span.text
                    max_spans = anchor.find_all('span', attrs={'class':'max'})
                    if max_spans:
                        two_dim[0][1] = max_spans[-1].text
                else:
                    two_dim[0][0] = anchor.find('span', attrs={'class':'val'})
                    max_spans = anchor.find_all('span', attrs={'class':'max'})
                    if max_spans:
                        two_dim[0][1] = max_spans[-1]
        except Exception:
            # keep the scraped values if front page parsing fails
            pass

    return two_dim
