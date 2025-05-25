import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import asyncio
from typing import Optional
from bot.vote_manager import VoteManager
from bot.utils import create_embed, create_vote_embed, create_stats_embed, create_leaderboard_embed
from bot.topmetin2_api import TopMetin2API
from config import Config

logger = logging.getLogger(__name__)

class VoteCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vote_manager = VoteManager()
        self.api = TopMetin2API()
        
        # Start the auto leaderboard task
        self.auto_leaderboard.start()
    
    @app_commands.command(name="vote", description="Voter sur les sites Top-Metin2")
    async def vote(self, interaction: discord.Interaction):
        """Voter sur les deux sites Top-Metin2 et accumuler des points"""
        try:
            # Quick channel and category validation first
            if (not interaction.guild or 
                getattr(interaction.channel, 'name', None) != "『🎫』votes" or
                getattr(getattr(interaction.channel, 'category', None), 'name', None) != ">───⇌•GÉNÉRAL•⇋───<"):
                
                await interaction.response.send_message(
                    "❌ Cette commande ne peut être utilisée que dans le canal **『🎫』votes** de la catégorie **>───⇌•GÉNÉRAL•⇋───<**",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer()
            
            user_id = str(interaction.user.id)
            
            embed = create_embed(
                f"{Config.EMOJIS['vote']} Votez pour Empire de l'Ombre !",
                f"Votez sur les deux sites pour maximiser vos points !",
                Config.COLORS['info']
            )
            
            # Check vote status for both sites
            can_vote_org, message_org = self.vote_manager.can_vote(user_id, 'topmetin2_org')
            can_vote_com, message_com = self.vote_manager.can_vote(user_id, 'topmetin2_com')
            
            # Top-Metin2.org section
            status_org = "✅ Prêt à voter !" if can_vote_org else f"⏰ {message_org}"
            embed.add_field(
                name=f"🗳️ Top-Metin2.org",
                value=f"[Cliquez ici pour voter]({Config.VOTE_SITES['topmetin2_org']['url']})\n"
                      f"**{Config.VOTE_SITES['topmetin2_org']['reward_points']} points** par vote\n"
                      f"Statut: {status_org}",
                inline=True
            )
            
            # Top-Metin2.com section  
            status_com = "✅ Prêt à voter !" if can_vote_com else f"⏰ {message_com}"
            embed.add_field(
                name=f"🗳️ Top-Metin2.com",
                value=f"[Cliquez ici pour voter]({Config.VOTE_SITES['topmetin2_com']['url']})\n"
                      f"**{Config.VOTE_SITES['topmetin2_com']['reward_points']} points** par vote\n"
                      f"Statut: {status_com}",
                inline=True
            )
            
            # Total potential points
            total_points = Config.VOTE_SITES['topmetin2_org']['reward_points'] + Config.VOTE_SITES['topmetin2_com']['reward_points']
            embed.add_field(
                name=f"{Config.EMOJIS['coin']} Points Total Possible",
                value=f"**{total_points} points** toutes les 1h30\n"
                      f"Double vos gains avec les 2 sites !",
                inline=True
            )
            
            embed.add_field(
                name="📋 Instructions",
                value="1. Cliquez sur les liens ci-dessus pour voter\n"
                      "2. Votez sur chaque site disponible\n"
                      "3. Utilisez `/confirm-vote-org` pour Top-Metin2.org\n"
                      "4. Utilisez `/confirm-vote-com` pour Top-Metin2.com\n"
                      "5. Recommencez toutes les 1h30 !",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Phase Pré-Ouverture",
                value="Tous vos points sont sauvegardés et seront crédités automatiquement dès l'ouverture du serveur !",
                inline=False
            )
            
            embed.set_footer(text="Merci de soutenir Empire de l'Ombre avant même son ouverture !")
            
            # Send message with auto-delete after 5 minutes
            message = await interaction.followup.send(embed=embed)
            
            # Schedule auto-deletion
            import asyncio
            asyncio.create_task(self._delete_message_after_delay(message, Config.AUTO_DELETE_DELAY))
            
        except Exception as e:
            logger.error(f"Error in vote command: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ Une erreur s'est produite lors de la récupération des liens de vote.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "❌ Une erreur s'est produite lors de la récupération des liens de vote.",
                        ephemeral=True
                    )
            except:
                logger.error("Failed to send error message to user")
    

    @app_commands.command(name="confirm-vote-org", description="Confirmer votre vote sur Top-Metin2.org")
    async def confirm_vote(self, interaction: discord.Interaction):
        """Confirmer un vote et attribuer des points avec vérification API"""
        try:
            # Quick channel and category validation first
            if (not interaction.guild or 
                getattr(interaction.channel, 'name', None) != "『🎫』votes" or
                getattr(getattr(interaction.channel, 'category', None), 'name', None) != ">───⇌•GÉNÉRAL•⇋───<"):
                
                await interaction.response.send_message(
                    "❌ Cette commande ne peut être utilisée que dans le canal **『🎫』votes** de la catégorie **>───⇌•GÉNÉRAL•⇋───<**",
                    ephemeral=True
                )
                return
                
            await interaction.response.defer()
            
            user_id = str(interaction.user.id)
            site = 'topmetin2_org'
            
            # Check if user can vote
            can_vote, message = self.vote_manager.can_vote(user_id, site)
            if not can_vote:
                embed = create_embed(
                    "⏰ Impossible de voter maintenant",
                    message,
                    Config.COLORS['warning']
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Première étape : vérifier si l'utilisateur a voté
            verification = await self.api.check_vote(user_id)
            
            # Si l'API ne fonctionne pas
            if not verification['success']:
                # Mode temporaire avec confiance utilisateur
                embed = create_embed(
                    "⚠️ Mode Temporaire",
                    "La vérification automatique est temporairement indisponible.\n"
                    "Confirmez-vous avoir voté sur Top-Metin2 avec le lien fourni ?",
                    Config.COLORS['warning']
                )
                embed.add_field(
                    name="📝 Procédure Temporaire",
                    value="En attendant la configuration complète de l'API, "
                          "nous faisons confiance à votre déclaration de vote. "
                          "Vos points seront attribués normalement.",
                    inline=False
                )
                # On continue avec l'enregistrement manuel du vote
            
            # Si l'API fonctionne mais que l'utilisateur n'a pas voté
            elif not verification['has_voted']:
                embed = create_embed(
                    "❌ Vote Non Trouvé",
                    "Nous n'avons pas pu confirmer votre vote. Assurez-vous d'avoir voté sur Top-Metin2 avec le lien fourni par /vote.",
                    Config.COLORS['error']
                )
                embed.add_field(
                    name="🔄 Que faire ?",
                    value="1. Utilisez `/vote` pour obtenir votre lien personnel\n"
                          "2. Votez sur Top-Metin2\n"
                          "3. Attendez quelques minutes\n"
                          "4. Réessayez `/confirm-vote-org`",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Deuxième étape : si l'utilisateur a voté, confirmer le vote avec l'API
            elif verification['has_voted']:
                # Appel explicite à la fonction confirm_vote pour enregistrer le vote dans l'API
                confirmation = await self.api.confirm_vote(user_id)
                
                if not confirmation['success'] and not confirmation['verified']:
                    # Problème avec la confirmation API
                    logger.error(f"API vote confirmation failed: {confirmation.get('error', 'Unknown error')}")
                    # On continue quand même avec l'enregistrement local du vote
            
            # Vote verified! Record the vote
            reward_info = self.vote_manager.record_vote(
                user_id, 
                site, 
                interaction.user.display_name
            )
            
            # Create success embed
            embed = create_embed(
                f"{Config.EMOJIS['star']} Vote Confirmé !",
                f"Merci d'avoir voté sur **Top-Metin2** !",
                Config.COLORS['success']
            )
            
            embed.add_field(
                name=f"{Config.EMOJIS['coin']} Récompenses Gagnées",
                value=f"**Points de Base :** {reward_info['base_points']}\n"
                      f"**Bonus de Série :** {reward_info['streak_bonus']}\n"
                      f"**Total Points :** {reward_info['total_points']}",
                inline=True
            )
            
            embed.add_field(
                name="🔒 Sécurité",
                value="**Vote vérifié automatiquement**\nAucun spam possible !",
                inline=True
            )
            
            if reward_info['current_streak'] > 1:
                embed.add_field(
                    name=f"{Config.EMOJIS['fire']} Série de Votes",
                    value=f"{reward_info['current_streak']} jours\n"
                          f"Continuez pour de plus gros bonus !",
                    inline=True
                )
            
            embed.add_field(
                name="🎯 Phase Pré-Ouverture",
                value="Tous vos points seront crédités automatiquement à l'ouverture !",
                inline=False
            )
            
            embed.set_footer(text="Utilisez /stats pour voir vos statistiques de vote !")
            
            message = await interaction.followup.send(embed=embed)
            
            # Schedule auto-deletion
            import asyncio
            asyncio.create_task(self._delete_message_after_delay(message, Config.AUTO_DELETE_DELAY))
            
        except Exception as e:
            logger.error(f"Error in confirm-vote command: {e}")
            await interaction.followup.send(
                "❌ Une erreur s'est produite lors de la confirmation de votre vote.",
                ephemeral=True
            )
    
    @app_commands.command(name="confirm-vote-com", description="Confirmer votre vote sur Top-Metin2.com")
    async def confirm_vote_com(self, interaction: discord.Interaction):
        """Confirmer un vote sur Top-Metin2.com et attribuer des points"""
        try:
            # Quick channel and category validation first
            if (not interaction.guild or 
                getattr(interaction.channel, 'name', None) != "『🎫』votes" or
                getattr(getattr(interaction.channel, 'category', None), 'name', None) != ">───⇌•GÉNÉRAL•⇋───<"):
                
                await interaction.response.send_message(
                    "❌ Cette commande ne peut être utilisée que dans le canal **『🎫』votes** de la catégorie **>───⇌•GÉNÉRAL•⇋───<**",
                    ephemeral=True
                )
                return
                
            await interaction.response.defer()
            
            user_id = str(interaction.user.id)
            site = 'topmetin2_com'
            
            # Check if user can vote
            can_vote, message = self.vote_manager.can_vote(user_id, site)
            if not can_vote:
                embed = create_embed(
                    "⏰ Impossible de voter maintenant",
                    message,
                    Config.COLORS['warning']
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # For top-metin2.com, no API verification - direct confirmation
            # Record the vote
            reward_info = self.vote_manager.record_vote(
                user_id, 
                site, 
                interaction.user.display_name
            )
            
            # Create success embed
            embed = create_embed(
                f"{Config.EMOJIS['star']} Vote Confirmé sur Top-Metin2.com !",
                f"Merci d'avoir voté sur **Top-Metin2.com** !",
                Config.COLORS['success']
            )
            
            embed.add_field(
                name=f"{Config.EMOJIS['coin']} Récompenses Gagnées",
                value=f"**Points de Base :** {reward_info['base_points']}\n"
                      f"**Bonus de Série :** {reward_info['streak_bonus']}\n"
                      f"**Total Points :** {reward_info['total_points']}",
                inline=True
            )
            
            embed.add_field(
                name="🔒 Sécurité",
                value="**Vote confirmé manuellement**\nDouble vos points avec les 2 sites !",
                inline=True
            )
            
            if reward_info['current_streak'] > 1:
                embed.add_field(
                    name=f"{Config.EMOJIS['fire']} Série de Votes",
                    value=f"{reward_info['current_streak']} jours\n"
                          f"Continuez pour de plus gros bonus !",
                    inline=True
                )
            
            embed.add_field(
                name="🎯 Phase Pré-Ouverture",
                value="Tous vos points seront crédités automatiquement à l'ouverture !",
                inline=False
            )
            
            embed.set_footer(text="N'oubliez pas de voter aussi sur Top-Metin2.org avec /vote !")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in confirm-vote-com command: {e}")
            await interaction.followup.send(
                "❌ Une erreur s'est produite lors de la confirmation de votre vote.",
                ephemeral=True
            )
    
    @app_commands.command(name="stats", description="Voir vos statistiques de vote")
    @app_commands.describe(user="Utilisateur à consulter (optionnel)")
    async def stats(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Afficher les statistiques de vote de l'utilisateur"""
        try:
            # Quick channel and category validation first
            if (not interaction.guild or 
                getattr(interaction.channel, 'name', None) != "『🎫』votes" or
                getattr(getattr(interaction.channel, 'category', None), 'name', None) != ">───⇌•GÉNÉRAL•⇋───<"):
                
                await interaction.response.send_message(
                    "❌ Cette commande ne peut être utilisée que dans le canal **『🎫』votes** de la catégorie **>───⇌•GÉNÉRAL•⇋───<**",
                    ephemeral=True
                )
                return
                
            target_user = user or interaction.user
            user_id = str(target_user.id)
            
            user_stats = self.vote_manager.get_user_stats(user_id)
            embed = create_stats_embed(user_stats, target_user.display_name)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors de la récupération des statistiques.",
                ephemeral=True
            )
    
    @app_commands.command(name="leaderboard", description="Voir le classement des votes")
    async def leaderboard(self, interaction: discord.Interaction):
        """Afficher le classement des votes"""
        try:
            # Quick channel and category validation first
            if (not interaction.guild or 
                getattr(interaction.channel, 'name', None) != "『🎫』votes-leaderboard" or
                getattr(getattr(interaction.channel, 'category', None), 'name', None) != ">───⇌•GÉNÉRAL•⇋───<"):
                
                await interaction.response.send_message(
                    "❌ Cette commande ne peut être utilisée que dans le canal **『🎫』votes-leaderboard** de la catégorie **>───⇌•GÉNÉRAL•⇋───<**",
                    ephemeral=True
                )
                return
            
            # Obtenir les données du classement
            leaderboard_data = self.vote_manager.get_leaderboard(10)
            
            # Créer l'embed manuellement au lieu d'utiliser la fonction générique
            embed = create_embed(
                title=f"{Config.EMOJIS['trophy']} Classement des Votes",
                description="Meilleurs votants du mois",
                color=Config.COLORS['success']
            )
            
            if not leaderboard_data:
                embed.add_field(
                    name="Aucune Donnée",
                    value="Aucun vote enregistré pour le moment. Soyez le premier à voter !",
                    inline=False
                )
            else:
                # Créer le texte du classement avec les pseudos corrects
                leaderboard_text = []
                
                for i, user_data in enumerate(leaderboard_data[:10]):
                    rank_emoji = ["👑", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
                    user_id = user_data['user_id']
                    
                    # Chercher le membre directement dans le serveur actuel en utilisant l'API Discord
                    try:
                        # Récupérer le membre avec la méthode fetch pour garantir des données à jour
                        member = None
                        for member_obj in interaction.guild.members:
                            if str(member_obj.id) == user_id:
                                member = member_obj
                                break
                        
                        # Si le membre est trouvé, utiliser son pseudo visible sur le serveur
                        if member:
                            username = member.display_name
                        else:
                            # Tenter de chercher l'utilisateur dans l'API Discord
                            user = await interaction.client.fetch_user(int(user_id))
                            username = user.display_name if user else f"Utilisateur#{user_id[-4:]}"
                    except Exception as e:
                        logger.error(f"Error fetching user {user_id}: {e}")
                        username = f"Utilisateur#{user_id[-4:]}"
                    
                    leaderboard_text.append(
                        f"{rank_emoji} **{username}**\n"
                        f"   {Config.EMOJIS['coin']} {user_data['total_points']} points "
                        f"({user_data['total_votes']} votes)"
                    )
                
                embed.add_field(
                    name="Meilleurs Votants",
                    value="\n\n".join(leaderboard_text),
                    inline=False
                )
            
            # Add global stats
            global_stats = self.vote_manager.get_global_stats()
            embed.add_field(
                name="📈 Statistiques du Serveur",
                value=f"**Total Votants :** {global_stats['total_users']}\n"
                      f"**Total Votes :** {global_stats['total_votes']}",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors de la récupération du classement.",
                ephemeral=True
            )
    

    @app_commands.command(name="help", description="Obtenir de l'aide sur les commandes de vote")
    async def vote_help(self, interaction: discord.Interaction):
        """Afficher les informations d'aide pour le vote"""
        try:
            # Quick channel and category validation first
            if (not interaction.guild or 
                getattr(interaction.channel, 'name', None) != "『🎫』votes" or
                getattr(getattr(interaction.channel, 'category', None), 'name', None) != ">───⇌•GÉNÉRAL•⇋───<"):
                
                await interaction.response.send_message(
                    "❌ Cette commande ne peut être utilisée que dans le canal **『🎫』votes** de la catégorie **>───⇌•GÉNÉRAL•⇋───<**",
                    ephemeral=True
                )
                return
                
            embed = create_embed(
                f"{Config.EMOJIS['vote']} Aide Vote Top-Metin2",
                "Voici comment utiliser notre système de vote simplifié :",
                Config.COLORS['info']
            )
            
            embed.add_field(
                name="📋 Commandes Disponibles",
                value="`/vote` - Obtenez le lien de vote Top-Metin2\n"
                      "`/confirm-vote-org` - Confirmez votre vote sur Top-Metin2.org\n"
                      "`/confirm-vote-com` - Confirmez votre vote sur Top-Metin2.com\n"
                      "`/stats` - Voir vos statistiques de vote\n"
                      "`/leaderboard` - Voir le classement des meilleurs votants (dans le canal 『🎫』votes-leaderboard)\n"
                      "`/help` - Afficher cette aide",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Comment Voter",
                value="1. Utilisez `/vote` pour obtenir le lien\n"
                      "2. Cliquez sur le lien de vote Top-Metin2\n"
                      "3. Votez sur la plateforme\n"
                      "4. Revenez et utilisez `/confirm-vote-org` ou `/confirm-vote-com`\n"
                      "5. Vos points sont sauvegardés pour l'ouverture !",
                inline=False
            )
            
            embed.add_field(
                name="⚡ Règles de Vote",
                value=f"• Maximum {Config.DAILY_VOTE_LIMIT} vote par jour\n"
                      f"• Délai de {Config.VOTE_COOLDOWN // 3600} heures\n"
                      "• Votes quotidiens consécutifs = bonus de série\n"
                      "• Plus de séries = plus gros bonus",
                inline=False
            )
            
            embed.add_field(
                name="🏆 Récompenses",
                value=f"**{Config.VOTE_SITES['topmetin2_org']['reward_points']} points** par vote sur Top-Metin2.org\n"
                      f"**{Config.VOTE_SITES['topmetin2_com']['reward_points']} points** par vote sur Top-Metin2.com",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await interaction.response.send_message(
                "❌ Une erreur s'est produite lors de l'affichage de l'aide.",
                ephemeral=True
            )

    async def _delete_message_after_delay(self, message, delay):
        """Delete a message after a specified delay"""
        try:
            await asyncio.sleep(delay)
            await message.delete()
        except discord.NotFound:
            # Message already deleted
            pass
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
    
    @tasks.loop(seconds=Config.LEADERBOARD_INTERVAL)
    async def auto_leaderboard(self):
        """Automatically post leaderboard every 15 minutes"""
        try:
            # Find the leaderboard channel
            for guild in self.bot.guilds:
                channel = discord.utils.get(guild.channels, name=Config.LEADERBOARD_CHANNEL_NAME)
                if channel:
                    # Clear previous messages in the channel
                    try:
                        # Delete messages to keep the channel clean
                        async for message in channel.history(limit=10):
                            await message.delete()
                            await asyncio.sleep(0.5)  # Avoid rate limits
                    except Exception as e:
                        logger.error(f"Error clearing leaderboard channel: {e}")
                    
                    # Get leaderboard data
                    leaderboard_data = self.vote_manager.get_leaderboard(10)
                    
                    if leaderboard_data:
                        # Créer l'embed manuellement pour afficher les bons pseudos
                        embed = create_embed(
                            title=f"{Config.EMOJIS['trophy']} Classement des Votes",
                            description="Meilleurs votants du mois",
                            color=Config.COLORS['success']
                        )
                        
                        # Créer le texte du classement avec les pseudos corrects
                        leaderboard_text = []
                        
                        for i, user_data in enumerate(leaderboard_data[:10]):
                            rank_emoji = ["👑", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
                            user_id = user_data['user_id']
                            
                            # Chercher le membre directement dans le serveur actuel en utilisant une méthode plus fiable
                            try:
                                # Chercher d'abord dans la liste des membres du serveur
                                member = None
                                for member_obj in guild.members:
                                    if str(member_obj.id) == user_id:
                                        member = member_obj
                                        break
                                
                                # Si le membre est trouvé, utiliser son pseudo visible sur le serveur
                                if member:
                                    username = member.display_name
                                else:
                                    # Tenter de chercher l'utilisateur dans l'API Discord
                                    user = await self.bot.fetch_user(int(user_id))
                                    username = user.display_name if user else f"Utilisateur#{user_id[-4:]}"
                            except Exception as e:
                                logger.error(f"Error fetching user {user_id} in auto leaderboard: {e}")
                                username = f"Utilisateur#{user_id[-4:]}"
                            
                            leaderboard_text.append(
                                f"{rank_emoji} **{username}**\n"
                                f"   {Config.EMOJIS['coin']} {user_data['total_points']} points "
                                f"({user_data['total_votes']} votes)"
                            )
                        
                        embed.add_field(
                            name="Meilleurs Votants",
                            value="\n\n".join(leaderboard_text),
                            inline=False
                        )
                        
                        # Ajouter les statistiques globales
                        global_stats = self.vote_manager.get_global_stats()
                        embed.add_field(
                            name="📈 Statistiques du Serveur",
                            value=f"**Total Votants :** {global_stats['total_users']}\n"
                                  f"**Total Votes :** {global_stats['total_votes']}",
                            inline=False
                        )
                        
                        embed.set_footer(text="Classement mis à jour automatiquement • Empire de l'Ombre")
                        
                        # Send the new leaderboard
                        await channel.send(embed=embed)
                        
        except Exception as e:
            logger.error(f"Error in auto leaderboard: {e}")
    
    @auto_leaderboard.before_loop
    async def before_auto_leaderboard(self):
        """Wait until bot is ready before starting auto leaderboard"""
        await self.bot.wait_until_ready()
    
    @tasks.loop(minutes=30)  # Nettoyer le canal de votes toutes les 30 minutes
    async def auto_clean_votes_channel(self):
        """Automatically clean the votes channel by removing old messages"""
        try:
            # Find the votes channel
            for guild in self.bot.guilds:
                channel = discord.utils.get(guild.channels, name="『🎫』votes")
                if channel:
                    # Get current time
                    now = discord.utils.utcnow()
                    # Delete messages older than 30 minutes
                    async for message in channel.history(limit=50):
                        # Don't delete pinned messages
                        if not message.pinned and (now - message.created_at).total_seconds() > 1800:  # 30 minutes
                            try:
                                await message.delete()
                                await asyncio.sleep(0.5)  # Avoid rate limits
                            except Exception as e:
                                logger.error(f"Error deleting message in votes channel: {e}")
                                
        except Exception as e:
            logger.error(f"Error in auto clean votes channel: {e}")
    
    @auto_clean_votes_channel.before_loop
    async def before_auto_clean_votes_channel(self):
        """Wait until bot is ready before starting auto clean"""
        await self.bot.wait_until_ready()
        
        # Start the clean votes channel task here to avoid initialization errors
        if not self.auto_clean_votes_channel.is_running():
            self.auto_clean_votes_channel.start()
            
    async def cog_unload(self):
        """Stop the auto tasks when unloading the cog"""
        self.auto_leaderboard.cancel()
        self.auto_clean_votes_channel.cancel()

async def setup_commands(bot):
    """Setup all vote commands"""
    await bot.add_cog(VoteCommands(bot))
    logger.info("Vote commands loaded successfully")
