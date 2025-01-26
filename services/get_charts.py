import requests
from bs4 import BeautifulSoup
from aiogram import types
from aiogram.utils.markdown import hlink

async def get_yandex_chart(limit=10):
    """Актуальный парсинг чарта Яндекс.Музыки 2024"""
    try:
        url = "https://music.yandex.ru/chart"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        tracks = []
        
        for track in soup.select('.d-track[data-item-id]'):  # Основной контейнер
            try:
                # Название трека
                title = track.select_one('.d-track__name').text.strip()
                
                # Исполнители
                artists = ', '.join(
                    [a.text.strip() for a in track.select('.d-track__artists a')]
                )
                
                # Ссылка на трек
                track_id = track['data-item-id']
                track_url = f"https://music.yandex.ru/track/{track_id}"
                
                tracks.append({
                    'title': f"{title} - {artists}",
                    'url': track_url
                })
                
                if len(tracks) >= limit:
                    break
                    
            except Exception as track_error:
                print(f"Ошибка обработки трека: {track_error}")
                continue
                
        return tracks[:limit]
        
    except Exception as e:
        print(f"Yandex error: {str(e)}")
        return []

async def show_charts_handler(message: types.Message):
    """Обработчик команды /charts"""
    try:
        args = message.text.split()
        limit = min(int(args[1]), 50) if len(args) > 1 and args[1].isdigit() else 10
        
        tracks = await get_yandex_chart(limit)
        
        if not tracks:
            return await message.answer("😔 Не удалось получить данные. Попробуйте позже.")
            
        response = [f"🎶 Топ-{len(tracks)} из Яндекс.Музыки:\n"]
        response.extend(
            f"{idx}. {hlink(track['title'], track['url'])}" 
            for idx, track in enumerate(tracks, 1)
        )
        
        await message.answer(
            "\n".join(response),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)}")