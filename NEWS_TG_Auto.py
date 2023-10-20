import telebot
from dotenv import load_dotenv
from newsapi import NewsApiClient
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
from newspaper import Article
from bs4 import BeautifulSoup
import requests
import datetime as dt
import os

# Load environment variables
load_dotenv()

# Access the TELEGRAM_API_KEY variable
telegram_api_key = os.getenv("TELEGRAM_API_KEY")

# Initialize the bot with the API token
bot = telebot.TeleBot(telegram_api_key)

# Access the NEWS_API_KEY variable
news_api_key = os.getenv("NEWS_API_KEY")

# Initialize NewsAPI
newsapi = NewsApiClient(api_key=news_api_key)

# Initializing a pre-trained summarization model from Hugging Face
# BART model pre-trained on English language, and fine-tuned on CNN Daily Mail.
model_name = "facebook/bart-large-cnn"  
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
summarizer = pipeline("summarization", model=model, tokenizer=tokenizer)

# Error handling function
def handle_error(message, error):
    bot.reply_to(message, f"An error occurred: {error}")

# Command handler for /start
@bot.message_handler(commands=['start'])
def start(message):
    try:
        bot.reply_to(message, "Hello! Welcome to SG_TopNews")
    except Exception as e:
        handle_error(message, e)

# Command handler for /help
@bot.message_handler(commands=['help'])
def help(message):
    try:
        bot.reply_to(message, """
        Sure, the following commands are available:
        /start ---> You will be greeted with the welcome message.
        /help ---> You will be shown various commands available.
        /fetchnews ---> Top 5 news from Singapore will be sent.
        /summarize_Text_url ---> News content of the given URL will be summarized and sent.
                                 "Command format: /summarize_Text_url URL"
        """)
    except Exception as e:
        handle_error(message, e)

# Command handler for /fetchnews
@bot.message_handler(commands=['fetchnews'])
def fetchnews(message):
    try:
        # Obtaining the top headlines in Singapore
        data = newsapi.get_top_headlines(language='en', country='sg')

        if data['status'] == 'ok':
            if 'articles' in data:
                articles = data['articles']

                # Send the top 5 news articles to Telegram
                for article in articles[:5]:
                    news_title = article['title']
                    news_url = article['url']
                    news_date = dt.datetime.strptime(article['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
                    message_text = f"{news_title}\n{news_url}\nPublished on {news_date}"
                    bot.send_message(message.chat.id, message_text)
            else:
                print("No articles found in the response.")
        else:
            print("Failed to fetch news. Status code:", data['status'])

    except Exception as e:
        handle_error(message, e)

# Response function to text message from the user
"""@bot.message_handler(func=lambda message: True)
def handle_text_message(message):
    try:
        user_message = message.text
        bot.reply_to(message, f"You said: {user_message}")
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {e}")"""

def extract_article_content(url):
    article = Article(url)
    article.download()
    article.parse()

    if article.text:
        return {'title': article.title, 'content': article.text}
    else:
        # If direct extraction fails, try web scraping
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            paragraphs = soup.find_all('p')
            content = '\n'.join([p.get_text() for p in paragraphs])
            return {'title': article.title, 'content': content}

    return None

# Command handler for /summarize_Text_url
@bot.message_handler(commands=['summarize_Text_url'])
def summarize_url(message):
    # Check if a URL is provided
    if len(message.text.split()) < 2:
        bot.reply_to(message, "Please provide a valid URL after the command, e.g., /summarize_Text_url https://example.com/news-article-url")
        return

    # Get the URL from the command
    url = message.text.split()[1]

    # Extract content from the provided URL
    text_article = extract_article_content(url)

    if text_article:
        # Summarize the article
        summary = summarizer(text_article['content'], max_length=150, min_length=30, do_sample=False)

        # Send the summary to Telegram
        if 'summary' in summary[0]:
            summary_message = f"Title: {text_article['title']}\n\nSummary: {summary[0]['summary']}"
            bot.reply_to(message, summary_message)
        else:
            bot.reply_to(message, "Failed to generate a summary for the provided URL.")
        
    else:
        bot.reply_to(message, "Failed to extract article content from the provided URL.")


def main():
    print("@NewsTGPy_Bot is running")
    # Start the bot
    bot.polling()

if __name__ == "__main__":
    main()
