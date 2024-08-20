import discord
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import asyncio
import os
from keep_alive import keep_alive

# Define the Discord client with Intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
client = discord.Client(intents=intents)

IMAGE_SIZE = (600, 600)  # Size to resize each image
IMAGES_PER_ROW = 7  # Number of images per row

BASE_URL = "https://dropnite.com"  # Base URL for the site

# Mapping of rarity classes to background image file paths
RARITY_BACKGROUNDS = {
    'rarity-icon_series': 'new/icon.png',
    'rarity-marvel': 'new/marvel.jpg',
    'rarity-epic': 'new/epic.jpg',
    'rarity-rare': 'new/rare.jpg',
    'rarity-uncommon': 'new/uncommon.jpg',
    'rarity-dark': 'new/dark.jpg',
    'rarity-star_wars': 'new/starwar.png',
    'rarity-gaming_legends': 'new/gaminglegend.jpg',
    'rarity-legendary': 'new/legendary.jpg',
    'rarity-common': 'new/common.jpg'
}

VBUCKS_ICON_URL = "https://dropnite.com/img-shop/fortnite-vbucks-icon.png"  # V-Bucks icon URL

# Paths to the font files
FONT_PATH_LARGE = "font/jer/Jersey10-Regular.ttf"  # Path to Jersey font file
FONT_PATH_SMALL = "font/ked/CedarvilleCursive-Regular.ttf"  # Path to Cedarville Cursive font file

def scrape_fortnite_shop():
    url = "https://dropnite.com/shop/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    image_data = []
    for div_tag in soup.find_all('div', class_='card'):
        img_tag = div_tag.find('img', class_='card-img-top img-fluid')
        if img_tag:
            src = img_tag.get('src')
            class_name = next((cls for cls in div_tag.get('class', []) if cls.startswith('rarity-')), None)

            name_tag = div_tag.find('h3', class_='card-title card-name item-name')
            vbuck_tag = div_tag.find('h5', class_='card-text card-namesmall')

            if src:
                if not src.startswith('http'):
                    src = BASE_URL + src

                item_name = name_tag.get_text(strip=True) if name_tag else "Unknown Item"
                vbuck_cost = vbuck_tag.get_text(strip=True) if vbuck_tag else "0 V-Bucks"

                bg_image_path = RARITY_BACKGROUNDS.get(class_name)
                image_data.append((src, bg_image_path, item_name, vbuck_cost))

    return image_data if image_data else "No images found in the shop."

def create_image_collage(image_data, output_file):
    images = []

    try:
        font_large = ImageFont.truetype(FONT_PATH_LARGE, 80)
        font_small = ImageFont.truetype(FONT_PATH_LARGE, 80)
    except IOError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    try:
        vbucks_icon_response = requests.get(VBUCKS_ICON_URL)
        vbucks_icon_response.raise_for_status()
        vbucks_icon = Image.open(BytesIO(vbucks_icon_response.content)).resize((120, 120))
    except Exception as e:
        print(f"Error loading V-Bucks icon: {e}")
        vbucks_icon = None

    for url, bg_image_path, item_name, vbuck_cost in image_data:
        try:
            response = requests.get(url)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).resize(IMAGE_SIZE)

            if bg_image_path and os.path.exists(bg_image_path):
                background = Image.open(bg_image_path).resize(IMAGE_SIZE)
            else:
                background = Image.new('RGBA', IMAGE_SIZE, color=(255, 255, 255))

            background.paste(image, (0, 0), image.convert('RGBA'))

            draw = ImageDraw.Draw(background)

            # Draw item name
            text = item_name
            text_bbox = draw.textbbox((0, 0), text, font=font_large)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_position = ((IMAGE_SIZE[0] - text_width) // 2, IMAGE_SIZE[1] * 3 // 4 - text_height // 2)
            draw.text(text_position, text, fill="white", font=font_large)

            if vbucks_icon:
                icon_x = (IMAGE_SIZE[0] - vbucks_icon.width) // 2 -30  # Move icon leftward by 30 pixels
                icon_y = IMAGE_SIZE[1] - vbucks_icon.height -1# Move icon downward by 30 pixels
                background.paste(vbucks_icon, (icon_x, icon_y), vbucks_icon)
                # Draw V-Bucks cost
                cost_bbox = draw.textbbox((0, 0), vbuck_cost, font=font_small)
                cost_x = icon_x + vbucks_icon.width + 7
                cost_y = icon_y + (vbucks_icon.height - cost_bbox[3] + cost_bbox[1]) // 2
                draw.text((cost_x, cost_y), vbuck_cost, fill="white", font=font_small)
            images.append(background)

        except Exception as e:
            print(f"Error loading image from {url}: {e}")

    if not images:
        return "No valid images to create a collage."

    num_images = len(images)
    rows = (num_images + IMAGES_PER_ROW - 1) // IMAGES_PER_ROW
    width = IMAGE_SIZE[0] * IMAGES_PER_ROW
    height = IMAGE_SIZE[1] * rows

    collage = Image.new('RGB', (width, height), color=(255, 255, 255))

    for index, image in enumerate(images):
        row = index // IMAGES_PER_ROW
        col = index % IMAGES_PER_ROW
        x = col * IMAGE_SIZE[0]
        y = row * IMAGE_SIZE[1]
        collage.paste(image, (x, y))

    collage.save(output_file, format='PNG', optimize=True, quality=85)

async def post_daily_shop():
    await client.wait_until_ready()
    channel = client.get_channel(1209539512842326048)  # Replace with your channel ID

    while not client.is_closed():
        preparing_message = await channel.send("Doc is preparing today's item shop...")

        image_data = scrape_fortnite_shop()
        if isinstance(image_data, str):
            await channel.send(image_data)
        else:
            create_image_collage(image_data, 'xenon.png')
            with open('xenon.png', 'rb') as f:
                await channel.send(file=discord.File(f, 'xenon.png'))

        await preparing_message.delete()
        await asyncio.sleep(86400)  # Wait 24 hours before posting again

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    client.loop.create_task(post_daily_shop())

@client.event
async def on_message(message):
    if message.content == '/show' and not message.author.bot:
        if os.path.exists('collage.png'):
            await message.channel.send(file=discord.File('collage.png'))
        else:
            await message.channel.send("No image available. Please wait for the next update.")

async def main():
    await client.start( os.environ['Discord'])  # Use your bot token here



if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())