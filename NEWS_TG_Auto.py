import telebot
from dotenv import load_dotenv
from newsapi import NewsApiClient
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
from newspaper import Article
from bs4 import BeautifulSoup
import requests
import datetime as dt
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Access API Keys
telegram_api_key = os.getenv("TELEGRAM_API_KEY")
news_api_key = os.getenv("NEWS_API_KEY")

# Initialize the bot with the API token
bot = telebot.TeleBot(telegram_api_key)

# Initialize NewsAPI
newsapi = NewsApiClient(api_key=news_api_key)

# Initializing a pre-trained summarization model "BART" from Hugging Face
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
                    published_at = dt.datetime.strptime(article['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
                    message_text = f"{news_title}\n{news_url}\nPublished on {published_at}"
                    bot.send_message(message.chat.id, message_text)
            else:
                print("No articles found in the response.")
        else:
            print("Failed to fetch news. Status code:", data['status'])

    except Exception as e:
        handle_error(message, e)

#Funtion to extract articles from given URL
def extract_article_content(url):
    article = Article(url)
    article.download()
    article.parse()

    if article.text:
        logging.info("article content obtained via newspaper library")
        return {'title': article.title, 'content': article.text}

    else:
        # If direct extraction fails, try web scraping
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            paragraphs = soup.find_all('p')
            content = '\n'.join([p.get_text() for p in paragraphs])
            print("article content obtained via beautiful soup library")
            return {'title': article.title, 'content': content}
        else:
            logging.warning("article content not obtained via beautiful soup library after scraping")

    return None

# Command handler for /summarize_Text_url
@bot.message_handler(commands=['summarize_Text_url'])
def summarize_url(message):
    try:
        # Check if a URL is provided
        command_parts = message.text.split()
        if len(command_parts) < 2:
            bot.reply_to(message, "Please provide a valid URL after the command, e.g., /summarize_Text_url https://example.com/news-article-url")
            return

        # Get the URL from the command
        url = command_parts[1]

        # Extract content from the provided URL
        text_article = extract_article_content(url)

        if text_article:
            # Split the text into smaller chunks (e.g., 1024 tokens each)
            max_seq_length = 1024
            text_chunks = [text_article['content'][i:i + max_seq_length] for i in range(0, len(text_article['content']), max_seq_length)]

            # Summarize each chunk and accumulate the summaries
            summaries = []
            for chunk in text_chunks:
                summary = summarizer(chunk, max_length=150, min_length=30, do_sample=False)  # Summary is a list of dictionaries
                if summary:
                    summaries.append(summary[0]['summary_text'])
                else:
                    bot.reply_to(message, "Failed to generate a summary for the provided URL")

            # Send the final summary to Telegram
            summary_message = f"Title: {text_article['title']}\n\nSummary: {summaries}"
            bot.reply_to(message, summary_message)
        else:
            bot.reply_to(message, "Failed to extract article content from the provided URL")
    except Exception as e:
        handle_error(message, e)

# Echo function to echo all remaining messages from the user
@bot.message_handler(func=lambda m: True)
def echo_all(message):
    reply = f'You said {message.text}'
    bot.reply_to(message, reply)

def main():
    print("@NewsTGPy_Bot is running")
    # Start the bot
    bot.infinity_polling()

if __name__ == "__main__":
    main()
