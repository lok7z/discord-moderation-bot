import discord
import json
import asyncio  # Pour utiliser sleep pour le mute
from discord import Intents

with open('config.json', 'r') as config_file:
    config = json.load(config_file)
    token = config['token']

intents = Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True  # Assurez-vous que l'intent des membres est activé

client = discord.Client(intents=intents)

auto_rank_channel_id = None
log_channel_id = None
rank_tag = None
role_id = None

# Variables pour stocker le dernier message supprimé et son horodatage
last_deleted_message = None
last_deleted_time = None

def check(message, author):
    return message.author == author and isinstance(message.channel, discord.TextChannel)

@client.event
async def on_ready():
    print(f'Bot connecté en tant que {client.user}')

@client.event
async def on_message(message):
    global auto_rank_channel_id, log_channel_id, rank_tag, role_id, last_deleted_message, last_deleted_time

    if message.author == client.user:
        return

    # Vérifiez si l'utilisateur a des permissions d'administrateur
    is_admin = message.author.guild_permissions.administrator

    if message.content.startswith('+autorank-setup') and is_admin:
        await message.channel.send("ID du salon où les joueurs peuvent exécuter la commande +rankup :")
        try:
            auto_rank_message = await client.wait_for('message', check=lambda m: check(m, message.author))
            auto_rank_channel_id = int(auto_rank_message.content)

            await message.channel.send("ID du salon de log :")
            log_message = await client.wait_for('message', check=lambda m: check(m, message.author))
            log_channel_id = int(log_message.content)

            await message.channel.send("TAG à avoir dans le nom d'affichages pour obtenir le rôle :")
            tag_message = await client.wait_for('message', check=lambda m: check(m, message.author))
            rank_tag = tag_message.content

            await message.channel.send("ID du rôle à attribuer :")
            role_message = await client.wait_for('message', check=lambda m: check(m, message.author))
            role_id = int(role_message.content)

            await message.channel.send("Configuration terminée.")
        except ValueError:
            await message.channel.send("Veuillez entrer un ID de salon valide.")
        return

    if message.content.startswith('+create') and is_admin:
        await message.channel.send("Quel type de salon voulez-vous créer ? (Chat ou Vocal)")
        try:
            type_message = await client.wait_for('message', check=lambda m: check(m, message.author))
            salon_type = type_message.content.lower()

            if salon_type not in ["chat", "vocal"]:
                await message.channel.send("Veuillez entrer 'Chat' ou 'Vocal'.")
                return

            await message.channel.send("Quel nom voulez-vous donner au salon ?")
            name_message = await client.wait_for('message', check=lambda m: check(m, message.author))
            salon_name = name_message.content

            await message.channel.send("Souhaitez-vous que ce salon soit privé ? (oui ou non)")
            private_message = await client.wait_for('message', check=lambda m: check(m, message.author))
            is_private = private_message.content.lower() == "oui"

            max_members = None
            if salon_type == "vocal":
                await message.channel.send("Quel est le nombre maximum de personnes dans le salon vocal ?")
                max_members_message = await client.wait_for('message', check=lambda m: check(m, message.author))
                max_members = int(max_members_message.content)

            overwrites = {
                message.guild.default_role: discord.PermissionOverwrite(read_messages=False)
            }

            if is_private:
                for role in message.guild.roles:
                    if role.permissions.administrator:
                        overwrites[role] = discord.PermissionOverwrite(read_messages=True)

            if salon_type == "chat":
                new_channel = await message.guild.create_text_channel(salon_name, overwrites=overwrites)
            else:
                new_channel = await message.guild.create_voice_channel(salon_name, overwrites=overwrites, user_limit=max_members)

            await message.channel.send(f"Le salon **{new_channel.name}** a été créé avec succès.")
        except Exception as e:
            await message.channel.send(f"Une erreur est survenue : {str(e)}")
        return

    if message.content.startswith('+new') and is_admin:
        current_channel = message.channel
        channel_name = current_channel.name
        position = current_channel.position

        await current_channel.delete()  # Supprimer le salon actuel
        new_channel = await message.guild.create_text_channel(channel_name, position=position)  # Créer un nouveau salon
        await new_channel.send(f"{message.author.mention}, le salon a été recréé.")
        return

    if message.content.startswith('+delete') and is_admin:
        await message.channel.send("Veuillez entrer l'ID du salon à supprimer :")
        try:
            delete_message = await client.wait_for('message', check=lambda m: check(m, message.author))
            channel_to_delete = client.get_channel(int(delete_message.content))
            
            if channel_to_delete:
                await channel_to_delete.delete()
                await message.channel.send(f"Le salon **{channel_to_delete.name}** a été supprimé avec succès.")
            else:
                await message.channel.send("Salon non trouvé. Veuillez vérifier l'ID.")
        except Exception as e:
            await message.channel.send(f"Une erreur est survenue : {str(e)}")
        return

    if message.content.startswith('+purge') and is_admin:
        await message.channel.send("Combien de messages souhaitez-vous supprimer ? (entrez un nombre ou 'all' pour tous les messages)")
        try:
            purge_message = await client.wait_for('message', check=lambda m: check(m, message.author))
            if purge_message.content.lower() == "all":
                await message.channel.purge()
                await message.channel.send("Tous les messages ont été supprimés.")
            else:
                number_to_delete = int(purge_message.content)
                deleted_messages = await message.channel.purge(limit=number_to_delete)

                # Enregistrez le dernier message supprimé
                if deleted_messages:
                    last_deleted_message = deleted_messages[-1]
                    last_deleted_time = datetime.datetime.now()  # Enregistrez le temps de suppression

                await message.channel.send(f"{len(deleted_messages)} messages supprimés.")
        except ValueError:
            await message.channel.send("Veuillez entrer un nombre valide ou 'all'.")
        return

    if message.content.startswith('+lock') and is_admin:
        await message.channel.set_permissions(message.guild.default_role, send_messages=False)
        await message.channel.send("Le salon est maintenant verrouillé.")
        return

    if message.content.startswith('+unlock') and is_admin:
        await message.channel.set_permissions(message.guild.default_role, send_messages=True)
        await message.channel.send("Le salon est maintenant déverrouillé.")
        return

    if message.content.startswith('+rankup') and str(message.channel.id) == str(auto_rank_channel_id):
        if rank_tag in message.author.display_name:
            role = discord.utils.get(message.guild.roles, id=role_id)
            logs_channel = client.get_channel(log_channel_id)

            if role:
                if role in message.author.roles:
                    await message.channel.send(f"{message.author.mention}, vous avez déjà le rôle **{role.name}**.")
                else:
                    await message.author.add_roles(role)
                    await message.channel.send(f"{message.author.mention}, vous avez été promu au rôle **{role.name}**!")
                    
                    if logs_channel:
                        await logs_channel.send(f"Le rôle **{role.name}** a été ajouté à {message.author.mention} (ID: {message.author.id})")
            else:
                await message.channel.send("Le rôle spécifié n'existe pas dans ce serveur.")
        else:
            await message.channel.send(f"{message.author.mention}, vous n'avez pas '{rank_tag}' dans votre nom d'affichages.")

    # Commande +mute
    if message.content.startswith('+mute') and is_admin:
        await message.channel.send("Veuillez entrer l'ID de la personne à mute :")
        try:
            user_id_message = await client.wait_for('message', check=lambda m: check(m, message.author))
            user_id = int(user_id_message.content)
            member_to_mute = message.guild.get_member(user_id)

            if not member_to_mute:
                await message.channel.send("Membre non trouvé. Veuillez vérifier l'ID.")
                return

            await message.channel.send("Veuillez entrer la durée du mute en minutes :")
            duration_message = await client.wait_for('message', check=lambda m: check(m, message.author))
            duration_minutes = int(duration_message.content)

            # Création d'un rôle "Muted" si ce n'est pas déjà fait
            muted_role = discord.utils.get(message.guild.roles, name="Muted")
            if not muted_role:
                muted_role = await message.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False, speak=False))

                for channel in message.guild.channels:
                    await channel.set_permissions(muted_role, speak=False, send_messages=False)

            # Attribuer le rôle "Muted" au membre
            await member_to_mute.add_roles(muted_role)
            await message.channel.send(f"{member_to_mute.mention} a été mute pour {duration_minutes} minute(s).")

            # Attendre la durée spécifiée
            await asyncio.sleep(duration_minutes * 60)

            # Retirer le rôle "Muted" après la durée
            await member_to_mute.remove_roles(muted_role)
            await message.channel.send(f"{member_to_mute.mention} a été unmute après {duration_minutes} minute(s).")
        except ValueError:
            await message.channel.send("Veuillez entrer un ID valide ou une durée valide.")
        return

    # Commande +unmute
    if message.content.startswith('+unmute') and is_admin:
        await message.channel.send("Veuillez entrer l'ID de la personne à unmute :")
        try:
            user_id_message = await client.wait_for('message', check=lambda m: check(m, message.author))
            user_id = int(user_id_message.content)
            member_to_unmute = message.guild.get_member(user_id)

            if not member_to_unmute:
                await message.channel.send("Membre non trouvé. Veuillez vérifier l'ID.")
                return

            # Création d'un rôle "Muted" si ce n'est pas déjà fait
            muted_role = discord.utils.get(message.guild.roles, name="Muted")
            if muted_role in member_to_unmute.roles:
                await member_to_unmute.remove_roles(muted_role)
                await message.channel.send(f"{member_to_unmute.mention} a été unmute avec succès.")
            else:
                await message.channel.send(f"{member_to_unmute.mention} n'est pas mute.")
        except ValueError:
            await message.channel.send("Veuillez entrer un ID valide.")
        return

    if message.content.startswith('+help'):
        embed = discord.Embed(title="Help Command", color=0x800080)  # Couleur violet
        embed.add_field(name="**Modération**", value="", inline=False)
        embed.add_field(name="+lock", value="Verrouille le salon.", inline=False)
        embed.add_field(name="+unlock", value="Déverrouille le salon.", inline=False)
        embed.add_field(name="+purge", value="Supprime un nombre spécifié de messages ou tous les messages.", inline=False)
        embed.add_field(name="+delete", value="Supprime un salon en utilisant son ID.", inline=False)
        embed.add_field(name="+mute", value="Mute un membre pour une durée spécifiée.", inline=False)
        embed.add_field(name="+unmute", value="Unmute un membre.", inline=False)  # Ajout de l'aide pour +unmute

        embed.add_field(name="**Channel**", value="", inline=False)
        embed.add_field(name="+create", value="Crée un nouveau salon (Chat ou Vocal).", inline=False)
        embed.add_field(name="+new", value="Recrée le salon actuel.", inline=False)

        embed.add_field(name="**Auto Rank**", value="", inline=False)
        embed.add_field(name="+autorank-setup", value="Configure l'auto-rank pour le serveur.", inline=False)
        embed.add_field(name="+rankup", value="Attribue le rôle spécifié si le TAG est dans votre nom.", inline=False)

        embed.add_field(name="**Autre**", value="", inline=False)
        embed.add_field(name="+help", value="Affiche cette aide.", inline=False)

        await message.channel.send(embed=embed)

client.run(token)
