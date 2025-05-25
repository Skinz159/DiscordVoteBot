import discord
from discord.ext import commands
import asyncio
import logging
import os
from config import Config
from bot.commands import setup_commands

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Metin2VoteBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
    async def on_ready(self):
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f'Synced {len(synced)} command(s)')
        except Exception as e:
            logger.error(f'Failed to sync commands: {e}')
    
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ Command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        else:
            logger.error(f'Command error: {error}')
            await ctx.send("❌ An error occurred while processing your command.")

async def main():
    bot = Metin2VoteBot()
    
    # Setup commands
    await setup_commands(bot)
    
    # Get token from environment
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error('DISCORD_TOKEN environment variable not found!')
        return
    
    try:
        await bot.start(token)
    except discord.LoginFailure:
        logger.error('Invalid Discord token provided!')
    except Exception as e:
        logger.error(f'Error starting bot: {e}')

if __name__ == '__main__':
    asyncio.run(main())
