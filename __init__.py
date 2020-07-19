from datetime import datetime

import discord
from discord.ext import commands

import database as db
from leveling import Leveling, calculate_level, calculate_xp_needed

bot = commands.Bot(command_prefix=">")

db.init_db()
bot.add_cog(Leveling(bot))


def has_permissions():
    def predicate(ctx):
        return ctx.author.guild_permissions.manage_messages is True

    return commands.check(predicate)


def is_number(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


@bot.event
async def on_ready():
    for guild in bot.guilds:
        fetched_guild = db.get_guild_settings(guild.id)
        if fetched_guild is None:
            new_guild = (guild.id, 3, 15, 50, 5, 0, 0)
            db.add_guild_settings(new_guild)


@bot.event
async def on_guild_join(guild):
    fetched_guild = db.get_guild_settings(guild.id)
    if fetched_guild is None:
        new_guild = (guild.id, 3, 15, 50, 5, 0, 0)
        db.add_guild_settings(new_guild)


@bot.command()
async def ping(ctx):
    embed = discord.Embed(
        title="**Ping**", description=f"Pong! {round(bot.latency * 1000)}ms"
    )
    embed.set_author(name=f"{bot.user.name}", icon_url=bot.user.avatar_url)
    await ctx.send(embed=embed)


@commands.check_any(has_permissions())
@bot.command()
async def reward(ctx, role, role_level):
    strip = ["<", ">", "#", "@", "!", "&"]
    str_role = role.lower()

    for item in strip:
        str_role = str_role.strip(item)
    reward_role = ctx.guild.get_role(int(str_role))
    if reward_role is None:
        await ctx.send("That is not a valid role")
    elif is_number(role_level) is False:
        await ctx.send("Please enter a valid number for level")
    else:
        retrieved_reward = db.get_single_guild_reward(ctx.guild.id, reward_role.id)
        if retrieved_reward is None:
            db.add_guild_reward(ctx.guild.id, reward_role.id, role_level)
            await ctx.send(f"Added {reward_role.mention} reward at level {role_level}")
        else:
            list_reward = list(retrieved_reward)
            list_reward[2] = role_level
            db.update_guild_reward(list_reward)
            await ctx.send(f"Updated {reward_role.mention} reward to level {role_level}")


@commands.check_any(has_permissions())
@bot.command()
async def remove(ctx, role):
    strip = ["<", ">", "#", "@", "!", "&"]
    str_role = role.lower()
    for item in strip:
        str_role = str_role.strip(item)
    reward_role = ctx.guild.get_role(int(str_role))
    if reward_role is None:
        await ctx.send("That is not a valid role")
    else:
        db.delete_guild_reward(ctx.guild.id, reward_role.id)
        await ctx.send(f"Removed {reward_role.mention} reward")


@commands.check_any(has_permissions())
@bot.command()
async def levelset(ctx, setting="view", value="view"):
    strip = ["<", ">", "#", "@", "!", "&"]
    str_value = value.lower()
    for item in strip:
        str_value = str_value.strip(item)
    if value == "view":
        guild = db.get_guild_settings(ctx.guild.id)
        user_channel = ctx.guild.get_channel(guild[5])
        if user_channel is None:
            user_channel = "None"
        else:
            user_channel = user_channel.mention
        log_channel = ctx.guild.get_channel(guild[6])
        if log_channel is None:
            log_channel = "None"
        else:
            log_channel = log_channel.mention
        embed = discord.Embed(title="Current Level System settings",
                              description=(
                                  f'**Texttime:** {guild[1]}\n'
                                  f'**Base:** {guild[2]}\n'
                                  f'**Modifier:** {guild[3]}\n'
                                  f'**Amount:** {guild[4]}\n'
                                  f'**User-Channel:** {user_channel}\n'
                                  f'**Log-Channel:** {log_channel}\n'
                              ))
        await ctx.send(embed=embed)
    elif is_number(str_value) is False:
        await ctx.send("please enter a valid number for the value")
    elif setting.lower() == "texttime":
        db.update_text_time(str_value, ctx.guild.id)
        await ctx.send(f"texttime now set to {str_value} minutes.")
    elif setting.lower() == "base":
        db.update_base(str_value, ctx.guild.id)
        await ctx.send(f"Base XP now set to {str_value}.")
    elif setting.lower() == "modifier":
        db.update_modifier(str_value, ctx.guild.id)
        await ctx.send(f"Modifier now set to {str_value}.")
    elif setting.lower() == "amount":
        db.update_amount(str_value, ctx.guild.id)
        await ctx.send(f"XP Amount now set to {str_value} per valid message.")
    elif setting.lower() == "user-channel":
        user_channel = ctx.guild.get_channel(int(str_value))
        if int(str_value) == 0:
            db.update_channel(str_value, ctx.guild.id)
            await ctx.send(f"User channel disabled.")
        elif user_channel is None:
            await ctx.send("Please enter a valid channel.")
        else:
            db.update_channel(user_channel.id, ctx.guild.id)
            await ctx.send(f"User channel now set to {user_channel.mention}.")
    elif setting.lower() == "log-channel":
        log_channel = ctx.guild.get_channel(int(str_value))
        if int(str_value) == 0:
            db.update_channel(str_value, ctx.guild.id)
            await ctx.send(f"Log Channel disabled.")
        elif log_channel is None:
            await ctx.send("Please enter a valid channel.")
        else:
            db.update_log_channel(log_channel.id, ctx.guild.id)
            await ctx.send(f"Log Channel now set to {log_channel.mention}.")


@bot.command()
async def level(ctx, user="me"):
    guild = db.get_guild_settings(ctx.guild.id)
    if ctx.author.guild_permissions.manage_messages or ctx.channel.id == guild[5] or guild[5] == 0:
        if user == "me":
            str_user = f'{ctx.author.id}'
        else:
            str_user = user
        strip = ["<", ">", "#", "@", "!", "&"]
        for item in strip:
            str_user = str_user.strip(item)
        user = ctx.guild.get_member(int(str_user))
        if user is None:
            await ctx.send("Please enter a valid user.")
        else:
            retrieved_user = db.get_user(user.id, ctx.guild.id)
            user_level = calculate_level(retrieved_user[0], retrieved_user[2])
            rewards = db.get_guild_rewards(ctx.guild.id)
            next_reward = (ctx.guild.id, 0, 0)
            for reward1 in rewards:
                if reward1[2] < user_level:
                    pass
                elif reward1[2] < next_reward[2] or next_reward[2] == 0:
                    next_reward = reward1

            role_reward = ctx.guild.get_role(next_reward[1])
            xp_current_level = calculate_xp_needed(ctx.guild.id, user_level)
            xp_next_level = calculate_xp_needed(ctx.guild.id, (user_level + 1))
            level_progress = retrieved_user[2] - xp_current_level
            xp_between = xp_next_level - xp_current_level
            embed = discord.Embed(title=f"Level and EXP for {user.nick}",
                                  color=user.color)
            embed.add_field(name="XP", value=f"{retrieved_user[2]}", inline=True)
            embed.add_field(name="Level", value=f"{user_level}", inline=True)
            embed.add_field(name="Progress", value=f"{level_progress}/{xp_between}", inline=True)
            if next_reward[1] == 0:
                embed.add_field(name="Next Reward", value=f"None",
                                inline=True)
            else:
                embed.add_field(name="Next Reward", value=f"{role_reward.mention}\n at level {next_reward[2]}",
                                inline=True)
            embed.set_thumbnail(url=user.avatar_url)
            embed.set_footer(text=f"{ctx.guild.name}", icon_url=ctx.guild.icon_url)
            await ctx.send(embed=embed)


@bot.command()
async def leaderboard(ctx, user="all"):
    guild = db.get_guild_settings(ctx.guild.id)
    if ctx.author.guild_permissions.manage_messages or ctx.channel.id == guild[5] or guild[5] == 0:
        ranked_users = db.get_ranked_users(ctx.guild.id)
        if user.lower() == "all":
            leader_board_text = ""
            i = 0
            while i < 10 and i < len(ranked_users):
                retrieved_user = ctx.guild.get_member(ranked_users[i][1])
                leader_board_text += f"**{i + 1}** {retrieved_user.mention} **XP:** {ranked_users[i][2]}\n"
                i += 1
            embed = discord.Embed(title="LeaderBoard", description=leader_board_text, color=0xFAD766)
            embed.set_footer(text=f"Total Users {len(ranked_users)}")
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)
        if user.lower() == "me":
            requesting_user = db.get_user(ctx.author.id, ctx.guild.id)
            leader_board_text = ""
            i = 0
            user_index = ranked_users.index(requesting_user)
            if user_index - 4 < 0:
                start_index = 0
            else:
                start_index = user_index - 4

            while i < 9 and i < len(ranked_users) and start_index < len(ranked_users):
                retrieved_user = ctx.guild.get_member(ranked_users[start_index][1])
                leader_board_text += f"**{start_index + 1}** {retrieved_user.mention} **XP:** {ranked_users[start_index][2]}\n"
                i += 1
                start_index += 1
            embed = discord.Embed(title="LeaderBoard", description=leader_board_text, color=0xFAD766)
            embed.set_footer(text=f"Total Users {len(ranked_users)}")
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)


@commands.check_any(has_permissions())
@bot.command()
async def award(ctx, user, amount):
    str_user = user.lower()
    strip = ["<", ">", "#", "@", "!", "&"]
    for item in strip:
        str_user = str_user.strip(item)
    user = ctx.guild.get_member(int(str_user))
    if user is None:
        await ctx.send("Please enter a valid user.")
    elif int(amount) < 1:
        await ctx.send("Please enter a positive number.")
    else:
        retrieved_user = db.get_user(user.id, ctx.guild.id)
        new_xp = retrieved_user[2] + int(amount)
        db.update_user_xp(user.id, ctx.guild.id, new_xp, retrieved_user[3])
        await ctx.send(f"{user.mention} has been awarded {amount} xp")


@commands.check_any(has_permissions())
@bot.command()
async def reclaim(ctx, user, amount):
    str_user = user.lower()
    strip = ["<", ">", "#", "@", "!", "&"]
    for item in strip:
        str_user = str_user.strip(item)
    user = ctx.guild.get_member(int(str_user))
    if user is None:
        await ctx.send("Please enter a valid user.")
    else:
        if amount.lower() != "all":
            pass
        elif amount[0] == "-":
            await ctx.send("Please enter a positive number.")
        retrieved_user = db.get_user(user.id, ctx.guild.id)
        if amount.lower() == "all":
            new_xp = 0
        else:
            new_xp = retrieved_user[2] - int(amount)
        db.update_user_xp(user.id, ctx.guild.id, new_xp, retrieved_user[3])
        await ctx.send(f"{user.mention} has had {amount} xp reclaimed")


@commands.check_any(has_permissions())
@bot.command()
async def ignore(ctx, *, arg):
    if len(ctx.message.mentions) > 0:
        mention_list = ""
        for member in ctx.message.mentions:
            db.ignore_user_xp(member.id, ctx.guild.id, True)
            mention_list += f"{member.mention}"
        await ctx.send(f"{mention_list} can no longer gain xp.")
    if len(ctx.message.channel_mentions) > 0:
        mention_list = ""
        for channel in ctx.message.channel_mentions:
            db.add_ignored_channel(ctx.guild.id, channel.id)
            mention_list += f"{channel.mention}"
        await ctx.send(f"Can no longer gain xp in {mention_list}")


@commands.check_any(has_permissions())
@bot.command()
async def recog(ctx, *, arg):
    if len(ctx.message.mentions) > 0:
        mention_list = ""
        for member in ctx.message.mentions:
            db.ignore_user_xp(member.id, ctx.guild.id, False)
            mention_list += f"{member.mention}"
        await ctx.send(f"{mention_list} can no longer gain xp.")
    if len(ctx.message.channel_mentions) > 0:
        mention_list = ""
        for channel in ctx.message.channel_mentions:
            db.delete_ignored_channel(channel.id)
            mention_list += f"{channel.mention}"
        await ctx.send(f"Can gain xp in {mention_list} again")


bot.remove_command("help")


@bot.command()
async def help(ctx):
    await ctx.send(
        "`>award <user> <amount>` grants the user xp amount\n"
        "`>reclaim <user> <amount>` removes xp amount or use all for all xp\n"
        "`>level <user>` displays experience info of specified user. leave blank for self\n"
        "`>reward <role> <level>` adds reward to server at level\n"
        "`>remove <role>` removes reward from server\n"
        "`>ignore <user or channel mention>` ignores xp gain of user or in channel. Can take multiple users and channels at once\n"
        "`>recog <user or channel mention>` restores xp gain to users and channels\n"
        "`>levelset <setting> <value>` sets setting to value. Leave blank for current settings\n"
        "`>leaderboard <me>` show leaderboard. If no argument returns top 10, with me returns 4 above and 4 below you with rank."
    )


with open("token", "r") as f:
    bot.run(f.readline().strip())
