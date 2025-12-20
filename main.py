import os
import json
import requests
import feedparser
import textwrap
from datetime import datetime
from groq import Groq

# --- CONFIGURATION ---
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
client = Groq(api_key=GROQ_API_KEY)
HISTORY_FILE = "history.json"

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
    1. "score": "Developer Anxiety Index" (0-100). 
       - 0-40: Calm/Boring.
       - 41-70: Annoyed/Typical (Bugs, Hype).
       - 71-100: Panic/Crisis.
    2. "vibe": A snarky comment (Max 180 chars). TONE: Dry, technical.
    3. "color": Hex code (e.g. #FF0000 for panic).

    Return JSON: {{ "score": int, "vibe": "string", "color": "hex" }}
    """

    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"}
    )
    return completion.choices[0].message.content

def update_history_and_get_points(current_score):
    """
    Saves score to history.json and returns SVG polyline points string.
    Graph Box: x=450, y=55, w=120, h=40
    """
    # 1. Load History
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except:
            history = []

    # 2. Append Today
    today = datetime.now().strftime("%Y-%m-%d")
    # Only append if date is different from last entry to avoid duplicates on re-runs
    if not history or history[-1]['date'] != today:
        history.append({"date": today, "score": current_score})
    else:
        # Update today's score if we re-ran it
        history[-1]['score'] = current_score

    # 3. Keep last 7 days
    history = history[-7:]

    # 4. Save History
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

    # 5. Generate Sparkline Points
    # Graph dimensions
    box_x = 450
    box_y = 55
    box_w = 120
    box_h = 40

    if len(history) < 2:
        # Not enough data for a line, return a flat line in the middle
        return f"{box_x},{box_y + box_h/2} {box_x + box_w},{box_y + box_h/2}"

    points = []
    step_x = box_w / (len(history) - 1)

    for i, entry in enumerate(history):
        # Normalize score (0-100) to height (0-40)
        # Higher score = Lower Y value (because SVG Y goes down)
        # We want 100 anxiety to be at the TOP (y=55) and 0 at BOTTOM (y=95)
        normalized_h = (entry['score'] / 100) * box_h

        # Invert Y: Y = (Top Edge + Height) - BarHeight
        point_y = (box_y + box_h) - normalized_h
        point_x = box_x + (i * step_x)

        points.append(f"{point_x},{point_y}")

    return " ".join(points)

def update_svg(data):
    ai_data = json.loads(data)
    score = ai_data.get('score', 50)
    vibe = ai_data.get('vibe', 'AI is sleeping.')
    color = ai_data.get('color', '#333333')

    score = min(max(score, 0), 100)
    width = (score / 100) * 400 # Adjusted width for new layout
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Handle History & Sparkline
    sparkline_points = update_history_and_get_points(score)

    # Handle Text Wrap
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
    new_svg = new_svg.replace('{SPARKLINE_POINTS}', sparkline_points) # <--- Insert Points

    with open('vibe.svg', 'w') as f:
        f.write(new_svg)
    print("SVG updated successfully!")

if __name__ == "__main__":
    all_headlines = []
    all_headlines.extend(get_hackernews_headlines())
    all_headlines.extend(get_reddit_headlines())
    all_headlines.extend(get_devto_headlines())

    full_text = "\n".join(all_headlines) or "No news."
    ai_response = analyze_vibe(full_text)
    update_svg(ai_response)