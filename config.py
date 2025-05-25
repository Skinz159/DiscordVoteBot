import os

class Config:
    """Configuration settings for the Metin2 Vote Bot"""
    
    # Bot settings
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
    
    # Top-Metin2 API settings
    TOPMETIN2_API_KEY = '5bb0e8ed-0ad2-4764-aa0a-98f52c8f2ab1'
    TOPMETIN2_API_URL = 'https://top-metin2.org/api'
    
    # Vote settings
    VOTE_COOLDOWN = 5400   # 1.5 hours in seconds (90 minutes)
    DAILY_VOTE_LIMIT = 999   # Maximum votes per day per user (pratiquement illimité)
    
    # Auto-deletion and leaderboard settings
    AUTO_DELETE_DELAY = 300  # 5 minutes before auto-deleting vote messages
    LEADERBOARD_INTERVAL = 900  # 15 minutes in seconds for auto leaderboard
    LEADERBOARD_CHANNEL_NAME = "『🎫』votes-leaderboard"  # Channel name for auto leaderboard
    
    # Vote sites configuration
    VOTE_SITES = {
        'topmetin2_org': {
            'name': 'Top-Metin2.org',
            'url': 'https://top-metin2.org/in/445-empire-de-l-ombre/',
            'reward_points': 15,
            'api_enabled': True
        },
        'topmetin2_com': {
            'name': 'Top-Metin2.com',
            'url': 'https://www.top-metin2.com/website/in/567',
            'reward_points': 15,
            'api_enabled': False
        }
    }
    
    # Reward settings
    BASE_REWARD_POINTS = 5
    STREAK_BONUS_MULTIPLIER = 1.1
    WEEKLY_BONUS = 25
    MONTHLY_BONUS = 100
    
    # File paths
    VOTES_DATA_FILE = 'data/votes.json'
    
    # Colors for embeds
    COLORS = {
        'success': 0x00ff00,
        'error': 0xff0000,
        'info': 0x0099ff,
        'warning': 0xffaa00
    }
    
    # Emojis
    EMOJIS = {
        'vote': '🗳️',
        'star': '⭐',
        'trophy': '🏆',
        'fire': '🔥',
        'crown': '👑',
        'coin': '🪙'
    }
