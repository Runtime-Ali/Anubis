from datetime import datetime, timedelta

from discord.ext import commands

from database import get_guild_settings, get_user, add_user, update_user_xp, get_guild_rewards, get_ignored_channels


def calculate_level(guild_id, xp):
    guild = get_guild_settings(guild_id)
    base = guild[2]
    modifier = guild[3]
    i = 0
    while True:
        xp_needed = base + (round(base * (modifier / 100) * i) * i)
        if xp < xp_needed:
            return i + 1
        i += 1


def calculate_xp_needed(guild_id, level):
    guild = get_guild_settings(guild_id)
    base = guild[2]
    modifier = guild[3]
    level -= 2
    if level == 0:
        return 0
    else:
        return base + (round(base * (modifier / 100) * level) * level)


class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        ignored_channels = get_ignored_channels(message.guild.id)
        if message.author.bot:
            pass
        elif message.channel.id in ignored_channels:
            pass
        else:
            guild = get_guild_settings(message.guild.id)
            text_time = timedelta(minutes=guild[1])
            amount = guild[4]
            timeout = datetime.utcnow() + text_time
            user = get_user(message.author.id, message.guild.id)
            if user is None:
                new_user = (message.guild.id, message.author.id, 0, timeout, False)
                add_user(new_user)
                user = get_user(message.author.id, message.guild.id)
            next_xp_time = datetime.strptime(user[3], "%Y-%m-%d %H:%M:%S.%f")
            if user[4]:
                pass
            elif next_xp_time < datetime.utcnow():
                new_xp = user[2] + amount
                update_user_xp(message.author.id, message.guild.id, new_xp, timeout)
                user_level = calculate_level(message.guild.id, new_xp)
                rewards = get_guild_rewards(message.guild.id)
                if len(rewards) > 0:
                    for reward in rewards:
                        for role in message.author.roles:
                            if reward[1] == role.id:
                                pass
                            elif reward[2] < user_level:
                                role = message.guild.get_role(reward[1])
                                await message.author.add_roles(role)