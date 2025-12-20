import os
import requests
import feedparser
import textwrap
from datetime import datetime
from groq import Groq

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
client = Groq(api_key=GROQ_API_KEY)

def get_hackernews_headlines():
    print("Fetching Hacker News...")
    headlines = []
    try:
        top_ids = requests.get('https://hacker-news.firebaseio.com/v0/topstories.json').json()[:5]
        for item_id in top_ids:
            item_url = f'https://hacker-news.firebaseio.com/v0/item/{item_id}.json'
            data = requests.get(item_url).json()
            if 'title' in data:
                headlines.append(f"HN: {data['title']}")
    except Exception as e:
        print(f"Error fetching HN: {e}")
    return headlines

def get_reddit_headlines():
    print("Fetching Reddit...")
    headlines = []
    urls = [
        "https://www.reddit.com/r/programming/top/.rss?t=day",
        "https://www.reddit.com/r/ArtificialInteligence/top/.rss?t=day"
    ]
    try:
        for url in urls:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                headlines.append(f"Reddit: {entry.title}")
    except Exception as e:
        print(f"Error fetching Reddit: {e}")
    return headlines

def get_devto_headlines():
    print("Fetching Dev.to...")
    headlines = []
    try:
        data = requests.get('https://dev.to/api/articles?top=1').json()
        for article in data[:5]:
            headlines.append(f"Dev.to: {article['title']}")
    except Exception as e:
        print(f"Error fetching Dev.to: {e}")
    return headlines

def analyze_vibe(text_data):
    print("Asking the AI...")

    prompt = f"""
    Here are the top trending tech headlines:
    {text_data}

    Perform a "Vibe Check" as a cynical Senior Software Engineer.
    
    1. "score": Calculate the "Developer Anxiety Index" (0-100). BE STRICT.
       - 0-30: Slow news day, everything is calm.
       - 31-60: Standard annoyance. AI hype, new JS frameworks, normal bugs. (Most days are here).
       - 61-80: Major security vulnerability (e.g. Log4j), big layoffs, or a popular service is down.
       - 81-100: AWS is down globally, the internet is breaking, total panic.
    
    2. "vibe": Write a snarky, relatable comment (Max 180 chars).
       - TONE: Dry humor, tired, technical.
       - FORBIDDEN: Do not use "humanity", "existential", "soul".
    
    3. "color": Hex code (e.g., #FF0000 for panic, #FFA500 for annoyance, #00FF00 for calm).

    Return JSON: {{ "score": int, "vibe": "string", "color": "hex" }}
    """

    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b", 
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"}
    )

    return completion.choices[0].message.content

def update_svg(data):
    import json

    ai_data = json.loads(data)
    score = ai_data.get('score', 50)
    vibe = ai_data.get('vibe', 'AI is sleeping.')
    color = ai_data.get('color', '#333333')

    
    score = min(max(score, 0), 100)

    width = (score / 100) * 540
    date_str = datetime.now().strftime("%Y-%m-%d")

    
    
    wrapped_lines = textwrap.wrap(f'"{vibe}"', width=55)

    
    svg_lines = ""
    for i, line in enumerate(wrapped_lines):
        
        line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        
        
        
        dy = "0" if i == 0 else "1.4em"
        svg_lines += f'<tspan x="50" dy="{dy}">{line}</tspan>'

    with open('template.svg', 'r') as f:
        svg_content = f.read()

    new_svg = svg_content.replace('{SCORE}', str(score))
    new_svg = new_svg.replace('{VIBE_LINES}', svg_lines) 
    new_svg = new_svg.replace('{COLOR}', color)
    new_svg = new_svg.replace('{WIDTH}', str(width))
    new_svg = new_svg.replace('{DATE}', date_str)

    with open('vibe.svg', 'w') as f:
        f.write(new_svg)
    print("SVG updated successfully!")

if __name__ == "__main__":
    all_headlines = []
    all_headlines.extend(get_hackernews_headlines())
    all_headlines.extend(get_reddit_headlines())
    all_headlines.extend(get_devto_headlines())

    full_text = "\n".join(all_headlines)

    if not full_text:
        full_text = "No news today."

    ai_response = analyze_vibe(full_text)

    update_svg(ai_response)
