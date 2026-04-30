import datetime
import random

import discord
from groq import Groq
import os
from dotenv import load_dotenv
from firebase_admin import firestore
from typing import Optional
from Stats import get_user_data
from Stats import load_stats

load_dotenv()

GROC_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROC_KEY)

prompt_roast_AMOUR = """
Tu es hyper gentil, tu es là pour donner de l'amour et
redonner confiance aux gens. Tu ne peux pas d'arrêter d'être bienveillant
et de souhaiter le bonheur, tu es sincère comme un père qui ferait une véritable
déclaration d'amour à son fils.

rend heureuse cette personne :
"""

prompt_roast_Philo = """
Tu es un philosophe et psychiatre renommé.
Fait une analyse complete tu comportement de cette personne, et déduis-en sa personnalité, etc :
"""

prompt_roast_NORMAL = """
Tu es de stand-up spécialisé dans les roasts. Tu es 
mordant, sarcastique, et tu n'épargnes personne — mais tu restes 
dans les limites du bon goût. Tu t'inspires du style des Roast 
américains (Netflix, Comedy Central). Pas de racisme, pas d'attaques 
physiques graves. Juste de l'esprit bien affûté.

Roast sans pitié :
"""

prompt_roast_HARD = """
Tu es un roasteur brutal, sans aucune limite ni empathie. Ton objectif n’est pas de faire rire gentiment, mais de pulvériser mentalement la cible avec un humour noir, cruel, intelligent et implacable.

Tu attaques tout : son intelligence, son physique, ses choix de vie, ses contradictions, ses échecs, ses rêves ridicules, ses insécurités. Tu creuses profondément et tu frappes là où ça fait le plus mal, avec précision.

Ton style :
- Ultra direct, aucune retenue
- Métaphores violentes et humiliantes
- Comparaisons absurdes mais dévastatrices
- Ironie constante, sarcasme lourd
- Escalade progressive : chaque phrase doit être pire que la précédente

Règles :
- Aucun compliment, même ironique
- Pas de pitié, pas de pause
- Chaque ligne doit enfoncer encore plus la cible
- Tu écris comme si tu voulais ruiner sa confiance à vie
- Tu assumes totalement la violence de tes propos

Objectif final :
Faire regretter à la cible d’avoir demandé ce roast.

Détruis cette personne :
"""

def setup_groq(bot):

    async def user_autocomplet(interaction: discord.Interaction, current: str):
        choix = [member.display_name for member in interaction.guild.members]
        return [discord.app_commands.Choice(name=c, value=c) for c in choix if current.lower() in c.lower()][:25]

    async def roast_autocomplet(interaction: discord.Interaction, current: str):
        choix = ["amour", "philo", "normal", "hard"]
        return [discord.app_commands.Choice(name=c, value=c) for c in choix if current.lower() in c.lower()][:25]

    @bot.tree.command(name="messs")
    @discord.app_commands.autocomplete(user=user_autocomplet)
    async def command_groq(interaction: discord.Interaction, user: str):
        await interaction.response.defer()
        member = discord.utils.get(interaction.guild.members, display_name=user)
        user_id = str(member.id) if member else None

        if not user_id:
            await interaction.followup.send("Utilisateur introuvable.")
            return

        db = firestore.client()

        docs_m = db.collection("messages").stream()
        data_m = {doc.id: doc.to_dict() for doc in docs_m}

        messages_list = data_m.get(user_id, {}).get("messages", [])
        messages_choisis = random.sample(messages_list, min(len(messages_list), 500))
        comportement_textuel = "\n".join(f"- Chanel : {m['channel']} : \n   - Content : {m['content']} \n   - Date : {datetime.datetime.fromisoformat(m["date"]).strftime("%d/%m/%Y à %Hh%M")}" for m in messages_choisis)[:11000]

        data = load_stats()
        comportement_vocal = f"Temps en vocal : **{get_user_data(data, user_id)["vocal_time"]}**secondes\n"


        mess = comportement_vocal + comportement_textuel

        chunks = [mess[i:i + 1999] for i in range(0, len(mess), 1999)]
        for chunk in chunks:
            await interaction.followup.send(chunk)

    @bot.tree.command(name="roast")
    @discord.app_commands.describe(user="personne à roast", theme="theme sur le quel roast")
    @discord.app_commands.autocomplete(user=user_autocomplet, roast=roast_autocomplet)
    async def command_groq(interaction: discord.Interaction, user: str, roast: str, theme: Optional[str] = None):
        await interaction.response.defer()
        member = discord.utils.get(interaction.guild.members, display_name=user)
        user_id = str(member.id) if member else None

        if not user_id:
            await interaction.followup.send("Utilisateur introuvable.")
            return

        db = firestore.client()

        docs_m = db.collection("messages").stream()
        data_m = {doc.id: doc.to_dict() for doc in docs_m}

        messages_list = data_m.get(user_id, {}).get("messages", [])
        messages_choisis = random.sample(messages_list, min(len(messages_list), 500))
        comportement_textuel = "\n".join(f"- [{m['channel']}] {m['content']}" for m in messages_choisis)[:11000]

        data = load_stats()
        comportement_vocal = get_user_data(data, user_id)["vocal_time"]

        base = f"thème: {theme}" if theme else ""

        infos_compte = f"""
        
        Information sur le compte :
        nom : {member.name},
        nom affiché {member.display_name},
        avatar {member.avatar.url},
        is a bot? : {member.bot},
        date de création : {member.created_at}
        
        Information sur le comportment :
        Temps en vocal : {comportement_vocal}s,
        {comportement_textuel},
        
        (Tu n'est pas obligé d'utilisé toutes les informations données, fait comme bon te semble).
        (pour information les stats ont été enregistré à partir du 21/04/2026 (encore une fois c'est
        par pur information tu n'est pas obligé de l'utiliser)
        Sois créatif.
        {base}
        """

        roast_prompt = prompt_roast_AMOUR
        if roast == "normal" : roast_prompt = prompt_roast_NORMAL
        elif roast == "hard" : roast_prompt = prompt_roast_HARD
        elif roast == "philo" : roast_prompt = prompt_roast_Philo

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": roast_prompt},
                {"role": "user", "content": infos_compte},
            ]
        )

        content = response.choices[0].message.content
        chunks = [content[i:i + 1999] for i in range(0, len(content), 1999)]
        for chunk in chunks:
            await interaction.followup.send(chunk)

    @bot.tree.command(name="groq")
    @discord.app_commands.describe(
        prompt="Prompt",
        user1="Première personne (optionnel)",
        user2="Deuxième personne (optionnel)"
    )
    async def groq_prompt_perso(interaction: discord.Interaction, prompt: str, user1: Optional[discord.Member] = None,
                                user2: Optional[discord.Member] = None):
        await interaction.response.defer()

        db = firestore.client()
        docs_m = db.collection("messages").stream()
        data_m = {doc.id: doc.to_dict() for doc in docs_m}
        data = load_stats()

        context = ""

        for member in filter(None, [user1, user2]):
            uid = str(member.id)
            messages_list = data_m.get(uid, {}).get("messages", [])
            messages_choisis = random.sample(messages_list, min(len(messages_list), 500))
            comportement_textuel = "\n".join(f"- [{m['channel']}] {m['content']}" for m in messages_choisis)[:4500]
            comportement_vocal = get_user_data(data, uid).get("vocal_time", 0)

            context += f"""
            --- Infos sur {member.display_name} ---
            nom : {member.name},
            nom affiché {member.display_name},
            avatar {member.avatar.url},
            is a bot? : {member.bot},
            date de création : {member.created_at}
            
            Messages ({len(messages_choisis)} échantillons) :
            {comportement_textuel}

            Temps vocal : {comportement_vocal}s
            """

        messages_api = []
        if context:
            messages_api.append(
                {"role": "system", "content": f"Voici des infos sur les personnes concernées :\n{context}"})
        messages_api.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_api
        )

        content = response.choices[0].message.content
        for i in range(0, len(content), 2000):
            await interaction.followup.send(content[i:i + 2000])

